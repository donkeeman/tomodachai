"""Tests for the save/load system."""

from __future__ import annotations

import pytest

from tomodachai.character import Character, CharacterState, Customizable, Preferences, Profile
from tomodachai.game_state import GameState
from tomodachai.memory import MemoryStore, SocialEvent
from tomodachai.relationship import (
    BreakupReason,
    Fight,
    Relationship,
    RelationshipEvent,
    RelationshipSlots,
    RelationshipStage,
    RelationshipTracker,
)
from tomodachai.save import (
    NUM_SLOTS,
    SaveManager,
    SlotInfo,
    _deserialize_character,
    _deserialize_events,
    _deserialize_relationships,
    _serialize_character,
    _serialize_events,
    _serialize_relationships,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_char(char_id: int = 1, name: str = "테스트") -> Character:
    return Character(
        id=char_id,
        profile=Profile(
            name=name,
            birthday="03-15",
            blood_type="A",
            favorite_color="blue",
            gender="M",
        ),
        preferences=Preferences(
            food_ranks=[1, 2, 3],
            food_eaten=[True, False, True],
        ),
        state=CharacterState(
            satisfaction=60.0,
            level=2,
            hunger=10.0,
        ),
        customizable=Customizable(),
    )


def _make_game(island: str = "테스트 마을") -> GameState:
    gs = GameState(island_name=island, day_count=5, money=1000)
    gs.add_character(_make_char(1, "민수"))
    gs.add_character(_make_char(2, "지은"))
    return gs


# ---------------------------------------------------------------------------
# Character serialization round-trip
# ---------------------------------------------------------------------------


def test_character_serialize_roundtrip():
    char = _make_char(1, "민수")
    data = _serialize_character(char)

    assert data["id"] == 1
    assert data["profile"]["name"] == "민수"
    assert data["profile"]["birthday"] == "03-15"
    assert data["preferences"]["food_ranks"] == [1, 2, 3]
    assert data["state"]["satisfaction"] == 60.0

    restored = _deserialize_character(data)
    assert restored.id == char.id
    assert restored.profile.name == char.profile.name
    assert restored.profile.birthday == char.profile.birthday
    assert restored.preferences.food_ranks == char.preferences.food_ranks
    assert restored.state.satisfaction == char.state.satisfaction
    assert restored.state.level == char.state.level


def test_character_serialize_appearance_fields():
    char = _make_char(1)
    data = _serialize_character(char)
    app = data["profile"]["appearance"]
    assert "face_shape" in app
    assert "eye" in app
    assert "adjust" in app["eye"]
    assert "hair" in app
    assert "body" in app


def test_character_serialize_customizable():
    char = _make_char(1)
    char.customizable.nicknames = {"2": "지지"}
    char.customizable.songs = [True, False, False, False, False, False, False, False]
    data = _serialize_character(char)
    assert data["customizable"]["nicknames"] == {"2": "지지"}
    assert data["customizable"]["songs"][0] is True

    restored = _deserialize_character(data)
    assert restored.customizable.nicknames == {"2": "지지"}
    assert restored.customizable.songs[0] is True


# ---------------------------------------------------------------------------
# Relationship serialization round-trip
# ---------------------------------------------------------------------------


def test_relationship_serialize_roundtrip():
    tracker = RelationshipTracker()
    # Add a relationship pair
    rel = Relationship(friendship=72.0, romance=15.0, stage=RelationshipStage.BEST_FRIEND)
    rel.event_log.append(RelationshipEvent(day=5, event_type="conversation", summary="대화함"))
    tracker._relationships[(1, 2)] = rel

    # Slots
    tracker._slots[1] = RelationshipSlots(best_friend=2, lover=None, enemy=None)

    # Ex-lover tags
    from tomodachai.relationship import ExLoverTag
    tracker._ex_lover_tags[1] = [ExLoverTag(target=3, reason=BreakupReason.FIGHT, day=42)]

    # Fights
    tracker._fights.append(Fight(participants=(1, 3), cause="말다툼", resolved=False))

    data = _serialize_relationships(tracker)
    assert "1:2" in data["pairs"]
    assert data["pairs"]["1:2"]["friendship"] == 72.0
    assert data["pairs"]["1:2"]["stage"] == "best_friend"
    assert len(data["pairs"]["1:2"]["events"]) == 1

    assert data["slots"]["1"]["best_friend"] == 2
    assert data["ex_lover_tags"]["1"][0]["reason"] == "fight"
    assert data["fights"][0]["cause"] == "말다툼"

    restored = _deserialize_relationships(data)
    assert (1, 2) in restored._relationships
    assert restored._relationships[(1, 2)].friendship == 72.0
    assert restored._relationships[(1, 2)].stage == RelationshipStage.BEST_FRIEND
    assert len(restored._relationships[(1, 2)].event_log) == 1
    assert restored._slots[1].best_friend == 2
    assert restored._ex_lover_tags[1][0].reason == BreakupReason.FIGHT
    assert restored._fights[0].cause == "말다툼"


def test_relationship_empty_roundtrip():
    tracker = RelationshipTracker()
    data = _serialize_relationships(tracker)
    restored = _deserialize_relationships(data)
    assert len(restored._relationships) == 0
    assert len(restored._slots) == 0


# ---------------------------------------------------------------------------
# Event (MemoryStore) serialization round-trip
# ---------------------------------------------------------------------------


def test_events_serialize_roundtrip():
    store = MemoryStore()
    store.add_event(SocialEvent(
        tick=3,
        event_type="conversation",
        participants=["1", "2"],
        summary="즐거운 대화",
        emotional_impact={"1": 0.5, "2": 0.3},
    ))
    store.add_event(SocialEvent(
        tick=7,
        event_type="fight",
        participants=["1", "3"],
        summary="싸움",
        emotional_impact={"1": -0.8},
    ))

    data = _serialize_events(store)
    assert len(data) == 2
    assert data[0]["tick"] == 3
    assert data[1]["event_type"] == "fight"

    restored = _deserialize_events(data)
    assert len(restored._events) == 2
    assert restored._events[0].summary == "즐거운 대화"
    assert restored._events[1].emotional_impact["1"] == -0.8


def test_events_empty_roundtrip():
    store = MemoryStore()
    data = _serialize_events(store)
    assert data == []
    restored = _deserialize_events(data)
    assert len(restored._events) == 0


# ---------------------------------------------------------------------------
# SaveManager — slot save/load
# ---------------------------------------------------------------------------


def test_save_and_load_roundtrip(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    gs = _make_game("별빛 마을")
    mgr.save(1, gs)

    loaded = mgr.load(1)
    assert loaded.island_name == "별빛 마을"
    assert loaded.day_count == 5
    assert loaded.money == 1000
    assert len(loaded.characters) == 2
    names = {c.profile.name for c in loaded.characters}
    assert names == {"민수", "지은"}


def test_save_creates_files(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    gs = _make_game()
    mgr.save(1, gs)

    slot_dir = tmp_path / "slot_1"
    assert (slot_dir / "game.json").exists()
    assert (slot_dir / "meta.json").exists()
    assert (slot_dir / "events.json").exists()
    assert (slot_dir / "relationships.json").exists()
    assert (slot_dir / "characters" / "1.json").exists()
    assert (slot_dir / "characters" / "2.json").exists()


def test_save_json_is_human_readable(tmp_path):
    """Verify indented, non-ascii JSON."""
    import json
    mgr = SaveManager(save_dir=tmp_path)
    gs = _make_game("별빛 마을")
    mgr.save(1, gs)

    raw = (tmp_path / "slot_1" / "game.json").read_text(encoding="utf-8")
    # Should contain Korean characters directly (ensure_ascii=False)
    assert "별빛 마을" in raw
    # Should be indented
    assert "\n" in raw
    data = json.loads(raw)
    assert data["island_name"] == "별빛 마을"


def test_load_missing_slot_raises(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        mgr.load(1)


def test_invalid_slot_raises(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    gs = _make_game()
    with pytest.raises(ValueError):
        mgr.save(0, gs)
    with pytest.raises(ValueError):
        mgr.save(NUM_SLOTS + 1, gs)
    with pytest.raises(ValueError):
        mgr.load(0)


def test_save_multiple_slots(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)

    gs1 = GameState(island_name="마을1", day_count=1, money=100)
    gs2 = GameState(island_name="마을2", day_count=2, money=200)
    gs3 = GameState(island_name="마을3", day_count=3, money=300)

    mgr.save(1, gs1)
    mgr.save(2, gs2)
    mgr.save(3, gs3)

    assert mgr.load(1).island_name == "마을1"
    assert mgr.load(2).island_name == "마을2"
    assert mgr.load(3).island_name == "마을3"


def test_overwrite_save(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    gs = GameState(island_name="처음", day_count=1, money=0)
    mgr.save(1, gs)

    gs2 = GameState(island_name="업데이트", day_count=10, money=9999)
    mgr.save(1, gs2)

    loaded = mgr.load(1)
    assert loaded.island_name == "업데이트"
    assert loaded.day_count == 10


# ---------------------------------------------------------------------------
# SaveManager — list_slots
# ---------------------------------------------------------------------------


def test_list_slots_all_empty(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    slots = mgr.list_slots()
    assert len(slots) == NUM_SLOTS
    for s in slots:
        assert s.exists is False


def test_list_slots_with_saves(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    gs = GameState(island_name="별빛", day_count=7, money=500)
    mgr.save(2, gs)

    slots = mgr.list_slots()
    assert len(slots) == NUM_SLOTS

    by_slot = {s.slot: s for s in slots}
    assert by_slot[1].exists is False
    assert by_slot[2].exists is True
    assert by_slot[2].island_name == "별빛"
    assert by_slot[2].day_count == 7
    assert by_slot[2].last_saved != ""
    assert by_slot[3].exists is False


def test_list_slots_returns_pydantic_model(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    slots = mgr.list_slots()
    assert all(isinstance(s, SlotInfo) for s in slots)


# ---------------------------------------------------------------------------
# SaveManager — delete_slot
# ---------------------------------------------------------------------------


def test_delete_slot(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    gs = _make_game()
    mgr.save(1, gs)
    assert (tmp_path / "slot_1").exists()

    mgr.delete_slot(1)
    assert not (tmp_path / "slot_1").exists()

    # After deletion, load should raise
    with pytest.raises(FileNotFoundError):
        mgr.load(1)


def test_delete_nonexistent_slot_is_noop(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    # Should not raise
    mgr.delete_slot(2)


def test_delete_invalid_slot_raises(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    with pytest.raises(ValueError):
        mgr.delete_slot(0)


# ---------------------------------------------------------------------------
# SaveManager — temp save/load
# ---------------------------------------------------------------------------


def test_temp_save_and_load(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    gs = _make_game("임시 마을")

    assert mgr.has_temp_save() is False

    mgr.save_temp(gs)
    assert mgr.has_temp_save() is True

    loaded = mgr.load_temp()
    assert loaded.island_name == "임시 마을"
    assert loaded.day_count == 5
    assert len(loaded.characters) == 2


def test_temp_save_creates_correct_structure(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    gs = _make_game()
    mgr.save_temp(gs)

    temp_dir = tmp_path / "_temp"
    assert temp_dir.exists()
    assert (temp_dir / "game.json").exists()
    assert (temp_dir / "meta.json").exists()


def test_load_temp_raises_when_missing(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        mgr.load_temp()


def test_clear_temp(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    gs = _make_game()
    mgr.save_temp(gs)
    assert mgr.has_temp_save() is True

    mgr.clear_temp()
    assert mgr.has_temp_save() is False
    assert not (tmp_path / "_temp").exists()


def test_clear_temp_noop_when_missing(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    # Should not raise
    mgr.clear_temp()


def test_overwrite_temp_save(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    gs1 = GameState(island_name="첫번째", day_count=1, money=0)
    mgr.save_temp(gs1)

    gs2 = GameState(island_name="두번째", day_count=99, money=5000)
    mgr.save_temp(gs2)

    loaded = mgr.load_temp()
    assert loaded.island_name == "두번째"
    assert loaded.day_count == 99


# ---------------------------------------------------------------------------
# Relationships + memory preserved across save/load
# ---------------------------------------------------------------------------


def test_relationships_preserved(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    gs = _make_game()

    # Set up some relationships
    gs.relationships.update(1, 2, {"friendship": 55.0, "romance": 10.0})

    mgr.save(1, gs)
    loaded = mgr.load(1)

    rel = loaded.relationships.get(1, 2)
    assert rel.friendship == 55.0
    assert rel.romance == 10.0


def test_memory_events_preserved(tmp_path):
    mgr = SaveManager(save_dir=tmp_path)
    gs = _make_game()

    gs.memory.add_event(SocialEvent(
        tick=1,
        event_type="conversation",
        participants=["1", "2"],
        summary="저녁 대화",
        emotional_impact={"1": 0.2},
    ))

    mgr.save(1, gs)
    loaded = mgr.load(1)

    events = loaded.memory.get_events_for("1", limit=10)
    assert len(events) == 1
    assert events[0].summary == "저녁 대화"
