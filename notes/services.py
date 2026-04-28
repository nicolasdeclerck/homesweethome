"""Logique métier du domaine `notes`."""
from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from foyer.models import Foyer, MembreFoyer

from .models import Commentaire, Note


@dataclass
class NoteAvecCommentaires:
    """Note enrichie de ses commentaires séparés en actifs/orphelins.

    Un commentaire est *actif* tant que son extrait est encore présent
    dans le contenu de la note. Sinon il est *orphelin* (le passage
    commenté a été modifié ou supprimé par le propriétaire).
    """

    note: Note
    commentaires_actifs: list[Commentaire]
    commentaires_orphelins: list[Commentaire]


def get_or_create_note(membre: MembreFoyer) -> Note:
    """Retourne la note du membre, en la créant à vide si elle n'existe pas."""
    note, _ = Note.objects.get_or_create(membre=membre)
    return note


def lister_notes_du_foyer(foyer: Foyer) -> list[NoteAvecCommentaires]:
    """Retourne les notes des membres du foyer, enrichies de leurs commentaires.

    Les notes sont ordonnées par ancienneté de l'arrivée dans le foyer
    (membre le plus ancien en premier). Pour chaque note, les commentaires
    sont séparés en *actifs* (ancre encore présente) et *orphelins*
    (passage commenté disparu).
    """
    notes = (
        Note.objects.filter(membre__foyer=foyer)
        .select_related("membre__user", "membre__foyer")
        .prefetch_related("commentaires__auteur")
        .order_by("membre__date_arrivee", "membre_id")
    )
    resultat: list[NoteAvecCommentaires] = []
    for note in notes:
        actifs: list[Commentaire] = []
        orphelins: list[Commentaire] = []
        for commentaire in note.commentaires.all():
            if commentaire.extrait and commentaire.extrait in note.contenu:
                actifs.append(commentaire)
            else:
                orphelins.append(commentaire)
        resultat.append(
            NoteAvecCommentaires(
                note=note,
                commentaires_actifs=actifs,
                commentaires_orphelins=orphelins,
            )
        )
    return resultat


def mettre_a_jour_contenu(note: Note, contenu: str) -> Note:
    note.contenu = contenu
    note.save(update_fields=["contenu", "date_maj"])
    return note


def marquer_note_consultee(note: Note) -> Note:
    """Met à jour la dernière consultation pour réinitialiser le compteur de non-lus."""
    note.derniere_consultation = timezone.now()
    note.save(update_fields=["derniere_consultation"])
    return note


def creer_commentaire(
    *, note: Note, auteur, extrait: str, contenu: str
) -> Commentaire:
    return Commentaire.objects.create(
        note=note,
        auteur=auteur,
        extrait=extrait,
        contenu=contenu,
    )


def compter_commentaires_non_lus(membre: MembreFoyer) -> int:
    """Compte les commentaires sur la note du membre depuis sa dernière consultation.

    Sert au badge UI dans la navigation. Un commentaire posté par le
    propriétaire lui-même ne devrait pas exister (il ne peut pas commenter
    sa propre note), donc on n'a pas besoin d'exclure son auteur.
    """
    note = Note.objects.filter(membre=membre).first()
    if note is None:
        return 0
    qs = note.commentaires.all()
    if note.derniere_consultation is not None:
        qs = qs.filter(date_creation__gt=note.derniere_consultation)
    return qs.count()
