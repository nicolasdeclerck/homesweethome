import pytest

from comptes.tests.factories import UserFactory
from foyer.models import Foyer, MembreFoyer
from foyer.services import compute_default_foyer_name, get_or_create_foyer_for_user


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
    assert MembreFoyer.objects.filter(user=user, foyer=foyer).exists()


def test_get_or_create_foyer_is_idempotent():
    user = UserFactory()
    foyer_first = get_or_create_foyer_for_user(user)

    foyer_second = get_or_create_foyer_for_user(user)

    assert foyer_first == foyer_second
    assert Foyer.objects.count() == 1
    assert MembreFoyer.objects.filter(user=user).count() == 1
