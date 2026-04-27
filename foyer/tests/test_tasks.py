import logging

from django.test import override_settings

from foyer.tasks import send_invitation_email_task


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_send_invitation_email_task_runs_eagerly(caplog):
    caplog.set_level(logging.INFO, logger="foyer.tasks")

    result = send_invitation_email_task.delay(invitation_id=42)

    assert result.successful()
    assert "invitation_id=42" in caplog.text
