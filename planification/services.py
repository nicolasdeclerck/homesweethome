"""Logique métier du domaine `planification`."""
from __future__ import annotations

from collections import OrderedDict
from datetime import date

from activites.models import Activite
from foyer.models import Foyer, MembreFoyer

from .models import Affectation, PeriodePlanification


def lister_periodes(foyer: Foyer) -> list[PeriodePlanification]:
    """Retourne les périodes du foyer, ordonnées de la plus récente à la plus
    ancienne (cf. ``Meta.ordering``)."""
    return list(foyer.periodes_planification.all())


def creer_periode(
    *, foyer: Foyer, date_debut: date, date_fin: date
) -> PeriodePlanification:
    """Crée une période de planification après validation complète.

    Lève ``ValidationError`` si les dates sont incohérentes ou si la période
    chevauche une période existante du foyer (le contrôle de chevauchement
    vit dans ``PeriodePlanification.clean``).
    """
    periode = PeriodePlanification(
        foyer=foyer, date_debut=date_debut, date_fin=date_fin
    )
    periode.full_clean()
    periode.save()
    return periode


def affectations_par_jour(
    periode: PeriodePlanification,
) -> OrderedDict[date, list[Affectation]]:
    """Regroupe les affectations d'une période par jour, en incluant tous les
    jours de la période (même ceux sans affectation, valeur = liste vide).

    L'ordre des jours suit celui de ``periode.jours()``. À l'intérieur d'un
    jour, l'ordre des affectations suit ``Affectation.Meta.ordering``.
    """
    affectations = list(
        periode.affectations.select_related(
            "activite", "activite__categorie", "membre", "membre__user"
        ).all()
    )
    par_jour: OrderedDict[date, list[Affectation]] = OrderedDict()
    for jour in periode.jours():
        par_jour[jour] = []
    for affectation in affectations:
        par_jour.setdefault(affectation.jour, []).append(affectation)
    return par_jour


def creer_affectation(
    *,
    periode: PeriodePlanification,
    activite: Activite,
    membre: MembreFoyer,
    jour: date,
) -> Affectation:
    """Crée une affectation après validation complète.

    Lève ``ValidationError`` si le jour n'appartient pas à la période ou
    si l'activité / le membre n'appartiennent pas au foyer de la période.
    """
    affectation = Affectation(
        periode=periode, activite=activite, membre=membre, jour=jour
    )
    affectation.full_clean()
    affectation.save()
    return affectation


def supprimer_affectation(affectation: Affectation) -> None:
    """Supprime une affectation. Wrappé par un service pour garder un point
    d'entrée unique côté domaine (logging futur, hooks, etc.)."""
    affectation.delete()
