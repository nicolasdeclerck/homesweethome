from django.apps import apps

from evaluations import urls as evaluations_urls


def test_app_is_installed():
    assert apps.is_installed("evaluations")


def test_urls_module_is_importable():
    assert evaluations_urls.app_name == "evaluations"
    assert evaluations_urls.urlpatterns == []
