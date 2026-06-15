"""Pydantic schemas for API request/response."""

from __future__ import annotations

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Character
# ---------------------------------------------------------------------------


class PersonalitySliders(BaseModel):
    movement: int  # 0~10
    speech: int  # 0~10
    expressiveness: int  # 0~10
    attitude: int  # 0~10
    overall: int  # 0~10


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


class StepResponse(BaseModel):
    step: int
    events: list[EventOut]


# ---------------------------------------------------------------------------
# Personalities
# ---------------------------------------------------------------------------


class PersonalityTypeOut(BaseModel):
    code: str
    name: str
    group: str
    description: str


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------


class LocationOut(BaseModel):
    id: str
    name: str
    location_type: str
    capacity: int
    event_types: list[str]
    description: str
    characters: list[int]  # 현재 해당 장소에 있는 캐릭터 ID 목록


class MoveResponse(BaseModel):
    char_id: int
    destination: str
    success: bool
    message: str


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------


class SlotInfoOut(BaseModel):
    slot: int
    exists: bool
    island_name: str = ""
    day_count: int = 0
    last_saved: str = ""


class SaveResponse(BaseModel):
    ok: bool
    slot: int
    message: str = ""


class LoadResponse(BaseModel):
    ok: bool
    slot: int | str
    island_name: str = ""
    day_count: int = 0
    characters: int = 0
    message: str = ""


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------


class NewsArticleOut(BaseModel):
    id: int
    day: int
    news_type: str  # "real" | "absurd"
    headline: str
    body: str


class NewsGenerateRequest(BaseModel):
    news_type: str = "real"


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------


class MorningMarketOut(BaseModel):
    item: int
    discount_price: int


class ShopDailyOut(BaseModel):
    food: list[int] = []
    clothing: list[int] = []
    interior: list[int] = []


class ShopOut(BaseModel):
    daily: ShopDailyOut
    morning_market: MorningMarketOut | None = None
    seasonal: list[int] = []


class BuyResponse(BaseModel):
    ok: bool
    item_id: int
    remaining_money: int
    message: str = ""


# ---------------------------------------------------------------------------
# Fountain events
# ---------------------------------------------------------------------------


class DonationOut(BaseModel):
    day: int
    character_count: int
    amount: int
    remaining_money: int


class DonationStatusOut(BaseModel):
    day: int
    donated: bool


class RapVerseOut(BaseModel):
    name: str
    line: str


class RapBattleOut(BaseModel):
    participants: list[str]
    verses: list[RapVerseOut]
    winner: str


class WordChainRoundOut(BaseModel):
    name: str
    word: str


class WordChainOut(BaseModel):
    participants: list[str]
    rounds: list[WordChainRoundOut]
    eliminated: str | None = None
    winner: str


class RapBattleRequest(BaseModel):
    char_ids: list[int]


class WordChainRequest(BaseModel):
    char_ids: list[int]
    item_pool: list[str] = []


class BuyMarketResponse(BaseModel):
    ok: bool
    item_id: int | None = None
    discount_price: int | None = None
    remaining_money: int
    message: str = ""
