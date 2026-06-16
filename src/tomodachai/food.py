"""음식 마스터 데이터 + 선호 구간 (prototype/game/items.py 규칙 이식)."""

from __future__ import annotations

import random

from tomodachai.character import Character

# 인덱스 = 음식 ID
FOODS: list[str] = [
    "김치찌개",
    "초밥",
    "햄버거",
    "샐러드",
    "라면",
    "케이크",
    "떡볶이",
    "스테이크",
    "두부",
    "아이스크림",
]

# 선호 구간별 반응: (텍스트, 만족도Δ, (happiness, energy, stress)Δ)
TIER_REACTIONS: dict[str, tuple[str, int, tuple[float, float, float]]] = {
    "favorite": ("최애예요!! (눈이 커지고 춤을 춥니다)", 8, (2.5, 1.0, -1.0)),
    "like": ("웃으며 맛있게 먹습니다.", 4, (1.5, 0.5, -0.5)),
    "normal": ("무난하게 먹습니다.", 1, (0.5, 0.3, 0.0)),
    "dislike": ("찡그리며 억지로 삼킵니다...", -3, (-1.5, 0.0, 1.0)),
    "worst": ("우웩! 쓰러질 듯 괴로워합니다!!", -6, (-2.5, -1.0, 2.0)),
}


def preference_tier(rank: int, food_count: int = len(FOODS)) -> str:
    """순위(rank, 0=가장 좋아함) → 선호 구간 (prototype 규칙)."""
    n = food_count
    if rank < 2:
        return "favorite"
    if rank < 4:
        return "like"
    if rank >= n - 2:
        return "worst"
    if rank >= n - 4:
        return "dislike"
    return "normal"


def ensure_food_prefs(char: Character) -> None:
    """food_ranks/food_eaten가 비었으면 캐릭터별 결정적 시드로 초기화 (멱등)."""
    prefs = char.preferences
    n = len(FOODS)
    if len(prefs.food_ranks) != n:
        seed = char.id if isinstance(char.id, int) else abs(hash(char.id))
        ranks = list(range(n))
        random.Random(seed).shuffle(ranks)
        prefs.food_ranks = ranks
    if len(prefs.food_eaten) != n:
        prefs.food_eaten = [False] * n


def feed(char: Character, food_id: int) -> str:
    """캐릭터에게 음식을 준다 (prototype/game items.feed 규칙). 반환: 결과 메시지.

    Raises:
        ValueError: food_id가 음식 범위를 벗어날 때.
    """
    if not (0 <= food_id < len(FOODS)):
        raise ValueError(f"음식 id {food_id} 없음")
    ensure_food_prefs(char)

    tier = preference_tier(char.preferences.food_ranks[food_id])
    text, sat, (h, e, s) = TIER_REACTIONS[tier]

    st = char.state
    st.hunger = max(0.0, st.hunger - 50)
    st.satisfaction = min(100.0, st.satisfaction + sat)
    st.mood.adjust(happiness=h, energy=e, stress=s)

    discovered = ""
    if not char.preferences.food_eaten[food_id]:
        char.preferences.food_eaten[food_id] = True
        discovered = " (도감에 기록!)"

    return f"🍽 {char.name}에게 {FOODS[food_id]}을(를) 주었습니다 → {text}{discovered}"
