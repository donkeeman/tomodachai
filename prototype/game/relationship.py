# 관계 시스템 (02-relationship.md): 수치 변동, 상태 텍스트, 궁합, 단계 전환
from __future__ import annotations

import random
from typing import List, Optional, Tuple

from .models import Character, GameState

# friendship 구간 → 상태 텍스트 (문서 매핑 그대로)
FRIENDSHIP_LABELS = [
    (-100, -70, "앙숙"),
    (-69, -50, "사이가 나쁨"),
    (-49, -20, "서먹서먹"),
    (-19, 19, "그저 그런 사이"),
    (20, 39, "알고 지내는 사이"),
    (40, 59, "친해지는 중"),
    (60, 79, "꽤 친한 사이"),
    (80, 100, "둘도 없는 친구"),
]

ROMANCE_LABELS = [
    (1, 20, "약간 신경 쓰이는"),
    (21, 49, "좋아하는 것 같은"),
    (50, 79, "많이 좋아하는"),
    (80, 100, "완전 반한"),
]

BREAKUP_REASONS = {
    "mutual": "합의",
    "fight": "싸움",
    "cheating": "바람",
    "boredom": "권태",
    "triangle": "삼각관계",
    "misunderstanding": "오해",
}


def friendship_label(v: float) -> str:
    for lo, hi, label in FRIENDSHIP_LABELS:
        if lo <= v <= hi:
            return label
    return "그저 그런 사이"


def romance_label(v: float) -> Optional[str]:
    # romance > 0일 때만 표시
    for lo, hi, label in ROMANCE_LABELS:
        if lo <= v <= hi:
            return label
    return None


def affinity(a: Character, b: Character) -> float:
    # 궁합: 성격/혈액형/별자리 + 캐릭터별 시드 → 0.7~1.3 고정 계수
    # 구체 공식은 미확정이므로 결정적 해시 기반 잠정 구현
    rng = random.Random(a.seed * 31 + b.seed * 17 + hash(a.blood_type + b.blood_type) % 1000)
    base = rng.uniform(0.75, 1.25)
    # 성격 계통 선호/비선호의 미세 보정은 생략 (프로토타입 범위 외)
    return round(max(0.7, min(1.3, base)), 2)


def affinity_applies(a: Character, b: Character) -> bool:
    # 이미 관계가 형성된 후에는 궁합 영향 없음
    rel = a.rel(b.id)
    return rel.friendship < 30 and rel.romance < 20


def conversation_delta(state: GameState, a: Character, b: Character) -> None:
    # 대화 기본 델타: friendship +1~4, romance +0.5~2 (MVP: 연애는 남녀 간만)
    # romance는 반함(spark) 상태에서만 누적 — 반하기 전엔 0 고정 (반함 트리거)
    rng = state.rng
    for x, y in ((a, b), (b, a)):
        coef = affinity(x, y) if affinity_applies(x, y) else 1.0
        x.rel(y.id).add(friendship=rng.uniform(1, 4) * coef)
        if x.gender != y.gender and x.rel(y.id).spark:
            x.rel(y.id).add(romance=rng.uniform(0.5, 2) * coef)
        # 친구와 대화 → 기분 회복
        x.mood.adjust(happiness=0.5, energy=0.3, stress=-0.5)


def do_spark(state: GameState, a: Character, b: Character, reason: str = "") -> str:
    # 반함 처리: 이 순간부터 romance 누적 시작. 단방향 (a → b)
    rel = a.rel(b.id)
    rel.spark = True
    rel.add(romance=state.rng.uniform(10, 18))
    a.mood.adjust(happiness=1.5, energy=1)
    detail = f" ({reason})" if reason else ""
    state.add_event(type="spark", participants=[a.id, b.id],
                    summary=f"{a.name}이(가) {b.name}에게 반함{detail}")
    return f"💘 {a.name}이(가) {b.name}에게 반한 것 같습니다...!{detail}"


def daily_decay(state: GameState) -> None:
    # 자연 변동: 하루 1회, 0을 향해 -0.5~1 (대화 1회로 상쇄 가능한 수준)
    rng = state.rng
    for char in state.characters.values():
        for other_id, rel in char.relationships.items():
            decay = rng.uniform(0.5, 1.0)
            if rel.friendship > 0:
                rel.friendship = max(0.0, rel.friendship - decay)
            elif rel.friendship < 0:
                rel.friendship = min(0.0, rel.friendship + decay)
            if rel.romance > 0:
                rel.romance = max(0.0, rel.romance - decay)
            # 연심이 0 근처까지 식으면 반함 해제 (마음이 식음). 현재 연인은 제외
            if rel.spark and rel.romance < 3 and char.slots["lover"] != other_id:
                rel.spark = False
                other = state.characters[other_id]
                state.add_event(type="spark_end", participants=[char.id, other_id],
                                summary=f"{char.name}의 {other.name}을(를) 향한 마음이 어느새 식음")


def mutual(a: Character, b: Character, attr: str) -> Tuple[float, float]:
    return getattr(a.rel(b.id), attr), getattr(b.rel(a.id), attr)


def update_slots(state: GameState, a: Character, b: Character) -> List[str]:
    # 수치 조건 기반 슬롯 성립/해제 판정. 발생한 전환을 한국어 알림으로 반환
    notices = []
    f_ab, f_ba = mutual(a, b, "friendship")

    # 베프 성립 (양방향 ≥ 70, 양쪽 슬롯 모두 비어있거나 서로일 때)
    if f_ab >= 70 and f_ba >= 70:
        if a.slots["best_friend"] is None and b.slots["best_friend"] is None:
            a.slots["best_friend"] = b.id
            b.slots["best_friend"] = a.id
            ev = state.add_event(type="best_friend", participants=[a.id, b.id],
                                 summary=f"{a.name}와(과) {b.name}이(가) 베스트 프렌드가 됨")
            notices.append(f"💛 {a.name}와(과) {b.name}이(가) 베프가 되었습니다!")

    # 원수 성립 (양방향 ≤ -50)
    if f_ab <= -50 and f_ba <= -50:
        if a.slots["enemy"] is None and b.slots["enemy"] is None:
            a.slots["enemy"] = b.id
            b.slots["enemy"] = a.id
            state.add_event(type="enemy", participants=[a.id, b.id],
                            summary=f"{a.name}와(과) {b.name}이(가) 원수가 됨")
            notices.append(f"⚡ {a.name}와(과) {b.name}이(가) 원수가 되었습니다...")

    # 베프 해제 (수치가 크게 떨어지면)
    if a.slots["best_friend"] == b.id and (f_ab < 40 or f_ba < 40):
        a.slots["best_friend"] = None
        b.slots["best_friend"] = None
        notices.append(f"💔 {a.name}와(과) {b.name}의 베프 관계가 깨졌습니다.")

    # 원수 해제 (양쪽 모두 회복 시)
    if a.slots["enemy"] == b.id and f_ab > -20 and f_ba > -20:
        a.slots["enemy"] = None
        b.slots["enemy"] = None
        notices.append(f"🕊 {a.name}와(과) {b.name}이(가) 더 이상 원수가 아닙니다.")

    return notices


def decide_breakup_reason(state: GameState, a: Character, b: Character,
                          after_fight: bool, third_party: bool) -> str:
    # 이별 사유는 시스템이 조건 기반으로 자동 판정 (LLM 판단 아님)
    if third_party:
        return "cheating"
    if after_fight:
        return "fight"
    f_ab, f_ba = mutual(a, b, "friendship")
    if f_ab > -10 and f_ba > -10:
        return "boredom"
    return state.rng.choice(["mutual", "misunderstanding"])


def do_breakup(state: GameState, a: Character, b: Character, reason: str) -> str:
    # 이별 처리: 슬롯 해제 + 전 연인 태그 + 사유별 수치 변동
    from .models import ExLoverTag
    rng = state.rng
    a.slots["lover"] = None
    b.slots["lover"] = None
    a.ex_lovers.append(ExLoverTag(target=b.id, reason=reason, day=state.day))
    b.ex_lovers.append(ExLoverTag(target=a.id, reason=reason, day=state.day))

    # 사유별 수치 변동 (수치 변동표 잠정값)
    if reason == "fight":
        a.rel(b.id).add(romance=-rng.uniform(10, 15), friendship=-rng.uniform(25, 30))
        b.rel(a.id).add(friendship=-rng.uniform(25, 30))  # 당한 쪽 romance 유지(미련)
        b.satisfaction -= 20
    elif reason == "cheating":
        a.rel(b.id).add(romance=-15, friendship=-15)
        b.rel(a.id).add(friendship=-rng.uniform(30, 40))
        b.satisfaction -= 25
    elif reason == "boredom":
        a.rel(b.id).add(romance=-25)
        b.rel(a.id).add(romance=-15)
    else:  # mutual / misunderstanding / triangle
        a.rel(b.id).add(romance=-rng.uniform(20, 30), friendship=-5)
        b.rel(a.id).add(romance=-rng.uniform(20, 30), friendship=-5)
        a.satisfaction -= 10
        b.satisfaction -= 10

    ev = state.add_event(type="breakup", participants=[a.id, b.id], reason=reason,
                         summary=f"{a.name}와(과) {b.name}이(가) 헤어짐 (사유: {BREAKUP_REASONS[reason]})")
    return f"💔 {a.name}와(과) {b.name}이(가) 헤어졌습니다. (사유: {BREAKUP_REASONS[reason]})"


def relation_brief(state: GameState, a: Character, b: Character) -> str:
    # 플레이어 표시용: 수치 노출 없이 카테고리 + 상태 텍스트
    rel = a.rel(b.id)
    parts = [friendship_label(rel.friendship)]
    r = romance_label(rel.romance)
    if r:
        parts.append(r)
    if rel.spark and a.slots["lover"] != b.id:
        parts.append("[반함]")
    if a.slots["best_friend"] == b.id:
        parts.append("[베프]")
    if a.slots["lover"] == b.id:
        parts.append("[연인]")
    if a.slots["enemy"] == b.id:
        parts.append("[원수]")
    if any(t.target == b.id for t in a.ex_lovers):
        parts.append("[전 연인]")
    return " ".join(parts)
