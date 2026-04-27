import pytest
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


@pytest.mark.parametrize(
    "name, kwargs",
    [
        ("foyer:invitation-create", None),
        ("foyer:invitation-liste", None),
        ("foyer:invitation-lien", {"pk": 1}),
        ("foyer:invitation-annuler", {"pk": 1}),
        ("foyer:invitation-accepter", {"token": "abc-def"}),
    ],
)
def test_named_invitation_urls_resolve(name, kwargs):
    url = reverse(name, kwargs=kwargs) if kwargs else reverse(name)
    assert url.startswith("/foyer/invitations/")
