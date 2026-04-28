"""Signaux du domaine `foyer`.

Crée automatiquement le foyer rattaché à un nouvel utilisateur. On passe
par un signal `post_save(User)` pour respecter la règle « pas d'effet de
bord en GET » : `MonFoyerView` se contente désormais de lire un foyer
qui existe déjà.
"""
from __future__ import annotations

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services import get_or_create_foyer_for_user


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def creer_foyer_pour_nouvel_utilisateur(sender, instance, created, **kwargs):
    if not created:
        return
    get_or_create_foyer_for_user(instance)
