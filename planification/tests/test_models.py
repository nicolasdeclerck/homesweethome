from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from activites.tests.factories import ActiviteFactory
from foyer.tests.factories import FoyerFactory, MembreFoyerFactory
from planification.models import Affectation, PeriodePlanification
from planification.tests.factories import (
    AffectationFactory,
    PeriodePlanificationFactory,
)

# ---------------------------------------------------------------------------
# PeriodePlanification
# ---------------------------------------------------------------------------


def test_periode_str_contient_les_dates():
    periode = PeriodePlanificationFactory(
        date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 7)
    )

    assert str(periode) == "Période du 2026-05-01 au 2026-05-07"


def test_periode_jours_retourne_la_liste_des_jours_inclus():
    periode = PeriodePlanificationFactory(
        date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 3)
    )

    assert periode.jours() == [
        date(2026, 5, 1),
        date(2026, 5, 2),
        date(2026, 5, 3),
    ]


def test_periode_clean_refuse_date_fin_avant_date_debut():
    foyer = FoyerFactory()
    periode = PeriodePlanification(
        foyer=foyer,
        date_debut=date(2026, 5, 7),
        date_fin=date(2026, 5, 1),
    )

    with pytest.raises(ValidationError) as excinfo:
        periode.full_clean()
    assert "date_fin" in excinfo.value.message_dict


def test_periode_clean_accepte_date_fin_egale_date_debut():
    foyer = FoyerFactory()
    periode = PeriodePlanification(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 1),
    )
    periode.full_clean()  # ne lève pas


def test_periode_check_constraint_au_niveau_db():
    """Défense en profondeur : la contrainte CheckConstraint bloque
    l'insertion en SQL brut sans passer par `clean()`."""
    foyer = FoyerFactory()

    with pytest.raises(IntegrityError):
        PeriodePlanification.objects.create(
            foyer=foyer,
            date_debut=date(2026, 5, 7),
            date_fin=date(2026, 5, 1),
        )


def test_periode_clean_refuse_chevauchement_total():
    foyer = FoyerFactory()
    PeriodePlanificationFactory(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 10),
    )
    nouvelle = PeriodePlanification(
        foyer=foyer,
        date_debut=date(2026, 5, 3),
        date_fin=date(2026, 5, 8),
    )

    with pytest.raises(ValidationError):
        nouvelle.full_clean()


def test_periode_clean_refuse_chevauchement_partiel_par_la_gauche():
    foyer = FoyerFactory()
    PeriodePlanificationFactory(
        foyer=foyer,
        date_debut=date(2026, 5, 5),
        date_fin=date(2026, 5, 10),
    )
    nouvelle = PeriodePlanification(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 6),
    )

    with pytest.raises(ValidationError):
        nouvelle.full_clean()


def test_periode_clean_refuse_chevauchement_partiel_par_la_droite():
    foyer = FoyerFactory()
    PeriodePlanificationFactory(
        foyer=foyer,
        date_debut=date(2026, 5, 5),
        date_fin=date(2026, 5, 10),
    )
    nouvelle = PeriodePlanification(
        foyer=foyer,
        date_debut=date(2026, 5, 8),
        date_fin=date(2026, 5, 15),
    )

    with pytest.raises(ValidationError):
        nouvelle.full_clean()


def test_periode_clean_refuse_chevauchement_par_unique_jour_commun():
    """Le jour de fin de la période A == jour de début de la période B
    est considéré comme un chevauchement (les bornes sont incluses)."""
    foyer = FoyerFactory()
    PeriodePlanificationFactory(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 7),
    )
    nouvelle = PeriodePlanification(
        foyer=foyer,
        date_debut=date(2026, 5, 7),
        date_fin=date(2026, 5, 14),
    )

    with pytest.raises(ValidationError):
        nouvelle.full_clean()


def test_periode_clean_accepte_dates_adjacentes_sans_jour_commun():
    """Période A finissant le 7, période B démarrant le 8 → pas de chevauchement."""
    foyer = FoyerFactory()
    PeriodePlanificationFactory(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 7),
    )
    nouvelle = PeriodePlanification(
        foyer=foyer,
        date_debut=date(2026, 5, 8),
        date_fin=date(2026, 5, 14),
    )

    nouvelle.full_clean()  # ne lève pas


def test_periode_clean_n_empeche_pas_chevauchement_entre_foyers_distincts():
    foyer_a = FoyerFactory()
    foyer_b = FoyerFactory()
    PeriodePlanificationFactory(
        foyer=foyer_a,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 10),
    )
    nouvelle_b = PeriodePlanification(
        foyer=foyer_b,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 10),
    )

    nouvelle_b.full_clean()  # ne lève pas


def test_periode_clean_ignore_la_periode_courante_quand_elle_a_un_pk():
    """Modifier (save) une période existante ne doit pas être bloqué par
    son propre intervalle."""
    foyer = FoyerFactory()
    periode = PeriodePlanificationFactory(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 7),
    )
    periode.date_fin = date(2026, 5, 10)

    periode.full_clean()  # ne lève pas


# ---------------------------------------------------------------------------
# Affectation
# ---------------------------------------------------------------------------


def test_affectation_str_lisible():
    foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer, titre="Vaisselle")
    periode = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 7)
    )
    affectation = Affectation(
        periode=periode,
        activite=activite,
        membre=membre,
        jour=date(2026, 5, 3),
    )

    assert "Vaisselle" in str(affectation)
    assert "2026-05-03" in str(affectation)


def test_affectation_clean_refuse_jour_avant_periode():
    foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 7)
    )
    affectation = Affectation(
        periode=periode,
        activite=activite,
        membre=membre,
        jour=date(2026, 4, 30),
    )

    with pytest.raises(ValidationError) as excinfo:
        affectation.full_clean()
    assert "jour" in excinfo.value.message_dict


def test_affectation_clean_refuse_jour_apres_periode():
    foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 7)
    )
    affectation = Affectation(
        periode=periode,
        activite=activite,
        membre=membre,
        jour=date(2026, 5, 8),
    )

    with pytest.raises(ValidationError) as excinfo:
        affectation.full_clean()
    assert "jour" in excinfo.value.message_dict


def test_affectation_clean_refuse_activite_d_un_autre_foyer():
    foyer = FoyerFactory()
    autre_foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite_autre = ActiviteFactory(foyer=autre_foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 7)
    )
    affectation = Affectation(
        periode=periode,
        activite=activite_autre,
        membre=membre,
        jour=date(2026, 5, 3),
    )

    with pytest.raises(ValidationError) as excinfo:
        affectation.full_clean()
    assert "activite" in excinfo.value.message_dict


def test_affectation_clean_refuse_membre_d_un_autre_foyer():
    foyer = FoyerFactory()
    autre_foyer = FoyerFactory()
    activite = ActiviteFactory(foyer=foyer)
    membre_autre = MembreFoyerFactory(foyer=autre_foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 7)
    )
    affectation = Affectation(
        periode=periode,
        activite=activite,
        membre=membre_autre,
        jour=date(2026, 5, 3),
    )

    with pytest.raises(ValidationError) as excinfo:
        affectation.full_clean()
    assert "membre" in excinfo.value.message_dict


def test_affectation_meme_activite_plusieurs_fois_meme_jour_autorisee():
    """Pas de contrainte d'unicité (cf. spec produit)."""
    foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer, date_debut=date(2026, 5, 1), date_fin=date(2026, 5, 7)
    )

    AffectationFactory(
        periode=periode, activite=activite, membre=membre, jour=date(2026, 5, 3)
    )
    AffectationFactory(
        periode=periode, activite=activite, membre=membre, jour=date(2026, 5, 3)
    )

    assert Affectation.objects.filter(
        periode=periode, jour=date(2026, 5, 3)
    ).count() == 2
