"""Logique métier du domaine `activites`."""
from __future__ import annotations

from collections import OrderedDict

from foyer.models import Foyer

from .models import Activite, Categorie


def _normaliser_nom_categorie(nom: str) -> str:
    return " ".join(nom.split())


def get_or_create_categorie(foyer: Foyer, nom: str) -> tuple[Categorie, bool]:
    """Retourne la catégorie `(foyer, nom)` en la créant au besoin.

    Le nom est normalisé (espaces collapsés, trims). La recherche est
    insensible à la casse pour éviter les doublons « Cuisine » / « cuisine ».
    """
    nom_normalise = _normaliser_nom_categorie(nom)
    existante = Categorie.objects.filter(
        foyer=foyer, nom__iexact=nom_normalise
    ).first()
    if existante is not None:
        return existante, False
    return (
        Categorie.objects.create(foyer=foyer, nom=nom_normalise),
        True,
    )


def creer_activite(*, foyer: Foyer, titre: str, categorie_nom: str) -> Activite:
    """Crée une activité dans le foyer, en créant la catégorie si besoin."""
    categorie, _ = get_or_create_categorie(foyer=foyer, nom=categorie_nom)
    return Activite.objects.create(
        foyer=foyer,
        titre=titre.strip(),
        categorie=categorie,
    )


def lister_activites_par_categorie(
    foyer: Foyer,
) -> OrderedDict[Categorie, list[Activite]]:
    """Retourne les activités du foyer, regroupées et triées par catégorie."""
    activites = (
        Activite.objects.filter(foyer=foyer)
        .select_related("categorie")
        .order_by("categorie__nom", "titre")
    )
    groupes: OrderedDict[Categorie, list[Activite]] = OrderedDict()
    for activite in activites:
        groupes.setdefault(activite.categorie, []).append(activite)
    return groupes
