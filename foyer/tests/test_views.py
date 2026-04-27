from django.test import Client
from django.urls import reverse

from comptes.tests.factories import UserFactory
from foyer.models import Foyer, MembreFoyer


def test_get_mon_foyer_anonymous_redirects_to_login():
    client = Client()

    response = client.get(reverse("foyer:mon-foyer"))

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


def test_get_mon_foyer_authenticated_returns_200_and_creates_foyer():
    user = UserFactory(email="alice@example.com")
    client = Client()
    client.force_login(user)

    response = client.get(reverse("foyer:mon-foyer"))

    assert response.status_code == 200
    assert MembreFoyer.objects.filter(user=user).exists()
    content = response.content.decode("utf-8")
    assert "Foyer de Alice" in content
    assert "alice@example.com" in content
    assert "Membre depuis" in content


def test_get_mon_foyer_does_not_create_duplicate_foyer():
    user = UserFactory()
    client = Client()
    client.force_login(user)

    client.get(reverse("foyer:mon-foyer"))
    client.get(reverse("foyer:mon-foyer"))

    assert Foyer.objects.count() == 1
    assert MembreFoyer.objects.filter(user=user).count() == 1
