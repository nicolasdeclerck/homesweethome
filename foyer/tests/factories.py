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


class InvitationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invitation

    foyer = factory.SubFactory(FoyerFactory)
    email = factory.Sequence(lambda n: f"invite{n}@example.com")
    prenom = factory.Faker("first_name", locale="fr_FR")
    cree_par = factory.SelfAttribute("foyer.cree_par")
