import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import foyer.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('foyer', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='foyer',
            name='cree_par',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='foyers_crees',
                to=settings.AUTH_USER_MODEL,
                verbose_name='créé par',
            ),
        ),
        migrations.CreateModel(
            name='Invitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, verbose_name='adresse e-mail')),
                ('prenom', models.CharField(max_length=60, verbose_name='prénom')),
                ('token', models.CharField(default=foyer.models._generate_invitation_token, editable=False, max_length=80, unique=True, verbose_name='token')),
                ('statut', models.CharField(choices=[('en_attente', 'En attente'), ('acceptee', 'Acceptée'), ('annulee', 'Annulée')], default='en_attente', max_length=20, verbose_name='statut')),
                ('date_creation', models.DateTimeField(auto_now_add=True, verbose_name='date de création')),
                ('date_expiration', models.DateTimeField(default=foyer.models._default_invitation_expiration, verbose_name="date d'expiration")),
                ('cree_par', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='invitations_envoyees', to=settings.AUTH_USER_MODEL, verbose_name='créée par')),
                ('foyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='foyer.foyer', verbose_name='foyer')),
            ],
            options={
                'verbose_name': 'Invitation',
                'verbose_name_plural': 'Invitations',
                'ordering': ['-date_creation'],
            },
        ),
        migrations.AddConstraint(
            model_name='invitation',
            constraint=models.UniqueConstraint(
                condition=models.Q(('statut', 'en_attente')),
                fields=('foyer', 'email'),
                name='unique_invitation_en_attente_par_foyer_email',
            ),
        ),
    ]
