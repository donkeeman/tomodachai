from tomodachai.character import Character


def test_character_creation():
    c = Character(
        id="char_1",
        name="민수",
        personality_code="EWSOB",
        speech_habit="~인 거지",
        backstory="동네 반장을 맡고 있는 활발한 청년",
    )
    assert c.id == "char_1"
    assert c.name == "민수"
    assert c.personality_code == "EWSOB"


def test_character_defaults():
    c = Character(
        id="char_2",
        name="지은",
        personality_code="IWVOG",
    )
    assert c.speech_habit == ""
    assert c.backstory == ""


def test_character_equality():
    a = Character(id="1", name="A", personality_code="EWSOB")
    b = Character(id="1", name="A", personality_code="EWSOB")
    assert a == b


def test_character_different_ids():
    a = Character(id="1", name="A", personality_code="EWSOB")
    b = Character(id="2", name="A", personality_code="EWSOB")
    assert a != b
