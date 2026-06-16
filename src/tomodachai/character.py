from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


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


# ---------------------------------------------------------------------------
# Appearance sub-models
# ---------------------------------------------------------------------------

class AppearanceAdjust(BaseModel):
    """파츠별 미세 조절 파라미터."""
    spacing: int = 0
    height: int = 0
    size: int = 0
    angle: int = 0


class Eye(BaseModel):
    base: int = 1
    lash: int = 0
    color: str = "#000000"
    adjust: AppearanceAdjust = Field(default_factory=AppearanceAdjust)


class Eyebrow(BaseModel):
    id: int = 1
    adjust: AppearanceAdjust = Field(default_factory=AppearanceAdjust)


class Nose(BaseModel):
    id: int = 1
    adjust: AppearanceAdjust = Field(default_factory=AppearanceAdjust)


class Mouth(BaseModel):
    id: int = 1
    adjust: AppearanceAdjust = Field(default_factory=AppearanceAdjust)


class Hair(BaseModel):
    front: int = 1
    back: int = 1
    color: str = "#000000"


class Body(BaseModel):
    height: int = 5   # 0~10
    build: int = 5    # 0~10


class Appearance(BaseModel):
    face_shape: int = 1
    skin_color: str = "#F5D6B8"
    eye: Eye = Field(default_factory=Eye)
    eyebrow: Eyebrow = Field(default_factory=Eyebrow)
    nose: Nose = Field(default_factory=Nose)
    mouth: Mouth = Field(default_factory=Mouth)
    hair: Hair = Field(default_factory=Hair)
    glasses: int | None = None
    body: Body = Field(default_factory=Body)


# ---------------------------------------------------------------------------
# Personality & Voice sub-models
# ---------------------------------------------------------------------------

class Personality(BaseModel):
    """성격 슬라이더 5종 (0~10 int).

    movement + speech → 4계통 결정
    expressiveness + attitude → 4형 결정
    overall → 유형 판정 무관, 병맛 톤 강도에만 영향
    """
    movement: int = 5       # 느림(0) ↔ 빠름(10)
    speech: int = 5         # 유순(0) ↔ 직설(10)
    expressiveness: int = 5  # 냉정(0) ↔ 감정적(10)
    attitude: int = 5       # 진지(0) ↔ 여유(10)
    overall: int = 5        # 특이(0) ↔ 평범(10)


class Voice(BaseModel):
    preset: str = "default"
    pitch: int = 5
    speed: int = 5
    quality: str | None = None
    tone: str | None = None
    accent: str | None = None
    intonation: str | None = None


# ---------------------------------------------------------------------------
# Profile sub-model
# ---------------------------------------------------------------------------

class Profile(BaseModel):
    name: str
    birthday: str = ""           # "MM-DD"
    blood_type: str = ""         # "A" / "B" / "O" / "AB"
    favorite_color: str = ""     # 좋아하는 색 (기본 복장 색상)
    gender: str = ""             # 자유 텍스트, 수정 불가
    appearance: Appearance = Field(default_factory=Appearance)
    personality: Personality = Field(default_factory=Personality)
    voice: Voice = Field(default_factory=Voice)

    @property
    def zodiac(self) -> str:
        """birthday에서 런타임 계산 — 저장하지 않음."""
        return calculate_zodiac(self.birthday)


# ---------------------------------------------------------------------------
# Preferences sub-models
# ---------------------------------------------------------------------------

class ClothingPreference(BaseModel):
    likes: str = ""
    dislikes: str = ""


class InteriorPreference(BaseModel):
    likes: str = ""
    dislikes: str = ""


class PersonalityGroup(BaseModel):
    """생성 시 랜덤 배정된 선호/비선호 성격 계통."""
    group: str = ""          # 계통 이름 e.g. "steady", "outgoing"
    is_positive: bool = True  # True → 선호, False → 비선호


class Preferences(BaseModel):
    food_ranks: list[int] = Field(default_factory=list)
    """인덱스 = 음식 ID, 값 = 순위. 생성 시 확정, 불변."""

    food_eaten: list[bool] = Field(default_factory=list)
    """인덱스 = 음식 ID, 값 = 이 캐릭터에게 먹여봤는지."""

    clothing: ClothingPreference = Field(default_factory=ClothingPreference)
    interior: InteriorPreference = Field(default_factory=InteriorPreference)
    personality_group: PersonalityGroup = Field(default_factory=PersonalityGroup)


# ---------------------------------------------------------------------------
# State sub-models
# ---------------------------------------------------------------------------

class Mood(BaseModel):
    """단기 감정 상태 3축 (0~10 int)."""
    happiness: int = 5   # ↑ 좋아하는 음식/친구 대화, ↓ 싫어하는 음식/싸움
    energy: int = 5      # ↑ 대화/활동, ↓ 배고픔/거절
    stress: int = 2      # ↑ 싸움/배고픔/거절, ↓ 친구 대화/시간 경과

    def label(self) -> str:
        """3축 조합을 한 단어 한글 감정으로 (prototype/game Mood.label 규칙)."""
        if self.stress >= 7:
            return "짜증남" if self.energy >= 5 else "지침"
        if self.happiness >= 7:
            return "신남" if self.energy >= 6 else "흐뭇함"
        if self.happiness <= 3:
            return "우울함" if self.energy <= 4 else "심술남"
        if self.energy <= 3:
            return "나른함"
        return "평온함"

    def adjust(self, happiness: float = 0, energy: float = 0, stress: float = 0) -> None:
        """3축을 델타만큼 조정하고 0~10으로 클램프 (int 저장, round)."""

        def _clamp(v: float) -> int:
            return max(0, min(10, round(v)))

        self.happiness = _clamp(self.happiness + happiness)
        self.energy = _clamp(self.energy + energy)
        self.stress = _clamp(self.stress + stress)


class CharacterState(BaseModel):
    satisfaction: float = 50.0   # 장기 레벨업 경험치, 마이너스 가능 → 절망
    level: int = 1
    hunger: float = 0.0          # 0~100, 시간 경과로 증가
    mood: Mood = Field(default_factory=Mood)
    sick: str | None = None      # None / "cold" / "stomachache"
    current_location: str = ""
    current_outfit: int | None = None
    current_interior: int | None = None
    photo_frame: int | None = None


# ---------------------------------------------------------------------------
# Customizable sub-models
# ---------------------------------------------------------------------------

class SpeechHabits(BaseModel):
    """감정별 말버릇 5종."""
    normal: str = ""
    happy: str = ""
    angry: str = ""
    sad: str = ""
    worried: str = ""

    def as_dict(self) -> dict[str, str]:
        return {k: v for k, v in self.model_dump().items() if v}


class MiniTrait(BaseModel):
    """카테고리별 미니 개성 (보유 풀 + 활성 1개)."""
    owned: list[int] = Field(default_factory=list)
    active: int | None = None    # None → 성격 기본값 사용


class MiniTraits(BaseModel):
    walking: MiniTrait = Field(default_factory=MiniTrait)
    eating: MiniTrait = Field(default_factory=MiniTrait)
    idle: MiniTrait = Field(default_factory=MiniTrait)


class Customizable(BaseModel):
    speech_habits: SpeechHabits = Field(default_factory=SpeechHabits)
    mini_traits: MiniTraits = Field(default_factory=MiniTraits)
    nicknames: dict[str, str] = Field(default_factory=dict)
    """char_id(str) → 이 캐릭터가 상대에게 부르는 별명."""
    songs: list[bool] = Field(default_factory=lambda: [False] * 8)
    """길이 8. 장르 순서: 트로트/아이돌/발라드/락/랩/뮤지컬·오페라/동요/찬송가."""


# ---------------------------------------------------------------------------
# Records sub-model
# ---------------------------------------------------------------------------

class Records(BaseModel):
    treasure_collection: list[int] = Field(default_factory=list)
    confession_count: dict[str, int] = Field(default_factory=dict)
    """char_id(str) → 고백 횟수."""
    photos: list[int] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Character (top-level)
# ---------------------------------------------------------------------------

class Character(BaseModel):
    """캐릭터 모델. 신규 중첩 구조 + 구버전 플랫 구조 하위 호환.

    JSON 저장 형식은 char_{id}.json 스키마를 따른다.
    id는 int 권장 (신버전), str도 허용 (구버전 하위 호환).
    """
    id: int | str

    # 주요 섹션 (JSON 저장 구조와 일치)
    profile: Profile
    preferences: Preferences = Field(default_factory=Preferences)
    state: CharacterState = Field(default_factory=CharacterState)
    customizable: Customizable = Field(default_factory=Customizable)
    records: Records = Field(default_factory=Records)

    # 구버전 하위 호환 필드 (flat 구조 접근용)
    food_preferences: dict[str, str] = Field(default_factory=dict)
    """구버전: item_id → 선호 등급("최애"/"좋아함"/"보통"/"싫어함"/"최악")."""
    clothing_preferences: dict[str, str] = Field(default_factory=dict)
    """구버전: 의류 스타일 선호도."""
    mini_personality: list[str] = Field(default_factory=list)
    """구버전: 미세 행동 특성 텍스트 목록."""

    @model_validator(mode="before")
    @classmethod
    def _migrate(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data

        # ── 구버전 플랫 구조 → 신버전 중첩 구조 마이그레이션 ──────────────

        # profile이 없으면 플랫 필드를 묶어 profile 생성
        if "profile" not in data:
            profile_fields = {
                "name": data.pop("name", ""),
                "birthday": data.pop("birthday", ""),
                "blood_type": data.pop("blood_type", ""),
                "favorite_color": data.pop("favorite_color", ""),
                "gender": data.pop("gender", ""),
            }
            # personality 슬라이더도 profile 하위로 이동
            if "personality" in data:
                profile_fields["personality"] = data.pop("personality")
            # zodiac은 저장하지 않음 — birthday에서 런타임 계산
            data.pop("zodiac", None)
            data["profile"] = profile_fields

        # 구버전 speech_habits / speech_habit → customizable.speech_habits 마이그레이션
        if "customizable" not in data:
            old_habits = data.pop("speech_habits", None)
            old_habit_single = data.pop("speech_habit", None)

            if old_habits and isinstance(old_habits, dict):
                data["customizable"] = {"speech_habits": old_habits}
            elif old_habit_single and isinstance(old_habit_single, str):
                data["customizable"] = {"speech_habits": {"normal": old_habit_single}}

        # 구버전 satisfaction / hunger / mood → state 마이그레이션
        if "state" not in data:
            state_fields: dict = {}
            for field in ("satisfaction", "hunger", "sick"):
                if field in data:
                    state_fields[field] = data.pop(field)
            if "mood" in data:
                state_fields["mood"] = data.pop("mood")
            if state_fields:
                data["state"] = state_fields

        # 구버전 필드 제거 (소비만 함, 저장하지 않음)
        data.pop("backstory", None)
        data.pop("personality_code", None)  # 런타임 계산으로 전환

        # 구버전 food_preferences / clothing_preferences → 최상위 필드로 유지
        # (preferences.food_ranks와 별개 구조이므로 별도 보존)
        # 구버전 nicknames → customizable.nicknames 이동 (최상위에서 제거)
        old_nicknames = data.pop("nicknames", None)
        if old_nicknames and "customizable" not in data:
            data["customizable"] = {"nicknames": old_nicknames}
        elif old_nicknames and isinstance(data.get("customizable"), dict):
            data["customizable"].setdefault("nicknames", old_nicknames)

        # preferences 섹션 없을 때 신버전 필드 마이그레이션
        if "preferences" not in data:
            pref_fields: dict = {}
            for field in ("food_ranks", "food_eaten", "clothing", "interior", "personality_group"):
                if field in data:
                    pref_fields[field] = data.pop(field)
            if pref_fields:
                data["preferences"] = pref_fields

        return data

    # ------------------------------------------------------------------
    # Computed properties — runtime only, not stored
    # ------------------------------------------------------------------

    @property
    def personality_code(self) -> str:
        """성격 슬라이더에서 런타임으로 계산 — 저장하지 않음."""
        from tomodachai.personality import PersonalitySliders, determine_personality
        p = self.profile.personality
        sliders = PersonalitySliders(
            movement=p.movement / 10.0,
            speech=p.speech / 10.0,
            expressiveness=p.expressiveness / 10.0,
            attitude=p.attitude / 10.0,
        )
        return determine_personality(sliders)

    # ------------------------------------------------------------------
    # Backward-compat properties — simulation.py / conversation.py 호환
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self.profile.name

    @property
    def birthday(self) -> str:
        return self.profile.birthday

    @property
    def zodiac(self) -> str:
        return self.profile.zodiac

    @property
    def blood_type(self) -> str:
        return self.profile.blood_type

    @property
    def gender(self) -> str:
        return self.profile.gender

    @property
    def favorite_color(self) -> str:
        return self.profile.favorite_color

    @property
    def speech_habits(self) -> dict[str, str]:
        """conversation.py 호환: 말버릇을 dict[str, str]로 반환."""
        return self.customizable.speech_habits.as_dict()

    @property
    def nicknames(self) -> dict[str, str]:
        """구버전 호환: customizable.nicknames 위임."""
        return self.customizable.nicknames

    @property
    def backstory(self) -> str:
        """conversation.py 호환: backstory 필드 제거됨, 빈 문자열 반환."""
        return ""

    # satisfaction / hunger — simulation.py가 직접 대입하므로 setter 필요
    @property
    def satisfaction(self) -> float:
        return self.state.satisfaction

    @satisfaction.setter
    def satisfaction(self, value: float) -> None:
        self.state.satisfaction = value

    @property
    def hunger(self) -> float:
        return self.state.hunger

    @hunger.setter
    def hunger(self, value: float) -> None:
        self.state.hunger = value
