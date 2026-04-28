from django import forms


class PeriodeCreationForm(forms.Form):
    """Formulaire de création d'une période : deux dates bornes incluses."""

    date_debut = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(
            attrs={"type": "date", "class": "field-input", "autocomplete": "off"}
        ),
    )
    date_fin = forms.DateField(
        label="Date de fin",
        widget=forms.DateInput(
            attrs={"type": "date", "class": "field-input", "autocomplete": "off"}
        ),
    )

    def clean(self):
        cleaned = super().clean()
        date_debut = cleaned.get("date_debut")
        date_fin = cleaned.get("date_fin")
        if date_debut and date_fin and date_fin < date_debut:
            # Aligné sur la validation modèle (`PeriodePlanification.clean`).
            # On la dédouble côté form pour offrir un message inline avant
            # l'aller-retour service / modèle.
            raise forms.ValidationError(
                "La date de fin doit être postérieure ou égale à la date de début."
            )
        return cleaned


class AffectationCreationForm(forms.Form):
    """Formulaire de création d'une affectation pour un jour donné.

    `activite_id` et `membre_id` sont validés côté vue (appartenance au
    foyer), pas ici, pour éviter de devoir injecter le foyer dans le form.
    """

    activite_id = forms.IntegerField(
        widget=forms.HiddenInput(), min_value=1
    )
    membre_id = forms.IntegerField(
        widget=forms.HiddenInput(), min_value=1
    )
    jour = forms.DateField(
        widget=forms.HiddenInput(),
    )
