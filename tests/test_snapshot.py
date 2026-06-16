"""snapshot 집계기 — 계약 DTO 변환."""

import pytest  # noqa: F401  # Task 6 fixture에서 사용 예정

from tomodachai.character import (
    Character,
    CharacterState,
    Customizable,
    Profile,
    SpeechHabits,
)
from tomodachai.config import AppConfig, LLMConfig, LocationConfig, SimulationConfig
from tomodachai.game_state import GameState


def _gs_with_two():
    cfg = AppConfig(
        llm=LLMConfig(provider="litellm", model="ollama/gemma3", temperature=0.8),
        simulation=SimulationConfig(),
        locations=[LocationConfig(id="fountain", name="분수대")],
    )
    gs = GameState(config=cfg)
    for cid, name, gender in [(1, "민수", "남성"), (2, "지은", "여성")]:
        gs.add_character(
            Character(
                id=cid,
                personality_code="outgoing_dynamo",
                profile=Profile(name=name, birthday="03-15", blood_type="B", gender=gender),
                state=CharacterState(current_location="분수대"),
                customizable=Customizable(speech_habits=SpeechHabits(normal="~")),
            )
        )
    return gs


def test_char_dict_basic_fields():
    from tomodachai.api.snapshot import char_dict

    gs = _gs_with_two()
    minsu = gs.get_character(1)
    minsu.state.mood.happiness = 8
    minsu.state.mood.energy = 7
    minsu.state.mood.stress = 2

    d = char_dict(gs, minsu)
    assert d["id"] == 1
    assert d["name"] == "민수"
    assert d["gender"] == "M"
    assert d["mood"] == "신남"
    assert d["hunger"] == 0
    assert d["satisfaction"] == 50
    assert d["lover"] is None
    assert d["best_friend"] is None
    assert d["enemy"] is None
    assert d["crushes"] == []
    assert isinstance(d["friends"], list)
    assert isinstance(d["dex"], list)
    assert isinstance(d["food_eaten"], list)


def test_char_dict_gender_female():
    from tomodachai.api.snapshot import char_dict

    gs = _gs_with_two()
    assert char_dict(gs, gs.get_character(2))["gender"] == "F"


def test_gender_normalization():
    """한국어/영어 성별 표기를 모두 'M'/'F' 로 정규화."""
    from tomodachai.api.snapshot import _gender

    for female in ("여성", "여", "F", "f", "Female", "woman"):
        assert _gender(female) == "F", female
    for male in ("남성", "M", "male", "", "기타"):
        assert _gender(male) == "M", male


def test_map_event_conversation_shape():
    from tomodachai.api.snapshot import map_event

    gs = _gs_with_two()
    entry = {
        "seq": 1,
        "day": 2,
        "clock": "09:30",
        "raw": {"type": "conversation", "participants": [1, 2], "location": "분수대"},
    }
    ev = map_event(gs, entry)
    assert ev["seq"] == 1
    assert ev["day"] == 2
    assert ev["clock"] == "09:30"
    assert isinstance(ev["dialogue"], list)
    assert isinstance(ev["messages"], list)
    assert ev["major"] is False


def test_map_event_fight_scene_and_major():
    from tomodachai.api.snapshot import map_event

    gs = _gs_with_two()
    entry = {
        "seq": 5,
        "day": 1,
        "clock": "10:00",
        "raw": {
            "type": "fight",
            "participants": ["민수", "지은"],
            "summary": "민수와(과) 지은의 긴장이 폭발하여 싸움이 벌어졌다!",
        },
    }
    ev = map_event(gs, entry)
    assert ev["major"] is True
    assert ev["scene"] == "민수와(과) 지은의 긴장이 폭발하여 싸움이 벌어졌다!"


def test_map_event_confession_success_is_major_with_scene():
    from tomodachai.api.snapshot import map_event

    gs = _gs_with_two()
    entry = {
        "seq": 9,
        "day": 1,
        "clock": "20:00",
        "raw": {
            "type": "confession_success",
            "participants": ["민수", "지은"],
            "summary": "민수가 지은에게 고백하여 연인이 되었다!",
        },
    }
    ev = map_event(gs, entry)
    assert ev["major"] is True
    assert ev["scene"] == "민수가 지은에게 고백하여 연인이 되었다!"


def test_build_snapshot_contract_keys():
    from tomodachai.api.snapshot import build_snapshot

    gs = _gs_with_two()
    snap = build_snapshot(gs, since=0)
    for key in (
        "village",
        "provider",
        "day",
        "clock",
        "minutes",
        "seq",
        "locations",
        "foods",
        "rankings",
        "asleep",
        "realtime",
        "photos",
        "dishes",
        "characters",
        "events",
        "bubbles",
    ):
        assert key in snap, f"missing {key}"
    assert len(snap["characters"]) == 2
    assert snap["locations"]["fountain"] == "분수대"
    assert snap["rankings"] == {"best_couple": [], "popular_m": [], "popular_f": [], "fighters": []}
    assert snap["photos"] == [] and snap["dishes"] == [] and snap["bubbles"] == []


def test_build_snapshot_events_since():
    from tomodachai.api.snapshot import build_snapshot

    gs = _gs_with_two()
    gs.record_events([{"type": "conversation", "participants": [1, 2]}])
    snap = build_snapshot(gs, since=0)
    assert snap["seq"] == 1
    assert len(snap["events"]) == 1
    assert build_snapshot(gs, since=1)["events"] == []


def test_snapshot_foods_is_master_list():
    from tomodachai.api.snapshot import build_snapshot
    from tomodachai.food import FOODS

    gs = _gs_with_two()
    assert build_snapshot(gs, since=0)["foods"] == FOODS


def test_char_dict_dex_filled_after_feed():
    from tomodachai.api.snapshot import char_dict
    from tomodachai.food import FOODS, feed, preference_tier

    gs = _gs_with_two()
    minsu = gs.get_character(1)
    feed(minsu, food_id=0)  # 김치찌개 먹임 → dex에 1건

    d = char_dict(gs, minsu)
    assert len(d["dex"]) == 1
    entry = d["dex"][0]
    assert entry["name"] == FOODS[0]
    assert entry["tier"] == preference_tier(minsu.preferences.food_ranks[0])


def test_char_dict_dex_empty_before_feed():
    from tomodachai.api.snapshot import char_dict

    gs = _gs_with_two()
    assert char_dict(gs, gs.get_character(2))["dex"] == []


@pytest.fixture
def client_snap():
    from fastapi.testclient import TestClient

    from tomodachai.api.routes import set_game_state
    from tomodachai.server import create_app

    gs = _gs_with_two()
    app = create_app()
    set_game_state(gs)
    return TestClient(app), gs


def test_api_snapshot_returns_contract(client_snap):
    client, _gs = client_snap
    resp = client.get("/api/snapshot?since=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["characters"]) == 2
    assert "events" in data and "seq" in data


def test_api_reset_clears(client_snap):
    client, gs = client_snap
    gs.record_events([{"type": "x"}])
    resp = client.post("/api/reset", json={})
    assert resp.status_code == 200
    snap = client.get("/api/snapshot?since=0").json()
    assert snap["seq"] == 0
    assert snap["characters"] == []


def test_api_feed_succeeds_and_fills_dex(client_snap):
    client, gs = client_snap
    resp = client.post("/api/feed", json={"char_id": 1, "food_id": 0})
    assert resp.status_code == 200
    assert "🍽" in resp.json()["message"]

    snap = client.get("/api/snapshot?since=0").json()
    minsu = next(c for c in snap["characters"] if c["id"] == 1)
    assert len(minsu["dex"]) == 1
    # feed 이벤트가 로그에 기록되어 scene으로 재생됨
    assert any("🍽" in e["scene"] for e in snap["events"])


def test_api_feed_unknown_char(client_snap):
    client, _gs = client_snap
    resp = client.post("/api/feed", json={"char_id": 999, "food_id": 0})
    assert resp.status_code == 404


def test_api_feed_invalid_food(client_snap):
    client, _gs = client_snap
    resp = client.post("/api/feed", json={"char_id": 1, "food_id": 99})
    assert resp.status_code == 400
