from django.db import models

from foyer.models import Foyer


class Categorie(models.Model):
    nom = models.CharField("nom", max_length=60)
    foyer = models.ForeignKey(
        Foyer,
        # CASCADE volontaire : une catégorie n'a aucun sens hors de son foyer.
        # Aligné sur la justification de `MembreFoyer.foyer` (cf. foyer/models.py).
        # Déroge à la convention PROTECT par défaut documentée dans CLAUDE.md.
        on_delete=models.CASCADE,
        related_name="categories",
        verbose_name="foyer",
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ["nom"]
        constraints = [
            models.UniqueConstraint(
                fields=["foyer", "nom"],
                name="unique_categorie_par_foyer_nom",
            ),
        ]

    def __str__(self) -> str:
        return self.nom


class Activite(models.Model):
    titre = models.CharField("titre", max_length=120)
    categorie = models.ForeignKey(
        Categorie,
        # CASCADE volontaire : nécessaire pour que la suppression d'un foyer
        # cascade jusqu'aux activités sans buter sur un PROTECT intermédiaire
        # (Django ne réconcilie pas les chemins de suppression). Si on ouvre
        # plus tard la suppression d'une catégorie isolée, on validera côté
        # service (refus si activités liées) plutôt que via on_delete.
        on_delete=models.CASCADE,
        related_name="activites",
        verbose_name="catégorie",
    )
    foyer = models.ForeignKey(
        Foyer,
        # CASCADE volontaire : même justification que `Categorie.foyer`.
        on_delete=models.CASCADE,
        related_name="activites",
        verbose_name="foyer",
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "Activité"
        verbose_name_plural = "Activités"
        ordering = ["categorie__nom", "titre"]

    def __str__(self) -> str:
        return self.titre
