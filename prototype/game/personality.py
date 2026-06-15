# 16가지 성격 시스템 (01-character.md)
# Movement+Speech 합산 → 4계통, Expressiveness+Attitude 합산 → 4형 (균등 분할)
from __future__ import annotations

from typing import Tuple

from .models import Character

# 계통 순서는 잠정 (합산 낮음 → 높음). 구현 실험으로 조정 가능
GROUPS = ["안정파", "신중파", "사교파", "주도파"]

TYPES = {
    "안정파": ["외유내강형", "다정다감형", "우유부단형", "순진무구형"],
    "사교파": ["좌충우돌형", "시끌벅적형", "재기발랄형", "명랑쾌활형"],
    "주도파": ["시원시원형", "속전속결형", "유아독존형", "거두절미형"],
    "신중파": ["완전무결형", "유비무환형", "우물쭈물형", "묵묵부답형"],
}

# LLM 프롬프트용 성격 묘사
TYPE_HINTS = {
    "외유내강형": "겉은 부드럽지만 심지가 굳음. 조용히 자기 페이스 유지",
    "다정다감형": "따뜻하고 배려심 많음. 상대 기분을 먼저 살핌",
    "우유부단형": "결정을 잘 못 내리고 이리저리 흔들림",
    "순진무구형": "순수하고 잘 속음. 모든 걸 좋게 해석",
    "좌충우돌형": "energetic하고 사고뭉치. 일단 저지르고 봄",
    "시끌벅적형": "목소리 크고 분위기 메이커. 조용한 걸 못 참음",
    "재기발랄형": "재치있고 장난기 많음. 농담을 즐김",
    "명랑쾌활형": "밝고 긍정적. 웃음이 많음",
    "시원시원형": "화통하고 결단력 있음. 뒤끝 없음",
    "속전속결형": "성격 급하고 즉시 행동. 기다리는 걸 싫어함",
    "유아독존형": "자기중심적이고 자신감 넘침. 칭찬받는 걸 좋아함",
    "거두절미형": "말이 짧고 핵심만 말함. 돌려 말하지 않음",
    "완전무결형": "꼼꼼하고 완벽주의. 실수를 싫어함",
    "유비무환형": "걱정 많고 항상 대비함. 신중하게 행동",
    "우물쭈물형": "소심하고 망설임 많음. 먼저 말 걸기 어려워함",
    "묵묵부답형": "과묵하고 속을 알 수 없음. 짧게 대답",
}

# 계통별 기본 대기 모션 (미니 개성 미설정 시)
GROUP_IDLE = {
    "안정파": "반듯하게 서 있기",
    "사교파": "까불까불",
    "주도파": "한쪽 발 기대기",
    "신중파": "팔짱",
}


def classify(char: Character) -> Tuple[str, str]:
    # 합산 0~16을 4구간 균등 분할
    group_sum = char.movement + char.speech
    form_sum = char.expressiveness + char.attitude
    group = GROUPS[min(group_sum // 5, 3)] if group_sum < 16 else GROUPS[3]
    forms = TYPES[group]
    form = forms[min(form_sum // 5, 3)] if form_sum < 16 else forms[3]
    return group, form


def personality_label(char: Character) -> str:
    group, form = classify(char)
    return f"{group} {form}"


def intensity_hints(char: Character) -> str:
    # 슬라이더 세부 값 → 행동/말투 강도 정보 (유형이 같아도 수치로 차이)
    hints = []
    hints.append("행동이 빠릿빠릿함" if char.movement >= 6 else
                 "행동이 느긋함" if char.movement <= 2 else "행동 속도는 보통")
    hints.append("말투가 직설적임" if char.speech >= 6 else
                 "말투가 유순함" if char.speech <= 2 else "말투는 보통")
    hints.append("감정 표현이 풍부함" if char.expressiveness >= 6 else
                 "감정을 잘 드러내지 않음" if char.expressiveness <= 2 else "감정 표현은 보통")
    hints.append("태도가 여유로움" if char.attitude >= 6 else
                 "태도가 진지함" if char.attitude <= 2 else "")
    return ", ".join(h for h in hints if h)


def weirdness_hint(char: Character) -> str:
    # Overall 슬라이더: 병맛 톤 강도 (특이 ↔ 평범)
    if char.overall <= 2:
        return "가끔 맥락 없이 엉뚱하고 기이한 소리를 함"
    if char.overall >= 6:
        return "지극히 평범하고 상식적인 범위에서 말함"
    return "대체로 평범하지만 가끔 엉뚱한 구석이 있음"


def idle_trait(char: Character) -> str:
    if char.mini_traits.get("idle"):
        return char.mini_traits["idle"]
    group, _ = classify(char)
    return GROUP_IDLE[group]
