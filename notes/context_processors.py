"""Context processors du domaine `notes`."""
from __future__ import annotations

from foyer.models import MembreFoyer

from .services import compter_commentaires_non_lus


def notes_badge(request):
    """Expose le nombre de commentaires non lus sur la note du user connecté.

    Utilisé pour afficher un badge sur l'item "Notes" de la sidebar. La
    valeur est 0 pour un visiteur non connecté ou un user sans foyer.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"notes_non_lus": 0}
    membre = MembreFoyer.objects.filter(user=user).first()
    if membre is None:
        return {"notes_non_lus": 0}
    return {"notes_non_lus": compter_commentaires_non_lus(membre)}
