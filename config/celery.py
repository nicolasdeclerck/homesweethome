"""Configuration de l'app Celery."""
import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("homesweethome")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


# Tâches périodiques. Pour les exécuter, lancer Celery Beat aux côtés du worker
# (`celery -A config beat --loglevel=info`).
app.conf.beat_schedule = {
    "expirer-invitations-en-attente": {
        "task": "foyer.tasks.expirer_invitations_en_attente",
        # Toutes les heures à la minute 7 — léger décalage pour ne pas
        # se caler sur le 0 de chaque heure.
        "schedule": crontab(minute=7),
    },
}
