from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class EmailAuthenticationForm(AuthenticationForm):
    """Authentifie un utilisateur via son adresse e-mail et son mot de passe.

    Le champ ``username`` du formulaire d'auth Django reste nommé ``username``
    (contrat interne avec ``authenticate``) mais reçoit une valeur d'e-mail.
    """

    username = forms.EmailField(
        label=_("Adresse e-mail"),
        widget=forms.EmailInput(attrs={
            "autofocus": True,
            "autocomplete": "email",
            "class": "field-input",
            "placeholder": "vous@exemple.com",
        }),
    )

    error_messages = {
        "invalid_login": _(
            "Identifiants invalides. Vérifie ton adresse e-mail et ton mot de passe."
        ),
        "inactive": _(
            "Identifiants invalides. Vérifie ton adresse e-mail et ton mot de passe."
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].widget = forms.PasswordInput(attrs={
            "autocomplete": "current-password",
            "class": "field-input",
        })
        self.fields["password"].label = _("Mot de passe")
