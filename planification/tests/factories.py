from datetime import date, timedelta

import factory

from activites.tests.factories import ActiviteFactory
from foyer.tests.factories import FoyerFactory, MembreFoyerFactory
from planification.models import Affectation, PeriodePlanification


class PeriodePlanificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PeriodePlanification

    foyer = factory.SubFactory(FoyerFactory)
    date_debut = factory.LazyFunction(lambda: date(2026, 5, 1))
    date_fin = factory.LazyFunction(lambda: date(2026, 5, 7))


class AffectationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Affectation

    periode = factory.SubFactory(PeriodePlanificationFactory)
    activite = factory.LazyAttribute(
        lambda o: ActiviteFactory(foyer=o.periode.foyer)
    )
    membre = factory.LazyAttribute(
        lambda o: MembreFoyerFactory(foyer=o.periode.foyer)
    )
    jour = factory.LazyAttribute(lambda o: o.periode.date_debut + timedelta(days=0))
