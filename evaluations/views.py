from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import View

from activites.models import Activite
from foyer.models import MembreFoyer

from .forms import EvaluationForm
from .services import (
    enregistrer_evaluation,
    get_evaluation,
    get_evaluation_autre_membre,
)


def _foyer_du_user(user):
    membre = (
        MembreFoyer.objects.select_related("foyer")
        .filter(user=user)
        .first()
    )
    return membre.foyer if membre else None


class _FoyerRequiredMixin(LoginRequiredMixin):
    """Garde-fou : l'utilisateur doit appartenir à un foyer.

    Aligné sur `_ActivitesFoyerMixin` (cf. activites/views.py). Expose
    `request.foyer` aux vues filles.
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


def _initial_from_evaluation(evaluation):
    if evaluation is None:
        return {}
    return {
        "charge_mentale": evaluation.charge_mentale,
        "charge_physique": evaluation.charge_physique,
        "duree": evaluation.duree,
    }


def _contexte_form(*, request, activite, form, succes=False):
    autre_membre, evaluation_autre = get_evaluation_autre_membre(
        foyer=request.foyer, activite=activite, user=request.user
    )
    return {
        "activite": activite,
        "form": form,
        "succes": succes,
        "autre_membre": autre_membre,
        "evaluation_autre": evaluation_autre,
    }


class EvaluationView(_FoyerRequiredMixin, View):
    """Écran P3.1/P3.2 : évaluation d'une activité par l'utilisateur courant."""

    template_page = "evaluations/evaluer.html"
    template_form = "evaluations/_evaluation_form.html"

    def _get_activite(self, request, activite_id):
        # Garde-fou métier : on ne peut évaluer qu'une activité de son foyer.
        return get_object_or_404(Activite, pk=activite_id, foyer=request.foyer)

    def get(self, request, activite_id):
        activite = self._get_activite(request, activite_id)
        evaluation_user = get_evaluation(user=request.user, activite=activite)
        form = EvaluationForm(initial=_initial_from_evaluation(evaluation_user))
        contexte = _contexte_form(request=request, activite=activite, form=form)
        contexte["active_nav"] = "activites"
        return render(request, self.template_page, contexte)

    def post(self, request, activite_id):
        activite = self._get_activite(request, activite_id)
        form = EvaluationForm(request.POST)
        is_htmx = request.headers.get("HX-Request") == "true"

        if not form.is_valid():
            contexte = _contexte_form(request=request, activite=activite, form=form)
            if is_htmx:
                return render(request, self.template_form, contexte, status=400)
            contexte["active_nav"] = "activites"
            return render(request, self.template_page, contexte, status=400)

        enregistrer_evaluation(
            user=request.user,
            activite=activite,
            charge_mentale=form.cleaned_data["charge_mentale"],
            charge_physique=form.cleaned_data["charge_physique"],
            duree=form.cleaned_data["duree"],
        )

        if is_htmx:
            # On renvoie le fragment avec un état "Enregistré" et on
            # déclenche `evaluation-enregistree` pour qu'un retour à la
            # liste reflète le nouveau label « Évaluée ».
            contexte = _contexte_form(
                request=request, activite=activite, form=form, succes=True
            )
            response = render(request, self.template_form, contexte)
            response["HX-Trigger"] = "evaluation-enregistree"
            return response

        messages.success(request, "Évaluation enregistrée.")
        return redirect(reverse("activites:activite-liste"))
