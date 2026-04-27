"""Logique métier du domaine `foyer`."""
from __future__ import annotations

from django.db import transaction

from .models import Foyer, MembreFoyer

_DEFAULT_FOYER_NAME = "Mon foyer"


def compute_default_foyer_name(email: str) -> str:
    """Calcule un nom de foyer par défaut depuis une adresse e-mail.

    Extrait la partie locale (avant ``@``), prend le premier segment
    avant ``.`` ou ``+``, ne garde que les caractères alphabétiques et
    capitalise. Retourne ``"Foyer de {Nom}"`` si exploitable, sinon
    ``"Mon foyer"``.
    """
    if not email or "@" not in email:
        return _DEFAULT_FOYER_NAME

    local_part = email.split("@", 1)[0]
    head = local_part.split(".")[0].split("+")[0]
    cleaned = "".join(c for c in head if c.isalpha())

    if not cleaned:
        return _DEFAULT_FOYER_NAME

    return f"Foyer de {cleaned.capitalize()}"


@transaction.atomic
def get_or_create_foyer_for_user(user) -> Foyer:
    """Retourne le foyer de l'utilisateur, en créant un nouveau si absent.

    L'utilisateur devient membre unique du foyer fraîchement créé.
    Idempotent : un appel répété pour un user déjà rattaché ne crée rien.
    """
    membre = MembreFoyer.objects.select_related("foyer").filter(user=user).first()
    if membre is not None:
        return membre.foyer

    foyer = Foyer.objects.create(nom=compute_default_foyer_name(user.email))
    MembreFoyer.objects.create(user=user, foyer=foyer)
    return foyer
