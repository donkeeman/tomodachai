"""고백/배고픔 말풍선 — Bubble 모델 + 시뮬 큐."""

import pytest

from tomodachai.bubble import Bubble
from tomodachai.character import Character, CharacterState, Customizable, Profile, SpeechHabits
from tomodachai.config import AppConfig, LLMConfig, LocationConfig, SimulationConfig
from tomodachai.simulation import Simulation


def _char(cid: int, name: str) -> Character:
    return Character(
        id=cid,
        profile=Profile(name=name, birthday="03-15", blood_type="B", gender="남성"),
        state=CharacterState(),
        customizable=Customizable(speech_habits=SpeechHabits(normal="~")),
    )


@pytest.fixture
def make_sim(mock_llm, sample_personalities):
    def _factory(chars=None):
        cfg = AppConfig(
            llm=LLMConfig(provider="litellm", model="ollama/gemma3", temperature=0.8),
            simulation=SimulationConfig(),
            locations=[LocationConfig(name="공원", capacity=5)],
        )
        chars = chars if chars is not None else [_char(1, "A"), _char(2, "B")]
        return Simulation(
            config=cfg, characters=chars, llm=mock_llm, personalities=sample_personalities
        )
    return _factory


def test_bubble_defaults():
    b = Bubble(kind="confess_request", char_id=1)
    assert b.kind == "confess_request"
    assert b.char_id == 1
    assert b.target_id is None
    assert b.text == ""


def test_simulation_starts_with_empty_bubbles(make_sim):
    sim = make_sim()
    assert sim.bubbles == []
    assert sim._confession_count == {}


def test_hungry_bubble_added_once(make_sim):
    sim = make_sim()
    sim.characters[0].hunger = 85.0
    sim._update_needs()
    hungry = [b for b in sim.bubbles if b.kind == "hungry" and b.char_id == 1]
    assert len(hungry) == 1
    assert "배고" in hungry[0].text
    # 다시 호출해도 중복 추가 안 함
    sim._update_needs()
    hungry = [b for b in sim.bubbles if b.kind == "hungry" and b.char_id == 1]
    assert len(hungry) == 1


def test_no_hungry_bubble_below_threshold(make_sim):
    sim = make_sim()
    sim.characters[0].hunger = 50.0
    sim._update_needs()
    assert not any(b.kind == "hungry" for b in sim.bubbles)
