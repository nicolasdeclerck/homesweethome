"""Logique métier du domaine `evaluations`."""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model

from activites.models import Activite
from foyer.models import Foyer, MembreFoyer

from .models import Evaluation

User = get_user_model()


def enregistrer_evaluation(
    *,
    user: settings.AUTH_USER_MODEL,
    activite: Activite,
    charge_mentale: int,
    charge_physique: int,
    duree: int,
) -> Evaluation:
    """Upsert l'évaluation de `user` pour `activite`.

    Crée la ligne si absente, met à jour les 3 critères et `date_maj`
    sinon. Le caller doit s'être assuré que `activite.foyer` correspond
    au foyer de l'user (cf. `EvaluationView`).
    """
    evaluation, _ = Evaluation.objects.update_or_create(
        user=user,
        activite=activite,
        defaults={
            "charge_mentale": charge_mentale,
            "charge_physique": charge_physique,
            "duree": duree,
        },
    )
    return evaluation


def get_evaluation(
    *,
    user: settings.AUTH_USER_MODEL,
    activite: Activite,
) -> Evaluation | None:
    """Retourne l'évaluation de `user` pour `activite`, ou `None`."""
    return Evaluation.objects.filter(user=user, activite=activite).first()


def get_autre_membre(*, foyer: Foyer, user: settings.AUTH_USER_MODEL) -> User | None:
    """Retourne l'autre membre du foyer (s'il existe), ou `None`.

    Comme `MembreFoyer.user` est `OneToOneField` et qu'un foyer ne contient
    aujourd'hui qu'un ou deux membres, on prend le premier autre membre.
    Si la règle change (foyer recomposé, etc.), il faudra revoir.
    """
    autre = (
        MembreFoyer.objects.select_related("user")
        .filter(foyer=foyer)
        .exclude(user=user)
        .first()
    )
    return autre.user if autre is not None else None


def get_evaluation_autre_membre(
    *,
    foyer: Foyer,
    activite: Activite,
    user: settings.AUTH_USER_MODEL,
) -> tuple[User | None, Evaluation | None]:
    """Retourne `(autre_membre, evaluation_de_l_autre_membre)`.

    `autre_membre` peut être `None` (user seul dans le foyer).
    `evaluation` peut être `None` (autre membre pas encore évalué).
    """
    autre = get_autre_membre(foyer=foyer, user=user)
    if autre is None:
        return None, None
    evaluation = (
        Evaluation.objects.filter(user=autre, activite=activite).first()
    )
    return autre, evaluation
