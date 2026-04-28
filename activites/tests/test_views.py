from django.test import Client
from django.urls import reverse

from activites.models import Activite, Categorie
from activites.tests.factories import ActiviteFactory, CategorieFactory
from comptes.tests.factories import UserFactory
from foyer.tests.factories import MembreFoyerFactory

# ---------------------------------------------------------------------------
# ActivitesListView
# ---------------------------------------------------------------------------


def test_liste_anonymous_redirects_to_login():
    client = Client()

    response = client.get(reverse("activites:activite-liste"))

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


def test_liste_authentifie_retourne_200_avec_etat_vide():
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.get(reverse("activites:activite-liste"))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Activités" in content
    assert "Aucune activité pour le moment" in content


def test_liste_affiche_les_activites_groupees_par_categorie():
    membre = MembreFoyerFactory()
    foyer = membre.foyer
    cuisine = CategorieFactory(foyer=foyer, nom="Cuisine")
    salle = CategorieFactory(foyer=foyer, nom="Salle de bain")
    ActiviteFactory(foyer=foyer, categorie=cuisine, titre="Faire la vaisselle")
    ActiviteFactory(foyer=foyer, categorie=salle, titre="Nettoyer la douche")

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("activites:activite-liste"))

    content = response.content.decode("utf-8")
    assert "Cuisine" in content
    assert "Faire la vaisselle" in content
    assert "Salle de bain" in content
    assert "Nettoyer la douche" in content


def test_liste_n_affiche_pas_les_activites_d_un_autre_foyer():
    membre = MembreFoyerFactory()
    autre_membre = MembreFoyerFactory()
    ActiviteFactory(foyer=autre_membre.foyer, titre="Tâche d'un autre foyer")

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("activites:activite-liste"))

    assert "Tâche d'un autre foyer" not in response.content.decode("utf-8")


def test_liste_propose_les_categories_existantes_dans_le_datalist():
    membre = MembreFoyerFactory()
    CategorieFactory(foyer=membre.foyer, nom="Cuisine")

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("activites:activite-liste"))

    content = response.content.decode("utf-8")
    assert 'list="categories-existantes"' in content
    assert '<option value="Cuisine"></option>' in content


# ---------------------------------------------------------------------------
# ActiviteCreateView
# ---------------------------------------------------------------------------


def test_create_get_redirige_vers_la_liste():
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.get(reverse("activites:activite-create"))

    assert response.status_code == 302
    assert response.url == reverse("activites:activite-liste")


def test_create_post_non_htmx_cree_et_redirige():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        reverse("activites:activite-create"),
        {"titre": "Faire les courses", "categorie_nom": "Courses"},
    )

    assert response.status_code == 302
    assert response.url == reverse("activites:activite-liste")
    assert Activite.objects.filter(foyer=membre.foyer).count() == 1
    assert Categorie.objects.filter(foyer=membre.foyer, nom="Courses").exists()


def test_create_post_htmx_renvoie_200_avec_hx_trigger():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        reverse("activites:activite-create"),
        {"titre": "Faire la vaisselle", "categorie_nom": "Cuisine"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert response["HX-Trigger"] == "activites-mises-a-jour"
    assert Activite.objects.filter(foyer=membre.foyer).count() == 1


def test_create_post_htmx_avec_titre_vide_renvoie_400():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        reverse("activites:activite-create"),
        {"titre": "  ", "categorie_nom": "Cuisine"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 400
    assert "HX-Trigger" not in response
    assert Activite.objects.filter(foyer=membre.foyer).count() == 0


def test_create_post_non_htmx_avec_titre_vide_renvoie_400():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        reverse("activites:activite-create"),
        {"titre": "", "categorie_nom": "Cuisine"},
    )

    assert response.status_code == 400
    assert Activite.objects.filter(foyer=membre.foyer).count() == 0


def test_create_post_reutilise_categorie_existante_case_insensitive():
    membre = MembreFoyerFactory()
    CategorieFactory(foyer=membre.foyer, nom="Cuisine")
    client = Client()
    client.force_login(membre.user)

    client.post(
        reverse("activites:activite-create"),
        {"titre": "Vaisselle", "categorie_nom": "cuisine"},
    )

    assert Categorie.objects.filter(foyer=membre.foyer).count() == 1


def test_create_anonymous_redirects_to_login():
    client = Client()

    response = client.post(
        reverse("activites:activite-create"),
        {"titre": "X", "categorie_nom": "Y"},
    )

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


# ---------------------------------------------------------------------------
# ActivitesListeFragmentView
# ---------------------------------------------------------------------------


def test_liste_fragment_renvoie_la_liste_du_foyer_courant():
    membre = MembreFoyerFactory()
    cuisine = CategorieFactory(foyer=membre.foyer, nom="Cuisine")
    ActiviteFactory(foyer=membre.foyer, categorie=cuisine, titre="Vaisselle")

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("activites:activite-liste-fragment"))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Cuisine" in content
    assert "Vaisselle" in content


def test_liste_fragment_anonymous_redirects_to_login():
    client = Client()

    response = client.get(reverse("activites:activite-liste-fragment"))

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


def test_liste_fragment_contient_le_span_oob_compteur():
    membre = MembreFoyerFactory()
    ActiviteFactory(foyer=membre.foyer)

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("activites:activite-liste-fragment"))

    content = response.content.decode("utf-8")
    assert 'id="activites-compteur"' in content
    assert 'hx-swap-oob="true"' in content
    assert "1 activité" in content


def test_liste_full_page_n_active_pas_l_oob_compteur():
    """Le span OOB ne doit s'activer que sur la réponse fragment."""
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.get(reverse("activites:activite-liste"))

    content = response.content.decode("utf-8")
    assert "hx-swap-oob" not in content


def test_liste_affiche_pill_a_evaluer_si_user_n_a_pas_evalue():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer, titre="Faire la vaisselle")

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("activites:activite-liste"))

    content = response.content.decode("utf-8")
    assert "À évaluer" in content
    assert "Évaluée" not in content
    # La ligne doit être un lien vers l'écran d'évaluation.
    assert reverse(
        "evaluations:activite-evaluer", kwargs={"activite_id": activite.pk}
    ) in content


def test_liste_affiche_pill_evaluee_si_user_a_evalue():
    from evaluations.tests.factories import EvaluationFactory

    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer)
    EvaluationFactory(user=membre.user, activite=activite)

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("activites:activite-liste"))

    content = response.content.decode("utf-8")
    assert "Évaluée" in content
    assert "À évaluer" not in content
