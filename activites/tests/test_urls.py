from django.urls import reverse


def test_activite_liste_url_resolves():
    assert reverse("activites:activite-liste") == "/activites/"


def test_activite_create_url_resolves():
    assert reverse("activites:activite-create") == "/activites/ajouter/"


def test_activite_liste_fragment_url_resolves():
    assert (
        reverse("activites:activite-liste-fragment")
        == "/activites/liste-fragment/"
    )
