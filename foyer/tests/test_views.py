from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from comptes.tests.factories import UserFactory
from foyer.models import Foyer, Invitation, MembreFoyer
from foyer.tests.factories import (
    FoyerFactory,
    InvitationFactory,
    MembreFoyerFactory,
)

# ---------------------------------------------------------------------------
# MonFoyerView
# ---------------------------------------------------------------------------


def test_get_mon_foyer_anonymous_redirects_to_login():
    client = Client()

    response = client.get(reverse("foyer:mon-foyer"))

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


def test_get_mon_foyer_authenticated_returns_200_and_creates_foyer():
    user = UserFactory(email="alice@example.com")
    client = Client()
    client.force_login(user)

    response = client.get(reverse("foyer:mon-foyer"))

    assert response.status_code == 200
    assert MembreFoyer.objects.filter(user=user).exists()
    content = response.content.decode("utf-8")
    assert "Foyer de Alice" in content
    assert "alice@example.com" in content
    assert "Membre depuis" in content


def test_get_mon_foyer_does_not_create_duplicate_foyer():
    user = UserFactory()
    client = Client()
    client.force_login(user)

    client.get(reverse("foyer:mon-foyer"))
    client.get(reverse("foyer:mon-foyer"))

    assert Foyer.objects.count() == 1
    assert MembreFoyer.objects.filter(user=user).count() == 1


def test_mon_foyer_affiche_section_invitation_pour_le_createur():
    membre = MembreFoyerFactory()
    membre.foyer.cree_par = membre.user
    membre.foyer.save(update_fields=["cree_par"])
    client = Client()
    client.force_login(membre.user)

    response = client.get(reverse("foyer:mon-foyer"))

    content = response.content.decode("utf-8")
    assert "Inviter un membre" in content
    assert "Générer le lien" in content


def test_mon_foyer_n_affiche_pas_section_invitation_pour_un_membre_non_createur():
    foyer = FoyerFactory()
    autre_membre = MembreFoyerFactory(foyer=foyer)
    client = Client()
    client.force_login(autre_membre.user)

    response = client.get(reverse("foyer:mon-foyer"))

    content = response.content.decode("utf-8")
    assert "Inviter un membre" not in content
    assert "Générer le lien" not in content


def test_mon_foyer_liste_les_invitations_en_attente():
    membre = MembreFoyerFactory()
    foyer = membre.foyer
    foyer.cree_par = membre.user
    foyer.save(update_fields=["cree_par"])
    InvitationFactory(foyer=foyer, prenom="Marie", email="marie@example.com")

    client = Client()
    client.force_login(membre.user)
    response = client.get(reverse("foyer:mon-foyer"))

    content = response.content.decode("utf-8")
    assert "Marie" in content
    assert "marie@example.com" in content


# ---------------------------------------------------------------------------
# InvitationCreateView
# ---------------------------------------------------------------------------


def _setup_createur():
    membre = MembreFoyerFactory()
    membre.foyer.cree_par = membre.user
    membre.foyer.save(update_fields=["cree_par"])
    return membre.user, membre.foyer


def test_invitation_create_anonymous_redirects_to_login():
    response = Client().post(reverse("foyer:invitation-create"), {})

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url


def test_invitation_create_non_createur_returns_403():
    foyer = FoyerFactory()
    autre = MembreFoyerFactory(foyer=foyer)
    client = Client()
    client.force_login(autre.user)

    response = client.post(reverse("foyer:invitation-create"), {})

    assert response.status_code == 403


def test_invitation_create_post_valid_data_renvoie_le_lien():
    user, foyer = _setup_createur()
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("foyer:invitation-create"),
        {"email": "marie@example.com", "prenom": "Marie"},
    )

    assert response.status_code == 200
    invitation = Invitation.objects.get(foyer=foyer, email="marie@example.com")
    assert invitation.statut == Invitation.Statut.EN_ATTENTE
    content = response.content.decode("utf-8")
    assert invitation.token in content
    assert "Copier le lien" in content
    assert response["HX-Trigger"] == "invitations-mises-a-jour"


def test_invitation_create_post_invalid_email_renvoie_le_form_avec_erreurs():
    user, _foyer = _setup_createur()
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("foyer:invitation-create"),
        {"email": "pas-un-email", "prenom": "Marie"},
    )

    assert response.status_code == 400
    assert not Invitation.objects.exists()
    assert b"Inviter un membre" in response.content


def test_invitation_create_post_email_deja_membre_renvoie_le_form_avec_erreur():
    user, foyer = _setup_createur()
    autre = MembreFoyerFactory(foyer=foyer)
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("foyer:invitation-create"),
        {"email": autre.user.email, "prenom": "Doublon"},
    )

    assert response.status_code == 400
    assert not Invitation.objects.exists()


def test_invitation_create_post_email_dans_autre_foyer_renvoie_le_form_avec_erreur():
    user, _foyer = _setup_createur()
    autre = MembreFoyerFactory()
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("foyer:invitation-create"),
        {"email": autre.user.email, "prenom": "Camille"},
    )

    assert response.status_code == 400
    assert not Invitation.objects.exists()


def test_invitation_create_post_doublon_renvoie_le_lien_existant():
    user, foyer = _setup_createur()
    existante = InvitationFactory(
        foyer=foyer, email="marie@example.com", cree_par=user
    )
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("foyer:invitation-create"),
        {"email": "marie@example.com", "prenom": "Marie"},
    )

    assert response.status_code == 200
    assert Invitation.objects.filter(foyer=foyer, email="marie@example.com").count() == 1
    content = response.content.decode("utf-8")
    assert existante.token in content
    assert "déjà en cours" in content.lower()


def test_invitation_create_get_renvoie_le_form_vierge():
    user, _ = _setup_createur()
    client = Client()
    client.force_login(user)

    response = client.get(reverse("foyer:invitation-create"))

    assert response.status_code == 200
    assert b"Inviter un membre" in response.content


# ---------------------------------------------------------------------------
# InvitationsListeView
# ---------------------------------------------------------------------------


def test_invitation_liste_renvoie_les_invitations_en_attente_du_foyer():
    user, foyer = _setup_createur()
    InvitationFactory(foyer=foyer, prenom="Marie", email="marie@example.com")
    InvitationFactory(foyer=foyer, prenom="Camille", email="camille@example.com")
    autre_foyer = FoyerFactory()
    InvitationFactory(foyer=autre_foyer)
    client = Client()
    client.force_login(user)

    response = client.get(reverse("foyer:invitation-liste"))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Marie" in content
    assert "Camille" in content
    assert "marie@example.com" in content
    assert content.count("card pending") == 2  # only this foyer's invitations


def test_invitation_liste_refuse_membre_non_createur():
    foyer = FoyerFactory()
    autre = MembreFoyerFactory(foyer=foyer)
    client = Client()
    client.force_login(autre.user)

    response = client.get(reverse("foyer:invitation-liste"))

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# InvitationLinkView
# ---------------------------------------------------------------------------


def test_invitation_link_view_renvoie_le_lien_pour_invitation_en_attente():
    user, foyer = _setup_createur()
    invitation = InvitationFactory(foyer=foyer, cree_par=user)
    client = Client()
    client.force_login(user)

    response = client.get(reverse("foyer:invitation-lien", kwargs={"pk": invitation.pk}))

    assert response.status_code == 200
    assert invitation.token in response.content.decode("utf-8")


def test_invitation_link_view_renvoie_404_pour_invitation_acceptee():
    user, foyer = _setup_createur()
    invitation = InvitationFactory(
        foyer=foyer, cree_par=user, statut=Invitation.Statut.ACCEPTEE
    )
    client = Client()
    client.force_login(user)

    response = client.get(reverse("foyer:invitation-lien", kwargs={"pk": invitation.pk}))

    assert response.status_code == 404


def test_invitation_link_view_refuse_un_autre_foyer():
    user, _foyer = _setup_createur()
    invitation_autre = InvitationFactory()
    client = Client()
    client.force_login(user)

    response = client.get(
        reverse("foyer:invitation-lien", kwargs={"pk": invitation_autre.pk})
    )

    assert response.status_code == 404


def test_invitation_link_view_refuse_membre_non_createur():
    foyer = FoyerFactory()
    invitation = InvitationFactory(foyer=foyer, cree_par=foyer.cree_par)
    autre = MembreFoyerFactory(foyer=foyer)
    client = Client()
    client.force_login(autre.user)

    response = client.get(
        reverse("foyer:invitation-lien", kwargs={"pk": invitation.pk})
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# InvitationCancelView
# ---------------------------------------------------------------------------


def test_invitation_cancel_passe_l_invitation_a_annulee():
    user, foyer = _setup_createur()
    invitation = InvitationFactory(foyer=foyer, cree_par=user)
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("foyer:invitation-annuler", kwargs={"pk": invitation.pk})
    )

    assert response.status_code == 200
    invitation.refresh_from_db()
    assert invitation.statut == Invitation.Statut.ANNULEE
    assert response["HX-Trigger"] == "invitations-mises-a-jour"


def test_invitation_cancel_renvoie_la_liste_a_jour():
    user, foyer = _setup_createur()
    invitation_a_annuler = InvitationFactory(foyer=foyer, cree_par=user)
    InvitationFactory(foyer=foyer, cree_par=user, prenom="Camille", email="camille@example.com")
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("foyer:invitation-annuler", kwargs={"pk": invitation_a_annuler.pk})
    )

    content = response.content.decode("utf-8")
    assert "Camille" in content
    assert invitation_a_annuler.email not in content


def test_invitation_cancel_refuse_un_autre_foyer():
    user, _ = _setup_createur()
    autre = InvitationFactory()
    client = Client()
    client.force_login(user)

    response = client.post(reverse("foyer:invitation-annuler", kwargs={"pk": autre.pk}))

    assert response.status_code == 404
    autre.refresh_from_db()
    assert autre.statut == Invitation.Statut.EN_ATTENTE


def test_invitation_cancel_refuse_membre_non_createur():
    foyer = FoyerFactory()
    invitation = InvitationFactory(foyer=foyer, cree_par=foyer.cree_par)
    autre = MembreFoyerFactory(foyer=foyer)
    client = Client()
    client.force_login(autre.user)

    response = client.post(
        reverse("foyer:invitation-annuler", kwargs={"pk": invitation.pk})
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# AccepterInvitationView (GET)
# ---------------------------------------------------------------------------


def test_accepter_get_token_inconnu_renvoie_410():
    response = Client().get(
        reverse("foyer:invitation-accepter", kwargs={"token": "inconnu"})
    )

    assert response.status_code == 410
    assert b"plus valide" in response.content


def test_accepter_get_token_expire_renvoie_410():
    invitation = InvitationFactory(date_expiration=timezone.now() - timedelta(seconds=1))

    response = Client().get(
        reverse("foyer:invitation-accepter", kwargs={"token": invitation.token})
    )

    assert response.status_code == 410


def test_accepter_get_invitation_annulee_renvoie_410():
    invitation = InvitationFactory(statut=Invitation.Statut.ANNULEE)

    response = Client().get(
        reverse("foyer:invitation-accepter", kwargs={"token": invitation.token})
    )

    assert response.status_code == 410


def test_accepter_get_scenario_nouveau_affiche_form_creation_password():
    invitation = InvitationFactory(email="marie@example.com", prenom="Marie")

    response = Client().get(
        reverse("foyer:invitation-accepter", kwargs={"token": invitation.token})
    )

    content = response.content.decode("utf-8")
    assert response.status_code == 200
    assert "Bienvenue Marie" in content
    assert "Mot de passe" in content
    assert "Confirmer le mot de passe" in content


def test_accepter_get_scenario_user_existant_non_connecte_propose_login():
    UserFactory(email="marie@example.com")
    invitation = InvitationFactory(email="marie@example.com")

    response = Client().get(
        reverse("foyer:invitation-accepter", kwargs={"token": invitation.token})
    )

    content = response.content.decode("utf-8")
    assert "Un compte existe déjà" in content
    assert "Se connecter" in content
    assert "next=" in content


def test_accepter_get_scenario_user_existant_connecte_affiche_confirmation():
    user = UserFactory(email="marie@example.com")
    invitation = InvitationFactory(email="marie@example.com")
    client = Client()
    client.force_login(user)

    response = client.get(
        reverse("foyer:invitation-accepter", kwargs={"token": invitation.token})
    )

    content = response.content.decode("utf-8")
    assert "Confirmez pour rejoindre" in content
    assert "Confirmer le mot de passe" not in content


def test_accepter_get_scenario_user_existant_mauvais_compte_propose_logout():
    invitation = InvitationFactory(email="marie@example.com")
    autre = UserFactory(email="autre@example.com")
    client = Client()
    client.force_login(autre)

    response = client.get(
        reverse("foyer:invitation-accepter", kwargs={"token": invitation.token})
    )

    content = response.content.decode("utf-8")
    assert "Déconnectez-vous" in content


# ---------------------------------------------------------------------------
# AccepterInvitationView (POST)
# ---------------------------------------------------------------------------


def test_accepter_post_scenario_nouveau_cree_user_et_logue_et_redirige():
    invitation = InvitationFactory(email="marie@example.com", prenom="Marie")
    client = Client()

    response = client.post(
        reverse("foyer:invitation-accepter", kwargs={"token": invitation.token}),
        {"password": "azerty1234!", "password_confirm": "azerty1234!"},
    )

    assert response.status_code == 302
    assert response.url == reverse("foyer:mon-foyer")
    invitation.refresh_from_db()
    assert invitation.statut == Invitation.Statut.ACCEPTEE
    assert MembreFoyer.objects.filter(user__email="marie@example.com").exists()
    # session cookie set => connecté
    assert "_auth_user_id" in client.session


def test_accepter_post_scenario_nouveau_password_mismatch_renvoie_form_400():
    invitation = InvitationFactory(email="marie@example.com")

    response = Client().post(
        reverse("foyer:invitation-accepter", kwargs={"token": invitation.token}),
        {"password": "azerty1234!", "password_confirm": "different"},
    )

    assert response.status_code == 400
    assert not MembreFoyer.objects.exists()
    invitation.refresh_from_db()
    assert invitation.statut == Invitation.Statut.EN_ATTENTE


def test_accepter_post_scenario_nouveau_password_trop_faible_renvoie_400():
    invitation = InvitationFactory(email="marie@example.com")

    response = Client().post(
        reverse("foyer:invitation-accepter", kwargs={"token": invitation.token}),
        {"password": "abc", "password_confirm": "abc"},
    )

    assert response.status_code == 400
    invitation.refresh_from_db()
    assert invitation.statut == Invitation.Statut.EN_ATTENTE


def test_accepter_post_scenario_user_existant_connecte_cree_membre():
    user = UserFactory(email="marie@example.com")
    invitation = InvitationFactory(email="marie@example.com")
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("foyer:invitation-accepter", kwargs={"token": invitation.token})
    )

    assert response.status_code == 302
    assert response.url == reverse("foyer:mon-foyer")
    assert MembreFoyer.objects.filter(user=user, foyer=invitation.foyer).exists()
    invitation.refresh_from_db()
    assert invitation.statut == Invitation.Statut.ACCEPTEE


def test_accepter_post_scenario_user_existant_non_connecte_redirige_vers_login():
    UserFactory(email="marie@example.com")
    invitation = InvitationFactory(email="marie@example.com")

    response = Client().post(
        reverse("foyer:invitation-accepter", kwargs={"token": invitation.token}),
        {"password": "azerty1234!", "password_confirm": "azerty1234!"},
    )

    assert response.status_code == 302
    assert reverse("comptes:connexion") in response.url
    invitation.refresh_from_db()
    assert invitation.statut == Invitation.Statut.EN_ATTENTE


def test_accepter_post_token_invalide_renvoie_410():
    response = Client().post(
        reverse("foyer:invitation-accepter", kwargs={"token": "inconnu"}),
        {"password": "azerty1234!", "password_confirm": "azerty1234!"},
    )

    assert response.status_code == 410
