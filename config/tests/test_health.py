from django.test import Client


def test_health_endpoint_renvoie_200_quand_tout_va_bien():
    response = Client().get("/health/")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {"db": "ok", "cache": "ok"}


def test_health_endpoint_ne_demande_pas_d_auth():
    # Pas de redirection vers /connexion/, on renvoie directement 200.
    response = Client().get("/health/")

    assert response.status_code == 200
