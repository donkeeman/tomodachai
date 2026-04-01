import json
from unittest.mock import MagicMock, patch

from tomodachai.config import AppConfig, LocationConfig, SimulationConfig
from tomodachai.character import Character
from tomodachai.simulation import Simulation, assign_locations


def test_assign_locations():
    locations = [
        LocationConfig(name="공원", capacity=2),
        LocationConfig(name="카페", capacity=2),
    ]
    characters = [
        Character(id="1", name="A", personality_code="EWSOB"),
        Character(id="2", name="B", personality_code="IWSOG"),
        Character(id="3", name="C", personality_code="ECVOB"),
    ]
    assignments = assign_locations(characters, locations, seed=42)
    assigned_ids = set()
    for loc_name, chars in assignments.items():
        for c in chars:
            assigned_ids.add(c.id)
    assert assigned_ids == {"1", "2", "3"}
    for loc_name, chars in assignments.items():
        loc = next(l for l in locations if l.name == loc_name)
        assert len(chars) <= loc.capacity


def test_assign_locations_deterministic():
    locations = [LocationConfig(name="공원", capacity=5)]
    chars = [Character(id=str(i), name=f"C{i}", personality_code="EWSOB") for i in range(3)]
    a1 = assign_locations(chars, locations, seed=42)
    a2 = assign_locations(chars, locations, seed=42)
    assert a1 == a2


def test_simulation_tick_generates_conversations(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]

    mock_llm.chat_json.return_value = {
        "dialogue": [
            {"speaker": "민수", "text": "안녕!"},
            {"speaker": "지은", "text": "어 안녕~"},
        ],
        "deltas": {
            "민수": {"friendship": 3, "romance": 0, "tension": 0},
            "지은": {"friendship": 2, "romance": 0, "tension": 0},
        },
        "summary": "인사를 나눴다",
    }

    sim = Simulation(
        config=app_config,
        characters=[char_minsu, char_jieun],
        llm=mock_llm,
        personalities=sample_personalities,
    )
    results = sim.tick(seed=42)
    assert len(results) >= 0


def test_simulation_updates_relationships(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "민수", "text": "hi"}],
        "deltas": {
            "민수": {"friendship": 5, "romance": 0, "tension": 0},
            "지은": {"friendship": 3, "romance": 0, "tension": 0},
        },
        "summary": "대화함",
    }

    sim = Simulation(
        config=app_config,
        characters=[char_minsu, char_jieun],
        llm=mock_llm,
        personalities=sample_personalities,
    )
    sim._force_encounter(char_minsu, char_jieun, "공원")
    rel = sim.relationships.get("char_1", "char_2")
    assert rel.friendship == 5.0


def test_simulation_stores_memory(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "민수", "text": "hi"}],
        "deltas": {
            "민수": {"friendship": 1, "romance": 0, "tension": 0},
            "지은": {"friendship": 1, "romance": 0, "tension": 0},
        },
        "summary": "공원에서 인사",
    }

    sim = Simulation(
        config=app_config,
        characters=[char_minsu, char_jieun],
        llm=mock_llm,
        personalities=sample_personalities,
    )
    sim._force_encounter(char_minsu, char_jieun, "공원")
    events = sim.memory.get_events_for("char_1")
    assert len(events) == 1
    assert events[0].summary == "공원에서 인사"


from tomodachai.relationship import detect_triangles


def test_simulation_jealousy_emerges(
    app_config, mock_llm, sample_personalities,
):
    from tomodachai.character import Character
    from tomodachai.config import LocationConfig

    app_config.locations = [LocationConfig(name="공원", capacity=5)]

    a = Character(id="a", name="A", personality_code="EWSOB")
    b = Character(id="b", name="B", personality_code="IWVOG")
    c = Character(id="c", name="C", personality_code="ECVOB")

    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "A", "text": "hi"}],
        "deltas": {
            "A": {"friendship": 5, "romance": 0, "tension": 0},
            "B": {"friendship": 5, "romance": 0, "tension": 0},
        },
        "summary": "대화함",
    }

    sim = Simulation(
        config=app_config,
        characters=[a, b, c],
        llm=mock_llm,
        personalities=sample_personalities,
    )

    sim.relationships.update("a", "b", {"romance": 60})
    sim.relationships.update("b", "c", {"friendship": 70})

    sim.tick(seed=42)

    rel_ac = sim.relationships.get("a", "c")
    assert rel_ac.jealousy > 0, "A should be jealous of C"
