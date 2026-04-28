from datetime import date

import pytest
from django.core.exceptions import ValidationError

from activites.tests.factories import ActiviteFactory
from foyer.tests.factories import FoyerFactory, MembreFoyerFactory
from planification.models import Affectation, PeriodePlanification
from planification.services import (
    affectations_par_jour,
    creer_affectation,
    creer_periode,
    lister_periodes,
    supprimer_affectation,
)
from planification.tests.factories import (
    AffectationFactory,
    PeriodePlanificationFactory,
)


def test_creer_periode_persiste_les_dates():
    foyer = FoyerFactory()

    periode = creer_periode(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 7),
    )

    periode.refresh_from_db()
    assert periode.foyer_id == foyer.pk
    assert periode.date_debut == date(2026, 5, 1)
    assert periode.date_fin == date(2026, 5, 7)


def test_creer_periode_refuse_dates_incoherentes():
    foyer = FoyerFactory()

    with pytest.raises(ValidationError):
        creer_periode(
            foyer=foyer,
            date_debut=date(2026, 5, 7),
            date_fin=date(2026, 5, 1),
        )

    assert PeriodePlanification.objects.count() == 0


def test_creer_periode_refuse_chevauchement():
    foyer = FoyerFactory()
    PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 10)
    )

    with pytest.raises(ValidationError):
        creer_periode(
            foyer=foyer,
            date_debut=date(2026, 5, 5),
            date_fin=date(2026, 5, 15),
        )

    assert PeriodePlanification.objects.filter(foyer=foyer).count() == 1


def test_lister_periodes_retourne_les_periodes_du_foyer_en_ordre():
    foyer = FoyerFactory()
    p1 = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 7)
    )
    p2 = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 6, 1), date_fin=date(2026, 6, 7)
    )

    # Plus récente d'abord (cf. Meta.ordering = ["-date_debut"]).
    assert lister_periodes(foyer) == [p2, p1]


def test_lister_periodes_n_inclut_pas_d_autres_foyers():
    foyer = FoyerFactory()
    autre_foyer = FoyerFactory()
    PeriodePlanificationFactory(foyer=autre_foyer)

    assert lister_periodes(foyer) == []


def test_affectations_par_jour_inclut_les_jours_vides():
    """Tous les jours de la période sont retournés, même sans affectation,
    pour que l'UI puisse afficher chaque jour avec son bouton « + Ajouter »."""
    periode = PeriodePlanificationFactory(
        date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 3)
    )

    par_jour = affectations_par_jour(periode)

    assert list(par_jour.keys()) == [
        date(2026, 5, 1),
        date(2026, 5, 2),
        date(2026, 5, 3),
    ]
    assert all(value == [] for value in par_jour.values())


def test_affectations_par_jour_regroupe_les_affectations():
    foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 3)
    )
    a1 = AffectationFactory(
        periode=periode, activite=activite, membre=membre, jour=date(2026, 5, 1)
    )
    a2 = AffectationFactory(
        periode=periode, activite=activite, membre=membre, jour=date(2026, 5, 1)
    )
    a3 = AffectationFactory(
        periode=periode, activite=activite, membre=membre, jour=date(2026, 5, 3)
    )

    par_jour = affectations_par_jour(periode)

    assert par_jour[date(2026, 5, 1)] == [a1, a2]
    assert par_jour[date(2026, 5, 2)] == []
    assert par_jour[date(2026, 5, 3)] == [a3]


def test_creer_affectation_persiste_et_renvoie_l_objet():
    foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 7)
    )

    affectation = creer_affectation(
        periode=periode,
        activite=activite,
        membre=membre,
        jour=date(2026, 5, 3),
    )

    affectation.refresh_from_db()
    assert affectation.periode_id == periode.pk
    assert affectation.activite_id == activite.pk
    assert affectation.membre_id == membre.pk
    assert affectation.jour == date(2026, 5, 3)


def test_creer_affectation_refuse_jour_hors_periode():
    foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 7)
    )

    with pytest.raises(ValidationError):
        creer_affectation(
            periode=periode,
            activite=activite,
            membre=membre,
            jour=date(2026, 5, 8),
        )

    assert Affectation.objects.count() == 0


def test_creer_affectation_refuse_activite_d_un_autre_foyer():
    foyer = FoyerFactory()
    autre_foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite_autre = ActiviteFactory(foyer=autre_foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 7)
    )

    with pytest.raises(ValidationError):
        creer_affectation(
            periode=periode,
            activite=activite_autre,
            membre=membre,
            jour=date(2026, 5, 3),
        )

    assert Affectation.objects.count() == 0


def test_creer_affectation_refuse_membre_d_un_autre_foyer():
    foyer = FoyerFactory()
    autre_foyer = FoyerFactory()
    membre_autre = MembreFoyerFactory(foyer=autre_foyer)
    activite = ActiviteFactory(foyer=foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 7)
    )

    with pytest.raises(ValidationError):
        creer_affectation(
            periode=periode,
            activite=activite,
            membre=membre_autre,
            jour=date(2026, 5, 3),
        )


def test_supprimer_affectation_efface_la_ligne():
    affectation = AffectationFactory()
    affectation_pk = affectation.pk

    supprimer_affectation(affectation)

    assert not Affectation.objects.filter(pk=affectation_pk).exists()
