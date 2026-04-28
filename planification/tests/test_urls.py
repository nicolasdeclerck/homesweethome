from django.urls import resolve, reverse


def test_periode_liste_url_resolves():
    url = reverse("planification:periode-liste")
    assert url == "/planification/"
    assert resolve(url).func.view_class.__name__ == "PeriodesListView"


def test_periode_create_url_resolves():
    url = reverse("planification:periode-create")
    assert url == "/planification/ajouter/"
    assert resolve(url).func.view_class.__name__ == "PeriodeCreateView"


def test_periode_liste_fragment_url_resolves():
    url = reverse("planification:periode-liste-fragment")
    assert url == "/planification/liste-fragment/"


def test_periode_detail_url_resolves():
    url = reverse("planification:periode-detail", kwargs={"periode_id": 42})
    assert url == "/planification/42/"


def test_affectations_liste_fragment_url_resolves():
    url = reverse(
        "planification:affectations-liste-fragment",
        kwargs={"periode_id": 42},
    )
    assert url == "/planification/42/affectations-fragment/"


def test_affectation_create_url_resolves():
    url = reverse(
        "planification:affectation-create", kwargs={"periode_id": 42}
    )
    assert url == "/planification/42/affectations/ajouter/"


def test_affectation_delete_url_resolves():
    url = reverse(
        "planification:affectation-delete", kwargs={"affectation_id": 7}
    )
    assert url == "/planification/affectations/7/supprimer/"
