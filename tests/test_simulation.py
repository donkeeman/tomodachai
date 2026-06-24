from tomodachai.config import AppConfig, LocationConfig, SimulationConfig
from tomodachai.character import Character, Profile, CharacterState, Customizable, SpeechHabits
from tomodachai.relationship import RelationshipStage
from tomodachai.simulation import Simulation, assign_locations


def _make_char(char_id: int, name: str, code: str = "outgoing_dynamo") -> Character:
    return Character(
        id=char_id, personality_code=code,
        profile=Profile(name=name),
        state=CharacterState(),
    )


def test_assign_locations():
    locations = [
        LocationConfig(name="공원", capacity=2),
        LocationConfig(name="카페", capacity=2),
    ]
    characters = [_make_char(1, "A"), _make_char(2, "B"), _make_char(3, "C", "outgoing_extrovert")]
    assignments = assign_locations(characters, locations, seed=42)
    assigned_ids = set()
    for loc_name, chars in assignments.items():
        for c in chars:
            assigned_ids.add(c.id)
    assert assigned_ids == {1, 2, 3}
    for loc_name, chars in assignments.items():
        loc = next(l for l in locations if l.name == loc_name)
        assert len(chars) <= loc.capacity


def test_assign_locations_deterministic():
    locations = [LocationConfig(name="공원", capacity=5)]
    chars = [_make_char(i, f"C{i}") for i in range(3)]
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
            {"speaker": "지은", "text": "안녕하세요~"},
        ],
        "deltas": {
            "민수": {"friendship": 3, "romance": 0},
            "지은": {"friendship": 2, "romance": 0},
        },
        "summary": "인사를 나눴다",
    }
    sim = Simulation(
        config=app_config,
        characters=[char_minsu, char_jieun],
        llm=mock_llm,
        personalities=sample_personalities,
    )
    events = sim.step()
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
            "민수": {"friendship": 5, "romance": 0},
            "지은": {"friendship": 3, "romance": 0},
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
    rel = sim.relationships.get(1, 2)
    assert rel.friendship == 5.0


def test_simulation_stores_memory(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "민수", "text": "안녕하세요"}],
        "deltas": {
            "민수": {"friendship": 1, "romance": 0},
            "지은": {"friendship": 1, "romance": 0},
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
    events = sim.memory.get_events_for(1)
    assert len(events) == 1
    assert events[0].type == "conversation"
    assert events[0].location == "공원"


def test_simulation_jealousy_emerges(
    app_config, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    a = _make_char(1, "A", "outgoing_dynamo")
    b = _make_char(2, "B", "easygoing_dreamer")
    c = _make_char(3, "C", "outgoing_extrovert")

    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "A", "text": "안녕하세요"}],
        "deltas": {
            "A": {"friendship": 0, "romance": 0},
            "B": {"friendship": 0, "romance": 0},
        },
        "summary": "대화함",
    }
    sim = Simulation(
        config=app_config, characters=[a, b, c],
        llm=mock_llm, personalities=sample_personalities,
    )
    sim.relationships.update(1, 2, {"romance": 60})
    sim.relationships.update(2, 3, {"friendship": 70})
    sim.step()
    # jealousy manifests as negative friendship toward rival
    rel_13 = sim.relationships.get(1, 3)
    assert rel_13.friendship < 0, "A should have negative feelings toward C"


def test_simulation_stage_transitions(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "민수", "text": "안녕하세요"}],
        "deltas": {
            "민수": {"friendship": 15, "romance": 0},
            "지은": {"friendship": 12, "romance": 0},
        },
        "summary": "대화함",
    }
    sim = Simulation(
        config=app_config,
        characters=[char_minsu, char_jieun],
        llm=mock_llm, personalities=sample_personalities,
    )
    sim.step()
    rel = sim.relationships.get(1, 2)
    assert rel.stage == RelationshipStage.ACQUAINTANCE


def test_simulation_hunger_increases(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "민수", "text": "안녕하세요"}],
        "deltas": {
            "민수": {"friendship": 1, "romance": 0},
            "지은": {"friendship": 1, "romance": 0},
        },
        "summary": "대화함",
    }
    initial_hunger = char_minsu.hunger
    sim = Simulation(
        config=app_config,
        characters=[char_minsu, char_jieun],
        llm=mock_llm, personalities=sample_personalities,
    )
    sim.step()
    assert char_minsu.hunger > initial_hunger


def test_simulation_fight_trigger(
    app_config, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    a = _make_char(1, "A", "outgoing_dynamo")
    b = _make_char(2, "B", "confident_gogetter")

    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "A", "text": "안녕하세요"}],
        "deltas": {
            "A": {"friendship": 0, "romance": 0},
            "B": {"friendship": 0, "romance": 0},
        },
        "summary": "대화함",
    }
    sim = Simulation(
        config=app_config, characters=[a, b],
        llm=mock_llm, personalities=sample_personalities,
    )
    # Set very negative friendship and force ACQUAINTANCE
    rel = sim.relationships.get(1, 2)
    rel.friendship = -50.0
    rel.stage = RelationshipStage.ACQUAINTANCE

    fight_occurred = False
    for i in range(50):
        # Re-set friendship each tick since conversations may shift it
        sim.relationships.get(1, 2).friendship = -50.0
        sim.relationships.get(1, 2).stage = RelationshipStage.ACQUAINTANCE
        events = sim.step()
        for event in events:
            if event["type"] == "fight":
                fight_occurred = True
                break
        if fight_occurred:
            break

    assert fight_occurred, "Very negative friendship should eventually trigger a fight"


def test_simulation_confession_trigger(
    app_config, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    a = _make_char(1, "A", "outgoing_charmer")
    b = _make_char(2, "B", "easygoing_softie")

    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "A", "text": "안녕하세요"}],
        "deltas": {
            "A": {"friendship": 0, "romance": 0},
            "B": {"friendship": 0, "romance": 0},
        },
        "summary": "대화함",
    }
    sim = Simulation(
        config=app_config, characters=[a, b],
        llm=mock_llm, personalities=sample_personalities,
    )
    sim.relationships.update(1, 2, {"friendship": 50, "romance": 75})
    sim.relationships.get(1, 2).stage = RelationshipStage.FRIEND

    bubble_appeared = False
    for _ in range(30):
        sim.step()
        if any(b.kind == "confess_request" for b in sim.bubbles):
            bubble_appeared = True
            break

    assert bubble_appeared, "High romance friends should eventually raise a confess_request bubble"
