import pytest
from django.db import IntegrityError

from activites.models import Activite, Categorie
from activites.tests.factories import ActiviteFactory, CategorieFactory
from foyer.tests.factories import FoyerFactory


def test_categorie_str_returns_nom():
    categorie = Categorie(nom="Cuisine")
    assert str(categorie) == "Cuisine"


def test_categorie_unicite_par_foyer_nom():
    foyer = FoyerFactory()
    CategorieFactory(foyer=foyer, nom="Cuisine")

    with pytest.raises(IntegrityError):
        CategorieFactory(foyer=foyer, nom="Cuisine")


def test_categorie_meme_nom_autorise_dans_foyers_differents():
    foyer_a = FoyerFactory()
    foyer_b = FoyerFactory()

    CategorieFactory(foyer=foyer_a, nom="Cuisine")
    autre = CategorieFactory(foyer=foyer_b, nom="Cuisine")

    assert autre.pk is not None


def test_activite_str_returns_titre():
    activite = Activite(titre="Faire la vaisselle")
    assert str(activite) == "Faire la vaisselle"


def test_supprimer_categorie_cascade_ses_activites():
    activite = ActiviteFactory()
    categorie = activite.categorie
    activite_pk = activite.pk

    categorie.delete()

    assert not Activite.objects.filter(pk=activite_pk).exists()


def test_supprimer_foyer_cascade_categorie_et_activite():
    activite = ActiviteFactory()
    foyer = activite.foyer
    categorie_pk = activite.categorie.pk
    activite_pk = activite.pk

    foyer.delete()

    assert not Categorie.objects.filter(pk=categorie_pk).exists()
    assert not Activite.objects.filter(pk=activite_pk).exists()
