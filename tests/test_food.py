"""음식 마스터 + 선호 구간 (prototype/game/items.py 규칙)."""

from tomodachai.food import FOODS, TIER_REACTIONS, preference_tier


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
