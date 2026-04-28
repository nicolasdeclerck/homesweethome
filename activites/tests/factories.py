import factory

from activites.models import Activite, Categorie
from foyer.tests.factories import FoyerFactory


class CategorieFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Categorie

    nom = factory.Sequence(lambda n: f"Catégorie {n}")
    foyer = factory.SubFactory(FoyerFactory)


class ActiviteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Activite

    titre = factory.Sequence(lambda n: f"Activité {n}")
    categorie = factory.SubFactory(CategorieFactory)
    foyer = factory.SelfAttribute("categorie.foyer")
