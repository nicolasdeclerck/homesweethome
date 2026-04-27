"""Configuration pytest globale.

Les fixtures spécifiques à un domaine doivent être définies dans le
`conftest.py` de l'app concernée (ex. `foyer/tests/conftest.py`).
"""
import pytest


@pytest.fixture(autouse=True)
def _enable_db_access_for_all_tests(db):
    """Active automatiquement l'accès à la base pour tous les tests."""
    return db
