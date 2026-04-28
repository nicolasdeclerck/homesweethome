from django.test import Client
from django.urls import reverse

from activites.tests.factories import ActiviteFactory
from evaluations.models import Evaluation
from evaluations.tests.factories import EvaluationFactory
from foyer.tests.factories import FoyerFactory, MembreFoyerFactory


def _url(activite):
    return reverse("evaluations:activite-evaluer", kwargs={"activite_id": activite.pk})


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


def test_get_anonymous_redirects_to_login():
    activite = ActiviteFactory()
    client = Client()

    response = client.get(_url(activite))

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


def test_get_activite_d_un_autre_foyer_renvoie_404():
    membre = MembreFoyerFactory()
    activite_autre_foyer = ActiviteFactory()  # foyer différent
    client = Client()
    client.force_login(membre.user)

    response = client.get(_url(activite_autre_foyer))

    assert response.status_code == 404


def test_get_activite_du_foyer_renvoie_200_avec_form_vide():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer, titre="Faire les courses")
    client = Client()
    client.force_login(membre.user)

    response = client.get(_url(activite))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Faire les courses" in content
    assert "Vos évaluations" in content


def test_get_pre_remplit_form_si_evaluation_existante():
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

    response = client.get(_url(activite))

    content = response.content.decode("utf-8")
    # Le label `selected` est appliqué sur la pilule de la valeur courante.
    assert 'value="4"\n                       checked' in content
    assert 'value="2"\n                       checked' in content
    assert 'value="5"\n                       checked' in content


def test_get_affiche_evaluation_de_l_autre_membre_en_lecture_seule():
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

    response = client.get(_url(activite))

    content = response.content.decode("utf-8")
    assert "Camille" in content
    assert "5/5" in content


def test_get_indique_si_autre_membre_n_a_pas_evalue():
    foyer = FoyerFactory()
    moi = MembreFoyerFactory(foyer=foyer)
    MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer)
    client = Client()
    client.force_login(moi.user)

    response = client.get(_url(activite))

    content = response.content.decode("utf-8")
    assert "Pas encore évalué" in content


def test_get_indique_si_user_seul_dans_foyer():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer)
    client = Client()
    client.force_login(membre.user)

    response = client.get(_url(activite))

    content = response.content.decode("utf-8")
    assert "seul" in content


# ---------------------------------------------------------------------------
# POST — création / mise à jour
# ---------------------------------------------------------------------------


def test_post_cree_l_evaluation_redirect_fallback():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer)
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        _url(activite),
        data={"charge_mentale": 4, "charge_physique": 3, "duree": 2},
    )

    assert response.status_code == 302
    assert reverse("activites:activite-liste") in response.url
    evaluation = Evaluation.objects.get(user=membre.user, activite=activite)
    assert evaluation.charge_mentale == 4
    assert evaluation.charge_physique == 3
    assert evaluation.duree == 2


def test_post_htmx_renvoie_fragment_avec_hx_trigger():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer)
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        _url(activite),
        data={"charge_mentale": 1, "charge_physique": 1, "duree": 1},
        headers={"hx-request": "true"},
    )

    assert response.status_code == 200
    assert response["HX-Trigger"] == "evaluation-enregistree"
    content = response.content.decode("utf-8")
    assert "Évaluation enregistrée." in content


def test_post_met_a_jour_l_evaluation_existante():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer)
    EvaluationFactory(
        user=membre.user,
        activite=activite,
        charge_mentale=1,
        charge_physique=1,
        duree=1,
    )
    client = Client()
    client.force_login(membre.user)

    client.post(
        _url(activite),
        data={"charge_mentale": 5, "charge_physique": 4, "duree": 3},
    )

    assert Evaluation.objects.filter(user=membre.user, activite=activite).count() == 1
    evaluation = Evaluation.objects.get(user=membre.user, activite=activite)
    assert (evaluation.charge_mentale, evaluation.charge_physique, evaluation.duree) == (
        5,
        4,
        3,
    )


def test_post_refuse_valeur_hors_echelle_renvoie_400_htmx():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer)
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        _url(activite),
        data={"charge_mentale": 0, "charge_physique": 3, "duree": 3},
        headers={"hx-request": "true"},
    )

    assert response.status_code == 400
    assert not Evaluation.objects.filter(user=membre.user, activite=activite).exists()


def test_post_refuse_valeur_hors_echelle_fallback_400():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer)
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        _url(activite),
        data={"charge_mentale": 6, "charge_physique": 3, "duree": 3},
    )

    assert response.status_code == 400


def test_post_activite_autre_foyer_renvoie_404():
    membre = MembreFoyerFactory()
    activite_autre_foyer = ActiviteFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        _url(activite_autre_foyer),
        data={"charge_mentale": 3, "charge_physique": 3, "duree": 3},
    )

    assert response.status_code == 404
    assert not Evaluation.objects.filter(activite=activite_autre_foyer).exists()
