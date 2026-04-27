from django.test import Client
from django.urls import reverse

from comptes.tests.factories import UserFactory


def test_root_redirects_anonymous_to_connexion():
    client = Client()

    response = client.get("/")

    assert response.status_code == 302
    assert response.url == reverse("comptes:connexion")


def test_root_redirects_authenticated_to_mon_foyer():
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.get("/")

    assert response.status_code == 302
    assert response.url == reverse("foyer:mon-foyer")
