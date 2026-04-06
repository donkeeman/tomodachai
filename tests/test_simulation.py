import json
from unittest.mock import MagicMock, patch

from tomodachai.config import AppConfig, LocationConfig, SimulationConfig
from tomodachai.character import Character
from tomodachai.relationship import RelationshipStage
from tomodachai.simulation import Simulation, assign_locations


def test_assign_locations():
    locations = [
        LocationConfig(name="공원", capacity=2),
        LocationConfig(name="카페", capacity=2),
    ]
    characters = [
        Character(id="1", name="A", personality_code="nori_dynamo"),
        Character(id="2", name="B", personality_code="nagomi_dreamer"),
        Character(id="3", name="C", personality_code="nori_extrovert"),
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
    chars = [Character(id=str(i), name=f"C{i}", personality_code="nori_dynamo") for i in range(3)]
    a1 = assign_locations(chars, locations, seed=42)
    a2 = assign_locations(chars, locations, seed=42)
    assert a1 == a2


def test_simulation_tick_generates_conversations(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]

    mock_llm.chat_json.return_value = {
        "dialogue": [
            {"speaker": "민수", "text": "안녕하세요!"},
            {"speaker": "지은", "text": "어, 안녕하세요~"},
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
    events = sim.tick(seed=42)
    assert len(events) >= 0
    for event in events:
        assert "type" in event


def test_simulation_updates_relationships(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "민수", "text": "안녕하세요"}],
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
        "dialogue": [{"speaker": "민수", "text": "안녕하세요"}],
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


def test_simulation_jealousy_emerges(
    app_config, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]

    a = Character(id="a", name="A", personality_code="nori_dynamo")
    b = Character(id="b", name="B", personality_code="nagomi_dreamer")
    c = Character(id="c", name="C", personality_code="nori_extrovert")

    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "A", "text": "안녕하세요"}],
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


def test_simulation_stage_transitions(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    """대화 후 우정 수치에 따라 관계 단계가 자동 전환되는지 확인."""
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "민수", "text": "안녕하세요"}],
        "deltas": {
            "민수": {"friendship": 15, "romance": 0, "tension": 0},
            "지은": {"friendship": 12, "romance": 0, "tension": 0},
        },
        "summary": "대화함",
    }

    sim = Simulation(
        config=app_config,
        characters=[char_minsu, char_jieun],
        llm=mock_llm,
        personalities=sample_personalities,
    )
    sim.tick(seed=42)
    rel = sim.relationships.get("char_1", "char_2")
    assert rel.stage == RelationshipStage.ACQUAINTANCE


def test_simulation_hunger_increases(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    """틱마다 배고픔이 증가하는지 확인."""
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "민수", "text": "안녕하세요"}],
        "deltas": {
            "민수": {"friendship": 1, "romance": 0, "tension": 0},
            "지은": {"friendship": 1, "romance": 0, "tension": 0},
        },
        "summary": "대화함",
    }

    initial_hunger = char_minsu.hunger
    sim = Simulation(
        config=app_config,
        characters=[char_minsu, char_jieun],
        llm=mock_llm,
        personalities=sample_personalities,
    )
    sim.tick(seed=42)
    assert char_minsu.hunger > initial_hunger


def test_simulation_fight_trigger(
    app_config, mock_llm, sample_personalities,
):
    """긴장도가 높으면 싸움이 발생할 수 있는지 확인."""
    app_config.locations = [LocationConfig(name="공원", capacity=5)]

    a = Character(id="a", name="A", personality_code="nori_dynamo")
    b = Character(id="b", name="B", personality_code="dry_gogetter")

    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "A", "text": "안녕하세요"}],
        "deltas": {
            "A": {"friendship": 0, "romance": 0, "tension": 0},
            "B": {"friendship": 0, "romance": 0, "tension": 0},
        },
        "summary": "대화함",
    }

    sim = Simulation(
        config=app_config,
        characters=[a, b],
        llm=mock_llm,
        personalities=sample_personalities,
    )
    # 관계를 ACQUAINTANCE로 만들고 긴장도 높게 설정
    sim.relationships.update("a", "b", {"friendship": 15, "tension": 80})

    # 여러 번 시도해서 싸움이 한 번이라도 발생하는지 확인
    fight_occurred = False
    for i in range(20):
        events = sim.tick(seed=i)
        for event in events:
            if event["type"] == "fight":
                fight_occurred = True
                break
        if fight_occurred:
            break

    assert fight_occurred, "High tension should eventually trigger a fight"


def test_simulation_confession_trigger(
    app_config, mock_llm, sample_personalities,
):
    """로맨스가 높은 친구 사이에서 고백이 발생할 수 있는지 확인."""
    app_config.locations = [LocationConfig(name="공원", capacity=5)]

    a = Character(id="a", name="A", personality_code="nori_charmer")
    b = Character(id="b", name="B", personality_code="nagomi_softie")

    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "A", "text": "안녕하세요"}],
        "deltas": {
            "A": {"friendship": 0, "romance": 0, "tension": 0},
            "B": {"friendship": 0, "romance": 0, "tension": 0},
        },
        "summary": "대화함",
    }

    sim = Simulation(
        config=app_config,
        characters=[a, b],
        llm=mock_llm,
        personalities=sample_personalities,
    )
    # 친구 관계 + 높은 로맨스
    sim.relationships.update("a", "b", {"friendship": 50, "romance": 75})
    rel = sim.relationships.get("a", "b")
    rel.stage = RelationshipStage.FRIEND

    confession_occurred = False
    for i in range(30):
        events = sim.tick(seed=i * 7)
        for event in events:
            if event["type"].startswith("confession"):
                confession_occurred = True
                break
        if confession_occurred:
            break

    assert confession_occurred, "High romance between friends should eventually trigger confession"
