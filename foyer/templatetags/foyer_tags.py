"""Template tags & filters utilitaires pour le rendu du domaine ``foyer``."""
from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def initiale(value) -> str:
    """Retourne la 1re lettre de ``value`` en majuscule, ``?`` si vide."""
    if not value:
        return "?"
    text = str(value).strip()
    return text[0].upper() if text else "?"
