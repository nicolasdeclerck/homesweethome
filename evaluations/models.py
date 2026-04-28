from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from activites.models import Activite


class Evaluation(models.Model):
    """Évaluation par un user de la charge d'une activité de son foyer.

    Une évaluation est unique pour `(user, activite)` : on met à jour la
    ligne existante plutôt que d'en créer une nouvelle (cf. `services.py`).
    """

    ECHELLE_MIN = 1
    ECHELLE_MAX = 5

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        # CASCADE volontaire (RGPD) : la suppression d'un user efface ses
        # évaluations, conformément au droit à l'effacement. Cohérent avec
        # `MembreFoyer.user` (cf. foyer/models.py).
        on_delete=models.CASCADE,
        related_name="evaluations",
        verbose_name="utilisateur",
    )
    activite = models.ForeignKey(
        Activite,
        # CASCADE volontaire : nécessaire pour propager la suppression d'un
        # foyer (Foyer → Activite est déjà CASCADE) sans buter sur un PROTECT
        # intermédiaire. Aligné sur la justification documentée dans
        # `activites/models.py`.
        on_delete=models.CASCADE,
        related_name="evaluations",
        verbose_name="activité",
    )
    charge_mentale = models.PositiveSmallIntegerField(
        "charge mentale",
        validators=[
            MinValueValidator(ECHELLE_MIN),
            MaxValueValidator(ECHELLE_MAX),
        ],
    )
    charge_physique = models.PositiveSmallIntegerField(
        "charge physique",
        validators=[
            MinValueValidator(ECHELLE_MIN),
            MaxValueValidator(ECHELLE_MAX),
        ],
    )
    duree = models.PositiveSmallIntegerField(
        "durée",
        validators=[
            MinValueValidator(ECHELLE_MIN),
            MaxValueValidator(ECHELLE_MAX),
        ],
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)
    date_maj = models.DateTimeField("date de mise à jour", auto_now=True)

    class Meta:
        verbose_name = "Évaluation"
        verbose_name_plural = "Évaluations"
        ordering = ["-date_maj"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "activite"],
                name="unique_evaluation_par_user_activite",
            ),
            models.CheckConstraint(
                # Défense en profondeur : doublon des validators côté DB pour
                # se protéger d'un bypass via SQL brut. Valeurs inlinées car
                # `ECHELLE_MIN`/`ECHELLE_MAX` ne sont pas dans le scope de Meta.
                condition=models.Q(charge_mentale__gte=1)
                & models.Q(charge_mentale__lte=5)
                & models.Q(charge_physique__gte=1)
                & models.Q(charge_physique__lte=5)
                & models.Q(duree__gte=1)
                & models.Q(duree__lte=5),
                name="evaluation_valeurs_dans_echelle",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.activite}"
