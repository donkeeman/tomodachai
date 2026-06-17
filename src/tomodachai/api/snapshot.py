"""Babylon 프론트 계약(Snapshot) 집계기.

prototype/web_server.py snapshot()의 직렬화 규칙을 src/tomodachai 모델 위에서 재현한다.
무상태 — GameState를 읽기만 한다.
"""

from __future__ import annotations

from tomodachai.character import Character
from tomodachai.food import FOODS, preference_tier
from tomodachai.game_state import GameState


def _gender(text: str) -> str:
    """자유텍스트 성별 → 'M'/'F' (인식 못 하면 'M' 폴백).

    한국어("여성")뿐 아니라 영어 표기("F"/"female")도 수용한다.
    """
    t = (text or "").strip().lower()
    if "여" in t or t in ("f", "female", "w", "woman", "girl"):
        return "F"
    return "M"


def _int_id(char_id) -> int:
    return char_id if isinstance(char_id, int) else abs(hash(char_id)) % 100000


def _name_of(gs: GameState, char_id: int | None) -> str | None:
    if char_id is None:
        return None
    c = gs.get_character(char_id)
    return c.name if c else None


def char_dict(gs: GameState, char: Character) -> dict:
    """캐릭터 1명을 프론트 Character DTO(dict)로 변환."""
    int_id = _int_id(char.id)
    slots = gs.relationships.get_slots(int_id)

    # 단일 패스로 crushes(설레는 상대)와 friends(우정 top5) 동시 수집
    crushes: list[str] = []
    met: list[tuple[float, str, str]] = []
    for other in gs.characters:
        oid = _int_id(other.id)
        if oid == int_id:
            continue
        rel = gs.relationships.get(int_id, oid)
        if rel.spark and slots.lover != oid:
            crushes.append(other.name)
        met.append((rel.friendship, other.name, rel.get_status_text()))
    met.sort(key=lambda t: t[0], reverse=True)
    friends = [{"name": n, "label": lbl} for _f, n, lbl in met[:5]]

    prefs = char.preferences
    dex = [
        {"name": FOODS[fid], "tier": preference_tier(prefs.food_ranks[fid])}
        for fid, eaten in enumerate(prefs.food_eaten)
        if eaten and fid < len(prefs.food_ranks)
    ]

    loc_id = gs.location_manager.get_character_location(int_id)
    if not loc_id:
        # 위치 미등록 시 current_location(이름)을 장소 id로 역매핑 (프론트 locations는 id 키)
        name_to_id = {e["name"]: e["id"] for e in gs.location_manager.snapshot()}
        loc_id = name_to_id.get(char.state.current_location, char.state.current_location)

    return {
        "id": int_id,
        "name": char.name,
        "gender": _gender(char.gender),
        "location": loc_id,
        "mood": char.state.mood.label(),
        "hunger": round(char.state.hunger),
        "satisfaction": round(char.state.satisfaction),
        "lover": _name_of(gs, slots.lover),
        "best_friend": _name_of(gs, slots.best_friend),
        "enemy": _name_of(gs, slots.enemy),
        "crushes": crushes,
        "food_eaten": list(char.preferences.food_eaten),  # bool[]: 음식 인덱스별 섭취 여부
        "friends": friends,
        "dex": dex,
    }


# 메이저(자동 일시정지/강조) 이벤트 타입 — simulation.py가 실제 내보내는 type 값 기준
_MAJOR_TYPES = {"fight", "confession_success", "confession_fail"}

# 23:00(-5분)~07:00 수면창
_SLEEP_START_MIN = 23 * 60 - 5
_WAKE_MIN = 7 * 60


def bubble_dict(gs: GameState, bubble) -> dict:
    """Bubble → 프론트 DTO {kind, char, target|null, text}."""
    return {
        "kind": bubble.kind,
        "char": _name_of(gs, bubble.char_id),
        "target": _name_of(gs, bubble.target_id),
        "text": bubble.text,
    }


def map_event(gs: GameState, entry: dict) -> dict:
    """이벤트 로그 항목 → 프론트 EventItem dict."""
    raw = entry["raw"]
    etype = raw.get("type", "")

    dialogue: list[list[str]] = []
    result = raw.get("result")
    if etype == "conversation" and result is not None and not isinstance(result, str):
        dialogue = [[ln.speaker, ln.text] for ln in getattr(result, "dialogue", [])]

    # scene: conversation은 result.summary, 그 외 이벤트(fight/confession/catchup)는 raw["summary"]
    summary = None
    if isinstance(result, str):
        summary = result
    elif result is not None and getattr(result, "summary", None):
        summary = result.summary
    scene = summary or raw.get("summary") or ""
    return {
        "seq": entry["seq"],
        "day": entry["day"],
        "clock": entry["clock"],
        "scene": scene,
        "dialogue": dialogue,
        "messages": [],
        "major": etype in _MAJOR_TYPES,
    }


def _clock_and_minutes(gs: GameState) -> tuple[str, int]:
    clock_str = gs._clock_str()  # 포맷 소스 단일화 (GameState._clock_str)
    h, m = int(clock_str[:2]), int(clock_str[3:])
    return clock_str, h * 60 + m


def build_snapshot(gs: GameState, since: int) -> dict:
    """프론트 계약 Snapshot 전체 조립."""
    clock, minutes = _clock_and_minutes(gs)
    locations = {e["id"]: e["name"] for e in gs.location_manager.snapshot()}
    return {
        "village": gs.island_name,
        "provider": gs.config.llm.provider,
        "day": gs.day_count,
        "clock": clock,
        "minutes": minutes,
        "seq": gs._event_seq,
        "locations": locations,
        "foods": FOODS,
        # Plan 2(rankings)에서 채움
        "rankings": {"best_couple": [], "popular_m": [], "popular_f": [], "fighters": []},
        "asleep": minutes >= _SLEEP_START_MIN or minutes < _WAKE_MIN,
        "realtime": True,
        "photos": list(reversed(gs.photos[-40:])),
        "dishes": list(reversed(gs.dishes[-40:])),
        "characters": [char_dict(gs, c) for c in gs.characters],
        "events": [map_event(gs, e) for e in gs.events_since(since)],
        "bubbles": [bubble_dict(gs, b) for b in gs.bubbles],
    }
