"""Pydantic schemas for API request/response."""

from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Character
# ---------------------------------------------------------------------------

class PersonalitySliders(BaseModel):
    movement: int       # 0~10
    speech: int         # 0~10
    expressiveness: int # 0~10
    attitude: int       # 0~10
    overall: int        # 0~10


class CharacterCreate(BaseModel):
    """캐릭터 생성 요청 스키마.

    플랫 구조(구버전 호환)와 중첩 구조(신버전) 모두 수용.
    id는 int 또는 str("char_1" 등) 허용.
    """
    id: int | str
    name: str
    personality_code: str = ""
    birthday: str = ""
    zodiac: str = ""
    blood_type: str = ""
    favorite_color: str = ""
    gender: str = ""
    # 성격 슬라이더 (optional — 미입력 시 기본값 사용)
    personality: PersonalitySliders | None = None
    # 구버전 플랫 말버릇
    speech_habits: dict[str, str] = {}
    # 구버전 하위 호환 필드 (소비만 함)
    backstory: str = ""


# --- Sub-schemas for CharacterOut ---

class PreferencesOut(BaseModel):
    food_ranks: list[int]
    clothing: dict[str, str]
    interior: dict[str, str]


class MoodOut(BaseModel):
    happiness: int
    energy: int
    stress: int


class StateOut(BaseModel):
    satisfaction: float
    level: int
    hunger: float
    mood: MoodOut
    sick: str | None
    current_location: str


class MiniTraitEntry(BaseModel):
    owned: list[int]
    active: int | None


class CustomizableOut(BaseModel):
    speech_habits: dict[str, str]
    mini_traits: dict[str, MiniTraitEntry]
    nicknames: dict[str, str]


class RecordsOut(BaseModel):
    treasure_collection: list[int]
    confession_count: dict[str, int]
    photos: list[int]


class CharacterOut(BaseModel):
    id: int
    # profile
    name: str
    birthday: str
    zodiac: str = ""
    blood_type: str
    favorite_color: str
    gender: str
    personality_code: str = ""
    personality: PersonalitySliders
    # nested sections
    preferences: PreferencesOut
    state: StateOut
    customizable: CustomizableOut
    records: RecordsOut


# ---------------------------------------------------------------------------
# Relationship
# ---------------------------------------------------------------------------

class RelationshipOut(BaseModel):
    char_a: int
    char_b: int
    friendship: float
    romance: float
    stage: str
    status_text: str


# ---------------------------------------------------------------------------
# Game status
# ---------------------------------------------------------------------------

class GameStatusOut(BaseModel):
    island_name: str
    day_count: int
    money: int
    time_flip: bool
    characters: int
    locations: list[str]


# Keep old StatusResponse as an alias for backward compatibility
class StatusResponse(BaseModel):
    status: str
    characters: int
    tick: int
    locations: list[str]


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

class TickRequest(BaseModel):
    seed: int | None = None


class EventOut(BaseModel):
    id: int | None = None
    type: str
    participants: list[int]
    location: str | None = None
    day: int | None = None
    time: str | None = None
    reason: str | None = None
    result: str | None = None
    dialogue: list[dict] | None = None
    deltas: dict[str, dict[str, float]] | None = None


class TickResponse(BaseModel):
    tick: int
    events: list[EventOut]


# ---------------------------------------------------------------------------
# Personalities
# ---------------------------------------------------------------------------

class PersonalityTypeOut(BaseModel):
    code: str
    name: str
    family: str
    description: str
