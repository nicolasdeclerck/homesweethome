from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.utils import timezone

from comptes.tests.factories import UserFactory
from foyer.models import Foyer, Invitation, MembreFoyer
from foyer.tests.factories import (
    FoyerFactory,
    InvitationFactory,
    MembreFoyerFactory,
)


def test_foyer_str_returns_nom():
    foyer = Foyer(nom="Foyer de Nicolas")
    assert str(foyer) == "Foyer de Nicolas"


def test_membrefoyer_str_includes_user_and_foyer():
    user = UserFactory(email="alice@example.com")
    foyer = FoyerFactory(nom="Foyer test")
    membre = MembreFoyer(user=user, foyer=foyer)

    rendered = str(membre)

    assert "alice@example.com" in rendered
    assert "Foyer test" in rendered


def test_membrefoyer_user_is_unique():
    membre = MembreFoyerFactory()
    autre_foyer = FoyerFactory()

    # `MembreFoyerFactory` est idempotente sur `user` (cf. signal de bascule),
    # on tape donc directement l'ORM pour vérifier la contrainte OneToOneField.
    with pytest.raises(IntegrityError):
        MembreFoyer.objects.create(user=membre.user, foyer=autre_foyer)


def test_deleting_user_cascades_to_membrefoyer():
    membre = MembreFoyerFactory()
    user = membre.user
    membre_pk = membre.pk

    user.delete()

    assert not MembreFoyer.objects.filter(pk=membre_pk).exists()


def test_deleting_foyer_cascades_to_membrefoyer():
    membre = MembreFoyerFactory()
    foyer = membre.foyer
    membre_pk = membre.pk

    foyer.delete()

    assert not MembreFoyer.objects.filter(pk=membre_pk).exists()


def test_deleting_user_creator_is_protected():
    user = UserFactory()
    FoyerFactory(cree_par=user)

    with pytest.raises(ProtectedError):
        user.delete()


def test_invitation_str_includes_email_and_foyer_name():
    foyer = FoyerFactory(nom="Foyer test")
    invitation = InvitationFactory(foyer=foyer, email="marie@example.com")

    assert "marie@example.com" in str(invitation)
    assert "Foyer test" in str(invitation)


def test_invitation_token_is_generated_and_unique():
    invitation_a = InvitationFactory()
    invitation_b = InvitationFactory()

    assert invitation_a.token
    assert invitation_b.token
    assert invitation_a.token != invitation_b.token


def test_invitation_default_expiration_is_seven_days_in_the_future():
    invitation = InvitationFactory()

    delta = invitation.date_expiration - timezone.now()
    assert timedelta(days=6, hours=23) < delta <= timedelta(days=7)


def test_invitation_est_expiree_when_expiration_is_past():
    invitation = InvitationFactory(
        date_expiration=timezone.now() - timedelta(seconds=1)
    )

    assert invitation.est_expiree is True
    assert invitation.est_utilisable is False


def test_invitation_est_utilisable_only_when_en_attente_and_not_expired():
    invitation = InvitationFactory()
    assert invitation.est_utilisable is True

    invitation.statut = Invitation.Statut.ANNULEE
    assert invitation.est_utilisable is False


def test_invitation_unique_constraint_blocks_a_second_pending_for_same_pair():
    foyer = FoyerFactory()
    InvitationFactory(foyer=foyer, email="marie@example.com")

    with pytest.raises(IntegrityError):
        InvitationFactory(foyer=foyer, email="marie@example.com")


def test_invitation_unique_constraint_allows_new_pending_after_acceptee():
    foyer = FoyerFactory()
    premiere = InvitationFactory(
        foyer=foyer, email="marie@example.com", statut=Invitation.Statut.ACCEPTEE
    )

    seconde = InvitationFactory(foyer=foyer, email="marie@example.com")

    assert premiere.pk != seconde.pk
    assert seconde.statut == Invitation.Statut.EN_ATTENTE


def test_deleting_foyer_cascades_to_invitations():
    invitation = InvitationFactory()
    foyer = invitation.foyer
    invitation_pk = invitation.pk

    foyer.delete()

    assert not Invitation.objects.filter(pk=invitation_pk).exists()
