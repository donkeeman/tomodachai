"""도구 아이템 — 카메라(사진) / 프라이팬(요리). prototype/game use_tool 규칙 이식.

LLM(gs.llm.chat_json)으로 제목/요리명을 생성하고 게임 레벨 저장소에 적재한다.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tomodachai.character import Character
    from tomodachai.game_state import GameState

TOOLS = ("camera", "frying_pan")


def _int_id(char) -> int:
    return char.id if isinstance(char.id, int) else abs(hash(char.id)) % 100000


def use_tool(gs: GameState, char: Character, tool: str) -> str:
    """캐릭터가 도구를 사용한다. 반환: 결과 메시지.

    Raises:
        ValueError: 알 수 없는 도구일 때.
    """
    if tool == "camera":
        return _camera(gs, char)
    if tool == "frying_pan":
        return _frying_pan(gs, char)
    raise ValueError(f"알 수 없는 도구: {tool}")


def _camera(gs: GameState, char: Character) -> str:
    int_id = _int_id(char)
    loc_id = gs.location_manager.get_character_location(int_id) or ""
    loc = gs.location_manager.get_location(loc_id)
    loc_name = loc.name if loc else (char.state.current_location or "어딘가")

    mates = [
        c
        for c in gs.characters
        if _int_id(c) != int_id
        and loc_id
        and gs.location_manager.get_character_location(_int_id(c)) == loc_id
    ]
    if mates and random.random() < 0.5:
        m = random.choice(mates)
        subject = f"{loc_name}에 있는 주민 {m.name}의 자연스러운 한 컷"
        subj_label = m.name
    else:
        subject = f"{loc_name}의 풍경"
        subj_label = loc_name

    messages = [
        {
            "role": "system",
            "content": (
                "너는 관찰형 시뮬레이션 게임의 콘텐츠 생성기다. "
                "주민이 카메라로 사진을 한 장 찍었다. "
                "사진 제목은 캐릭터 성격이 묻어나는 짧은 한 문장(10자 내외, 엉뚱해도 좋음), "
                "감상은 캐릭터 말투로 1문장. "
                'JSON만 출력: {"title": "...", "caption": "..."}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"캐릭터: {char.name} ({char.personality_code}), 기분: {char.state.mood.label()}\n"
                f"피사체: {subject}"
            ),
        },
    ]
    data = gs.llm.chat_json(messages, max_tokens=200)
    title = str((data or {}).get("title") or f"무제 ({subj_label})")
    caption = str((data or {}).get("caption") or "").strip()

    gs.photos.append(
        {"day": gs.day_count, "author": char.name, "title": title, "subject": subj_label}
    )
    char.state.mood.adjust(happiness=1)

    msg = f"📸 {char.name}의 촬영 — 사진 '{title}' 갤러리에 저장"
    if caption:
        msg += f" ({char.name}: {caption})"
    return msg


def _frying_pan(gs: GameState, char: Character) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "너는 관찰형 시뮬레이션 게임의 콘텐츠 생성기다. "
                "주민이 프라이팬으로 즉흥 요리를 했다. "
                "요리 이름은 캐릭터 성격이 드러나는 창작 요리(15자 내외, 실존 요리 비틀기도 가능), "
                "완성 소감은 캐릭터 말투로 1문장(요리 실력은 복불복). "
                'JSON만 출력: {"dish": "...", "comment": "..."}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"캐릭터: {char.name} ({char.personality_code}), 기분: {char.state.mood.label()}"
            ),
        },
    ]
    data = gs.llm.chat_json(messages, max_tokens=200)
    dish = str((data or {}).get("dish") or "정체불명 볶음")
    comment = str((data or {}).get("comment") or "").strip()

    st = char.state
    st.hunger = max(0.0, st.hunger - 40)
    st.mood.adjust(happiness=1, energy=0.5)
    gs.dishes.append({"day": gs.day_count, "author": char.name, "dish": dish})

    msg = f"🍳 {char.name}의 즉흥 요리 — '{dish}' 카탈로그에 추가"
    if comment:
        msg += f" ({char.name}: {comment})"
    return msg
