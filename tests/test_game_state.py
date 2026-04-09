"""Tests for GameState catalog and new game.json fields."""

import pytest

from tomodachai.game_state import GameState

# ---------------------------------------------------------------------------
# Catalog helpers
# ---------------------------------------------------------------------------

def test_catalog_defaults():
    gs = GameState()
    assert gs.catalog == {"food": [], "clothing": [], "interior": [], "treasure": []}


def test_add_to_catalog_basic():
    gs = GameState()
    gs.add_to_catalog("food", 7)
    assert gs.catalog["food"] == [7]


def test_add_to_catalog_deduplicates():
    gs = GameState()
    gs.add_to_catalog("food", 7)
    gs.add_to_catalog("food", 7)
    assert gs.catalog["food"].count(7) == 1


def test_add_to_catalog_multiple_categories():
    gs = GameState()
    gs.add_to_catalog("food", 2)
    gs.add_to_catalog("clothing", 12)
    gs.add_to_catalog("interior", 5)
    gs.add_to_catalog("treasure", 1)
    assert gs.catalog["food"] == [2]
    assert gs.catalog["clothing"] == [12]
    assert gs.catalog["interior"] == [5]
    assert gs.catalog["treasure"] == [1]


def test_add_to_catalog_invalid_category():
    gs = GameState()
    with pytest.raises(ValueError, match="Unknown catalog category"):
        gs.add_to_catalog("weapon", 99)


def test_is_in_catalog_true():
    gs = GameState()
    gs.add_to_catalog("food", 4)
    assert gs.is_in_catalog("food", 4) is True


def test_is_in_catalog_false():
    gs = GameState()
    assert gs.is_in_catalog("food", 99) is False


def test_is_in_catalog_invalid_category():
    gs = GameState()
    with pytest.raises(ValueError, match="Unknown catalog category"):
        gs.is_in_catalog("weapon", 1)


def test_catalog_independent_per_category():
    gs = GameState()
    gs.add_to_catalog("food", 3)
    assert gs.is_in_catalog("clothing", 3) is False


# ---------------------------------------------------------------------------
# ending_credit_seen field
# ---------------------------------------------------------------------------

def test_ending_credit_seen_default():
    gs = GameState()
    assert gs.ending_credit_seen is False


def test_ending_credit_seen_mutable():
    gs = GameState()
    gs.ending_credit_seen = True
    assert gs.ending_credit_seen is True
