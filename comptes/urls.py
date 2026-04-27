from django.urls import path

from . import views

app_name = "comptes"

urlpatterns = [
    path("connexion/", views.ConnexionView.as_view(), name="connexion"),
    path("deconnexion/", views.DeconnexionView.as_view(), name="deconnexion"),
]
