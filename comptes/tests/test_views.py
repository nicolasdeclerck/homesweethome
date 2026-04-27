from django.test import Client
from django.urls import reverse

from comptes.tests.factories import UserFactory


def test_get_connexion_returns_login_form():
    client = Client()
    response = client.get(reverse("comptes:connexion"))

    assert response.status_code == 200
    assert b"Connexion" in response.content
    assert b'name="username"' in response.content
    assert b'name="password"' in response.content


def test_post_valid_credentials_logs_in_and_redirects():
    user = UserFactory(email="alice@example.com")
    client = Client()

    response = client.post(
        reverse("comptes:connexion"),
        data={"username": "alice@example.com", "password": "azerty1234!"},
    )

    assert response.status_code == 302
    assert response.url == "/"
    assert client.session.get("_auth_user_id") == str(user.pk)


def test_post_wrong_password_shows_generic_error():
    UserFactory(email="alice@example.com")
    client = Client()

    response = client.post(
        reverse("comptes:connexion"),
        data={"username": "alice@example.com", "password": "mauvais"},
    )

    assert response.status_code == 200
    assert b"Identifiants invalides" in response.content
    assert client.session.get("_auth_user_id") is None


def test_post_unknown_email_shows_same_generic_error():
    client = Client()

    response = client.post(
        reverse("comptes:connexion"),
        data={"username": "inconnu@example.com", "password": "azerty1234!"},
    )

    assert response.status_code == 200
    assert b"Identifiants invalides" in response.content
    assert client.session.get("_auth_user_id") is None


def test_post_deconnexion_logs_out_and_redirects():
    user = UserFactory(email="alice@example.com")
    client = Client()
    client.force_login(user)

    response = client.post(reverse("comptes:deconnexion"))

    assert response.status_code == 302
    assert response.url == reverse("comptes:connexion")
    assert client.session.get("_auth_user_id") is None
