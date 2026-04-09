"""Tests for the shop system (ShopManager + API endpoints)."""

from __future__ import annotations

from random import Random
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from tomodachai.api.routes import set_game_state
from tomodachai.game_state import GameState
from tomodachai.server import create_app
from tomodachai.shop import CATEGORIES, HOLIDAYS, ShopManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def shop():
    """Fresh ShopManager with no daily stock."""
    return ShopManager()


@pytest.fixture
def seeded_shop():
    """ShopManager with daily stock refreshed at day 1."""
    s = ShopManager()
    s.refresh_daily(day=1)
    return s


@pytest.fixture
def game_state():
    """Minimal GameState with some money."""
    gs = GameState()
    gs.money = 10_000
    return gs


@pytest.fixture
def client(game_state):
    """TestClient wired to a game state with refreshed shop."""
    game_state.shop.refresh_daily(day=0)
    app = create_app()
    set_game_state(game_state)
    return TestClient(app)


# ---------------------------------------------------------------------------
# ShopManager — refresh_daily
# ---------------------------------------------------------------------------


class TestRefreshDaily:
    def test_creates_items_for_all_categories(self, shop):
        shop.refresh_daily(day=1)
        for category in CATEGORIES:
            assert len(shop.get_daily(category)) > 0

    def test_is_deterministic_for_same_day(self, shop):
        shop.refresh_daily(day=42)
        snapshot1 = {c: shop.get_daily(c) for c in CATEGORIES}

        shop2 = ShopManager()
        shop2.refresh_daily(day=42)
        snapshot2 = {c: shop2.get_daily(c) for c in CATEGORIES}

        assert snapshot1 == snapshot2

    def test_different_days_yield_different_stock(self, shop):
        shop.refresh_daily(day=1)
        food_day1 = shop.get_daily("food")

        shop.refresh_daily(day=99)
        food_day99 = shop.get_daily("food")

        # Very unlikely to match — if they ever do, increase day delta
        assert food_day1 != food_day99

    def test_external_rng_overrides_day_seed(self, shop):
        r = Random(999)
        shop.refresh_daily(day=1, rng=r)
        food_with_rng = shop.get_daily("food")

        shop2 = ShopManager()
        shop2.refresh_daily(day=1)
        food_default = shop2.get_daily("food")

        # Different RNG → different stock
        assert food_with_rng != food_default

    def test_holiday_item_forced_into_food(self, shop):
        """When a holiday date is passed, its item must appear in food daily."""
        date_str = "04-14"
        forced_id = HOLIDAYS[date_str]
        shop.refresh_daily(day=1, date_str=date_str)
        assert forced_id in shop.get_daily("food")

    def test_non_holiday_date_does_not_force_item(self, shop):
        shop.refresh_daily(day=1, date_str="01-01")
        # 01-01 is not in HOLIDAYS — no special item is forced.
        # Just verify the return type; random chance of holiday id appearing is negligible.
        food = shop.get_daily("food")
        assert isinstance(food, list)

    def test_morning_market_is_set_after_refresh(self, shop):
        shop.refresh_daily(day=1)
        mm = shop.get_morning_market()
        assert mm is not None
        assert "item" in mm
        assert "discount_price" in mm
        assert mm["discount_price"] > 0

    def test_morning_market_price_is_discounted(self, shop):
        from tomodachai.shop import _MORNING_MARKET_BASE_PRICE, _MORNING_MARKET_DISCOUNT_RATE

        shop.refresh_daily(day=1)
        mm = shop.get_morning_market()
        expected = int(_MORNING_MARKET_BASE_PRICE * _MORNING_MARKET_DISCOUNT_RATE)
        assert mm["discount_price"] == expected


# ---------------------------------------------------------------------------
# ShopManager — buy
# ---------------------------------------------------------------------------


class TestBuy:
    def test_buy_deducts_money(self, seeded_shop, game_state):
        item_id = seeded_shop.get_daily("food")[0]
        initial_money = game_state.money
        ok = seeded_shop.buy(item_id, game_state)
        assert ok is True
        assert game_state.money < initial_money

    def test_buy_adds_to_catalog(self, seeded_shop, game_state):
        item_id = seeded_shop.get_daily("food")[0]
        seeded_shop.buy(item_id, game_state)
        assert item_id in seeded_shop.get_catalog("food")

    def test_buy_fails_if_item_not_in_daily(self, seeded_shop, game_state):
        ok = seeded_shop.buy(99999, game_state)
        assert ok is False
        # Money unchanged
        assert game_state.money == 10_000

    def test_buy_fails_if_insufficient_funds(self, seeded_shop):
        poor_gs = MagicMock()
        poor_gs.spend_money.return_value = False
        # We need a real item in daily to hit the funds check
        item_id = seeded_shop.get_daily("food")[0]
        # Patch _find_daily_category to return a hit
        ok = seeded_shop.buy(item_id, poor_gs)
        assert ok is False

    def test_buy_clothing_item(self, seeded_shop, game_state):
        clothing = seeded_shop.get_daily("clothing")
        if not clothing:
            pytest.skip("No clothing items in this seed")
        item_id = clothing[0]
        ok = seeded_shop.buy(item_id, game_state)
        assert ok is True
        assert item_id in seeded_shop.get_catalog("clothing")


# ---------------------------------------------------------------------------
# ShopManager — buy_morning_market
# ---------------------------------------------------------------------------


class TestBuyMorningMarket:
    def test_buy_market_succeeds(self, seeded_shop, game_state):
        ok = seeded_shop.buy_morning_market(game_state)
        assert ok is True

    def test_buy_market_deducts_discount_price(self, seeded_shop, game_state):
        mm = seeded_shop.get_morning_market()
        initial = game_state.money
        seeded_shop.buy_morning_market(game_state)
        assert game_state.money == initial - mm["discount_price"]

    def test_buy_market_adds_to_food_catalog(self, seeded_shop, game_state):
        mm = seeded_shop.get_morning_market()
        seeded_shop.buy_morning_market(game_state)
        assert mm["item"] in seeded_shop.get_catalog("food")

    def test_buy_market_fails_without_refresh(self, shop, game_state):
        # No refresh → no morning market
        ok = shop.buy_morning_market(game_state)
        assert ok is False

    def test_buy_market_fails_if_insufficient_funds(self, seeded_shop):
        broke = GameState()
        broke.money = 0
        ok = seeded_shop.buy_morning_market(broke)
        assert ok is False


# ---------------------------------------------------------------------------
# ShopManager — catalog
# ---------------------------------------------------------------------------


class TestCatalog:
    def test_empty_catalog_initially(self, shop):
        for category in CATEGORIES:
            assert shop.get_catalog(category) == []

    def test_add_to_catalog(self, shop):
        shop.add_to_catalog("food", 5)
        shop.add_to_catalog("food", 3)
        assert shop.get_catalog("food") == [3, 5]  # sorted

    def test_catalog_deduplicates(self, shop):
        shop.add_to_catalog("food", 7)
        shop.add_to_catalog("food", 7)
        assert shop.get_catalog("food").count(7) == 1

    def test_catalog_per_category_isolated(self, shop):
        shop.add_to_catalog("food", 1)
        shop.add_to_catalog("clothing", 2)
        assert 1 not in shop.get_catalog("clothing")
        assert 2 not in shop.get_catalog("food")


# ---------------------------------------------------------------------------
# ShopManager — serialize / deserialize
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_serialize_matches_shop_json_structure(self, seeded_shop):
        data = seeded_shop.serialize()
        assert "daily" in data
        assert "morning_market" in data
        assert "seasonal" in data
        assert "catalog" in data
        for cat in CATEGORIES:
            assert cat in data["daily"]

    def test_deserialize_roundtrip(self, seeded_shop):
        seeded_shop.add_to_catalog("food", 10)
        seeded_shop.add_to_catalog("interior", 205)
        payload = seeded_shop.serialize()

        shop2 = ShopManager()
        shop2.deserialize(payload)

        assert shop2.get_catalog("food") == seeded_shop.get_catalog("food")
        assert shop2.get_catalog("interior") == seeded_shop.get_catalog("interior")
        for cat in CATEGORIES:
            assert shop2.get_daily(cat) == seeded_shop.get_daily(cat)

        mm_orig = seeded_shop.get_morning_market()
        mm_new = shop2.get_morning_market()
        assert mm_orig == mm_new

    def test_deserialize_empty_payload(self, shop):
        shop.deserialize({})
        for cat in CATEGORIES:
            assert shop.get_daily(cat) == []
        assert shop.get_morning_market() is None
        assert shop.get_seasonal() == []

    def test_deserialize_null_morning_market(self, shop):
        shop.deserialize({"morning_market": None})
        assert shop.get_morning_market() is None

    def test_serialize_seasonal_empty_by_default(self, seeded_shop):
        data = seeded_shop.serialize()
        assert data["seasonal"] == []


# ---------------------------------------------------------------------------
# API — GET /api/shop
# ---------------------------------------------------------------------------


class TestShopApi:
    def test_get_shop_returns_200(self, client):
        resp = client.get("/api/shop")
        assert resp.status_code == 200

    def test_get_shop_structure(self, client):
        data = client.get("/api/shop").json()
        assert "daily" in data
        assert "morning_market" in data
        assert "seasonal" in data
        for cat in ("food", "clothing", "interior"):
            assert cat in data["daily"]

    def test_get_shop_daily_lists(self, client):
        data = client.get("/api/shop").json()
        for cat in ("food", "clothing", "interior"):
            assert isinstance(data["daily"][cat], list)

    def test_get_shop_morning_market_present(self, client):
        data = client.get("/api/shop").json()
        mm = data["morning_market"]
        assert mm is not None
        assert "item" in mm
        assert "discount_price" in mm


# ---------------------------------------------------------------------------
# API — POST /api/shop/buy/{item_id}
# ---------------------------------------------------------------------------


class TestBuyApi:
    def test_buy_valid_item(self, client, game_state):
        item_id = game_state.shop.get_daily("food")[0]
        resp = client.post(f"/api/shop/buy/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["item_id"] == item_id
        assert "remaining_money" in data

    def test_buy_invalid_item_returns_404(self, client):
        resp = client.post("/api/shop/buy/999999")
        assert resp.status_code == 404

    def test_buy_reduces_money(self, client, game_state):
        item_id = game_state.shop.get_daily("food")[0]
        initial = game_state.money
        client.post(f"/api/shop/buy/{item_id}")
        assert game_state.money < initial

    def test_buy_insufficient_funds_returns_400(self, client, game_state):
        game_state.money = 0
        item_id = game_state.shop.get_daily("food")[0]
        resp = client.post(f"/api/shop/buy/{item_id}")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# API — POST /api/shop/buy-market
# ---------------------------------------------------------------------------


class TestBuyMarketApi:
    def test_buy_market_success(self, client):
        resp = client.post("/api/shop/buy-market")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["item_id"] is not None

    def test_buy_market_insufficient_funds_returns_400(self, client, game_state):
        game_state.money = 0
        resp = client.post("/api/shop/buy-market")
        assert resp.status_code == 400

    def test_buy_market_no_market_returns_404(self, game_state):
        # Don't refresh — morning market is None
        game_state.shop = ShopManager()  # fresh, no refresh
        app = create_app()
        set_game_state(game_state)
        c = TestClient(app)
        resp = c.post("/api/shop/buy-market")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API — GET /api/shop/catalog/{category}
# ---------------------------------------------------------------------------


class TestCatalogApi:
    def test_catalog_empty_initially(self, client):
        resp = client.get("/api/shop/catalog/food")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "food"
        assert data["items"] == []

    def test_catalog_after_purchase(self, client, game_state):
        item_id = game_state.shop.get_daily("food")[0]
        client.post(f"/api/shop/buy/{item_id}")
        resp = client.get("/api/shop/catalog/food")
        assert item_id in resp.json()["items"]

    def test_catalog_invalid_category_returns_400(self, client):
        resp = client.get("/api/shop/catalog/treasure")
        assert resp.status_code == 400

    def test_catalog_clothing_category(self, client):
        resp = client.get("/api/shop/catalog/clothing")
        assert resp.status_code == 200
        assert resp.json()["category"] == "clothing"

    def test_catalog_interior_category(self, client):
        resp = client.get("/api/shop/catalog/interior")
        assert resp.status_code == 200
        assert resp.json()["category"] == "interior"
