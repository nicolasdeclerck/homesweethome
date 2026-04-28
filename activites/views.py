from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import TemplateView, View

from evaluations.services import (
    enregistrer_evaluation,
    get_evaluation,
    get_evaluation_autre_membre,
)
from foyer.models import MembreFoyer

from .forms import ActiviteCreationForm
from .models import Activite
from .services import (
    creer_activite,
    lister_activites_par_categorie,
    mettre_a_jour_activite,
)


def _foyer_du_user(user):
    membre = (
        MembreFoyer.objects.select_related("foyer")
        .filter(user=user)
        .first()
    )
    return membre.foyer if membre else None


class _ActivitesFoyerMixin(LoginRequiredMixin):
    """Garde-fou : l'utilisateur doit appartenir à un foyer.

    Expose `request.foyer` aux vues filles. En pratique, le signal
    `post_save(User)` crée toujours un foyer pour chaque user, mais on
    garde ce filet de sécurité (équivalent du pattern `_CreateurFoyerRequiredMixin`).
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


def _contexte_liste(foyer, *, user=None):
    """Contexte partagé entre la vue page et le fragment de liste.

    Quand `user` est fourni, chaque `Activite` est annotée avec
    `evaluee_par_user` (cf. `lister_activites_par_categorie`) — utilisé
    pour rendre le label « Évaluée » / « À évaluer » à droite de chaque
    ligne.
    """
    activites_par_categorie = lister_activites_par_categorie(foyer, user=user)
    nb_activites = sum(len(v) for v in activites_par_categorie.values())
    return {
        "foyer": foyer,
        "activites_par_categorie": activites_par_categorie,
        "categories_existantes": list(
            foyer.categories.order_by("nom").values_list("nom", flat=True)
        ),
        "nb_activites": nb_activites,
    }


def _contexte_form(foyer, form, *, activite=None, user=None):
    """Contexte rendu par `_activite_form.html`, pour création ou édition.

    Quand `activite` est None on est en création : action vers
    `activite-create`, libellé « Ajouter ». Sinon on cible la vue de
    modification de cette activité, avec le libellé « Enregistrer », et
    on expose l'évaluation de l'autre membre du foyer (lecture seule).
    """
    if activite is None:
        form_action = reverse("activites:activite-create")
        submit_label = "Ajouter"
        drawer_title = "Nouvelle activité"
        drawer_sub = "Ajoutez une tâche récurrente du foyer."
        autre_membre, evaluation_autre = None, None
    else:
        form_action = reverse(
            "activites:activite-modifier",
            kwargs={"activite_id": activite.pk},
        )
        submit_label = "Enregistrer"
        drawer_title = "Modifier l'activité"
        drawer_sub = "Ajustez le titre, la catégorie et votre évaluation."
        autre_membre, evaluation_autre = get_evaluation_autre_membre(
            foyer=foyer, activite=activite, user=user
        )
    return {
        "form": form,
        "activite": activite,
        "categories_existantes": list(
            foyer.categories.order_by("nom").values_list("nom", flat=True)
        ),
        "form_action": form_action,
        "submit_label": submit_label,
        "drawer_title": drawer_title,
        "drawer_sub": drawer_sub,
        "autre_membre": autre_membre,
        "evaluation_autre": evaluation_autre,
    }


def _initial_form(activite, user):
    """Pré-remplit le form d'édition avec l'évaluation existante de `user`."""
    initial = {
        "titre": activite.titre,
        "categorie_nom": activite.categorie.nom,
    }
    evaluation = get_evaluation(user=user, activite=activite)
    if evaluation is not None:
        initial.update({
            "charge_mentale": evaluation.charge_mentale,
            "charge_physique": evaluation.charge_physique,
            "duree": evaluation.duree,
        })
    return initial


class ActivitesListView(_ActivitesFoyerMixin, TemplateView):
    template_name = "activites/liste.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexte_liste(self.request.foyer, user=self.request.user))
        # Le drawer initial est en mode "création".
        context.update(
            _contexte_form(
                self.request.foyer,
                ActiviteCreationForm(),
                user=self.request.user,
            )
        )
        context["active_nav"] = "activites"
        return context


class ActiviteCreateView(_ActivitesFoyerMixin, View):
    template_form = "activites/_activite_form.html"

    def get(self, request):
        # Sur GET HTMX (ex. réinitialisation du drawer après une édition),
        # on renvoie un fragment "création" frais. Hors HTMX, on garde le
        # comportement existant (redirect vers la liste).
        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                self.template_form,
                _contexte_form(
                    request.foyer, ActiviteCreationForm(), user=request.user
                ),
            )
        return redirect("activites:activite-liste")

    def post(self, request):
        form = ActiviteCreationForm(request.POST)
        is_htmx = request.headers.get("HX-Request") == "true"

        if not form.is_valid():
            if is_htmx:
                return render(
                    request,
                    self.template_form,
                    _contexte_form(request.foyer, form, user=request.user),
                    status=400,
                )
            context = _contexte_liste(request.foyer, user=request.user)
            context.update(_contexte_form(request.foyer, form, user=request.user))
            context["active_nav"] = "activites"
            return render(request, "activites/liste.html", context, status=400)

        activite = creer_activite(
            foyer=request.foyer,
            titre=form.cleaned_data["titre"],
            categorie_nom=form.cleaned_data["categorie_nom"],
        )
        if form.has_evaluation():
            enregistrer_evaluation(
                user=request.user,
                activite=activite,
                charge_mentale=form.cleaned_data["charge_mentale"],
                charge_physique=form.cleaned_data["charge_physique"],
                duree=form.cleaned_data["duree"],
            )

        if is_htmx:
            response = render(
                request,
                self.template_form,
                _contexte_form(
                    request.foyer, ActiviteCreationForm(), user=request.user
                ),
            )
            response["HX-Trigger"] = "activites-mises-a-jour"
            return response

        messages.success(request, "Activité ajoutée.")
        return redirect(reverse("activites:activite-liste"))


class ActiviteUpdateView(_ActivitesFoyerMixin, View):
    template_form = "activites/_activite_form.html"

    def _activite_du_foyer(self, request, activite_id):
        # Filtre par foyer : 404 transparente si l'activité n'existe pas
        # ou appartient à un autre foyer (évite de leaker l'existence).
        return get_object_or_404(
            Activite, pk=activite_id, foyer=request.foyer
        )

    def get(self, request, activite_id):
        activite = self._activite_du_foyer(request, activite_id)
        if request.headers.get("HX-Request") != "true":
            return redirect("activites:activite-liste")
        form = ActiviteCreationForm(initial=_initial_form(activite, request.user))
        return render(
            request,
            self.template_form,
            _contexte_form(
                request.foyer, form, activite=activite, user=request.user
            ),
        )

    def post(self, request, activite_id):
        activite = self._activite_du_foyer(request, activite_id)
        form = ActiviteCreationForm(request.POST)
        is_htmx = request.headers.get("HX-Request") == "true"

        if not form.is_valid():
            if is_htmx:
                return render(
                    request,
                    self.template_form,
                    _contexte_form(
                        request.foyer, form, activite=activite, user=request.user
                    ),
                    status=400,
                )
            context = _contexte_liste(request.foyer, user=request.user)
            context.update(
                _contexte_form(
                    request.foyer, form, activite=activite, user=request.user
                )
            )
            context["active_nav"] = "activites"
            return render(request, "activites/liste.html", context, status=400)

        mettre_a_jour_activite(
            activite,
            titre=form.cleaned_data["titre"],
            categorie_nom=form.cleaned_data["categorie_nom"],
        )
        if form.has_evaluation():
            enregistrer_evaluation(
                user=request.user,
                activite=activite,
                charge_mentale=form.cleaned_data["charge_mentale"],
                charge_physique=form.cleaned_data["charge_physique"],
                duree=form.cleaned_data["duree"],
            )

        if is_htmx:
            # Réponse en mode "création" pour réinitialiser le drawer
            # avant sa fermeture (HX-Trigger).
            response = render(
                request,
                self.template_form,
                _contexte_form(
                    request.foyer, ActiviteCreationForm(), user=request.user
                ),
            )
            response["HX-Trigger"] = "activites-mises-a-jour"
            return response

        messages.success(request, "Activité modifiée.")
        return redirect(reverse("activites:activite-liste"))


class ActivitesListeFragmentView(_ActivitesFoyerMixin, View):
    template_liste = "activites/_activites_liste.html"

    def get(self, request):
        contexte = _contexte_liste(request.foyer, user=request.user)
        # Active le span OOB qui rafraîchit le compteur du sous-titre.
        contexte["oob_compteur"] = True
        return render(request, self.template_liste, contexte)
