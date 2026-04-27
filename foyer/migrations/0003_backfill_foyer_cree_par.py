from django.db import migrations


def backfill_cree_par(apps, schema_editor):
    """Pour chaque foyer sans `cree_par`, prend le premier membre par date d'arrivée."""
    Foyer = apps.get_model("foyer", "Foyer")
    MembreFoyer = apps.get_model("foyer", "MembreFoyer")

    for foyer in Foyer.objects.filter(cree_par__isnull=True):
        premier_membre = (
            MembreFoyer.objects.filter(foyer=foyer)
            .order_by("date_arrivee", "pk")
            .select_related("user")
            .first()
        )
        if premier_membre is None:
            continue
        foyer.cree_par = premier_membre.user
        foyer.save(update_fields=["cree_par"])


def reverse_backfill(apps, schema_editor):
    """Inverse non destructive : ne fait rien (la valeur peut rester en base)."""


class Migration(migrations.Migration):

    dependencies = [
        ("foyer", "0002_invitation_and_foyer_cree_par_nullable"),
    ]

    operations = [
        migrations.RunPython(backfill_cree_par, reverse_backfill),
    ]
