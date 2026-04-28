from django import forms


class ActiviteCreationForm(forms.Form):
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

    def clean_categorie_nom(self) -> str:
        # Collapse les espaces multiples ("  Salle   de  bain " → "Salle de bain")
        # pour aligner sur la normalisation côté service et éviter les doublons.
        return " ".join(self.cleaned_data["categorie_nom"].split())
