from django.test import Client
from django.urls import reverse

from comptes.tests.factories import UserFactory
from foyer.tests.factories import MembreFoyerFactory
from notes.models import Commentaire, Note
from notes.tests.factories import CommentaireFactory, NoteFactory

# ---------------------------------------------------------------------------
# NotesListView
# ---------------------------------------------------------------------------


def test_liste_anonyme_redirige_vers_la_connexion():
    client = Client()
    response = client.get(reverse("notes:liste"))
    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


def test_liste_user_sans_foyer_renvoie_403():
    user = UserFactory()
    # Le signal post_save crée un foyer automatiquement, on le supprime
    user.membrefoyer.delete()
    client = Client()
    client.force_login(user)
    response = client.get(reverse("notes:liste"))
    assert response.status_code == 403


def test_liste_authentifie_affiche_la_page_notes():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.get(reverse("notes:liste"))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Notes" in content
    assert "Ma note" in content


def test_liste_marque_la_note_consultee_pour_remettre_a_zero_le_badge():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    client.get(reverse("notes:liste"))

    note = Note.objects.get(membre=membre)
    assert note.derniere_consultation is not None


def test_liste_affiche_les_notes_des_autres_membres_du_foyer():
    membre = MembreFoyerFactory()
    autre_user = UserFactory()
    autre_membre = MembreFoyerFactory(foyer=membre.foyer, user=autre_user)
    NoteFactory(
        membre=autre_membre, contenu="Coucou je suis le co-membre"
    )

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("notes:liste"))

    assert "Coucou je suis le co-membre" in response.content.decode("utf-8")


def test_liste_n_affiche_pas_les_notes_d_un_autre_foyer():
    membre = MembreFoyerFactory()
    autre = MembreFoyerFactory()
    NoteFactory(membre=autre, contenu="Note dun autre foyer")

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("notes:liste"))

    assert "Note dun autre foyer" not in response.content.decode("utf-8")


# ---------------------------------------------------------------------------
# MaNoteView
# ---------------------------------------------------------------------------


def test_get_ma_note_non_htmx_redirige_vers_la_liste():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.get(reverse("notes:ma-note"))

    assert response.status_code == 302
    assert response.url == reverse("notes:liste")


def test_get_ma_note_htmx_renvoie_le_form_d_edition():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.get(
        reverse("notes:ma-note"), headers={"hx-request": "true"}
    )

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "<textarea" in content
    assert 'name="contenu"' in content


def test_post_ma_note_persiste_le_contenu():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        reverse("notes:ma-note"),
        data={"contenu": "Mon nouveau contenu"},
        headers={"hx-request": "true"},
    )

    assert response.status_code == 200
    note = Note.objects.get(membre=membre)
    assert note.contenu == "Mon nouveau contenu"


# ---------------------------------------------------------------------------
# CommentaireCreateView
# ---------------------------------------------------------------------------


def test_creer_commentaire_sur_note_d_un_co_membre():
    membre = MembreFoyerFactory()
    autre_user = UserFactory()
    autre = MembreFoyerFactory(foyer=membre.foyer, user=autre_user)
    note = NoteFactory(membre=autre, contenu="Une phrase à commenter.")

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse("notes:commentaire-create", kwargs={"note_id": note.pk}),
        data={"extrait": "phrase", "contenu": "Bien vu"},
        headers={"hx-request": "true"},
    )

    assert response.status_code == 200
    commentaire = Commentaire.objects.get(note=note)
    assert commentaire.auteur == membre.user
    assert commentaire.extrait == "phrase"
    assert commentaire.contenu == "Bien vu"
    assert response["HX-Trigger"] == "commentaires-mis-a-jour"


def test_creer_commentaire_refuse_sur_sa_propre_note():
    membre = MembreFoyerFactory()
    note = NoteFactory(membre=membre, contenu="Ma note.")

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse("notes:commentaire-create", kwargs={"note_id": note.pk}),
        data={"extrait": "Ma", "contenu": "Auto-commentaire"},
        headers={"hx-request": "true"},
    )

    assert response.status_code == 403
    assert Commentaire.objects.count() == 0


def test_creer_commentaire_refuse_sur_la_note_d_un_autre_foyer():
    membre = MembreFoyerFactory()
    autre = MembreFoyerFactory()
    note = NoteFactory(membre=autre, contenu="Note d'un autre foyer")

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse("notes:commentaire-create", kwargs={"note_id": note.pk}),
        data={"extrait": "Note", "contenu": "Hop"},
        headers={"hx-request": "true"},
    )

    assert response.status_code == 404
    assert Commentaire.objects.count() == 0


def test_creer_commentaire_invalide_renvoie_400():
    membre = MembreFoyerFactory()
    autre_user = UserFactory()
    autre = MembreFoyerFactory(foyer=membre.foyer, user=autre_user)
    note = NoteFactory(membre=autre, contenu="Texte.")

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse("notes:commentaire-create", kwargs={"note_id": note.pk}),
        data={"extrait": "", "contenu": ""},
        headers={"hx-request": "true"},
    )

    assert response.status_code == 400
    assert Commentaire.objects.count() == 0


# ---------------------------------------------------------------------------
# CommentaireDeleteView
# ---------------------------------------------------------------------------


def test_supprimer_son_propre_commentaire():
    membre = MembreFoyerFactory()
    autre_user = UserFactory()
    autre = MembreFoyerFactory(foyer=membre.foyer, user=autre_user)
    note = NoteFactory(membre=autre, contenu="Texte commentable.")
    commentaire = CommentaireFactory(
        note=note, auteur=membre.user, extrait="Texte"
    )

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse(
            "notes:commentaire-delete",
            kwargs={"commentaire_id": commentaire.pk},
        ),
        headers={"hx-request": "true"},
    )

    assert response.status_code == 200
    assert Commentaire.objects.filter(pk=commentaire.pk).count() == 0


def test_supprimer_le_commentaire_d_un_autre_renvoie_403():
    membre = MembreFoyerFactory()
    autre_user = UserFactory()
    autre = MembreFoyerFactory(foyer=membre.foyer, user=autre_user)
    note = NoteFactory(membre=autre, contenu="Texte.")
    commentaire = CommentaireFactory(
        note=note, auteur=autre_user, extrait="Texte"
    )

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse(
            "notes:commentaire-delete",
            kwargs={"commentaire_id": commentaire.pk},
        ),
        headers={"hx-request": "true"},
    )

    assert response.status_code == 403
    assert Commentaire.objects.filter(pk=commentaire.pk).count() == 1


def test_supprimer_un_commentaire_d_un_autre_foyer_renvoie_404():
    membre = MembreFoyerFactory()
    autre = MembreFoyerFactory()  # autre foyer
    note = NoteFactory(membre=autre, contenu="Texte.")
    commentaire = CommentaireFactory(
        note=note, auteur=autre.user, extrait="Texte"
    )

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse(
            "notes:commentaire-delete",
            kwargs={"commentaire_id": commentaire.pk},
        ),
        headers={"hx-request": "true"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Badge non-lus dans la sidebar
# ---------------------------------------------------------------------------


def test_badge_affiche_le_nombre_de_commentaires_non_lus():
    membre = MembreFoyerFactory()
    autre_user = UserFactory()
    autre = MembreFoyerFactory(foyer=membre.foyer, user=autre_user)
    note = NoteFactory(membre=membre, contenu="Texte.")
    note.derniere_consultation = None
    note.save(update_fields=["derniere_consultation"])
    CommentaireFactory(note=note, auteur=autre.user, extrait="Texte")

    client = Client()
    client.force_login(membre.user)
    # On charge une page qui utilise app_base.html (pas notes:liste qui
    # marque tout comme lu) — la page Activités fait l'affaire.
    response = client.get(reverse("activites:activite-liste"))

    content = response.content.decode("utf-8")
    assert "nav-badge" in content
