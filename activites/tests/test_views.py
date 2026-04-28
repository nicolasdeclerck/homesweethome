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


def test_liste_affiche_un_bouton_crayon_par_activite():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer, titre="Vaisselle")

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("activites:activite-liste"))

    content = response.content.decode("utf-8")
    expected_url = reverse(
        "activites:activite-modifier", kwargs={"activite_id": activite.pk}
    )
    assert 'hx-get="' + expected_url + '"' in content
    assert 'aria-label="Modifier Vaisselle"' in content


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


def test_create_get_non_htmx_redirige_vers_la_liste():
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.get(reverse("activites:activite-create"))

    assert response.status_code == 302
    assert response.url == reverse("activites:activite-liste")


def test_create_get_htmx_renvoie_le_form_de_creation():
    """GET HTMX → fragment "création" frais (utilisé pour réinitialiser
    le drawer après édition)."""
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.get(
        reverse("activites:activite-create"),
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert 'action="' + reverse("activites:activite-create") + '"' in content
    assert "Nouvelle activité" in content
    assert "Ajouter" in content


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
# ActiviteUpdateView
# ---------------------------------------------------------------------------


def test_update_anonymous_redirects_to_login():
    client = Client()
    response = client.get(
        reverse("activites:activite-modifier", kwargs={"activite_id": 1})
    )

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


def test_update_get_non_htmx_redirige_vers_la_liste():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer)

    client = Client()
    client.force_login(membre.user)
    response = client.get(
        reverse("activites:activite-modifier", kwargs={"activite_id": activite.pk})
    )

    assert response.status_code == 302
    assert response.url == reverse("activites:activite-liste")


def test_update_get_htmx_renvoie_le_form_prerempli():
    membre = MembreFoyerFactory()
    cuisine = CategorieFactory(foyer=membre.foyer, nom="Cuisine")
    activite = ActiviteFactory(
        foyer=membre.foyer, categorie=cuisine, titre="Faire la vaisselle"
    )

    client = Client()
    client.force_login(membre.user)
    response = client.get(
        reverse("activites:activite-modifier", kwargs={"activite_id": activite.pk}),
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert 'value="Faire la vaisselle"' in content
    assert 'value="Cuisine"' in content
    # L'apostrophe est échappée par Django (`&#x27;`) — d'où le match en deux temps.
    assert "Modifier" in content and "activité" in content
    assert "Enregistrer" in content
    expected_action = reverse(
        "activites:activite-modifier", kwargs={"activite_id": activite.pk}
    )
    assert 'action="' + expected_action + '"' in content


def test_update_get_pour_activite_d_un_autre_foyer_renvoie_404():
    membre = MembreFoyerFactory()
    autre_membre = MembreFoyerFactory()
    activite_autre = ActiviteFactory(foyer=autre_membre.foyer)

    client = Client()
    client.force_login(membre.user)
    response = client.get(
        reverse(
            "activites:activite-modifier", kwargs={"activite_id": activite_autre.pk}
        ),
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 404


def test_update_post_htmx_modifie_l_activite():
    membre = MembreFoyerFactory()
    cuisine = CategorieFactory(foyer=membre.foyer, nom="Cuisine")
    activite = ActiviteFactory(
        foyer=membre.foyer, categorie=cuisine, titre="Vaisselle"
    )

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse("activites:activite-modifier", kwargs={"activite_id": activite.pk}),
        {"titre": "Vider le lave-vaisselle", "categorie_nom": "Rangement"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert response["HX-Trigger"] == "activites-mises-a-jour"
    activite.refresh_from_db()
    assert activite.titre == "Vider le lave-vaisselle"
    assert activite.categorie.nom == "Rangement"
    # Toujours une seule activité dans le foyer (pas de double).
    assert Activite.objects.filter(foyer=membre.foyer).count() == 1


def test_update_post_pour_activite_d_un_autre_foyer_renvoie_404():
    membre = MembreFoyerFactory()
    autre_membre = MembreFoyerFactory()
    activite_autre = ActiviteFactory(
        foyer=autre_membre.foyer, titre="Original"
    )

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse(
            "activites:activite-modifier", kwargs={"activite_id": activite_autre.pk}
        ),
        {"titre": "Hijack", "categorie_nom": "X"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 404
    activite_autre.refresh_from_db()
    assert activite_autre.titre == "Original"


def test_update_post_htmx_avec_titre_vide_renvoie_400():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer, titre="Avant")

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse("activites:activite-modifier", kwargs={"activite_id": activite.pk}),
        {"titre": "  ", "categorie_nom": "Cuisine"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 400
    assert "HX-Trigger" not in response
    activite.refresh_from_db()
    assert activite.titre == "Avant"


def test_update_post_preserve_les_evaluations():
    from evaluations.models import Evaluation
    from evaluations.tests.factories import EvaluationFactory

    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer, titre="Avant")
    evaluation = EvaluationFactory(user=membre.user, activite=activite)

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse("activites:activite-modifier", kwargs={"activite_id": activite.pk}),
        {"titre": "Après", "categorie_nom": "Nouvelle catégorie"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert Evaluation.objects.filter(pk=evaluation.pk).exists()


def test_update_post_non_htmx_modifie_et_redirige():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer, titre="Avant")

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse("activites:activite-modifier", kwargs={"activite_id": activite.pk}),
        {"titre": "Après", "categorie_nom": "Cuisine"},
    )

    assert response.status_code == 302
    assert response.url == reverse("activites:activite-liste")
    activite.refresh_from_db()
    assert activite.titre == "Après"


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
    # La ligne ouvre désormais le drawer d'édition/évaluation (HTMX),
    # plus de page dédiée d'évaluation.
    expected_url = reverse(
        "activites:activite-modifier", kwargs={"activite_id": activite.pk}
    )
    assert 'hx-get="' + expected_url + '"' in content
    assert 'aria-label="Évaluer Faire la vaisselle"' in content


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


# ---------------------------------------------------------------------------
# Drawer combiné : édition + évaluation dans le même formulaire
# ---------------------------------------------------------------------------


def test_create_get_htmx_affiche_les_3_criteres_d_evaluation():
    """En mode création, le drawer doit déjà exposer les 3 rate-blocks."""
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.get(
        reverse("activites:activite-create"), HTTP_HX_REQUEST="true"
    )

    content = response.content.decode("utf-8")
    assert "Vos évaluations" in content
    assert 'name="charge_mentale"' in content
    assert 'name="charge_physique"' in content
    assert 'name="duree"' in content


def test_create_get_htmx_n_affiche_pas_le_bloc_autre_membre():
    """En création il n'y a pas encore d'activité : pas de bloc autre membre."""
    foyer = MembreFoyerFactory().foyer
    moi = MembreFoyerFactory(foyer=foyer)
    autre = MembreFoyerFactory(foyer=foyer)
    autre.user.first_name = "Camille"
    autre.user.save()

    client = Client()
    client.force_login(moi.user)
    response = client.get(
        reverse("activites:activite-create"), HTTP_HX_REQUEST="true"
    )

    content = response.content.decode("utf-8")
    assert "Camille" not in content
    assert "Pas encore évalué" not in content


def test_create_post_avec_eval_cree_l_activite_et_l_evaluation():
    from evaluations.models import Evaluation

    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        reverse("activites:activite-create"),
        {
            "titre": "Faire la vaisselle",
            "categorie_nom": "Cuisine",
            "charge_mentale": 4,
            "charge_physique": 2,
            "duree": 5,
        },
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    activite = Activite.objects.get(foyer=membre.foyer)
    evaluation = Evaluation.objects.get(user=membre.user, activite=activite)
    assert (evaluation.charge_mentale, evaluation.charge_physique, evaluation.duree) == (
        4,
        2,
        5,
    )


def test_create_post_sans_eval_cree_l_activite_seule():
    from evaluations.models import Evaluation

    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    client.post(
        reverse("activites:activite-create"),
        {"titre": "Faire la vaisselle", "categorie_nom": "Cuisine"},
    )

    activite = Activite.objects.get(foyer=membre.foyer)
    assert not Evaluation.objects.filter(user=membre.user, activite=activite).exists()


def test_create_post_eval_partielle_renvoie_400():
    """Tout-ou-rien sur l'évaluation : 1 critère sur 3 → form invalide."""
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        reverse("activites:activite-create"),
        {
            "titre": "Vaisselle",
            "categorie_nom": "Cuisine",
            "charge_mentale": 3,
            # charge_physique et duree manquants
        },
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 400
    assert Activite.objects.filter(foyer=membre.foyer).count() == 0


def test_update_get_htmx_pre_remplit_l_evaluation_existante():
    from evaluations.tests.factories import EvaluationFactory

    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer)
    EvaluationFactory(
        user=membre.user,
        activite=activite,
        charge_mentale=4,
        charge_physique=2,
        duree=5,
    )

    client = Client()
    client.force_login(membre.user)
    response = client.get(
        reverse("activites:activite-modifier", kwargs={"activite_id": activite.pk}),
        HTTP_HX_REQUEST="true",
    )

    content = response.content.decode("utf-8")
    # Sur les 3 rate-blocks, la pilule cochée correspond à la valeur stockée.
    assert 'value="4"\n                               checked' in content
    assert 'value="2"\n                               checked' in content
    assert 'value="5"\n                               checked' in content


def test_update_post_htmx_upsert_evaluation_avec_l_activite():
    from evaluations.models import Evaluation

    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer, titre="Avant")

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse("activites:activite-modifier", kwargs={"activite_id": activite.pk}),
        {
            "titre": "Après",
            "categorie_nom": "Cuisine",
            "charge_mentale": 5,
            "charge_physique": 4,
            "duree": 3,
        },
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    activite.refresh_from_db()
    assert activite.titre == "Après"
    evaluation = Evaluation.objects.get(user=membre.user, activite=activite)
    assert (evaluation.charge_mentale, evaluation.charge_physique, evaluation.duree) == (
        5,
        4,
        3,
    )


def test_update_drawer_affiche_evaluation_de_l_autre_membre():
    from evaluations.tests.factories import EvaluationFactory
    from foyer.tests.factories import FoyerFactory

    foyer = FoyerFactory()
    moi = MembreFoyerFactory(foyer=foyer)
    autre = MembreFoyerFactory(foyer=foyer)
    autre.user.first_name = "Camille"
    autre.user.save()
    activite = ActiviteFactory(foyer=foyer)
    EvaluationFactory(
        user=autre.user,
        activite=activite,
        charge_mentale=5,
        charge_physique=2,
        duree=1,
    )

    client = Client()
    client.force_login(moi.user)
    response = client.get(
        reverse("activites:activite-modifier", kwargs={"activite_id": activite.pk}),
        HTTP_HX_REQUEST="true",
    )

    content = response.content.decode("utf-8")
    assert "Camille" in content
    assert "5/5" in content


def test_update_drawer_indique_si_autre_membre_n_a_pas_evalue():
    from foyer.tests.factories import FoyerFactory

    foyer = FoyerFactory()
    moi = MembreFoyerFactory(foyer=foyer)
    MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer)

    client = Client()
    client.force_login(moi.user)
    response = client.get(
        reverse("activites:activite-modifier", kwargs={"activite_id": activite.pk}),
        HTTP_HX_REQUEST="true",
    )

    content = response.content.decode("utf-8")
    assert "Pas encore évalué" in content


def test_update_drawer_indique_si_user_seul_dans_foyer():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer)

    client = Client()
    client.force_login(membre.user)
    response = client.get(
        reverse("activites:activite-modifier", kwargs={"activite_id": activite.pk}),
        HTTP_HX_REQUEST="true",
    )

    content = response.content.decode("utf-8")
    assert "seul" in content
