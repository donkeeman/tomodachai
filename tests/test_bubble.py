"""고백/배고픔 말풍선 — Bubble 모델 + 시뮬 큐."""

import pytest

from tomodachai.bubble import Bubble
from tomodachai.character import Character, CharacterState, Customizable, Profile, SpeechHabits
from tomodachai.config import AppConfig, LLMConfig, LocationConfig, SimulationConfig
from tomodachai.game_state import GameState
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


def test_confession_creates_bubble_not_event(make_sim, monkeypatch):
    sim = make_sim()
    sim.relationships.update(1, 2, {"friendship": 50, "romance": 75})
    monkeypatch.setattr(sim._rng, "random", lambda: 0.0)
    ev = sim._maybe_confession_bubble(1, 2)
    assert any(b.kind == "confess_request" and b.char_id == 1 and b.target_id == 2
               for b in sim.bubbles)
    assert ev is not None and ev["type"] == "bubble"


def test_only_one_confess_request_pending(make_sim, monkeypatch):
    sim = make_sim()
    sim.relationships.update(1, 2, {"friendship": 50, "romance": 75})
    monkeypatch.setattr(sim._rng, "random", lambda: 0.0)
    sim._maybe_confession_bubble(1, 2)
    assert sim._maybe_confession_bubble(1, 2) is None
    assert sum(b.kind == "confess_request" for b in sim.bubbles) == 1


def test_no_confession_bubble_below_thresholds(make_sim, monkeypatch):
    sim = make_sim()
    sim.relationships.update(1, 2, {"friendship": 10, "romance": 75})  # friendship<20
    monkeypatch.setattr(sim._rng, "random", lambda: 0.0)
    assert sim._maybe_confession_bubble(1, 2) is None


def test_no_confession_when_already_lover(make_sim, monkeypatch):
    sim = make_sim()
    sim.relationships.update(1, 2, {"friendship": 50, "romance": 75})
    sim.relationships.set_lover(1, 2)
    monkeypatch.setattr(sim._rng, "random", lambda: 0.0)
    assert sim._maybe_confession_bubble(1, 2) is None


def _confess_bubble(sim, monkeypatch):
    sim.relationships.update(1, 2, {"friendship": 50, "romance": 75})
    monkeypatch.setattr(sim._rng, "random", lambda: 0.0)
    sim._maybe_confession_bubble(1, 2)
    return sim.bubbles[-1]


def test_resolve_confession_giveup_when_not_approved(make_sim, monkeypatch):
    sim = make_sim()
    b = _confess_bubble(sim, monkeypatch)
    ev = sim.resolve_confession(b, approved=False)
    assert ev["type"] == "confession_giveup"
    assert sim._confession_count[(1, 2)] == 3
    assert sim.relationships.get_slots(1).lover != 2


def test_resolve_confession_success(make_sim, monkeypatch):
    sim = make_sim()
    b = _confess_bubble(sim, monkeypatch)
    monkeypatch.setattr(sim._rng, "random", lambda: 0.0)   # <0.5 → 수락
    ev = sim.resolve_confession(b, approved=True)
    assert ev["type"] == "confession_success"
    assert sim.relationships.get_slots(1).lover == 2
    assert sim.relationships.get_slots(2).lover == 1
    assert sim.relationships.get(1, 2).spark is True
    assert sim._confession_count[(1, 2)] == 0
    # 뉴스/대화 맥락용으로 memory에도 confession 이벤트가 남아야 함 (legacy 패리티)
    mem = sim.memory.get_events_between(1, 2)
    assert any(e.type == "confession" and e.result == "accepted" for e in mem)


def test_resolve_confession_fail_increments_count(make_sim, monkeypatch):
    sim = make_sim()
    b = _confess_bubble(sim, monkeypatch)
    monkeypatch.setattr(sim._rng, "random", lambda: 0.99)  # >=0.5 → 거절
    ev = sim.resolve_confession(b, approved=True)
    assert ev["type"] == "confession_fail"
    assert sim._confession_count[(1, 2)] == 1
    assert sim.relationships.get_slots(1).lover != 2


# ------------------------------------------------------------------
# GameState 통합 테스트
# ------------------------------------------------------------------


def _gs_two():
    cfg = AppConfig(
        llm=LLMConfig(provider="litellm", model="ollama/gemma3", temperature=0.8),
        simulation=SimulationConfig(),
        locations=[LocationConfig(name="공원", capacity=5)],
    )
    gs = GameState(config=cfg)
    gs.add_character(_char(1, "A"))
    gs.add_character(_char(2, "B"))
    return gs


def test_gs_bubbles_property(monkeypatch):
    gs = _gs_two()
    sim = gs.simulation
    sim.relationships.update(1, 2, {"friendship": 50, "romance": 75})
    monkeypatch.setattr(sim._rng, "random", lambda: 0.0)
    sim._maybe_confession_bubble(1, 2)
    assert len(gs.bubbles) == 1


def test_answer_bubble_allow_records_event(monkeypatch):
    gs = _gs_two()
    sim = gs.simulation
    sim.relationships.update(1, 2, {"friendship": 50, "romance": 75})
    monkeypatch.setattr(sim._rng, "random", lambda: 0.0)
    sim._maybe_confession_bubble(1, 2)

    out = gs.answer_bubble(0, "A", allow=True)
    assert "scene" in out
    assert gs.bubbles == []
    assert any(e["raw"]["type"].startswith("confession") for e in gs.events_since(0))


def test_answer_bubble_name_mismatch(monkeypatch):
    gs = _gs_two()
    sim = gs.simulation
    sim.relationships.update(1, 2, {"friendship": 50, "romance": 75})
    monkeypatch.setattr(sim._rng, "random", lambda: 0.0)
    sim._maybe_confession_bubble(1, 2)
    out = gs.answer_bubble(0, "B", allow=True)  # index 0의 owner는 A
    assert "error" in out
    assert len(gs.bubbles) == 1


def test_answer_bubble_out_of_range():
    gs = _gs_two()
    out = gs.answer_bubble(5, "A", allow=True)
    assert "error" in out


def test_answer_bubble_hungry_guard():
    gs = _gs_two()
    gs.bubbles.append(Bubble(kind="hungry", char_id=1, text='A: "배고파요..."'))
    out = gs.answer_bubble(0, "A", allow=True)
    assert "error" in out
    assert len(gs.bubbles) == 1


def test_clear_hungry_bubble():
    gs = _gs_two()
    gs.bubbles.append(Bubble(kind="hungry", char_id=1, text='A: "배고파요..."'))
    gs.bubbles.append(Bubble(kind="hungry", char_id=2, text='B: "배고파요..."'))
    gs.clear_hungry_bubble(1)
    assert [b.char_id for b in gs.bubbles] == [2]
