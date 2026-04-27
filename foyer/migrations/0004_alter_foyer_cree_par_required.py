import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("foyer", "0003_backfill_foyer_cree_par"),
    ]

    operations = [
        migrations.AlterField(
            model_name="foyer",
            name="cree_par",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="foyers_crees",
                to=settings.AUTH_USER_MODEL,
                verbose_name="créé par",
            ),
        ),
    ]
