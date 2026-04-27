from django.apps import apps
from django.urls import reverse

from foyer import urls as foyer_urls


def test_app_is_installed():
    assert apps.is_installed("foyer")


def test_urls_module_is_importable():
    assert foyer_urls.app_name == "foyer"
    assert foyer_urls.urlpatterns == []


def test_admin_url_resolves():
    assert reverse("admin:index") == "/admin/"
