from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class InvitationCreationForm(forms.Form):
    email = forms.EmailField(
        label="Adresse e-mail",
        widget=forms.EmailInput(attrs={
            "autocomplete": "email",
            "class": "field-input",
            "placeholder": "marie@exemple.com",
        }),
    )
    prenom = forms.CharField(
        label="Prénom",
        max_length=60,
        widget=forms.TextInput(attrs={
            "autocomplete": "given-name",
            "class": "field-input",
            "placeholder": "Marie",
        }),
    )

    def clean_email(self) -> str:
        return self.cleaned_data["email"].strip().lower()

    def clean_prenom(self) -> str:
        return self.cleaned_data["prenom"].strip()


class AccepterInvitationNouveauCompteForm(forms.Form):
    password = forms.CharField(
        label="Choisis un mot de passe",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "class": "field-input",
        }),
    )
    password_confirm = forms.CharField(
        label="Confirme le mot de passe",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "class": "field-input",
        }),
    )

    def clean(self) -> dict:
        cleaned = super().clean()
        password = cleaned.get("password")
        password_confirm = cleaned.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Les deux mots de passe ne correspondent pas.")
        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password", exc)
        return cleaned
