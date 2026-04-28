from django import forms

from .models import Evaluation


class EvaluationForm(forms.Form):
    """Formulaire de saisie / mise à jour d'une évaluation.

    Valide les 3 critères sur l'échelle 1–5. Le rattachement
    `(user, activite)` est porté par la vue, pas par le form.
    """

    charge_mentale = forms.IntegerField(
        label="Charge mentale",
        min_value=Evaluation.ECHELLE_MIN,
        max_value=Evaluation.ECHELLE_MAX,
    )
    charge_physique = forms.IntegerField(
        label="Charge physique",
        min_value=Evaluation.ECHELLE_MIN,
        max_value=Evaluation.ECHELLE_MAX,
    )
    duree = forms.IntegerField(
        label="Durée",
        min_value=Evaluation.ECHELLE_MIN,
        max_value=Evaluation.ECHELLE_MAX,
    )
