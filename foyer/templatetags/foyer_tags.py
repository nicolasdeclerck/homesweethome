"""Template tags & filters utilitaires pour le rendu du domaine ``foyer``."""
from __future__ import annotations

import re

from django import template

register = template.Library()

_SEPARATEURS = re.compile(r"[\s\-_]+")


@register.filter
def initiale(value) -> str:
    """Retourne les initiales d'un nom (au plus deux lettres), ``?`` si vide.

    Gère les noms composés en splittant sur les espaces, tirets et underscores :
    "Marie-Claire" → "MC", "Jean Pierre" → "JP", "Alice" → "A".
    """
    if not value:
        return "?"
    text = str(value).strip()
    if not text:
        return "?"
    morceaux = [m for m in _SEPARATEURS.split(text) if m]
    if not morceaux:
        return "?"
    initiales = "".join(m[0] for m in morceaux)
    return initiales[:2].upper()
