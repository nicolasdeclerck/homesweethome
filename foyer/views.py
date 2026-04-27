from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, View

from .forms import AccepterInvitationNouveauCompteForm, InvitationCreationForm
from .models import Invitation, MembreFoyer
from .services import (
    EmailDansAutreFoyerError,
    EmailDejaMembreError,
    InvitationDejaEnAttenteError,
    InvitationInvalideError,
    accepter_invitation,
    annuler_invitation,
    creer_invitation,
    get_invitation_utilisable,
    get_or_create_foyer_for_user,
)


def _build_lien_invitation(request, invitation: Invitation) -> str:
    chemin = reverse("foyer:invitation-accepter", kwargs={"token": invitation.token})
    return request.build_absolute_uri(chemin)


def _membre_foyer_du_user(user):
    return (
        MembreFoyer.objects.select_related("foyer", "foyer__cree_par")
        .filter(user=user)
        .first()
    )


class MonFoyerView(LoginRequiredMixin, TemplateView):
    template_name = "foyer/mon_foyer.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        foyer = get_or_create_foyer_for_user(self.request.user)
        est_createur = foyer.cree_par_id == self.request.user.pk
        context["foyer"] = foyer
        context["membres"] = foyer.membres.select_related("user").all()
        context["est_createur"] = est_createur
        if est_createur:
            context["invitation_form"] = InvitationCreationForm()
            context["invitations_en_attente"] = self._invitations_en_attente(foyer)
        return context

    @staticmethod
    def _invitations_en_attente(foyer):
        return list(
            foyer.invitations.filter(statut=Invitation.Statut.EN_ATTENTE).order_by(
                "-date_creation"
            )
        )


class _CreateurFoyerRequiredMixin(LoginRequiredMixin):
    """Garde-fou : seul le créateur d'un foyer accède à ces vues."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        membre = _membre_foyer_du_user(request.user)
        if membre is None or membre.foyer.cree_par_id != request.user.pk:
            return HttpResponseForbidden(
                "Seul le créateur du foyer peut effectuer cette action."
            )
        request.foyer = membre.foyer
        return super().dispatch(request, *args, **kwargs)


class InvitationCreateView(_CreateurFoyerRequiredMixin, View):
    template_form = "foyer/_invitation_form.html"
    template_lien = "foyer/_invitation_lien.html"

    def get(self, request):
        return render(
            request,
            self.template_form,
            {"invitation_form": InvitationCreationForm()},
        )

    def post(self, request):
        form = InvitationCreationForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_form,
                {"invitation_form": form},
                status=400,
            )

        try:
            invitation = creer_invitation(
                foyer=request.foyer,
                email=form.cleaned_data["email"],
                prenom=form.cleaned_data["prenom"],
                cree_par=request.user,
            )
        except InvitationDejaEnAttenteError as exc:
            response = render(
                request,
                self.template_lien,
                {
                    "invitation": exc.invitation,
                    "lien": _build_lien_invitation(request, exc.invitation),
                    "deja_en_attente": True,
                },
            )
            response["HX-Trigger"] = "invitations-mises-a-jour"
            return response
        except (EmailDejaMembreError, EmailDansAutreFoyerError) as exc:
            form.add_error("email", str(exc))
            return render(
                request,
                self.template_form,
                {"invitation_form": form},
                status=400,
            )

        response = render(
            request,
            self.template_lien,
            {
                "invitation": invitation,
                "lien": _build_lien_invitation(request, invitation),
                "deja_en_attente": False,
            },
        )
        response["HX-Trigger"] = "invitations-mises-a-jour"
        return response


class InvitationsListeView(_CreateurFoyerRequiredMixin, View):
    template_liste = "foyer/_invitation_liste.html"

    def get(self, request):
        invitations = list(
            request.foyer.invitations.filter(
                statut=Invitation.Statut.EN_ATTENTE,
            ).order_by("-date_creation")
        )
        return render(
            request,
            self.template_liste,
            {"invitations_en_attente": invitations, "foyer": request.foyer},
        )


class InvitationLinkView(_CreateurFoyerRequiredMixin, View):
    template_lien = "foyer/_invitation_lien.html"

    def get(self, request, pk):
        invitation = get_object_or_404(
            Invitation,
            pk=pk,
            foyer=request.foyer,
            statut=Invitation.Statut.EN_ATTENTE,
        )
        return render(
            request,
            self.template_lien,
            {
                "invitation": invitation,
                "lien": _build_lien_invitation(request, invitation),
                "deja_en_attente": False,
            },
        )


class InvitationCancelView(_CreateurFoyerRequiredMixin, View):
    template_liste = "foyer/_invitation_liste.html"

    def post(self, request, pk):
        invitation = get_object_or_404(
            Invitation,
            pk=pk,
            foyer=request.foyer,
        )
        try:
            annuler_invitation(invitation, par_user=request.user)
        except InvitationInvalideError:
            pass  # invitation déjà acceptée/annulée → on renvoie la liste à jour

        invitations = list(
            request.foyer.invitations.filter(
                statut=Invitation.Statut.EN_ATTENTE,
            ).order_by("-date_creation")
        )
        response = render(
            request,
            self.template_liste,
            {"invitations_en_attente": invitations, "foyer": request.foyer},
        )
        response["HX-Trigger"] = "invitations-mises-a-jour"
        return response


class AccepterInvitationView(View):
    template_page = "foyer/accepter_invitation.html"
    template_invalide = "foyer/invitation_invalide.html"
    success_url = reverse_lazy("foyer:mon-foyer")

    def get(self, request, token):
        invitation = get_invitation_utilisable(token)
        if invitation is None:
            return render(request, self.template_invalide, status=410)
        return render(
            request,
            self.template_page,
            self._contexte_acceptation(request, invitation),
        )

    def post(self, request, token):
        invitation = get_invitation_utilisable(token)
        if invitation is None:
            return render(request, self.template_invalide, status=410)

        scenario = self._scenario(request, invitation)

        if scenario == "user_existant_connecte":
            try:
                accepter_invitation(invitation=invitation, user_existant=request.user)
            except InvitationInvalideError as exc:
                return render(
                    request,
                    self.template_page,
                    self._contexte_acceptation(request, invitation, erreur=str(exc)),
                    status=400,
                )
            return redirect(self.success_url)

        if scenario == "user_existant_non_connecte":
            return redirect(self._login_redirect_url(invitation))

        if scenario == "user_existant_mauvais_compte":
            return render(
                request,
                self.template_page,
                self._contexte_acceptation(request, invitation),
                status=400,
            )

        # Nouveau compte
        form = AccepterInvitationNouveauCompteForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_page,
                self._contexte_acceptation(
                    request, invitation, password_form=form
                ),
                status=400,
            )
        try:
            user = accepter_invitation(
                invitation=invitation,
                nouveau_password=form.cleaned_data["password"],
            )
        except InvitationInvalideError as exc:
            return render(
                request,
                self.template_page,
                self._contexte_acceptation(request, invitation, erreur=str(exc)),
                status=400,
            )

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect(self.success_url)

    @staticmethod
    def _scenario(request, invitation: Invitation) -> str:
        User = get_user_model()
        compte_existant = User.objects.filter(email__iexact=invitation.email).first()

        if request.user.is_authenticated:
            if compte_existant is not None and compte_existant.pk == request.user.pk:
                return "user_existant_connecte"
            return "user_existant_mauvais_compte"

        if compte_existant is not None:
            return "user_existant_non_connecte"
        return "nouveau"

    @staticmethod
    def _login_redirect_url(invitation: Invitation) -> str:
        accept_path = reverse(
            "foyer:invitation-accepter", kwargs={"token": invitation.token}
        )
        return reverse("comptes:connexion") + "?next=" + accept_path

    def _contexte_acceptation(
        self,
        request,
        invitation: Invitation,
        *,
        password_form=None,
        erreur: str | None = None,
    ):
        scenario = self._scenario(request, invitation)
        contexte = {
            "invitation": invitation,
            "scenario": scenario,
            "erreur": erreur,
        }
        if scenario == "nouveau":
            contexte["password_form"] = (
                password_form or AccepterInvitationNouveauCompteForm()
            )
        if scenario == "user_existant_non_connecte":
            contexte["login_url"] = self._login_redirect_url(invitation)
        return contexte
