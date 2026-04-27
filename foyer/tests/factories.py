import factory

from comptes.tests.factories import UserFactory
from foyer.models import Foyer, MembreFoyer


class FoyerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Foyer

    nom = factory.Sequence(lambda n: f"Foyer test {n}")


class MembreFoyerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MembreFoyer

    user = factory.SubFactory(UserFactory)
    foyer = factory.SubFactory(FoyerFactory)
