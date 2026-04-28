from activites.models import Activite, Categorie
from activites.services import (
    creer_activite,
    get_or_create_categorie,
    lister_activites_par_categorie,
    mettre_a_jour_activite,
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


def test_mettre_a_jour_activite_change_titre_et_categorie():
    foyer = FoyerFactory()
    cuisine = CategorieFactory(foyer=foyer, nom="Cuisine")
    activite = ActiviteFactory(
        foyer=foyer, categorie=cuisine, titre="Faire la vaisselle"
    )

    mettre_a_jour_activite(
        activite, titre="Vider le lave-vaisselle", categorie_nom="Rangement"
    )

    activite.refresh_from_db()
    assert activite.titre == "Vider le lave-vaisselle"
    assert activite.categorie.nom == "Rangement"
    # Nouvelle catégorie créée dans le foyer.
    assert Categorie.objects.filter(foyer=foyer, nom="Rangement").exists()


def test_mettre_a_jour_activite_reutilise_categorie_existante():
    foyer = FoyerFactory()
    cuisine = CategorieFactory(foyer=foyer, nom="Cuisine")
    rangement = CategorieFactory(foyer=foyer, nom="Rangement")
    activite = ActiviteFactory(foyer=foyer, categorie=cuisine, titre="X")

    # Casse différente : doit retomber sur la catégorie existante.
    mettre_a_jour_activite(activite, titre="X", categorie_nom="rangement")

    activite.refresh_from_db()
    assert activite.categorie_id == rangement.pk
    assert Categorie.objects.filter(foyer=foyer).count() == 2


def test_mettre_a_jour_activite_normalise_le_titre():
    foyer = FoyerFactory()
    activite = ActiviteFactory(foyer=foyer)

    mettre_a_jour_activite(
        activite, titre="  Sortir les poubelles  ", categorie_nom="Maison"
    )

    activite.refresh_from_db()
    assert activite.titre == "Sortir les poubelles"


def test_mettre_a_jour_activite_preserve_les_evaluations():
    from comptes.tests.factories import UserFactory
    from evaluations.models import Evaluation
    from evaluations.tests.factories import EvaluationFactory

    foyer = FoyerFactory()
    user = UserFactory()
    activite = ActiviteFactory(foyer=foyer, titre="Avant")
    evaluation = EvaluationFactory(user=user, activite=activite)

    mettre_a_jour_activite(
        activite, titre="Après", categorie_nom="Nouvelle catégorie"
    )

    # L'évaluation pointe toujours sur la même ligne, intacte.
    assert Evaluation.objects.filter(pk=evaluation.pk).exists()
    evaluation.refresh_from_db()
    assert evaluation.activite_id == activite.pk


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


def test_lister_activites_annote_evaluee_par_user_si_fourni():
    # Imports locaux : `evaluations` dépend d'`activites`, donc l'inverse
    # ne doit pas être un import top-level.
    from comptes.tests.factories import UserFactory
    from evaluations.tests.factories import EvaluationFactory

    foyer = FoyerFactory()
    user = UserFactory()
    cat = CategorieFactory(foyer=foyer)
    a_evaluee = ActiviteFactory(foyer=foyer, categorie=cat, titre="A")
    ActiviteFactory(foyer=foyer, categorie=cat, titre="B")
    EvaluationFactory(user=user, activite=a_evaluee)

    groupes = lister_activites_par_categorie(foyer, user=user)

    by_titre = {a.titre: a for a in groupes[cat]}
    assert by_titre["A"].evaluee_par_user is True
    assert by_titre["B"].evaluee_par_user is False


def test_lister_activites_annote_ignore_evaluations_d_autres_users():
    from comptes.tests.factories import UserFactory
    from evaluations.tests.factories import EvaluationFactory

    foyer = FoyerFactory()
    moi = UserFactory()
    autre = UserFactory()
    cat = CategorieFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer, categorie=cat)
    EvaluationFactory(user=autre, activite=activite)

    groupes = lister_activites_par_categorie(foyer, user=moi)

    assert list(groupes[cat])[0].evaluee_par_user is False
