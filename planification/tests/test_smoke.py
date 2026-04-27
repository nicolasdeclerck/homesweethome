from django.apps import apps

from planification import urls as planification_urls


def test_app_is_installed():
    assert apps.is_installed("planification")


def test_urls_module_is_importable():
    assert planification_urls.app_name == "planification"
    assert planification_urls.urlpatterns == []
