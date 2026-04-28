from django.urls import reverse


def test_url_activite_evaluer_resoud_avec_id():
    url = reverse("evaluations:activite-evaluer", kwargs={"activite_id": 42})

    assert url == "/evaluations/42/"
