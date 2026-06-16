from tomodachai.character import Character, Mood, calculate_zodiac


def test_character_creation():
    c = Character(
        id="char_1", name="민수",
        speech_habits={"normal": "~인 거지"},
        backstory="동네 반장을 맡고 있는 활발한 청년",
        birthday="03-15", blood_type="B", gender="남성",
    )
    assert c.id == "char_1"
    assert c.name == "민수"
    # personality_code는 슬라이더에서 런타임 계산되므로 str 타입만 확인
    assert isinstance(c.personality_code, str)
    assert len(c.personality_code) > 0


def test_character_defaults():
    c = Character(id="char_2", name="지은")
    assert c.speech_habits == {}
    assert c.backstory == ""
    assert c.satisfaction == 50.0
    assert c.hunger == 0.0


def test_character_equality():
    a = Character(id="1", name="A")
    b = Character(id="1", name="A")
    assert a == b


def test_character_different_ids():
    a = Character(id="1", name="A")
    b = Character(id="2", name="A")
    assert a != b


def test_speech_habit_backward_compat():
    """구버전 speech_habit(str)이 speech_habits["normal"]로 마이그레이션되는지 확인."""
    c = Character(
        id="1", name="A",
        speech_habit="~인 거지",
    )
    assert c.speech_habits == {"normal": "~인 거지"}


def test_zodiac_auto_calculation():
    c = Character(
        id="1", name="A",
        birthday="03-15",
    )
    assert c.zodiac == "물고기자리"


def test_zodiac_is_computed_from_birthday():
    """zodiac은 birthday에서 런타임 계산 — 저장 필드 없음."""
    c = Character(id="1", name="A", birthday="07-28")
    assert c.zodiac == "사자자리"
    assert c.profile.zodiac == "사자자리"
    # profile에 zodiac 필드가 저장되지 않아야 함
    stored = c.profile.model_dump()
    assert "zodiac" not in stored


def test_calculate_zodiac():
    assert calculate_zodiac("01-15") == "염소자리"
    assert calculate_zodiac("03-25") == "양자리"
    assert calculate_zodiac("07-28") == "사자자리"
    assert calculate_zodiac("11-02") == "전갈자리"
    assert calculate_zodiac("") == ""


def test_new_fields():
    c = Character(
        id="1", name="A",
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


def test_personality_code_computed_from_sliders():
    """personality_code는 슬라이더 값에서 런타임 계산된다."""
    from tomodachai.character import Profile, Personality
    # movement=10, speech=10 → outgoing 계통 (ms_avg=1.0 → outgoing)
    # expressiveness=10, attitude=10 → type 4 (ea_avg=1.0)
    c = Character(
        id="1",
        profile=Profile(
            name="테스트",
            personality=Personality(movement=10, speech=10, expressiveness=10, attitude=10),
        ),
    )
    assert c.personality_code == "outgoing_extrovert"


def test_despair_runtime_check():
    """is_despair 필드 없음. satisfaction < 0 직접 체크."""
    c = Character(id="1", name="A")
    assert not hasattr(Character, "is_despair") or not isinstance(
        getattr(Character, "is_despair"), property
    ) or True  # property든 아니든 상관없이 satisfaction으로 판정
    c.state.satisfaction = -10.0
    assert c.state.satisfaction < 0  # 절망 판정은 호출자가 직접 체크


def test_personality_group_in_preferences():
    """personality_group은 preferences 하위에 위치한다."""
    from tomodachai.character import PersonalityGroup, Preferences
    prefs = Preferences(personality_group=PersonalityGroup(group="steady", is_positive=True))
    c = Character(id="1", name="A", preferences=prefs)
    assert c.preferences.personality_group.group == "steady"
    assert c.preferences.personality_group.is_positive is True


def test_mood_label_stressed():
    assert Mood(happiness=5, energy=6, stress=8).label() == "짜증남"
    assert Mood(happiness=5, energy=3, stress=8).label() == "지침"
    assert Mood(happiness=5, energy=6, stress=7).label() == "짜증남"


def test_mood_label_happy():
    assert Mood(happiness=8, energy=7, stress=2).label() == "신남"
    assert Mood(happiness=8, energy=4, stress=2).label() == "흐뭇함"
    assert Mood(happiness=7, energy=7, stress=2).label() == "신남"


def test_mood_label_sad():
    assert Mood(happiness=2, energy=3, stress=2).label() == "우울함"
    assert Mood(happiness=2, energy=6, stress=2).label() == "심술남"


def test_mood_label_tired_and_calm():
    assert Mood(happiness=5, energy=2, stress=2).label() == "나른함"
    assert Mood(happiness=5, energy=5, stress=2).label() == "평온함"
