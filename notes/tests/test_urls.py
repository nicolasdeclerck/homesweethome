from django.urls import resolve, reverse


def test_url_liste():
    assert reverse("notes:liste") == "/notes/"
    match = resolve("/notes/")
    assert match.view_name == "notes:liste"


def test_url_ma_note():
    assert reverse("notes:ma-note") == "/notes/ma-note/"


def test_url_commentaire_create():
    url = reverse("notes:commentaire-create", kwargs={"note_id": 42})
    assert url == "/notes/42/commentaires/"


def test_url_commentaire_delete():
    url = reverse(
        "notes:commentaire-delete", kwargs={"commentaire_id": 7}
    )
    assert url == "/notes/commentaires/7/supprimer/"
