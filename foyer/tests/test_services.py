from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from comptes.tests.factories import UserFactory
from foyer.models import Foyer, Invitation, MembreFoyer
from foyer.services import (
    EmailDansAutreFoyerError,
    EmailDejaMembreError,
    InvitationDejaEnAttenteError,
    InvitationInvalideError,
    accepter_invitation,
    annuler_invitation,
    compute_default_foyer_name,
    creer_invitation,
    get_invitation_utilisable,
    get_or_create_foyer_for_user,
)
from foyer.tests.factories import (
    FoyerFactory,
    InvitationFactory,
    MembreFoyerFactory,
)


@pytest.mark.parametrize(
    "email, expected",
    [
        ("nicolas@example.com", "Foyer de Nicolas"),
        ("nicolas.declerck@example.com", "Foyer de Nicolas"),
        ("nicolas+tag@example.com", "Foyer de Nicolas"),
        ("ALICE@example.com", "Foyer de Alice"),
        ("françois@example.com", "Foyer de François"),
        ("1234@example.com", "Mon foyer"),
        ("...@example.com", "Mon foyer"),
        ("@example.com", "Mon foyer"),
        ("plain", "Mon foyer"),
        ("", "Mon foyer"),
    ],
)
def test_compute_default_foyer_name(email, expected):
    assert compute_default_foyer_name(email) == expected


def test_get_or_create_foyer_creates_when_missing():
    user = UserFactory(email="alice@example.com")

    foyer = get_or_create_foyer_for_user(user)

    assert foyer.nom == "Foyer de Alice"
    assert foyer.cree_par == user
    assert MembreFoyer.objects.filter(user=user, foyer=foyer).exists()


def test_get_or_create_foyer_is_idempotent():
    user = UserFactory()
    foyer_first = get_or_create_foyer_for_user(user)

    foyer_second = get_or_create_foyer_for_user(user)

    assert foyer_first == foyer_second
    assert Foyer.objects.count() == 1
    assert MembreFoyer.objects.filter(user=user).count() == 1


# ---------------------------------------------------------------------------
# creer_invitation
# ---------------------------------------------------------------------------


def test_creer_invitation_happy_path_normalises_email_and_trims_prenom():
    foyer = FoyerFactory()

    invitation = creer_invitation(
        foyer=foyer,
        email="  Marie@Example.COM  ",
        prenom="  Marie  ",
        cree_par=foyer.cree_par,
    )

    assert invitation.email == "marie@example.com"
    assert invitation.prenom == "Marie"
    assert invitation.statut == Invitation.Statut.EN_ATTENTE
    assert invitation.cree_par == foyer.cree_par
    assert invitation.token


def test_creer_invitation_refuse_si_email_deja_membre_du_meme_foyer():
    membre = MembreFoyerFactory()

    with pytest.raises(EmailDejaMembreError):
        creer_invitation(
            foyer=membre.foyer,
            email=membre.user.email,
            prenom="Doublon",
            cree_par=membre.foyer.cree_par,
        )


def test_creer_invitation_refuse_si_email_dans_un_autre_foyer():
    autre_membre = MembreFoyerFactory()
    foyer = FoyerFactory()

    with pytest.raises(EmailDansAutreFoyerError):
        creer_invitation(
            foyer=foyer,
            email=autre_membre.user.email,
            prenom="Camille",
            cree_par=foyer.cree_par,
        )


def test_creer_invitation_refuse_doublon_en_attente_et_renvoie_existante():
    foyer = FoyerFactory()
    existante = creer_invitation(
        foyer=foyer,
        email="marie@example.com",
        prenom="Marie",
        cree_par=foyer.cree_par,
    )

    with pytest.raises(InvitationDejaEnAttenteError) as exc_info:
        creer_invitation(
            foyer=foyer,
            email="MARIE@example.com",
            prenom="Marie",
            cree_par=foyer.cree_par,
        )

    assert exc_info.value.invitation.pk == existante.pk


def test_creer_invitation_recupere_l_existante_si_la_contrainte_unique_se_declenche():
    """Filet anti-race-condition : si une autre transaction a inséré une
    invitation entre notre `filter().first()` et notre `create()`, la
    contrainte ``unique_invitation_en_attente_par_foyer_email`` lève une
    `IntegrityError` qu'on convertit en `InvitationDejaEnAttenteError`
    portant l'invitation gagnante.

    On simule la course en patchant la 1re recherche de duplicat pour qu'elle
    renvoie ``None`` alors qu'une invitation existe déjà — ce qui force le
    chemin "création → IntegrityError → re-fetch".
    """
    foyer = FoyerFactory()
    deja_creee = InvitationFactory(
        foyer=foyer,
        email="marie@example.com",
        cree_par=foyer.cree_par,
    )

    real_filter = Invitation.objects.filter

    def fake_filter(*args, **kwargs):
        # On masque uniquement la requête "y a-t-il déjà une invitation
        # EN_ATTENTE pour ce couple ?", pour simuler la fenêtre de course.
        if (
            kwargs.get("statut") == Invitation.Statut.EN_ATTENTE
            and "foyer" in kwargs
            and "email" in kwargs
        ):
            mocked_qs = mock.MagicMock()
            mocked_qs.first.return_value = None
            return mocked_qs
        return real_filter(*args, **kwargs)

    with mock.patch.object(Invitation.objects, "filter", side_effect=fake_filter):
        with pytest.raises(InvitationDejaEnAttenteError) as exc_info:
            creer_invitation(
                foyer=foyer,
                email="marie@example.com",
                prenom="Marie",
                cree_par=foyer.cree_par,
            )

    assert exc_info.value.invitation.pk == deja_creee.pk
    # Aucune nouvelle invitation n'a été créée par-dessus la contrainte.
    assert (
        Invitation.objects.filter(
            foyer=foyer,
            email="marie@example.com",
            statut=Invitation.Statut.EN_ATTENTE,
        ).count()
        == 1
    )


def test_creer_invitation_acceptee_anterieure_ne_bloque_pas():
    foyer = FoyerFactory()
    InvitationFactory(
        foyer=foyer,
        email="marie@example.com",
        statut=Invitation.Statut.ANNULEE,
    )

    nouvelle = creer_invitation(
        foyer=foyer,
        email="marie@example.com",
        prenom="Marie",
        cree_par=foyer.cree_par,
    )

    assert nouvelle.statut == Invitation.Statut.EN_ATTENTE


# ---------------------------------------------------------------------------
# annuler_invitation
# ---------------------------------------------------------------------------


def test_annuler_invitation_passe_au_statut_annulee():
    invitation = InvitationFactory()

    annuler_invitation(invitation, par_user=invitation.cree_par)

    invitation.refresh_from_db()
    assert invitation.statut == Invitation.Statut.ANNULEE


def test_annuler_invitation_refuse_si_non_createur():
    invitation = InvitationFactory()
    autre_user = UserFactory()

    with pytest.raises(InvitationInvalideError):
        annuler_invitation(invitation, par_user=autre_user)


def test_annuler_invitation_refuse_si_deja_acceptee():
    invitation = InvitationFactory(statut=Invitation.Statut.ACCEPTEE)

    with pytest.raises(InvitationInvalideError):
        annuler_invitation(invitation, par_user=invitation.cree_par)


# ---------------------------------------------------------------------------
# get_invitation_utilisable
# ---------------------------------------------------------------------------


def test_get_invitation_utilisable_returns_invitation_quand_valide():
    invitation = InvitationFactory()

    found = get_invitation_utilisable(invitation.token)

    assert found is not None
    assert found.pk == invitation.pk


def test_get_invitation_utilisable_returns_none_pour_token_inconnu():
    InvitationFactory()
    assert get_invitation_utilisable("token-inconnu") is None


def test_get_invitation_utilisable_returns_none_si_expiree():
    invitation = InvitationFactory(
        date_expiration=timezone.now() - timedelta(seconds=1)
    )

    assert get_invitation_utilisable(invitation.token) is None


@pytest.mark.parametrize(
    "statut",
    [Invitation.Statut.ACCEPTEE, Invitation.Statut.ANNULEE],
)
def test_get_invitation_utilisable_returns_none_si_statut_pas_en_attente(statut):
    invitation = InvitationFactory(statut=statut)

    assert get_invitation_utilisable(invitation.token) is None


# ---------------------------------------------------------------------------
# accepter_invitation
# ---------------------------------------------------------------------------


def test_accepter_invitation_cree_user_et_membre_quand_compte_inexistant():
    foyer = FoyerFactory()
    invitation = InvitationFactory(
        foyer=foyer,
        email="marie@example.com",
        prenom="Marie",
    )

    user = accepter_invitation(invitation=invitation, nouveau_password="azerty1234!")

    assert user.email == "marie@example.com"
    assert user.first_name == "Marie"
    assert user.check_password("azerty1234!")
    assert MembreFoyer.objects.filter(user=user, foyer=foyer).exists()
    invitation.refresh_from_db()
    assert invitation.statut == Invitation.Statut.ACCEPTEE


def test_accepter_invitation_avec_user_existant_oprhelin_l_ajoute_au_foyer():
    user_existant = UserFactory(email="marie@example.com")
    invitation = InvitationFactory(email="marie@example.com")

    user = accepter_invitation(invitation=invitation, user_existant=user_existant)

    assert user.pk == user_existant.pk
    assert MembreFoyer.objects.filter(user=user_existant, foyer=invitation.foyer).exists()
    invitation.refresh_from_db()
    assert invitation.statut == Invitation.Statut.ACCEPTEE


def test_accepter_invitation_refuse_si_user_existant_email_different():
    user_existant = UserFactory(email="autre@example.com")
    invitation = InvitationFactory(email="marie@example.com")

    with pytest.raises(InvitationInvalideError):
        accepter_invitation(invitation=invitation, user_existant=user_existant)


def test_accepter_invitation_refuse_sans_password_ni_user_existant():
    invitation = InvitationFactory()

    with pytest.raises(InvitationInvalideError):
        accepter_invitation(invitation=invitation)


def test_accepter_invitation_refuse_si_invitation_pas_utilisable():
    invitation = InvitationFactory(statut=Invitation.Statut.ANNULEE)

    with pytest.raises(InvitationInvalideError):
        accepter_invitation(invitation=invitation, nouveau_password="azerty1234!")


def test_accepter_invitation_refuse_si_email_deja_un_compte():
    UserFactory(email="marie@example.com")
    invitation = InvitationFactory(email="marie@example.com")

    with pytest.raises(InvitationInvalideError):
        accepter_invitation(invitation=invitation, nouveau_password="azerty1234!")


def test_accepter_invitation_refuse_si_user_existant_a_deja_un_foyer():
    autre_membre = MembreFoyerFactory()
    invitation = InvitationFactory(email=autre_membre.user.email)

    with pytest.raises(InvitationInvalideError):
        accepter_invitation(invitation=invitation, user_existant=autre_membre.user)


def test_accepter_invitation_email_normalisation_avec_casse_differente():
    invitation = InvitationFactory(email="marie@example.com")

    user = accepter_invitation(invitation=invitation, nouveau_password="azerty1234!")

    assert user.email == "marie@example.com"
    User = get_user_model()
    assert User.objects.filter(email="marie@example.com").count() == 1
