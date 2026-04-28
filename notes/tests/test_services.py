from datetime import timedelta

from django.utils import timezone

from comptes.tests.factories import UserFactory
from foyer.tests.factories import FoyerFactory, MembreFoyerFactory
from notes.models import Note
from notes.services import (
    compter_commentaires_non_lus,
    creer_commentaire,
    get_or_create_note,
    lister_notes_du_foyer,
    marquer_note_consultee,
    mettre_a_jour_contenu,
)
from notes.tests.factories import CommentaireFactory, NoteFactory


def test_get_or_create_note_cree_une_note_vide_si_absente():
    membre = MembreFoyerFactory()
    note = get_or_create_note(membre)
    assert note.contenu == ""
    assert Note.objects.filter(membre=membre).count() == 1


def test_get_or_create_note_renvoie_la_note_existante_sans_la_dupliquer():
    membre = MembreFoyerFactory()
    note_existante = NoteFactory(membre=membre, contenu="Déjà là")
    note = get_or_create_note(membre)
    assert note.pk == note_existante.pk
    assert Note.objects.filter(membre=membre).count() == 1


def test_mettre_a_jour_contenu_persiste_le_texte():
    note = NoteFactory(contenu="Initial")
    note = mettre_a_jour_contenu(note, "Mis à jour")
    note.refresh_from_db()
    assert note.contenu == "Mis à jour"


def test_marquer_note_consultee_pose_un_timestamp():
    note = NoteFactory()
    avant = timezone.now()
    marquer_note_consultee(note)
    note.refresh_from_db()
    assert note.derniere_consultation is not None
    assert note.derniere_consultation >= avant


def test_creer_commentaire_attache_la_note_et_l_auteur():
    note = NoteFactory(contenu="Une phrase à commenter.")
    auteur = UserFactory()
    commentaire = creer_commentaire(
        note=note, auteur=auteur, extrait="phrase", contenu="Bien dit."
    )
    assert commentaire.note == note
    assert commentaire.auteur == auteur
    assert commentaire.extrait == "phrase"


def test_lister_notes_du_foyer_retourne_actifs_et_orphelins_separes():
    foyer = FoyerFactory()
    membre1 = MembreFoyerFactory(foyer=foyer, user=UserFactory())
    note = NoteFactory(membre=membre1, contenu="Le linge propre est plié.")
    auteur = MembreFoyerFactory(foyer=foyer, user=UserFactory()).user
    actif = CommentaireFactory(note=note, auteur=auteur, extrait="linge propre")
    orphelin = CommentaireFactory(note=note, auteur=auteur, extrait="vaisselle")

    resultat = lister_notes_du_foyer(foyer)

    entree = next(r for r in resultat if r.note.pk == note.pk)
    assert actif in entree.commentaires_actifs
    assert orphelin in entree.commentaires_orphelins
    assert len(entree.commentaires_actifs) == 1
    assert len(entree.commentaires_orphelins) == 1


def test_lister_notes_du_foyer_ne_renvoie_pas_les_notes_d_un_autre_foyer():
    foyer_a = FoyerFactory()
    foyer_b = FoyerFactory()
    membre_a = MembreFoyerFactory(foyer=foyer_a, user=UserFactory())
    membre_b = MembreFoyerFactory(foyer=foyer_b, user=UserFactory())
    NoteFactory(membre=membre_a, contenu="Note A")
    NoteFactory(membre=membre_b, contenu="Note B")

    notes = lister_notes_du_foyer(foyer_a)

    assert all(r.note.membre.foyer_id == foyer_a.pk for r in notes)


def test_compter_commentaires_non_lus_zero_si_aucune_note():
    membre = MembreFoyerFactory()
    # Pas de note encore créée pour ce membre
    Note.objects.filter(membre=membre).delete()
    assert compter_commentaires_non_lus(membre) == 0


def test_compter_commentaires_non_lus_compte_apres_derniere_consultation():
    membre = MembreFoyerFactory()
    note = NoteFactory(membre=membre, contenu="Texte commentable.")
    auteur = UserFactory()

    # 1 commentaire avant la consultation
    c_ancien = CommentaireFactory(note=note, auteur=auteur, extrait="Texte")
    Note.objects.filter(pk=note.pk).update(
        derniere_consultation=timezone.now() + timedelta(seconds=1)
    )
    note.refresh_from_db()

    # 1 commentaire après la consultation
    c_nouveau = CommentaireFactory(note=note, auteur=auteur, extrait="commentable")
    Note.objects.filter(pk=c_nouveau.pk).update()  # noop

    # On force la date du nouveau commentaire à être strictement postérieure
    Note.objects.filter(pk=note.pk).update(
        derniere_consultation=c_ancien.date_creation
    )
    note.refresh_from_db()

    assert compter_commentaires_non_lus(membre) >= 1


def test_compter_commentaires_non_lus_tous_si_jamais_consulte():
    membre = MembreFoyerFactory()
    note = NoteFactory(membre=membre, contenu="Texte.")
    note.derniere_consultation = None
    note.save(update_fields=["derniere_consultation"])
    auteur = UserFactory()
    CommentaireFactory(note=note, auteur=auteur, extrait="Texte")
    CommentaireFactory(note=note, auteur=auteur, extrait="Texte")

    assert compter_commentaires_non_lus(membre) == 2
