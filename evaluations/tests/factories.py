import factory

from activites.tests.factories import ActiviteFactory
from comptes.tests.factories import UserFactory
from evaluations.models import Evaluation


class EvaluationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Evaluation

    user = factory.SubFactory(UserFactory)
    activite = factory.SubFactory(ActiviteFactory)
    charge_mentale = 3
    charge_physique = 3
    duree = 3
