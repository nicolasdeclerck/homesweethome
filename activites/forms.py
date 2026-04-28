from django import forms

from evaluations.models import Evaluation


class ActiviteCreationForm(forms.Form):
    """Formulaire combiné : titre + catégorie + évaluation (optionnelle).

    Sert à la fois la création et l'édition d'une activité dans le drawer.
    Les 3 champs d'évaluation sont optionnels : à l'ajout rapide d'une
    activité on peut soumettre sans évaluer ; à l'édition la vue ne
    déclenche l'upsert que si les 3 valeurs sont fournies.
    """

    titre = forms.CharField(
        label="Titre",
        max_length=120,
        widget=forms.TextInput(attrs={
            "class": "field-input",
            "placeholder": "Faire les courses",
            "autocomplete": "off",
        }),
    )
    categorie_nom = forms.CharField(
        label="Catégorie",
        max_length=60,
        widget=forms.TextInput(attrs={
            "class": "field-input",
            "placeholder": "Cuisine",
            "autocomplete": "off",
            "list": "categories-existantes",
        }),
    )
    charge_mentale = forms.IntegerField(
        label="Charge mentale",
        required=False,
        min_value=Evaluation.ECHELLE_MIN,
        max_value=Evaluation.ECHELLE_MAX,
    )
    charge_physique = forms.IntegerField(
        label="Charge physique",
        required=False,
        min_value=Evaluation.ECHELLE_MIN,
        max_value=Evaluation.ECHELLE_MAX,
    )
    duree = forms.IntegerField(
        label="Durée",
        required=False,
        min_value=Evaluation.ECHELLE_MIN,
        max_value=Evaluation.ECHELLE_MAX,
    )

    def clean_categorie_nom(self) -> str:
        # Collapse les espaces multiples ("  Salle   de  bain " → "Salle de bain")
        # pour aligner sur la normalisation côté service et éviter les doublons.
        return " ".join(self.cleaned_data["categorie_nom"].split())

    def clean(self):
        cleaned = super().clean()
        eval_values = (
            cleaned.get("charge_mentale"),
            cleaned.get("charge_physique"),
            cleaned.get("duree"),
        )
        # Tout-ou-rien : on refuse une évaluation partielle pour éviter
        # une ligne `Evaluation` à moitié saisie côté API/curl. Le navigateur
        # envoie toujours les 3 (radios pré-cochés sur 3), donc cette branche
        # ne se déclenche qu'en cas de POST direct manipulé.
        present = [v is not None for v in eval_values]
        if any(present) and not all(present):
            raise forms.ValidationError(
                "Renseignez les 3 critères d'évaluation, ou aucun."
            )
        return cleaned

    def has_evaluation(self) -> bool:
        """Retourne True si les 3 critères ont été remplis et validés."""
        return (
            self.is_bound
            and self.is_valid()
            and self.cleaned_data.get("charge_mentale") is not None
            and self.cleaned_data.get("charge_physique") is not None
            and self.cleaned_data.get("duree") is not None
        )
