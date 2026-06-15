# 음식 마스터 데이터 (프로토타입 최소 구성) + 선호 구간 리액션 (01-character.md)
from __future__ import annotations

from typing import Tuple

from .models import Character, GameState

# 인덱스 = 음식 ID
FOODS = [
    "김치찌개", "초밥", "햄버거", "샐러드", "라면",
    "케이크", "떡볶이", "스테이크", "두부", "아이스크림",
]

# 선호 구간: 순위 기준 최애 2 / 좋아함 2 / 보통 / 싫어함 2 / 최악 2
def preference_tier(char: Character, food_id: int) -> str:
    rank = char.food_ranks[food_id]  # 0 = 가장 좋아함
    n = len(FOODS)
    if rank < 2:
        return "favorite"
    if rank < 4:
        return "like"
    if rank >= n - 2:
        return "worst"
    if rank >= n - 4:
        return "dislike"
    return "normal"


TIER_REACTIONS = {
    "favorite": ("최애예요!! (눈이 커지고 춤을 춥니다)", 8, (2.5, 1.0, -1.0)),
    "like": ("웃으며 맛있게 먹습니다.", 4, (1.5, 0.5, -0.5)),
    "normal": ("무난하게 먹습니다.", 1, (0.5, 0.3, 0.0)),
    "dislike": ("찡그리며 억지로 삼킵니다...", -3, (-1.5, 0.0, 1.0)),
    "worst": ("우웩! 쓰러질 듯 괴로워합니다!!", -6, (-2.5, -1.0, 2.0)),
}


def feed(state: GameState, char: Character, food_id: int) -> str:
    # 음식 주기: 배고픔 해소 + 선호 구간별 만족도/기분 변동
    tier = preference_tier(char, food_id)
    text, sat, (h, e, s) = TIER_REACTIONS[tier]
    char.hunger = max(0.0, char.hunger - 50)
    # 배고픔 말풍선 해소
    state.bubbles = [b for b in state.bubbles
                     if not (b.kind == "hungry" and b.char_id == char.id)]
    char.satisfaction = min(100.0, char.satisfaction + sat)
    char.mood.adjust(happiness=h, energy=e, stress=s)
    if not char.food_eaten[food_id]:
        char.food_eaten[food_id] = True
        discovered = " (도감에 기록!)"
    else:
        discovered = ""
    return f"🍽 {char.name}에게 {FOODS[food_id]}을(를) 주었습니다 → {text}{discovered}"


def food_dex(char: Character) -> str:
    # 도감식 표시: 줘본 것만 + 최애/최악은 발견 시 표시
    lines = []
    for fid, name in enumerate(FOODS):
        if not char.food_eaten[fid]:
            lines.append(f"  {name}: ???")
            continue
        tier = preference_tier(char, fid)
        label = {"favorite": "💖 최애", "like": "🙂 좋아함", "normal": "😐 보통",
                 "dislike": "😖 별로인 듯?", "worst": "🤢 최악"}[tier]
        # 싫어함 구간은 직접 표시하지 않음 → 리액션으로만 유추 (애매하게 표기)
        lines.append(f"  {name}: {label}")
    return "\n".join(lines)
