from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from .forms import EmailAuthenticationForm


# Limite les tentatives de connexion (POST) à 5/min/IP et 10/h/IP combinés.
# `block=True` renvoie un 429 ; les GET (formulaire) restent libres.
@method_decorator(
    ratelimit(key="ip", rate="5/m", method="POST", block=True),
    name="post",
)
@method_decorator(
    ratelimit(key="ip", rate="10/h", method="POST", block=True),
    name="post",
)
class ConnexionView(LoginView):
    template_name = "comptes/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class DeconnexionView(LogoutView):
    next_page = reverse_lazy("comptes:connexion")
