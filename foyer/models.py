import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def _default_invitation_expiration() -> "timezone.datetime":
    return timezone.now() + timedelta(days=settings.INVITATION_TTL_DAYS)


def _generate_invitation_token() -> str:
    return secrets.token_urlsafe(48)


class Foyer(models.Model):
    nom = models.CharField("nom", max_length=120)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="foyers_crees",
        verbose_name="créé par",
    )
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


class Invitation(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        ACCEPTEE = "acceptee", "Acceptée"
        ANNULEE = "annulee", "Annulée"

    foyer = models.ForeignKey(
        Foyer,
        on_delete=models.CASCADE,
        related_name="invitations",
        verbose_name="foyer",
    )
    email = models.EmailField("adresse e-mail")
    prenom = models.CharField("prénom", max_length=60)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invitations_envoyees",
        verbose_name="créée par",
    )
    token = models.CharField(
        "token",
        max_length=80,
        unique=True,
        default=_generate_invitation_token,
        editable=False,
    )
    statut = models.CharField(
        "statut",
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)
    date_expiration = models.DateTimeField(
        "date d'expiration",
        default=_default_invitation_expiration,
    )

    class Meta:
        verbose_name = "Invitation"
        verbose_name_plural = "Invitations"
        ordering = ["-date_creation"]
        constraints = [
            models.UniqueConstraint(
                fields=["foyer", "email"],
                condition=models.Q(statut="en_attente"),
                name="unique_invitation_en_attente_par_foyer_email",
            ),
        ]

    def __str__(self) -> str:
        return f"Invitation pour {self.email} dans {self.foyer}"

    @property
    def est_expiree(self) -> bool:
        return self.date_expiration <= timezone.now()

    @property
    def est_utilisable(self) -> bool:
        return self.statut == self.Statut.EN_ATTENTE and not self.est_expiree
