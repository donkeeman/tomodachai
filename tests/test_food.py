"""음식 마스터 + 선호 구간 (prototype/game/items.py 규칙)."""

import pytest

from tomodachai.character import Character, CharacterState, Profile
from tomodachai.food import FOODS, TIER_REACTIONS, ensure_food_prefs, feed, preference_tier


def test_foods_master_has_ten():
    assert len(FOODS) == 10
    assert FOODS[0] == "김치찌개"
    assert FOODS[9] == "아이스크림"


def test_preference_tier_boundaries():
    # n=10 기준: rank 0,1=favorite / 2,3=like / 4,5=normal / 6,7=dislike / 8,9=worst
    assert preference_tier(0) == "favorite"
    assert preference_tier(1) == "favorite"
    assert preference_tier(2) == "like"
    assert preference_tier(3) == "like"
    assert preference_tier(4) == "normal"
    assert preference_tier(5) == "normal"
    assert preference_tier(6) == "dislike"
    assert preference_tier(7) == "dislike"
    assert preference_tier(8) == "worst"
    assert preference_tier(9) == "worst"


def test_tier_reactions_keys_and_shape():
    assert set(TIER_REACTIONS) == {"favorite", "like", "normal", "dislike", "worst"}
    text, sat, (h, e, s) = TIER_REACTIONS["favorite"]
    assert isinstance(text, str)
    assert sat == 8
    assert (h, e, s) == (2.5, 1.0, -1.0)


# ---------------------------------------------------------------------------
# ensure_food_prefs / feed 테스트
# ---------------------------------------------------------------------------


def _char(cid=1, name="민수"):
    return Character(
        id=cid,
        personality_code="outgoing_dynamo",
        profile=Profile(name=name, birthday="03-15", blood_type="B", gender="남성"),
        state=CharacterState(hunger=80.0, satisfaction=50.0),
    )


def test_ensure_food_prefs_seeds_full_permutation():
    c = _char()
    ensure_food_prefs(c)
    assert sorted(c.preferences.food_ranks) == list(range(len(FOODS)))
    assert c.preferences.food_eaten == [False] * len(FOODS)


def test_ensure_food_prefs_is_deterministic_and_idempotent():
    a, b = _char(cid=7), _char(cid=7)
    ensure_food_prefs(a)
    ensure_food_prefs(b)
    assert a.preferences.food_ranks == b.preferences.food_ranks
    first = list(a.preferences.food_ranks)
    ensure_food_prefs(a)  # 두 번째 호출은 덮어쓰지 않음
    assert a.preferences.food_ranks == first


def test_feed_reduces_hunger_and_marks_dex():
    c = _char()
    msg = feed(c, food_id=0)
    assert c.state.hunger == 30.0  # 80 - 50
    assert c.preferences.food_eaten[0] is True
    assert "도감에 기록" in msg
    assert FOODS[0] in msg


def test_feed_hunger_clamps_at_zero():
    c = _char()
    c.state.hunger = 20.0
    feed(c, food_id=0)
    assert c.state.hunger == 0.0


def test_feed_second_time_no_discovery_note():
    c = _char()
    feed(c, food_id=0)
    msg2 = feed(c, food_id=0)
    assert "도감에 기록" not in msg2


def test_feed_favorite_boosts_satisfaction_and_mood():
    c = _char()
    ensure_food_prefs(c)
    fav_id = c.preferences.food_ranks.index(0)  # 최애(rank 0) 음식 id
    before = c.state.satisfaction
    feed(c, fav_id)
    assert c.state.satisfaction == before + 8  # favorite sat delta
    assert c.state.mood.happiness == 8  # 5 + favorite(+2.5) → round(7.5)


def test_feed_invalid_food_id_raises():
    c = _char()
    with pytest.raises(ValueError):
        feed(c, food_id=99)
