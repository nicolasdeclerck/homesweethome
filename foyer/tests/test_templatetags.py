"""Tests des template tags du domaine `foyer`."""
import pytest

from foyer.templatetags.foyer_tags import initiale


@pytest.mark.parametrize(
    ("entree", "attendu"),
    [
        ("Alice", "A"),
        ("alice", "A"),
        ("Marie-Claire", "MC"),
        ("marie-claire", "MC"),
        ("Jean Pierre", "JP"),
        ("Jean-Pierre Dupont", "JP"),  # tronqué à 2 initiales pour l'avatar
        ("  Anne  ", "A"),
        ("Anne_Marie", "AM"),
        ("", "?"),
        (None, "?"),
        ("---", "?"),
    ],
)
def test_initiale_filter(entree, attendu):
    assert initiale(entree) == attendu
