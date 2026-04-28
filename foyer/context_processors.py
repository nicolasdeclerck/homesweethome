"""Contexts globaux du domaine ``foyer``."""
from __future__ import annotations

from django.urls import reverse

from .models import MembreFoyer

# Items de navigation de la sidebar app. Chaque item est un dict :
#   - key      : identifiant interne (utilisé par `active_nav` côté vue) ;
#   - label    : libellé affiché ;
#   - icon     : nom du partial dans templates/partials/icons/_<icon>.html ;
#   - url_name : nom d'URL Django à résoudre via `reverse` ;
#   - bientot  : True si la rubrique est en "Bientôt" (rendu désactivé).
_NAV_ITEMS = (
    {
        "key": "membres",
        "label": "Membres",
        "icon": "users",
        "url_name": "foyer:mon-foyer",
        "bientot": False,
    },
    {
        "key": "activites",
        "label": "Activités",
        "icon": "list",
        "url_name": "activites:activite-liste",
        "bientot": False,
    },
    {
        "key": "planification",
        "label": "Planification",
        "icon": "calendar",
        "url_name": "planification:periode-liste",
        "bientot": False,
    },
)


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


def nav_items(request):
    """Expose les items de navigation de la sidebar app.

    Permet d'ajouter de nouvelles rubriques (Activités, Évaluations, Planning…)
    sans toucher aux templates : il suffit d'étendre `_NAV_ITEMS`.
    """
    items = []
    for item in _NAV_ITEMS:
        items.append(
            {
                **item,
                "url": reverse(item["url_name"]),
            }
        )
    return {"nav_items": items}
