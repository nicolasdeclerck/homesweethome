from django.conf import settings
from django.db import models


class Foyer(models.Model):
    nom = models.CharField("nom", max_length=120)
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "Foyer"
        verbose_name_plural = "Foyers"
        ordering = ["-date_creation"]

    def __str__(self) -> str:
        return self.nom


class MembreFoyer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membrefoyer",
        verbose_name="utilisateur",
    )
    foyer = models.ForeignKey(
        Foyer,
        on_delete=models.CASCADE,
        related_name="membres",
        verbose_name="foyer",
    )
    date_arrivee = models.DateField("date d'arrivée", auto_now_add=True)

    class Meta:
        verbose_name = "Membre du foyer"
        verbose_name_plural = "Membres du foyer"
        ordering = ["date_arrivee"]

    def __str__(self) -> str:
        return f"{self.user} → {self.foyer}"
