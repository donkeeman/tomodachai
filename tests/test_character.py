from tomodachai.character import Character, calculate_zodiac


def test_character_creation():
    c = Character(
        id="char_1", name="민수", personality_code="outgoing_dynamo",
        speech_habits={"normal": "~인 거지"},
        backstory="동네 반장을 맡고 있는 활발한 청년",
        birthday="03-15", blood_type="B", gender="남성",
    )
    assert c.id == "char_1"
    assert c.name == "민수"
    assert c.personality_code == "outgoing_dynamo"


def test_character_defaults():
    c = Character(id="char_2", name="지은", personality_code="easygoing_dreamer")
    assert c.speech_habits == {}
    assert c.backstory == ""
    assert c.satisfaction == 50.0
    assert c.hunger == 0.0


def test_character_equality():
    a = Character(id="1", name="A", personality_code="outgoing_dynamo")
    b = Character(id="1", name="A", personality_code="outgoing_dynamo")
    assert a == b


def test_character_different_ids():
    a = Character(id="1", name="A", personality_code="outgoing_dynamo")
    b = Character(id="2", name="A", personality_code="outgoing_dynamo")
    assert a != b


def test_speech_habit_backward_compat():
    """구버전 speech_habit(str)이 speech_habits["normal"]로 마이그레이션되는지 확인."""
    c = Character(
        id="1", name="A", personality_code="outgoing_dynamo",
        speech_habit="~인 거지",
    )
    assert c.speech_habits == {"normal": "~인 거지"}


def test_zodiac_auto_calculation():
    c = Character(
        id="1", name="A", personality_code="outgoing_dynamo",
        birthday="03-15",
    )
    assert c.zodiac == "물고기자리"


def test_zodiac_manual_override():
    c = Character(
        id="1", name="A", personality_code="outgoing_dynamo",
        birthday="03-15", zodiac="커스텀",
    )
    assert c.zodiac == "커스텀"


def test_calculate_zodiac():
    assert calculate_zodiac("01-15") == "염소자리"
    assert calculate_zodiac("03-25") == "양자리"
    assert calculate_zodiac("07-28") == "사자자리"
    assert calculate_zodiac("11-02") == "전갈자리"
    assert calculate_zodiac("") == ""


def test_new_fields():
    c = Character(
        id="1", name="A", personality_code="outgoing_dynamo",
        birthday="09-09", blood_type="AB", gender="여성",
        favorite_color="연두색",
        food_preferences={"item_1": "최애"},
        nicknames={"char_2": "수수"},
        mini_personality=["걸을 때 팔을 크게 흔든다"],
    )
    assert c.blood_type == "AB"
    assert c.zodiac == "처녀자리"
    assert c.food_preferences["item_1"] == "최애"
    assert c.nicknames["char_2"] == "수수"
    assert len(c.mini_personality) == 1
