import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


def test_str_returns_email():
    user = User(email="alice@example.com")
    assert str(user) == "alice@example.com"


def test_create_user_hashes_password():
    user = User.objects.create_user(email="alice@example.com", password="azerty1234!")
    assert user.email == "alice@example.com"
    assert user.password != "azerty1234!"
    assert user.check_password("azerty1234!")
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False


def test_create_user_normalises_email_domain():
    user = User.objects.create_user(email="alice@EXAMPLE.com", password="azerty1234!")
    assert user.email == "alice@example.com"


def test_create_user_requires_email():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="azerty1234!")


def test_create_superuser_sets_flags():
    user = User.objects.create_superuser(
        email="admin@example.com", password="azerty1234!"
    )
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.check_password("azerty1234!")


def test_create_superuser_requires_is_staff():
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            email="admin@example.com", password="x", is_staff=False
        )


def test_create_superuser_requires_is_superuser():
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            email="admin@example.com", password="x", is_superuser=False
        )
