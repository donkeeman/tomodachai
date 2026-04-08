"""Tests for tomodachai.location — LocationManager and movement logic."""

from __future__ import annotations

import random

from tomodachai.character import Character, CharacterState, Customizable, Mood, Profile
from tomodachai.location import (
    _FRIENDSHIP_FOLLOW,
    _HUNGER_HIGH,
    _SATISFACTION_LOW,
    _STRESS_HIGH,
    DEFAULT_LOCATIONS,
    Location,
    LocationManager,
    LocationType,
)
from tomodachai.relationship import RelationshipTracker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_char(
    char_id: int,
    name: str,
    hunger: float = 0.0,
    satisfaction: float = 50.0,
    stress: int = 2,
) -> Character:
    state = CharacterState(
        hunger=hunger,
        satisfaction=satisfaction,
        mood=Mood(happiness=5, energy=5, stress=stress),
    )
    return Character(
        id=char_id,
        profile=Profile(name=name),
        state=state,
        customizable=Customizable(),
    )


# ---------------------------------------------------------------------------
# DEFAULT_LOCATIONS
# ---------------------------------------------------------------------------


class TestDefaultLocations:
    def test_count(self):
        # 공유 거실 + 발코니 + 13 공개 장소 = 15
        assert len(DEFAULT_LOCATIONS) == 15

    def test_all_have_id_and_name(self):
        for loc in DEFAULT_LOCATIONS:
            assert loc.id, f"Location missing id: {loc}"
            assert loc.name, f"Location missing name: {loc}"

    def test_public_count(self):
        public = [loc for loc in DEFAULT_LOCATIONS if loc.location_type == LocationType.PUBLIC]
        assert len(public) == 13

    def test_shared_count(self):
        shared = [loc for loc in DEFAULT_LOCATIONS if loc.location_type == LocationType.SHARED_ROOM]
        assert len(shared) == 2

    def test_known_location_ids(self):
        ids = {loc.id for loc in DEFAULT_LOCATIONS}
        expected = {
            "living_room", "balcony",
            "grocery", "clothing", "interior", "fountain", "news_station",
            "park", "cafe", "beach", "plaza", "concert_hall",
            "amusement_park", "city_hall", "photo_studio",
        }
        assert expected == ids

    def test_capacity_positive(self):
        for loc in DEFAULT_LOCATIONS:
            assert loc.capacity > 0, f"{loc.id} capacity must be > 0"

    def test_event_types_not_empty(self):
        for loc in DEFAULT_LOCATIONS:
            assert loc.event_types, f"{loc.id} should have event_types"


# ---------------------------------------------------------------------------
# Location model
# ---------------------------------------------------------------------------


class TestLocationModel:
    def test_defaults(self):
        loc = Location(id="test", name="테스트")
        assert loc.location_type == LocationType.PUBLIC
        assert loc.capacity == 6
        assert loc.event_types == []

    def test_private_room_type(self):
        loc = Location(id="room_1", name="방", location_type=LocationType.PRIVATE_ROOM)
        assert loc.location_type == LocationType.PRIVATE_ROOM


# ---------------------------------------------------------------------------
# LocationManager — registry
# ---------------------------------------------------------------------------


class TestLocationManagerRegistry:
    def test_default_locations_loaded(self):
        mgr = LocationManager()
        assert len(mgr.all_locations()) == 15

    def test_add_location(self):
        mgr = LocationManager()
        extra = Location(id="secret", name="비밀 장소", location_type=LocationType.PRIVATE_ROOM)
        mgr.add_location(extra)
        assert mgr.get_location("secret") is not None

    def test_register_private_room(self):
        mgr = LocationManager()
        room = mgr.register_private_room(42, "민수")
        assert room.id == "room_42"
        assert room.location_type == LocationType.PRIVATE_ROOM
        assert "민수" in room.name
        assert mgr.get_location("room_42") is room

    def test_get_location_by_name(self):
        mgr = LocationManager()
        loc = mgr.get_location_by_name("카페")
        assert loc is not None
        assert loc.id == "cafe"

    def test_get_location_by_name_missing(self):
        mgr = LocationManager()
        assert mgr.get_location_by_name("없는장소") is None

    def test_public_locations(self):
        mgr = LocationManager()
        public = mgr.public_locations()
        assert len(public) == 13

    def test_shared_locations(self):
        mgr = LocationManager()
        shared = mgr.shared_locations()
        assert len(shared) == 2


# ---------------------------------------------------------------------------
# LocationManager — positions
# ---------------------------------------------------------------------------


class TestLocationManagerPositions:
    def test_move_character_by_id(self):
        mgr = LocationManager()
        assert mgr.move_character(1, "park")
        assert mgr.get_character_location(1) == "park"

    def test_move_character_by_name(self):
        mgr = LocationManager()
        # '카페'는 이름으로 이동
        assert mgr.move_character(2, "카페")
        assert mgr.get_character_location(2) == "cafe"

    def test_move_to_unknown_location(self):
        mgr = LocationManager()
        assert not mgr.move_character(1, "없는곳")

    def test_get_characters_at(self):
        mgr = LocationManager()
        mgr.move_character(1, "park")
        mgr.move_character(2, "park")
        mgr.move_character(3, "cafe")
        at_park = mgr.get_characters_at("park")
        assert set(at_park) == {1, 2}
        assert 3 not in at_park

    def test_get_character_location_unset(self):
        mgr = LocationManager()
        assert mgr.get_character_location(99) is None

    def test_remove_character(self):
        mgr = LocationManager()
        mgr.move_character(1, "park")
        mgr.remove_character(1)
        assert mgr.get_character_location(1) is None
        assert 1 not in mgr.get_characters_at("park")

    def test_capacity_check(self):
        mgr = LocationManager()
        # news_station capacity = 2
        mgr.move_character(10, "news_station")
        mgr.move_character(11, "news_station")
        assert mgr.is_at_capacity("news_station")

    def test_capacity_not_exceeded(self):
        mgr = LocationManager()
        mgr.move_character(10, "news_station")
        assert not mgr.is_at_capacity("news_station")

    def test_forced_move_ignores_capacity(self):
        """플레이어 강제 이동은 정원 초과 허용."""
        mgr = LocationManager()
        for i in range(10):
            mgr.move_character(i, "news_station")  # capacity=2이지만 강제
        assert len(mgr.get_characters_at("news_station")) == 10


# ---------------------------------------------------------------------------
# LocationManager — choose_destination
# ---------------------------------------------------------------------------


class TestChooseDestination:
    def _rng(self, seed: int = 42) -> random.Random:
        return random.Random(seed)

    def test_returns_valid_location(self):
        mgr = LocationManager()
        char = make_char(1, "민수")
        dest = mgr.choose_destination(char, rng=self._rng())
        assert dest in {loc.id for loc in mgr.all_locations()}

    def test_hungry_prefers_grocery(self):
        """배고프면 식료품점 가중치가 압도적으로 높아야 한다."""
        mgr = LocationManager()
        char = make_char(1, "민수", hunger=_HUNGER_HIGH + 10)
        counts: dict[str, int] = {}
        rng = random.Random(0)
        for _ in range(200):
            dest = mgr.choose_destination(char, rng=rng)
            counts[dest] = counts.get(dest, 0) + 1
        assert counts.get("grocery", 0) > 50, "hungry char should often pick grocery"

    def test_low_satisfaction_prefers_leisure(self):
        """만족도가 낮으면 여가 장소 선택 비율이 높아야 한다."""
        mgr = LocationManager()
        char = make_char(1, "민수", satisfaction=_SATISFACTION_LOW - 5)
        leisure = {"park", "cafe", "beach", "amusement_park"}
        counts: dict[str, int] = {}
        rng = random.Random(7)
        for _ in range(200):
            dest = mgr.choose_destination(char, rng=rng)
            counts[dest] = counts.get(dest, 0) + 1
        leisure_count = sum(counts.get(loc, 0) for loc in leisure)
        assert leisure_count > 80, "low-satisfaction char should prefer leisure spots"

    def test_high_stress_prefers_beach(self):
        """스트레스 높으면 해변/발코니 가중치↑."""
        mgr = LocationManager()
        char = make_char(1, "민수", stress=_STRESS_HIGH + 1)
        counts: dict[str, int] = {}
        rng = random.Random(13)
        for _ in range(200):
            dest = mgr.choose_destination(char, rng=rng)
            counts[dest] = counts.get(dest, 0) + 1
        beach_balcony = counts.get("beach", 0) + counts.get("balcony", 0)
        assert beach_balcony > 30, "stressed char should often pick beach or balcony"

    def test_night_prefers_private_room(self):
        """밤에는 개인 방으로 높은 확률로 이동해야 한다."""
        mgr = LocationManager()
        char = make_char(1, "민수")
        # 개인 방 등록
        mgr.register_private_room(1, "민수")
        counts: dict[str, int] = {}
        rng = random.Random(3)
        for _ in range(100):
            dest = mgr.choose_destination(char, time_of_day="밤", rng=rng)
            counts[dest] = counts.get(dest, 0) + 1
        assert counts.get("room_1", 0) >= 60, "night char should stay home often"

    def test_friend_follow(self):
        """친구가 있는 장소로 높은 가중치."""
        mgr = LocationManager()
        char_a = make_char(1, "민수")
        make_char(2, "지은")

        # char_b(id=2)를 카페에 위치
        mgr.move_character(2, "cafe")

        # 관계 설정 — 우정 높음
        rel_tracker = RelationshipTracker()
        rel_tracker.update(1, 2, {"friendship": _FRIENDSHIP_FOLLOW + 10})
        rel_tracker.update(2, 1, {"friendship": _FRIENDSHIP_FOLLOW + 10})

        counts: dict[str, int] = {}
        rng = random.Random(99)
        for _ in range(200):
            dest = mgr.choose_destination(char_a, relationships=rel_tracker, rng=rng)
            counts[dest] = counts.get(dest, 0) + 1
        assert counts.get("cafe", 0) > 40, "char should follow friend to cafe"

    def test_deterministic_with_seed(self):
        """같은 시드면 같은 결과."""
        mgr = LocationManager()
        char = make_char(1, "민수")
        dest1 = mgr.choose_destination(char, rng=random.Random(42))
        dest2 = mgr.choose_destination(char, rng=random.Random(42))
        assert dest1 == dest2


# ---------------------------------------------------------------------------
# LocationManager — snapshot
# ---------------------------------------------------------------------------


class TestSnapshot:
    def test_snapshot_structure(self):
        mgr = LocationManager()
        mgr.move_character(1, "park")
        mgr.move_character(2, "cafe")
        snap = mgr.snapshot()
        assert isinstance(snap, list)
        assert len(snap) == 15  # DEFAULT_LOCATIONS 수

        park_entry = next(e for e in snap if e["id"] == "park")
        assert park_entry["characters"] == [1]
        cafe_entry = next(e for e in snap if e["id"] == "cafe")
        assert cafe_entry["characters"] == [2]

    def test_snapshot_keys(self):
        mgr = LocationManager()
        snap = mgr.snapshot()
        required = {
            "id", "name", "location_type", "capacity",
            "event_types", "description", "characters",
        }
        for entry in snap:
            assert required.issubset(entry.keys())
