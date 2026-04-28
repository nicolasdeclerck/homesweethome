from django.conf import settings
from django.db import models

from foyer.models import MembreFoyer


class Note(models.Model):
    """Note personnelle d'un membre du foyer.

    Un membre a au plus une note (OneToOne). Les autres membres du foyer
    peuvent la consulter et y attacher des commentaires ancrés sur un
    passage. Le contenu est en texte brut, sans limite de taille.
    """

    membre = models.OneToOneField(
        MembreFoyer,
        # CASCADE volontaire : la note est strictement liée à son membre,
        # qui est lui-même CASCADE sur User et Foyer (RGPD). Déroge à la
        # convention PROTECT par défaut documentée dans CLAUDE.md.
        on_delete=models.CASCADE,
        related_name="note",
        verbose_name="membre",
    )
    contenu = models.TextField("contenu", blank=True, default="")
    derniere_consultation = models.DateTimeField(
        "dernière consultation par le propriétaire",
        null=True,
        blank=True,
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)
    date_maj = models.DateTimeField("dernière mise à jour", auto_now=True)

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"

    def __str__(self) -> str:
        return f"Note de {self.membre.user}"

    @property
    def foyer(self):
        return self.membre.foyer


class Commentaire(models.Model):
    """Commentaire ancré sur un passage de la note d'un autre membre.

    L'ancrage est fait par "extrait" (snippet du texte commenté). Si
    l'extrait n'est plus présent dans le contenu de la note (édition par
    le propriétaire), le commentaire est considéré comme orphelin et
    affiché dans une section dédiée.
    """

    note = models.ForeignKey(
        Note,
        # CASCADE volontaire : un commentaire n'a aucun sens sans sa note.
        on_delete=models.CASCADE,
        related_name="commentaires",
        verbose_name="note",
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        # CASCADE volontaire (RGPD) : suppression du user → effacement
        # de ses commentaires. Aligné sur `MembreFoyer.user`.
        on_delete=models.CASCADE,
        related_name="commentaires_notes",
        verbose_name="auteur",
    )
    extrait = models.TextField("extrait commenté")
    contenu = models.TextField("contenu")
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"
        ordering = ["date_creation"]

    def __str__(self) -> str:
        return f"Commentaire de {self.auteur} sur {self.note}"

    @property
    def est_orphelin(self) -> bool:
        """Vrai si l'extrait n'est plus présent dans le contenu de la note."""
        if not self.extrait:
            return False
        return self.extrait not in self.note.contenu
