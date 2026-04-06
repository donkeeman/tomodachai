from unittest.mock import MagicMock

from tomodachai.personality import (
    PersonalitySliders,
    PersonalityType,
    determine_personality,
    load_personalities,
    match_personality,
)


def test_personality_type_model():
    p = PersonalityType(
        code="nagomi_softie",
        name="ふわふわ형 (포근이)",
        family="nagomi",
        description="테스트",
        behavior_guide="테스트 가이드",
    )
    assert p.code == "nagomi_softie"
    assert p.family == "nagomi"


def test_determine_personality_nagomi():
    sliders = PersonalitySliders(
        movement=0.1, speech=0.1,
        expressiveness=0.1, attitude=0.1,
    )
    assert determine_personality(sliders) == "nagomi_softie"


def test_determine_personality_nori():
    sliders = PersonalitySliders(
        movement=0.9, speech=0.9,
        expressiveness=0.9, attitude=0.9,
    )
    assert determine_personality(sliders) == "nori_extrovert"


def test_determine_personality_cool():
    sliders = PersonalitySliders(
        movement=0.3, speech=0.3,
        expressiveness=0.6, attitude=0.6,
    )
    assert determine_personality(sliders) == "cool_introvert"


def test_determine_personality_dry():
    sliders = PersonalitySliders(
        movement=0.6, speech=0.6,
        expressiveness=0.3, attitude=0.3,
    )
    assert determine_personality(sliders) == "dry_gogetter"


def test_load_personalities():
    personalities = load_personalities()
    assert len(personalities) == 16
    assert "nagomi_softie" in personalities
    assert "nori_dynamo" in personalities
    assert "cool_thinker" in personalities
    assert "dry_busybee" in personalities


def test_all_codes_have_family():
    personalities = load_personalities()
    families = {"nagomi", "cool", "dry", "nori"}
    for code, p in personalities.items():
        assert p.family in families
        assert p.code == code
        assert "_" in code


def test_each_family_has_four_types():
    personalities = load_personalities()
    by_family: dict[str, list] = {}
    for p in personalities.values():
        by_family.setdefault(p.family, []).append(p)
    assert len(by_family) == 4
    for family, types in by_family.items():
        assert len(types) == 4, f"{family} has {len(types)} types, expected 4"


def test_match_personality_returns_sliders(mock_llm):
    mock_llm.chat_json.return_value = {
        "movement": 0.8,
        "speech": 0.9,
        "expressiveness": 0.7,
        "attitude": 0.6,
        "reason": "활발하고 사교적인 성격",
    }
    sliders = match_personality(mock_llm, "활발하고 사교적이며 리더십이 있는 사람")
    assert isinstance(sliders, PersonalitySliders)
    assert 0.0 <= sliders.movement <= 1.0
    code = determine_personality(sliders)
    assert code.startswith("nori")
    mock_llm.chat_json.assert_called_once()
