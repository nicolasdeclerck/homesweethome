import pytest
from django.db import IntegrityError

from comptes.tests.factories import UserFactory
from foyer.models import Foyer, MembreFoyer
from foyer.tests.factories import FoyerFactory, MembreFoyerFactory


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
    user = UserFactory()
    MembreFoyerFactory(user=user)

    with pytest.raises(IntegrityError):
        MembreFoyerFactory(user=user)


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
