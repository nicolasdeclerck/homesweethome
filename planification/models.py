from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models

from activites.models import Activite
from foyer.models import Foyer, MembreFoyer


class PeriodePlanification(models.Model):
    """Période bornée par deux dates pendant laquelle on planifie des activités.

    Une période appartient à un foyer (et non à un user) : tous les membres
    du foyer voient et complètent la même période. Deux périodes d'un même
    foyer ne peuvent pas se chevaucher (validation applicative dans `clean`).
    """

    foyer = models.ForeignKey(
        Foyer,
        # CASCADE volontaire : une période n'a aucun sens hors de son foyer.
        # Aligné sur la justification de `Categorie.foyer` (cf. activites/models.py).
        # Déroge à la convention PROTECT par défaut documentée dans CLAUDE.md.
        on_delete=models.CASCADE,
        related_name="periodes_planification",
        verbose_name="foyer",
    )
    date_debut = models.DateField("date de début")
    date_fin = models.DateField("date de fin")
    date_creation = models.DateTimeField("date de création", auto_now_add=True)
    date_maj = models.DateTimeField("dernière mise à jour", auto_now=True)

    class Meta:
        verbose_name = "Période de planification"
        verbose_name_plural = "Périodes de planification"
        ordering = ["-date_debut"]
        constraints = [
            # Défense en profondeur : la cohérence des dates est aussi
            # vérifiée dans `clean()`, mais on double côté DB pour se
            # protéger d'un bypass via SQL brut.
            models.CheckConstraint(
                condition=models.Q(date_fin__gte=models.F("date_debut")),
                name="periode_planification_dates_coherentes",
            ),
        ]

    def __str__(self) -> str:
        return f"Période du {self.date_debut} au {self.date_fin}"

    def clean(self) -> None:
        super().clean()
        if (
            self.date_debut is not None
            and self.date_fin is not None
            and self.date_fin < self.date_debut
        ):
            raise ValidationError(
                {
                    "date_fin": (
                        "La date de fin doit être postérieure ou égale "
                        "à la date de début."
                    )
                }
            )
        if (
            self.date_debut is not None
            and self.date_fin is not None
            and self.foyer_id is not None
        ):
            # Non-chevauchement : une `CheckConstraint` ne suffit pas car
            # la condition porte sur deux lignes. On garde la garde
            # applicative ici + un test d'intégration dédié.
            chevauchements = PeriodePlanification.objects.filter(
                foyer_id=self.foyer_id,
                date_debut__lte=self.date_fin,
                date_fin__gte=self.date_debut,
            )
            if self.pk is not None:
                chevauchements = chevauchements.exclude(pk=self.pk)
            if chevauchements.exists():
                raise ValidationError(
                    "Cette période chevauche une période existante du foyer."
                )

    def jours(self) -> list:
        """Liste ordonnée des jours `date_debut..date_fin` (bornes incluses)."""
        if self.date_debut is None or self.date_fin is None:
            return []
        n_jours = (self.date_fin - self.date_debut).days + 1
        return [self.date_debut + timedelta(days=i) for i in range(n_jours)]


class Affectation(models.Model):
    """Affectation d'une activité à un membre du foyer pour un jour donné.

    Pas de contrainte d'unicité : la même activité peut être affectée
    plusieurs fois le même jour (libre, voir spec produit US-402).
    """

    periode = models.ForeignKey(
        PeriodePlanification,
        on_delete=models.CASCADE,
        related_name="affectations",
        verbose_name="période",
    )
    activite = models.ForeignKey(
        Activite,
        # CASCADE volontaire : nécessaire pour propager la suppression d'un
        # foyer (Foyer → Activite est CASCADE) sans buter sur un PROTECT
        # intermédiaire. Aligné sur `Evaluation.activite`.
        on_delete=models.CASCADE,
        related_name="affectations",
        verbose_name="activité",
    )
    membre = models.ForeignKey(
        MembreFoyer,
        # CASCADE volontaire (RGPD) : si un user est supprimé, son
        # `MembreFoyer` est CASCADE puis ses affectations le sont aussi.
        # Aligné sur `Evaluation.user`.
        on_delete=models.CASCADE,
        related_name="affectations",
        verbose_name="membre",
    )
    jour = models.DateField("jour")
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "Affectation"
        verbose_name_plural = "Affectations"
        ordering = ["jour", "date_creation"]

    def __str__(self) -> str:
        return f"{self.activite} → {self.membre} ({self.jour})"

    def clean(self) -> None:
        super().clean()
        if self.periode_id is not None and self.jour is not None:
            if not (
                self.periode.date_debut <= self.jour <= self.periode.date_fin
            ):
                raise ValidationError(
                    {"jour": "Le jour doit être compris dans la période."}
                )
        if self.periode_id is not None and self.activite_id is not None:
            if self.activite.foyer_id != self.periode.foyer_id:
                raise ValidationError(
                    {
                        "activite": (
                            "L'activité doit appartenir au foyer "
                            "de la période."
                        )
                    }
                )
        if self.periode_id is not None and self.membre_id is not None:
            if self.membre.foyer_id != self.periode.foyer_id:
                raise ValidationError(
                    {
                        "membre": (
                            "Le membre doit appartenir au foyer "
                            "de la période."
                        )
                    }
                )
