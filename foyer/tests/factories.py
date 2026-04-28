import factory

from comptes.tests.factories import UserFactory
from foyer.models import Foyer, Invitation, MembreFoyer


class FoyerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Foyer

    nom = factory.Sequence(lambda n: f"Foyer test {n}")
    cree_par = factory.SubFactory(UserFactory)


class MembreFoyerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MembreFoyer

    user = factory.SubFactory(UserFactory)
    foyer = factory.SubFactory(FoyerFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Aligne sur le membre auto-créé par le signal `post_save(User)`.

        Le signal `creer_foyer_pour_nouvel_utilisateur` crée déjà un
        `MembreFoyer` pour chaque nouvel utilisateur. Comme `user` est un
        `OneToOneField`, créer un second `MembreFoyer` pour le même user
        violerait la contrainte. La factory réoriente donc le membre existant
        vers le foyer demandé par le test.
        """
        user = kwargs["user"]
        foyer_cible = kwargs.get("foyer")
        existant = (
            model_class.objects.select_related("foyer")
            .filter(user=user)
            .first()
        )
        if existant is None:
            return super()._create(model_class, *args, **kwargs)

        if foyer_cible is None or existant.foyer_id == foyer_cible.pk:
            return existant

        ancien_foyer = existant.foyer
        existant.foyer = foyer_cible
        existant.save(update_fields=["foyer"])
        # Le foyer auto-créé devient orphelin : on le supprime pour ne pas
        # polluer les comptages dans les tests qui s'appuient sur Foyer.objects.
        if ancien_foyer.cree_par_id == user.pk and not ancien_foyer.membres.exists():
            ancien_foyer.delete()
        return existant


class InvitationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invitation

    foyer = factory.SubFactory(FoyerFactory)
    email = factory.Sequence(lambda n: f"invite{n}@example.com")
    prenom = factory.Faker("first_name", locale="fr_FR")
    cree_par = factory.SelfAttribute("foyer.cree_par")
