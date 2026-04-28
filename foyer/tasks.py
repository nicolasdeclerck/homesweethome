"""Tâches Celery du domaine `foyer`.

Toutes les tâches doivent être idempotentes et ne recevoir que des IDs
en argument (jamais d'objets Django sérialisés).
"""
from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def send_invitation_email_task(self, invitation_id: int) -> None:
    """Envoie le mail d'invitation correspondant à `invitation_id`.

    L'implémentation métier sera ajoutée dans un ticket dédié. Cette
    signature sert de gabarit pour valider la configuration Celery.
    """
    logger.info(
        "send_invitation_email_task appelée pour invitation_id=%s (task_id=%s)",
        invitation_id,
        self.request.id,
    )


@shared_task
def expirer_invitations_en_attente() -> int:
    """Marque les invitations `EN_ATTENTE` arrivées à expiration en `EXPIREE`.

    Idempotente : un second appel ne fait rien si tout est déjà à jour.
    Retourne le nombre d'invitations basculées (utile pour le monitoring).
    """
    # Import local pour éviter les imports circulaires au chargement de l'app.
    from .models import Invitation

    maintenant = timezone.now()
    nb = Invitation.objects.filter(
        statut=Invitation.Statut.EN_ATTENTE,
        date_expiration__lte=maintenant,
    ).update(statut=Invitation.Statut.EXPIREE)
    if nb:
        logger.info("expirer_invitations_en_attente: %s invitations marquées expirées", nb)
    return nb
