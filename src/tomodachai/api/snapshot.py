"""Babylon 프론트 계약(Snapshot) 집계기.

prototype/web_server.py snapshot()의 직렬화 규칙을 src/tomodachai 모델 위에서 재현한다.
무상태 — GameState를 읽기만 한다.
"""

from __future__ import annotations

from tomodachai.character import Character
from tomodachai.game_state import GameState


def _gender(text: str) -> str:
    """자유텍스트 성별 → 'M'/'F' (기타는 'M' 폴백)."""
    return "F" if "여" in text else "M"


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

    loc_id = gs.location_manager.get_character_location(int_id) or char.state.current_location

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
        "dex": [],  # Plan 2(feed)에서 채움
    }


# 메이저(자동 일시정지/강조) 이벤트 타입
_MAJOR_TYPES = {"fight", "confession", "breakup", "new_lover", "new_best_friend", "spark"}

# 23:00(-5분)~07:00 수면창
_SLEEP_START_MIN = 23 * 60 - 5
_WAKE_MIN = 7 * 60


def map_event(gs: GameState, entry: dict) -> dict:
    """이벤트 로그 항목 → 프론트 EventItem dict."""
    raw = entry["raw"]
    etype = raw.get("type", "")

    dialogue: list[list[str]] = []
    result = raw.get("result")
    if etype == "conversation" and result is not None and not isinstance(result, str):
        dialogue = [[ln.speaker, ln.text] for ln in getattr(result, "dialogue", [])]

    summary = None
    if isinstance(result, str):
        summary = result
    elif result is not None and getattr(result, "summary", None):
        summary = result.summary

    scene = summary or raw.get("reason") or ""
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
        "foods": [],  # Plan 2(feed)에서 채움
        # Plan 2(rankings)에서 채움
        "rankings": {"best_couple": [], "popular_m": [], "popular_f": [], "fighters": []},
        "asleep": minutes >= _SLEEP_START_MIN or minutes < _WAKE_MIN,
        "realtime": True,
        "photos": [],  # Plan 2(give)에서 채움
        "dishes": [],  # Plan 2(give)에서 채움
        "characters": [char_dict(gs, c) for c in gs.characters],
        "events": [map_event(gs, e) for e in gs.events_since(since)],
        "bubbles": [],  # Plan 2(bubble)에서 채움
    }
