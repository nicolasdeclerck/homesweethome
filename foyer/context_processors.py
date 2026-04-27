"""Contexts globaux du domaine ``foyer``."""
from __future__ import annotations

from .models import MembreFoyer


def foyer_courant(request):
    """Expose le foyer de l'utilisateur connecté à tous les templates.

    Permet aux layouts partagés (sidebar, top bar) d'afficher le nom du foyer
    sans que chaque vue n'ait à le réinjecter dans son contexte.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"foyer_courant": None}

    membre = (
        MembreFoyer.objects.select_related("foyer")
        .filter(user=user)
        .first()
    )
    return {"foyer_courant": membre.foyer if membre else None}
