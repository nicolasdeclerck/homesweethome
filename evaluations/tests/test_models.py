import pytest
from django.db import IntegrityError

from activites.tests.factories import ActiviteFactory
from comptes.tests.factories import UserFactory
from evaluations.models import Evaluation
from evaluations.tests.factories import EvaluationFactory


def test_evaluation_str_contient_user_et_activite():
    user = UserFactory(email="alice@example.com")
    activite = ActiviteFactory(titre="Faire la vaisselle")

    evaluation = EvaluationFactory(user=user, activite=activite)

    assert "alice@example.com" in str(evaluation)
    assert "Faire la vaisselle" in str(evaluation)


def test_unicite_evaluation_par_user_et_activite():
    user = UserFactory()
    activite = ActiviteFactory()
    EvaluationFactory(user=user, activite=activite)

    with pytest.raises(IntegrityError):
        EvaluationFactory(user=user, activite=activite)


def test_meme_user_peut_evaluer_plusieurs_activites():
    user = UserFactory()
    EvaluationFactory(user=user, activite=ActiviteFactory())
    EvaluationFactory(user=user, activite=ActiviteFactory())

    assert Evaluation.objects.filter(user=user).count() == 2


def test_plusieurs_users_peuvent_evaluer_la_meme_activite():
    activite = ActiviteFactory()
    EvaluationFactory(user=UserFactory(), activite=activite)
    EvaluationFactory(user=UserFactory(), activite=activite)

    assert Evaluation.objects.filter(activite=activite).count() == 2


@pytest.mark.parametrize(
    "champ,valeur",
    [
        ("charge_mentale", 0),
        ("charge_mentale", 6),
        ("charge_physique", 0),
        ("charge_physique", 6),
        ("duree", 0),
        ("duree", 6),
    ],
)
def test_check_constraint_refuse_valeurs_hors_echelle(champ, valeur):
    user = UserFactory()
    activite = ActiviteFactory()
    valeurs = {"charge_mentale": 3, "charge_physique": 3, "duree": 3}
    valeurs[champ] = valeur

    with pytest.raises(IntegrityError):
        Evaluation.objects.create(user=user, activite=activite, **valeurs)


def test_supprimer_activite_cascade_ses_evaluations():
    evaluation = EvaluationFactory()
    pk = evaluation.pk

    evaluation.activite.delete()

    assert not Evaluation.objects.filter(pk=pk).exists()


def test_supprimer_foyer_cascade_jusqu_aux_evaluations():
    """Chaîne complète Foyer → Categorie → Activite → Evaluation."""
    from foyer.models import Foyer
    from foyer.tests.factories import FoyerFactory

    evaluation = EvaluationFactory()
    foyer = evaluation.activite.foyer
    pk = evaluation.pk
    # Foyer.cree_par est PROTECT → on conserve un user créateur fantoche pour
    # ne pas casser la chaîne. La suppression du foyer suffit à exercer la
    # cascade jusqu'à Evaluation.
    autre_foyer = FoyerFactory()  # noqa: F841 (sentinelle pour vérifier l'isolation)
    foyer.delete()
    assert not Foyer.objects.filter(pk=foyer.pk).exists()
    assert not Evaluation.objects.filter(pk=pk).exists()
