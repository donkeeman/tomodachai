from __future__ import annotations

from pydantic import BaseModel, model_validator


def calculate_zodiac(birthday: str) -> str:
    """생일 문자열("MM-DD")을 받아 한국어 별자리 이름을 반환한다."""
    if not birthday:
        return ""
    try:
        month, day = int(birthday[:2]), int(birthday[3:5])
    except (ValueError, IndexError):
        return ""

    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "양자리"
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "황소자리"
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return "쌍둥이자리"
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return "게자리"
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "사자자리"
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "처녀자리"
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return "천칭자리"
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return "전갈자리"
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return "사수자리"
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return "염소자리"
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "물병자리"
    elif (month == 2 and day >= 19) or (month == 3 and day <= 20):
        return "물고기자리"
    return ""


class Character(BaseModel):
    id: str
    name: str
    personality_code: str
    backstory: str = ""

    # 프로필
    birthday: str = ""          # "MM-DD"
    zodiac: str = ""            # 별자리 (birthday에서 자동 계산)
    blood_type: str = ""        # "A" / "B" / "O" / "AB"
    favorite_color: str = ""    # 좋아하는 색 (기본 복장 색상)
    gender: str = ""            # 자유 텍스트, 제한 없음

    # 말버릇 (감정별 5종류)
    speech_habits: dict[str, str] = {}   # "normal"/"happy"/"angry"/"sad"/"worried"

    # 상태 수치
    satisfaction: float = 50.0  # 만족도/행복도 0~100
    hunger: float = 0.0         # 배고픔 0~100, 시간 경과로 증가

    # 선호도
    food_preferences: dict[str, str] = {}      # item_id → "최애"/"좋아함"/"보통"/"싫어함"/"최악"
    clothing_preferences: dict[str, str] = {}  # 의류 스타일 선호도

    # 관계
    nicknames: dict[str, str] = {}  # char_id → 이 캐릭터를 부르는 별명

    # 미니 개성
    mini_personality: list[str] = []  # 걷는 방식·먹는 방식·습관 등 미세 행동 특성

    @model_validator(mode="before")
    @classmethod
    def _migrate_and_compute(cls, data: dict) -> dict:
        # 하위 호환: 구버전 speech_habit(str) → speech_habits["normal"]로 마이그레이션
        if isinstance(data, dict):
            old_habit = data.pop("speech_habit", None)
            if old_habit and not data.get("speech_habits"):
                data["speech_habits"] = {"normal": old_habit}

        # birthday가 있고 zodiac이 비어 있으면 자동 계산
        birthday = data.get("birthday", "") if isinstance(data, dict) else ""
        zodiac = data.get("zodiac", "") if isinstance(data, dict) else ""
        if birthday and not zodiac:
            data["zodiac"] = calculate_zodiac(birthday)

        return data
