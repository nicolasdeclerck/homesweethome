from django.apps import apps

from activites import urls as activites_urls


def test_app_is_installed():
    assert apps.is_installed("activites")


def test_urls_module_is_importable():
    assert activites_urls.app_name == "activites"
    assert activites_urls.urlpatterns == []
