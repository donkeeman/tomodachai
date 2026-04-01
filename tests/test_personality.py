from pathlib import Path
from unittest.mock import MagicMock

from tomodachai.personality import PersonalityType, load_personalities, get_trait_values, match_personality


def test_personality_type_model():
    p = PersonalityType(
        code="EWSOB",
        name="불꽃 리더",
        description="테스트",
        behavior_guide="테스트 가이드",
    )
    assert p.code == "EWSOB"
    assert p.name == "불꽃 리더"


def test_get_trait_values():
    traits = get_trait_values("EWSOB")
    assert traits == {
        "energy": "extroverted",
        "warmth": "warm",
        "stability": "steady",
        "openness": "open",
        "assertiveness": "bold",
    }


def test_get_trait_values_introverted():
    traits = get_trait_values("ICVTG")
    assert traits == {
        "energy": "introverted",
        "warmth": "cool",
        "stability": "volatile",
        "openness": "traditional",
        "assertiveness": "gentle",
    }


def test_load_personalities():
    personalities = load_personalities()
    assert len(personalities) == 32
    assert "EWSOB" in personalities
    assert "ICVTG" in personalities
    assert personalities["EWSOB"].name == "불꽃 리더"


def test_all_codes_are_valid():
    personalities = load_personalities()
    for code, p in personalities.items():
        assert len(code) == 5
        assert code[0] in ("E", "I")
        assert code[1] in ("W", "C")
        assert code[2] in ("S", "V")
        assert code[3] in ("O", "T")
        assert code[4] in ("B", "G")
        assert p.code == code


def test_match_personality_returns_valid_code(mock_llm):
    personalities = load_personalities()
    mock_llm.chat_json.return_value = {
        "code": "EWSOB",
        "reason": "활발하고 사교적인 성격",
    }
    result = match_personality(
        mock_llm, personalities,
        "활발하고 사교적이며 리더십이 있는 사람",
    )
    assert result == "EWSOB"
    mock_llm.chat_json.assert_called_once()


def test_match_personality_prompt_contains_types(mock_llm):
    personalities = load_personalities()
    mock_llm.chat_json.return_value = {"code": "ICVTG", "reason": "test"}
    match_personality(mock_llm, personalities, "조용한 사람")
    call_args = mock_llm.chat_json.call_args
    prompt = call_args[0][0][1]["content"]
    assert "EWSOB" in prompt
    assert "불꽃 리더" in prompt
    assert "ICVTG" in prompt
