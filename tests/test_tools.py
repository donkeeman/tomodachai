"""도구 메커닉 — 카메라/프라이팬 (prototype use_tool 규칙)."""

import pytest

from tomodachai.character import (
    Character,
    CharacterState,
    Customizable,
    Profile,
    SpeechHabits,
)
from tomodachai.config import AppConfig, LLMConfig, LocationConfig, SimulationConfig
from tomodachai.game_state import GameState
from tomodachai.tools import use_tool


class _MockLLM:
    def __init__(self, response: dict):
        self._response = response
        self.calls = 0

    def chat_json(self, messages, **kwargs) -> dict:
        self.calls += 1
        return self._response


def _gs():
    cfg = AppConfig(
        llm=LLMConfig(provider="litellm", model="ollama/gemma3", temperature=0.8),
        simulation=SimulationConfig(),
        locations=[LocationConfig(id="fountain", name="분수대")],
    )
    gs = GameState(config=cfg)
    gs.add_character(
        Character(
            id=1,
            personality_code="outgoing_dynamo",
            profile=Profile(name="민수", birthday="03-15", blood_type="B", gender="남성"),
            state=CharacterState(hunger=80.0, current_location="분수대"),
            customizable=Customizable(speech_habits=SpeechHabits(normal="~")),
        )
    )
    return gs


def test_camera_stores_photo_and_boosts_mood():
    gs = _gs()
    gs.llm = _MockLLM({"title": "분수대의 오후", "caption": "찰칵!"})
    char = gs.get_character(1)
    before = char.state.mood.happiness

    msg = use_tool(gs, char, "camera")

    assert len(gs.photos) == 1
    photo = gs.photos[0]
    assert set(photo) == {"day", "author", "title", "subject"}
    assert photo["author"] == "민수"
    assert photo["title"] == "분수대의 오후"
    assert char.state.mood.happiness == min(10, before + 1)
    assert "분수대의 오후" in msg


def test_camera_falls_back_when_llm_empty():
    gs = _gs()
    gs.llm = _MockLLM({})
    char = gs.get_character(1)
    use_tool(gs, char, "camera")
    assert len(gs.photos) == 1
    assert gs.photos[0]["title"].startswith("무제")


def test_frying_pan_stores_dish_and_reduces_hunger():
    gs = _gs()
    gs.llm = _MockLLM({"dish": "민수표 폭탄볶음", "comment": "완성!"})
    char = gs.get_character(1)

    msg = use_tool(gs, char, "frying_pan")

    assert len(gs.dishes) == 1
    dish = gs.dishes[0]
    assert set(dish) == {"day", "author", "dish"}
    assert dish["author"] == "민수"
    assert dish["dish"] == "민수표 폭탄볶음"
    assert char.state.hunger == 40.0  # 80 - 40
    assert "민수표 폭탄볶음" in msg


def test_frying_pan_falls_back_when_llm_empty():
    gs = _gs()
    gs.llm = _MockLLM({})
    char = gs.get_character(1)
    use_tool(gs, char, "frying_pan")
    assert gs.dishes[0]["dish"] == "정체불명 볶음"


def test_unknown_tool_raises():
    gs = _gs()
    char = gs.get_character(1)
    with pytest.raises(ValueError):
        use_tool(gs, char, "hammer")
