"""Template tags & filters utilitaires pour le rendu du domaine ``notes``."""
from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def nom_membre(user) -> str:
    """Retourne un nom lisible pour afficher l'auteur d'un commentaire.

    Préfère le prénom (``first_name``) s'il est renseigné, sinon retombe
    sur l'email — qui est l'identifiant de connexion dans HomeSweetHome.
    """
    if user is None:
        return ""
    prenom = getattr(user, "first_name", "") or ""
    if prenom.strip():
        return prenom.strip()
    return getattr(user, "email", "") or ""
