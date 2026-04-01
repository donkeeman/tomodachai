from pathlib import Path

from tomodachai.personality import PersonalityType, load_personalities, get_trait_values


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
