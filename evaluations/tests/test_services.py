from activites.tests.factories import ActiviteFactory
from comptes.tests.factories import UserFactory
from evaluations.models import Evaluation
from evaluations.services import (
    enregistrer_evaluation,
    get_autre_membre,
    get_evaluation,
    get_evaluation_autre_membre,
)
from evaluations.tests.factories import EvaluationFactory
from foyer.tests.factories import FoyerFactory, MembreFoyerFactory


def test_enregistrer_evaluation_cree_si_inexistante():
    user = UserFactory()
    activite = ActiviteFactory()

    evaluation = enregistrer_evaluation(
        user=user,
        activite=activite,
        charge_mentale=2,
        charge_physique=4,
        duree=3,
    )

    assert evaluation.pk is not None
    assert evaluation.charge_mentale == 2
    assert evaluation.charge_physique == 4
    assert evaluation.duree == 3
    assert Evaluation.objects.filter(user=user, activite=activite).count() == 1


def test_enregistrer_evaluation_met_a_jour_si_existante():
    user = UserFactory()
    activite = ActiviteFactory()
    initiale = EvaluationFactory(
        user=user,
        activite=activite,
        charge_mentale=1,
        charge_physique=1,
        duree=1,
    )

    miseajour = enregistrer_evaluation(
        user=user,
        activite=activite,
        charge_mentale=5,
        charge_physique=4,
        duree=3,
    )

    assert miseajour.pk == initiale.pk
    assert Evaluation.objects.filter(user=user, activite=activite).count() == 1
    miseajour.refresh_from_db()
    assert miseajour.charge_mentale == 5
    assert miseajour.charge_physique == 4
    assert miseajour.duree == 3


def test_get_evaluation_retourne_none_si_inexistante():
    user = UserFactory()
    activite = ActiviteFactory()

    assert get_evaluation(user=user, activite=activite) is None


def test_get_evaluation_retourne_celle_du_user():
    user = UserFactory()
    autre_user = UserFactory()
    activite = ActiviteFactory()
    attendue = EvaluationFactory(user=user, activite=activite)
    EvaluationFactory(user=autre_user, activite=activite)  # bruit

    assert get_evaluation(user=user, activite=activite).pk == attendue.pk


def test_get_autre_membre_retourne_none_si_seul():
    membre = MembreFoyerFactory()

    assert get_autre_membre(foyer=membre.foyer, user=membre.user) is None


def test_get_autre_membre_retourne_l_autre_membre():
    foyer = FoyerFactory()
    moi = MembreFoyerFactory(foyer=foyer)
    autre = MembreFoyerFactory(foyer=foyer)

    resultat = get_autre_membre(foyer=foyer, user=moi.user)

    assert resultat == autre.user


def test_get_evaluation_autre_membre_retourne_paire_membre_evaluation():
    foyer = FoyerFactory()
    moi = MembreFoyerFactory(foyer=foyer)
    autre = MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer)
    eval_autre = EvaluationFactory(user=autre.user, activite=activite)

    membre, evaluation = get_evaluation_autre_membre(
        foyer=foyer, activite=activite, user=moi.user
    )

    assert membre == autre.user
    assert evaluation.pk == eval_autre.pk


def test_get_evaluation_autre_membre_sans_evaluation_de_l_autre():
    foyer = FoyerFactory()
    moi = MembreFoyerFactory(foyer=foyer)
    autre = MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer)

    membre, evaluation = get_evaluation_autre_membre(
        foyer=foyer, activite=activite, user=moi.user
    )

    assert membre == autre.user
    assert evaluation is None


def test_get_evaluation_autre_membre_seul_dans_foyer():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer)

    autre, evaluation = get_evaluation_autre_membre(
        foyer=membre.foyer, activite=activite, user=membre.user
    )

    assert autre is None
    assert evaluation is None
