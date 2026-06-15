"""음식 마스터 데이터 + 선호 구간 (prototype/game/items.py 규칙 이식)."""

from __future__ import annotations

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
