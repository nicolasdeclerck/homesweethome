from activites.models import Activite, Categorie
from activites.services import (
    creer_activite,
    get_or_create_categorie,
    lister_activites_par_categorie,
)
from activites.tests.factories import ActiviteFactory, CategorieFactory
from foyer.tests.factories import FoyerFactory


def test_get_or_create_categorie_cree_si_inexistante():
    foyer = FoyerFactory()

    categorie, cree = get_or_create_categorie(foyer=foyer, nom="Cuisine")

    assert cree is True
    assert categorie.nom == "Cuisine"
    assert categorie.foyer == foyer


def test_get_or_create_categorie_reutilise_existante_case_insensitive():
    foyer = FoyerFactory()
    CategorieFactory(foyer=foyer, nom="Cuisine")

    categorie, cree = get_or_create_categorie(foyer=foyer, nom="cuisine")

    assert cree is False
    assert Categorie.objects.filter(foyer=foyer).count() == 1
    assert categorie.nom == "Cuisine"  # nom d'origine conservé


def test_get_or_create_categorie_normalise_les_espaces():
    foyer = FoyerFactory()

    categorie, _ = get_or_create_categorie(foyer=foyer, nom="  Salle    de   bain  ")

    assert categorie.nom == "Salle de bain"


def test_creer_activite_avec_nouvelle_categorie():
    foyer = FoyerFactory()

    activite = creer_activite(
        foyer=foyer, titre="Faire les courses", categorie_nom="Courses"
    )

    assert activite.titre == "Faire les courses"
    assert activite.foyer == foyer
    assert activite.categorie.nom == "Courses"
    assert Categorie.objects.filter(foyer=foyer).count() == 1


def test_creer_activite_reutilise_categorie_existante():
    foyer = FoyerFactory()
    categorie = CategorieFactory(foyer=foyer, nom="Cuisine")

    activite = creer_activite(
        foyer=foyer, titre="Faire la vaisselle", categorie_nom="cuisine"
    )

    assert activite.categorie_id == categorie.pk
    assert Categorie.objects.filter(foyer=foyer).count() == 1


def test_creer_activite_isole_les_foyers():
    foyer_a = FoyerFactory()
    foyer_b = FoyerFactory()
    CategorieFactory(foyer=foyer_a, nom="Cuisine")

    creer_activite(foyer=foyer_b, titre="Cuire le riz", categorie_nom="Cuisine")

    assert Categorie.objects.filter(foyer=foyer_b).count() == 1
    assert Activite.objects.filter(foyer=foyer_a).count() == 0


def test_lister_activites_par_categorie_groupe_et_trie():
    foyer = FoyerFactory()
    cuisine = CategorieFactory(foyer=foyer, nom="Cuisine")
    salle = CategorieFactory(foyer=foyer, nom="Salle de bain")
    ActiviteFactory(foyer=foyer, categorie=cuisine, titre="Vaisselle")
    ActiviteFactory(foyer=foyer, categorie=cuisine, titre="Cuire")
    ActiviteFactory(foyer=foyer, categorie=salle, titre="Nettoyer")

    groupes = lister_activites_par_categorie(foyer)

    cles = list(groupes.keys())
    assert [c.nom for c in cles] == ["Cuisine", "Salle de bain"]
    assert [a.titre for a in groupes[cuisine]] == ["Cuire", "Vaisselle"]
    assert [a.titre for a in groupes[salle]] == ["Nettoyer"]


def test_lister_activites_par_categorie_ignore_les_autres_foyers():
    foyer = FoyerFactory()
    autre = FoyerFactory()
    ActiviteFactory(foyer=autre)

    assert lister_activites_par_categorie(foyer) == {}
