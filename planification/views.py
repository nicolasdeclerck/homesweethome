from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import TemplateView, View

from activites.models import Activite
from activites.services import lister_activites_par_categorie
from foyer.models import MembreFoyer

from .forms import AffectationCreationForm, PeriodeCreationForm
from .models import Affectation, PeriodePlanification
from .services import (
    affectations_par_jour,
    creer_affectation,
    creer_periode,
    lister_periodes,
    supprimer_affectation,
)


def _foyer_du_user(user):
    membre = (
        MembreFoyer.objects.select_related("foyer")
        .filter(user=user)
        .first()
    )
    return membre.foyer if membre else None


class _PlanificationFoyerMixin(LoginRequiredMixin):
    """Garde-fou : l'utilisateur doit appartenir à un foyer.

    Expose ``request.foyer`` aux vues filles. Aligné sur le pattern
    ``_ActivitesFoyerMixin`` (cf. activites/views.py).
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        foyer = _foyer_du_user(request.user)
        if foyer is None:
            return HttpResponseForbidden(
                "Aucun foyer associé à votre compte."
            )
        request.foyer = foyer
        return super().dispatch(request, *args, **kwargs)


def _contexte_liste(foyer):
    periodes = lister_periodes(foyer)
    return {
        "foyer": foyer,
        "periodes": periodes,
        "nb_periodes": len(periodes),
    }


def _contexte_periode_form(form):
    return {
        "form": form,
        "form_action": reverse("planification:periode-create"),
        "submit_label": "Créer",
        "drawer_title": "Nouvelle période",
        "drawer_sub": "Définissez la fenêtre de planification.",
    }


def _contexte_detail(periode, foyer):
    activites_par_categorie = lister_activites_par_categorie(foyer)
    membres = list(foyer.membres.select_related("user").all())
    return {
        "foyer": foyer,
        "periode": periode,
        "affectations_par_jour": affectations_par_jour(periode),
        "activites_par_categorie": activites_par_categorie,
        "membres": membres,
    }


class PeriodesListView(_PlanificationFoyerMixin, TemplateView):
    template_name = "planification/liste.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexte_liste(self.request.foyer))
        context.update(_contexte_periode_form(PeriodeCreationForm()))
        context["active_nav"] = "planification"
        return context


class PeriodesListeFragmentView(_PlanificationFoyerMixin, View):
    template_liste = "planification/_periodes_liste.html"

    def get(self, request):
        contexte = _contexte_liste(request.foyer)
        # Active le span OOB qui rafraîchit le compteur du sous-titre.
        contexte["oob_compteur"] = True
        return render(request, self.template_liste, contexte)


class PeriodeCreateView(_PlanificationFoyerMixin, View):
    template_form = "planification/_periode_form.html"

    def get(self, request):
        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                self.template_form,
                _contexte_periode_form(PeriodeCreationForm()),
            )
        return redirect("planification:periode-liste")

    def post(self, request):
        form = PeriodeCreationForm(request.POST)
        is_htmx = request.headers.get("HX-Request") == "true"

        if not form.is_valid():
            return self._render_form_invalide(request, form, is_htmx)

        try:
            creer_periode(
                foyer=request.foyer,
                date_debut=form.cleaned_data["date_debut"],
                date_fin=form.cleaned_data["date_fin"],
            )
        except ValidationError as exc:
            # Repropage les erreurs de validation modèle (ex. chevauchement)
            # dans le form, puis re-rend le formulaire en 400.
            for message in exc.messages:
                form.add_error(None, message)
            return self._render_form_invalide(request, form, is_htmx)

        if is_htmx:
            response = render(
                request,
                self.template_form,
                _contexte_periode_form(PeriodeCreationForm()),
            )
            response["HX-Trigger"] = "periodes-mises-a-jour"
            return response

        messages.success(request, "Période créée.")
        return redirect("planification:periode-liste")

    def _render_form_invalide(self, request, form, is_htmx):
        if is_htmx:
            return render(
                request,
                self.template_form,
                _contexte_periode_form(form),
                status=400,
            )
        contexte = _contexte_liste(request.foyer)
        contexte.update(_contexte_periode_form(form))
        contexte["active_nav"] = "planification"
        return render(
            request, "planification/liste.html", contexte, status=400
        )


def _periode_du_foyer(request, periode_id):
    return get_object_or_404(
        PeriodePlanification, pk=periode_id, foyer=request.foyer
    )


class PeriodeDetailView(_PlanificationFoyerMixin, View):
    template_name = "planification/detail.html"

    def get(self, request, periode_id):
        periode = _periode_du_foyer(request, periode_id)
        contexte = _contexte_detail(periode, request.foyer)
        contexte["active_nav"] = "planification"
        return render(request, self.template_name, contexte)


class AffectationsListeFragmentView(_PlanificationFoyerMixin, View):
    template_liste = "planification/_affectations_liste.html"

    def get(self, request, periode_id):
        periode = _periode_du_foyer(request, periode_id)
        return render(
            request,
            self.template_liste,
            _contexte_detail(periode, request.foyer),
        )


class AffectationCreateView(_PlanificationFoyerMixin, View):
    def post(self, request, periode_id):
        periode = _periode_du_foyer(request, periode_id)
        form = AffectationCreationForm(request.POST)

        if not form.is_valid():
            # Le form rejette les types invalides (ID non entier, date
            # malformée). Pas de cas légitime côté UI : on renvoie 400
            # sans formulaire dédié.
            return render(
                request,
                "planification/_affectations_liste.html",
                _contexte_detail(periode, request.foyer),
                status=400,
            )

        activite = get_object_or_404(
            Activite,
            pk=form.cleaned_data["activite_id"],
            foyer=request.foyer,
        )
        membre = get_object_or_404(
            MembreFoyer,
            pk=form.cleaned_data["membre_id"],
            foyer=request.foyer,
        )

        try:
            creer_affectation(
                periode=periode,
                activite=activite,
                membre=membre,
                jour=form.cleaned_data["jour"],
            )
        except ValidationError:
            # Jour hors période : rendu inchangé en 400.
            return render(
                request,
                "planification/_affectations_liste.html",
                _contexte_detail(periode, request.foyer),
                status=400,
            )

        return render(
            request,
            "planification/_affectations_liste.html",
            _contexte_detail(periode, request.foyer),
        )


class AffectationDeleteView(_PlanificationFoyerMixin, View):
    def post(self, request, affectation_id):
        # Filtre par foyer : 404 transparente si l'affectation n'appartient
        # pas au foyer courant (évite de leaker l'existence).
        affectation = get_object_or_404(
            Affectation,
            pk=affectation_id,
            periode__foyer=request.foyer,
        )
        periode = affectation.periode
        supprimer_affectation(affectation)
        return render(
            request,
            "planification/_affectations_liste.html",
            _contexte_detail(periode, request.foyer),
        )
