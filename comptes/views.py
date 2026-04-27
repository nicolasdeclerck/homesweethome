from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

from .forms import EmailAuthenticationForm


class ConnexionView(LoginView):
    template_name = "comptes/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class DeconnexionView(LogoutView):
    next_page = reverse_lazy("comptes:connexion")
