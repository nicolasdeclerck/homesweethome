from django.apps import AppConfig


class FoyerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "foyer"
    verbose_name = "Foyer"

    def ready(self) -> None:
        from . import signals  # noqa: F401  (enregistre les receivers)
