from django import forms

from .models import Note


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["contenu"]
        widgets = {
            "contenu": forms.Textarea(
                attrs={
                    "rows": 14,
                    "placeholder": "Écrivez votre note ici. Vos co-membres pourront sélectionner un passage pour y ajouter un commentaire.",
                    "class": "field-input note-textarea",
                }
            ),
        }
        labels = {"contenu": "Votre note"}


class CommentaireForm(forms.Form):
    extrait = forms.CharField(widget=forms.HiddenInput, max_length=20000)
    contenu = forms.CharField(
        label="Commentaire",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Votre commentaire…",
                "class": "field-input",
            }
        ),
        max_length=2000,
    )

    def clean_extrait(self) -> str:
        extrait = self.cleaned_data.get("extrait", "").strip()
        if not extrait:
            raise forms.ValidationError("Sélectionnez un passage à commenter.")
        return extrait

    def clean_contenu(self) -> str:
        contenu = self.cleaned_data.get("contenu", "").strip()
        if not contenu:
            raise forms.ValidationError("Le commentaire ne peut pas être vide.")
        return contenu
