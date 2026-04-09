"""Shop system — daily stock, morning market, seasonal items, catalog.

Item master data is not defined yet; this module operates on item IDs only.
Actual item definitions will be provided as external data files in a later phase.
"""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tomodachai.game_state import GameState

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Recognised item categories.
CATEGORIES: tuple[str, ...] = ("food", "clothing", "interior")

# Holiday overrides: "MM-DD" → item_id that must appear in daily food pool.
# Example: 4/14 블랙데이 → 짜장면 (placeholder id 99).
HOLIDAYS: dict[str, int] = {
    "04-14": 99,  # 블랙데이 — 짜장면
}

# Default pool sizes drawn from the global item-id range per category.
# These are placeholders until item master data exists.
_DEFAULT_POOL: dict[str, range] = {
    "food": range(1, 101),
    "clothing": range(101, 201),
    "interior": range(201, 301),
}

# How many items appear in the daily shop per category.
_DAILY_COUNT: dict[str, int] = {
    "food": 3,
    "clothing": 2,
    "interior": 1,
}

# Morning market: one food item drawn at a discount each day.
_MORNING_MARKET_DISCOUNT_RATE = 0.6  # 40% off placeholder base price
_MORNING_MARKET_BASE_PRICE = 2500    # placeholder until item master exists


# ---------------------------------------------------------------------------
# ShopManager
# ---------------------------------------------------------------------------


class ShopManager:
    """Manages all shop-related state for one game session.

    Daily stock is regenerated via :meth:`refresh_daily`.
    Catalog persists purchased item IDs per category across refreshes.
    """

    def __init__(self) -> None:
        # category → list of item IDs currently on the daily shelf
        self._daily_items: dict[str, list[int]] = {c: [] for c in CATEGORIES}

        # morning market special deal; None if not active
        self._morning_market: dict | None = None

        # seasonal / event-limited items (IDs only; content added later)
        self._seasonal_items: list[int] = []

        # catalog: category → set of item IDs ever acquired
        self._catalog: dict[str, set[int]] = {c: set() for c in CATEGORIES}

    # ------------------------------------------------------------------
    # Daily refresh
    # ------------------------------------------------------------------

    def refresh_daily(
        self, day: int, rng: Random | None = None, date_str: str | None = None
    ) -> None:
        """Regenerate daily stock for the given game day.

        Args:
            day:      Game day counter (used as RNG seed for determinism).
            rng:      Optional pre-seeded :class:`~random.Random` instance.
                      If *None*, a new one seeded with *day* is created.
            date_str: Current real date as "MM-DD" string (e.g. ``"04-14"``).
                      Used to force-include holiday items.
        """
        r = rng if rng is not None else Random(day)

        for category in CATEGORIES:
            pool = list(_DEFAULT_POOL[category])
            count = _DAILY_COUNT.get(category, 3)
            chosen: list[int] = r.sample(pool, min(count, len(pool)))
            self._daily_items[category] = chosen

        # Force holiday item into food pool.
        if date_str and date_str in HOLIDAYS:
            holiday_item = HOLIDAYS[date_str]
            food_items = self._daily_items["food"]
            if holiday_item not in food_items:
                # Replace last item to keep list length stable.
                if food_items:
                    food_items[-1] = holiday_item
                else:
                    food_items.append(holiday_item)

        # Morning market: one food item at a discount.
        food_pool = list(_DEFAULT_POOL["food"])
        market_item = r.choice(food_pool)
        discount_price = int(_MORNING_MARKET_BASE_PRICE * _MORNING_MARKET_DISCOUNT_RATE)
        self._morning_market = {
            "item": market_item,
            "discount_price": discount_price,
        }

    # ------------------------------------------------------------------
    # Read-only accessors
    # ------------------------------------------------------------------

    def get_daily(self, category: str) -> list[int]:
        """Return item IDs currently on the daily shelf for *category*."""
        return list(self._daily_items.get(category, []))

    def get_morning_market(self) -> dict | None:
        """Return ``{"item": id, "discount_price": int}`` or ``None``."""
        return dict(self._morning_market) if self._morning_market else None

    def get_seasonal(self) -> list[int]:
        """Return currently active seasonal item IDs."""
        return list(self._seasonal_items)

    # ------------------------------------------------------------------
    # Purchase
    # ------------------------------------------------------------------

    def buy(self, item_id: int, game_state: GameState) -> bool:
        """Buy *item_id* from the daily shelf.

        Finds which category the item belongs to, deducts its price from
        ``game_state.money``, and records the purchase in the catalog.

        Returns:
            ``True`` on success, ``False`` if item not in daily stock or
            insufficient funds.
        """
        category = self._find_daily_category(item_id)
        if category is None:
            return False

        price = self._get_item_price(item_id)
        if not game_state.spend_money(price):
            return False

        self.add_to_catalog(category, item_id)
        return True

    def buy_morning_market(self, game_state: GameState) -> bool:
        """Buy the morning-market item at its discounted price.

        Returns:
            ``True`` on success, ``False`` if no market active or
            insufficient funds.
        """
        if self._morning_market is None:
            return False

        item_id: int = self._morning_market["item"]
        price: int = self._morning_market["discount_price"]

        if not game_state.spend_money(price):
            return False

        # Morning market items are food.
        self.add_to_catalog("food", item_id)
        return True

    # ------------------------------------------------------------------
    # Catalog management
    # ------------------------------------------------------------------

    def add_to_catalog(self, category: str, item_id: int) -> None:
        """Record *item_id* as acquired in *category*'s catalog."""
        if category not in self._catalog:
            self._catalog[category] = set()
        self._catalog[category].add(item_id)

    def get_catalog(self, category: str) -> list[int]:
        """Return sorted list of catalog item IDs for *category*."""
        return sorted(self._catalog.get(category, set()))

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def serialize(self) -> dict:
        """Return a JSON-serialisable dict matching the shop.json format.

        Structure::

            {
                "daily": {"food": [...], "clothing": [...], "interior": [...]},
                "morning_market": {"item": id, "discount_price": int} | null,
                "seasonal": [...],
                "catalog": {"food": [...], "clothing": [...], "interior": [...]},
            }
        """
        return {
            "daily": {c: list(ids) for c, ids in self._daily_items.items()},
            "morning_market": dict(self._morning_market) if self._morning_market else None,
            "seasonal": list(self._seasonal_items),
            "catalog": {c: sorted(ids) for c, ids in self._catalog.items()},
        }

    def deserialize(self, data: dict) -> None:
        """Load shop state from a previously serialised dict.

        Unknown keys are silently ignored for forward-compatibility.
        """
        daily = data.get("daily", {})
        for category in CATEGORIES:
            raw = daily.get(category, [])
            self._daily_items[category] = [int(i) for i in raw]

        mm = data.get("morning_market")
        if mm:
            self._morning_market = {
                "item": int(mm["item"]),
                "discount_price": int(mm["discount_price"]),
            }
        else:
            self._morning_market = None

        self._seasonal_items = [int(i) for i in data.get("seasonal", [])]

        catalog = data.get("catalog", {})
        for category in CATEGORIES:
            raw_set = catalog.get(category, [])
            self._catalog[category] = {int(i) for i in raw_set}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_daily_category(self, item_id: int) -> str | None:
        """Return the category that contains *item_id* in today's daily stock."""
        for category, items in self._daily_items.items():
            if item_id in items:
                return category
        return None

    def _get_item_price(self, item_id: int) -> int:  # noqa: ARG002
        """Return the price for *item_id*.

        Placeholder until item master data exists.
        All items cost a fixed 1000 won for now.
        """
        return 1000
