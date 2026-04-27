from django.apps import apps
from django.urls import reverse

from comptes import urls as comptes_urls


def test_app_is_installed():
    assert apps.is_installed("comptes")


def test_urls_module_is_importable():
    assert comptes_urls.app_name == "comptes"
    assert len(comptes_urls.urlpatterns) == 2


def test_connexion_url_resolves():
    assert reverse("comptes:connexion") == "/connexion/"


def test_deconnexion_url_resolves():
    assert reverse("comptes:deconnexion") == "/deconnexion/"
