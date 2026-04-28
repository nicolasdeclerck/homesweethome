import logging
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from foyer.models import Invitation
from foyer.tasks import expirer_invitations_en_attente, send_invitation_email_task
from foyer.tests.factories import InvitationFactory


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_send_invitation_email_task_runs_eagerly(caplog):
    caplog.set_level(logging.INFO, logger="foyer.tasks")

    result = send_invitation_email_task.delay(invitation_id=42)

    assert result.successful()
    assert "invitation_id=42" in caplog.text


def test_expirer_invitations_marque_les_en_attente_arrivees_a_expiration():
    expiree = InvitationFactory(date_expiration=timezone.now() - timedelta(seconds=1))
    encore_valide = InvitationFactory(date_expiration=timezone.now() + timedelta(days=1))
    deja_acceptee = InvitationFactory(
        statut=Invitation.Statut.ACCEPTEE,
        date_expiration=timezone.now() - timedelta(days=1),
    )

    nb = expirer_invitations_en_attente()

    assert nb == 1
    expiree.refresh_from_db()
    encore_valide.refresh_from_db()
    deja_acceptee.refresh_from_db()
    assert expiree.statut == Invitation.Statut.EXPIREE
    assert encore_valide.statut == Invitation.Statut.EN_ATTENTE
    # On ne touche pas aux invitations déjà sorties du flux EN_ATTENTE.
    assert deja_acceptee.statut == Invitation.Statut.ACCEPTEE


def test_expirer_invitations_est_idempotente():
    InvitationFactory(date_expiration=timezone.now() - timedelta(seconds=1))

    expirer_invitations_en_attente()
    nb_second_run = expirer_invitations_en_attente()

    assert nb_second_run == 0
