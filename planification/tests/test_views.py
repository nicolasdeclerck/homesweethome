from datetime import date

from django.test import Client
from django.urls import reverse

from activites.tests.factories import ActiviteFactory
from comptes.tests.factories import UserFactory
from foyer.tests.factories import FoyerFactory, MembreFoyerFactory
from planification.models import Affectation, PeriodePlanification
from planification.tests.factories import (
    AffectationFactory,
    PeriodePlanificationFactory,
)

# ---------------------------------------------------------------------------
# PeriodesListView
# ---------------------------------------------------------------------------


def test_liste_anonymous_redirects_to_login():
    client = Client()

    response = client.get(reverse("planification:periode-liste"))

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


def test_liste_authentifie_etat_vide():
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.get(reverse("planification:periode-liste"))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Planification" in content
    assert "Aucune période pour le moment" in content


def test_liste_affiche_les_periodes_du_foyer():
    membre = MembreFoyerFactory()
    PeriodePlanificationFactory(
        foyer=membre.foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 7),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("planification:periode-liste"))

    content = response.content.decode("utf-8")
    assert "01/05/2026" in content
    assert "07/05/2026" in content


def test_liste_n_affiche_pas_les_periodes_d_un_autre_foyer():
    membre = MembreFoyerFactory()
    autre_membre = MembreFoyerFactory()
    PeriodePlanificationFactory(
        foyer=autre_membre.foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 7),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("planification:periode-liste"))

    content = response.content.decode("utf-8")
    assert "01/05/2026" not in content
    assert "Aucune période" in content


def test_liste_contient_le_lien_sidebar_planification():
    membre = MembreFoyerFactory()

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("planification:periode-liste"))

    content = response.content.decode("utf-8")
    assert "Planification" in content
    expected_url = reverse("planification:periode-liste")
    assert expected_url in content


# ---------------------------------------------------------------------------
# PeriodeCreateView
# ---------------------------------------------------------------------------


def test_create_get_non_htmx_redirige_vers_la_liste():
    user = UserFactory()
    client = Client()
    client.force_login(user)

    response = client.get(reverse("planification:periode-create"))

    assert response.status_code == 302
    assert response.url == reverse("planification:periode-liste")


def test_create_get_htmx_renvoie_le_form():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.get(
        reverse("planification:periode-create"),
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Nouvelle période" in content
    assert 'name="date_debut"' in content
    assert 'name="date_fin"' in content


def test_create_post_non_htmx_cree_et_redirige():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        reverse("planification:periode-create"),
        {"date_debut": "2026-05-01", "date_fin": "2026-05-07"},
    )

    assert response.status_code == 302
    assert response.url == reverse("planification:periode-liste")
    assert PeriodePlanification.objects.filter(foyer=membre.foyer).count() == 1


def test_create_post_htmx_renvoie_200_avec_hx_trigger():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        reverse("planification:periode-create"),
        {"date_debut": "2026-05-01", "date_fin": "2026-05-07"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert response["HX-Trigger"] == "periodes-mises-a-jour"
    assert PeriodePlanification.objects.filter(foyer=membre.foyer).count() == 1


def test_create_post_htmx_dates_incoherentes_renvoie_400():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.post(
        reverse("planification:periode-create"),
        {"date_debut": "2026-05-07", "date_fin": "2026-05-01"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 400
    assert "HX-Trigger" not in response
    assert PeriodePlanification.objects.filter(foyer=membre.foyer).count() == 0
    content = response.content.decode("utf-8")
    assert "postérieure" in content


def test_create_post_htmx_chevauchement_renvoie_400():
    membre = MembreFoyerFactory()
    PeriodePlanificationFactory(
        foyer=membre.foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 10),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse("planification:periode-create"),
        {"date_debut": "2026-05-05", "date_fin": "2026-05-15"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 400
    assert PeriodePlanification.objects.filter(foyer=membre.foyer).count() == 1
    content = response.content.decode("utf-8")
    assert "chevauche" in content


def test_create_anonymous_redirects_to_login():
    client = Client()

    response = client.post(
        reverse("planification:periode-create"),
        {"date_debut": "2026-05-01", "date_fin": "2026-05-07"},
    )

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


# ---------------------------------------------------------------------------
# PeriodesListeFragmentView
# ---------------------------------------------------------------------------


def test_liste_fragment_renvoie_la_liste_du_foyer():
    membre = MembreFoyerFactory()
    PeriodePlanificationFactory(
        foyer=membre.foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 7),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("planification:periode-liste-fragment"))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "01/05/2026" in content
    assert 'id="periodes-compteur"' in content
    assert 'hx-swap-oob="true"' in content


def test_liste_fragment_anonymous_redirects_to_login():
    client = Client()

    response = client.get(reverse("planification:periode-liste-fragment"))

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


# ---------------------------------------------------------------------------
# PeriodeDetailView
# ---------------------------------------------------------------------------


def test_detail_anonymous_redirects_to_login():
    client = Client()
    response = client.get(
        reverse("planification:periode-detail", kwargs={"periode_id": 1})
    )

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


def test_detail_affiche_les_jours_de_la_periode():
    membre = MembreFoyerFactory()
    periode = PeriodePlanificationFactory(
        foyer=membre.foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 3),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.get(
        reverse("planification:periode-detail", kwargs={"periode_id": periode.pk})
    )

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # Trois jours rendus → 3 boutons « + Ajouter une affectation ».
    assert content.count("+ Ajouter une affectation") == 3


def test_detail_affiche_les_affectations_existantes():
    foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    membre.user.first_name = "Camille"
    membre.user.save()
    activite = ActiviteFactory(foyer=foyer, titre="Vaisselle")
    periode = PeriodePlanificationFactory(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 3),
    )
    AffectationFactory(
        periode=periode,
        activite=activite,
        membre=membre,
        jour=date(2026, 5, 2),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.get(
        reverse("planification:periode-detail", kwargs={"periode_id": periode.pk})
    )

    content = response.content.decode("utf-8")
    assert "Vaisselle" in content
    assert "Camille" in content


def test_detail_pour_periode_d_un_autre_foyer_renvoie_404():
    membre = MembreFoyerFactory()
    autre_membre = MembreFoyerFactory()
    periode_autre = PeriodePlanificationFactory(foyer=autre_membre.foyer)

    client = Client()
    client.force_login(membre.user)
    response = client.get(
        reverse(
            "planification:periode-detail",
            kwargs={"periode_id": periode_autre.pk},
        )
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# AffectationCreateView
# ---------------------------------------------------------------------------


def test_affectation_create_post_htmx_cree_l_affectation():
    foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 7),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse(
            "planification:affectation-create", kwargs={"periode_id": periode.pk}
        ),
        {
            "activite_id": activite.pk,
            "membre_id": membre.pk,
            "jour": "2026-05-03",
        },
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert Affectation.objects.filter(periode=periode).count() == 1


def test_affectation_create_pour_periode_d_un_autre_foyer_renvoie_404():
    membre = MembreFoyerFactory()
    autre_membre = MembreFoyerFactory()
    periode_autre = PeriodePlanificationFactory(foyer=autre_membre.foyer)
    activite = ActiviteFactory(foyer=membre.foyer)

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse(
            "planification:affectation-create",
            kwargs={"periode_id": periode_autre.pk},
        ),
        {
            "activite_id": activite.pk,
            "membre_id": membre.pk,
            "jour": "2026-05-03",
        },
    )

    assert response.status_code == 404
    assert Affectation.objects.count() == 0


def test_affectation_create_avec_activite_d_un_autre_foyer_renvoie_404():
    foyer = FoyerFactory()
    autre_foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite_autre = ActiviteFactory(foyer=autre_foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 7),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse(
            "planification:affectation-create", kwargs={"periode_id": periode.pk}
        ),
        {
            "activite_id": activite_autre.pk,
            "membre_id": membre.pk,
            "jour": "2026-05-03",
        },
    )

    assert response.status_code == 404


def test_affectation_create_avec_membre_d_un_autre_foyer_renvoie_404():
    foyer = FoyerFactory()
    autre_foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    autre_membre = MembreFoyerFactory(foyer=autre_foyer)
    activite = ActiviteFactory(foyer=foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 7),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse(
            "planification:affectation-create", kwargs={"periode_id": periode.pk}
        ),
        {
            "activite_id": activite.pk,
            "membre_id": autre_membre.pk,
            "jour": "2026-05-03",
        },
    )

    assert response.status_code == 404


def test_affectation_create_avec_jour_hors_periode_renvoie_400():
    foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer)
    periode = PeriodePlanificationFactory(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 7),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse(
            "planification:affectation-create", kwargs={"periode_id": periode.pk}
        ),
        {
            "activite_id": activite.pk,
            "membre_id": membre.pk,
            "jour": "2026-05-15",
        },
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 400
    assert Affectation.objects.count() == 0


# ---------------------------------------------------------------------------
# AffectationDeleteView
# ---------------------------------------------------------------------------


def test_affectation_delete_post_supprime_l_affectation():
    membre = MembreFoyerFactory()
    activite = ActiviteFactory(foyer=membre.foyer)
    periode = PeriodePlanificationFactory(
        foyer=membre.foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 7),
    )
    affectation = AffectationFactory(
        periode=periode,
        activite=activite,
        membre=membre,
        jour=date(2026, 5, 3),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse(
            "planification:affectation-delete",
            kwargs={"affectation_id": affectation.pk},
        ),
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert not Affectation.objects.filter(pk=affectation.pk).exists()


def test_affectation_delete_pour_autre_foyer_renvoie_404():
    membre = MembreFoyerFactory()
    autre_membre = MembreFoyerFactory()
    affectation_autre = AffectationFactory(
        periode=PeriodePlanificationFactory(foyer=autre_membre.foyer),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.post(
        reverse(
            "planification:affectation-delete",
            kwargs={"affectation_id": affectation_autre.pk},
        ),
    )

    assert response.status_code == 404
    assert Affectation.objects.filter(pk=affectation_autre.pk).exists()


# ---------------------------------------------------------------------------
# AffectationsListeFragmentView
# ---------------------------------------------------------------------------


def test_affectations_fragment_renvoie_la_liste():
    foyer = FoyerFactory()
    membre = MembreFoyerFactory(foyer=foyer)
    activite = ActiviteFactory(foyer=foyer, titre="Vaisselle")
    periode = PeriodePlanificationFactory(
        foyer=foyer,
        date_debut=date(2026, 5, 1),
        date_fin=date(2026, 5, 3),
    )
    AffectationFactory(
        periode=periode,
        activite=activite,
        membre=membre,
        jour=date(2026, 5, 2),
    )

    client = Client()
    client.force_login(membre.user)
    response = client.get(
        reverse(
            "planification:affectations-liste-fragment",
            kwargs={"periode_id": periode.pk},
        ),
    )

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Vaisselle" in content


def test_affectations_fragment_pour_autre_foyer_renvoie_404():
    membre = MembreFoyerFactory()
    autre_membre = MembreFoyerFactory()
    periode_autre = PeriodePlanificationFactory(foyer=autre_membre.foyer)

    client = Client()
    client.force_login(membre.user)
    response = client.get(
        reverse(
            "planification:affectations-liste-fragment",
            kwargs={"periode_id": periode_autre.pk},
        ),
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Sidebar : item « Planification » présent
# ---------------------------------------------------------------------------


def test_sidebar_contient_le_lien_planification_quand_user_connecte():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.get(reverse("activites:activite-liste"))

    content = response.content.decode("utf-8")
    expected_url = reverse("planification:periode-liste")
    # Lien « Planification » présent dans la sidebar (depuis n'importe quelle page).
    assert expected_url in content
    assert "Planification" in content


def test_sidebar_marque_planification_active_sur_la_page_liste():
    membre = MembreFoyerFactory()
    client = Client()
    client.force_login(membre.user)

    response = client.get(reverse("planification:periode-liste"))

    content = response.content.decode("utf-8")
    assert 'aria-current="page"' in content
