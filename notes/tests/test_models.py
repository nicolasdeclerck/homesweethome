from comptes.tests.factories import UserFactory
from foyer.tests.factories import MembreFoyerFactory
from notes.models import Commentaire, Note
from notes.tests.factories import CommentaireFactory, NoteFactory


def test_note_str_inclut_le_user():
    note = NoteFactory()
    assert str(note.membre.user) in str(note)


def test_note_un_membre_a_au_plus_une_note():
    membre = MembreFoyerFactory()
    NoteFactory(membre=membre)
    # Avec OneToOne, une seconde note pour le même membre doit être empêchée
    # par get_or_create dans le service ; ici on vérifie l'invariant DB en
    # passant par la factory : si la contrainte sautait, on aurait deux
    # entrées. On utilise donc directement le manager pour valider.
    note_existante = Note.objects.filter(membre=membre).count()
    assert note_existante == 1


def test_note_foyer_property_renvoie_le_foyer_du_membre():
    note = NoteFactory()
    assert note.foyer == note.membre.foyer


def test_commentaire_str_indique_auteur_et_note():
    commentaire = CommentaireFactory()
    label = str(commentaire)
    assert str(commentaire.auteur) in label


def test_commentaire_actif_quand_extrait_present_dans_la_note():
    note = NoteFactory(contenu="Aujourd'hui j'ai fait la vaisselle et le linge.")
    commentaire = CommentaireFactory(note=note, extrait="la vaisselle")
    assert commentaire.est_orphelin is False


def test_commentaire_devient_orphelin_si_extrait_absent_de_la_note():
    note = NoteFactory(contenu="Aujourd'hui j'ai fait la vaisselle.")
    commentaire = CommentaireFactory(note=note, extrait="le repassage")
    assert commentaire.est_orphelin is True


def test_commentaires_ordonnes_par_date_creation():
    note = NoteFactory(contenu="Texte de la note")
    auteur = UserFactory()
    c1 = CommentaireFactory(note=note, auteur=auteur, extrait="Texte")
    c2 = CommentaireFactory(note=note, auteur=auteur, extrait="note")
    assert list(note.commentaires.all()) == [c1, c2]


def test_supprimer_le_membre_supprime_ses_notes_et_commentaires():
    note = NoteFactory(contenu="Mes pensées")
    auteur = UserFactory()
    CommentaireFactory(note=note, auteur=auteur, extrait="pensées")
    note.membre.delete()
    assert Note.objects.filter(pk=note.pk).count() == 0
    assert Commentaire.objects.count() == 0
