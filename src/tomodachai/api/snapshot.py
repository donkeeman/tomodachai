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

    # crushes: spark==True AND 현재 연인이 아닌 상대
    crushes: list[str] = []
    for other in gs.characters:
        oid = _int_id(other.id)
        if oid == int_id:
            continue
        rel = gs.relationships.get(int_id, oid)
        if rel.spark and slots.lover != oid:
            crushes.append(other.name)

    # friends: 만나본 상대를 우정 내림차순 top5, 라벨은 상태텍스트 (수치 비노출)
    met = []
    for other in gs.characters:
        oid = _int_id(other.id)
        if oid == int_id:
            continue
        rel = gs.relationships.get(int_id, oid)
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
        "food_eaten": list(char.preferences.food_eaten),
        "friends": friends,
        "dex": [],  # Plan 2(feed)에서 채움
    }
