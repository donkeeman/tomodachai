"""Location system — manages all game spaces and character positions.

장소 타입:
  PRIVATE_ROOM — 캐릭터 개인 방
  SHARED_ROOM  — 공유 공간 (거실, 발코니)
  PUBLIC       — 13개 공개 장소

LocationManager가 현재 캐릭터 위치를 추적하고
조건 기반 이동 결정(choose_destination)을 담당한다.
"""

from __future__ import annotations

import random
from enum import Enum

from pydantic import BaseModel, Field

from tomodachai.character import Character

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LocationType(str, Enum):
    PRIVATE_ROOM = "private_room"
    SHARED_ROOM = "shared_room"
    PUBLIC = "public"


# ---------------------------------------------------------------------------
# Location model
# ---------------------------------------------------------------------------


class Location(BaseModel):
    id: str
    name: str
    capacity: int = 6
    location_type: LocationType = LocationType.PUBLIC
    event_types: list[str] = Field(default_factory=list)
    description: str = ""


# ---------------------------------------------------------------------------
# Default locations
# ---------------------------------------------------------------------------

# 공유 주택 공간
_HOUSE_SHARED: list[Location] = [
    Location(
        id="living_room",
        name="거실",
        capacity=10,
        location_type=LocationType.SHARED_ROOM,
        event_types=["chat", "tv", "minigame", "birthday_party"],
        description="소파 수다, TV 시청, 여러 명 모임, 미니게임",
    ),
    Location(
        id="balcony",
        name="발코니",
        capacity=3,
        location_type=LocationType.SHARED_ROOM,
        event_types=["one_on_one_chat", "confession", "night_event", "contemplation"],
        description="혼자 생각, 1:1 대화, 밤 이벤트, 고백 장소",
    ),
]

# 13개 공개 장소
_PUBLIC_LOCATIONS: list[Location] = [
    Location(
        id="grocery",
        name="식료품점",
        capacity=4,
        location_type=LocationType.PUBLIC,
        event_types=["food_shopping", "morning_market"],
        description="음식 구매",
    ),
    Location(
        id="clothing",
        name="의류점",
        capacity=3,
        location_type=LocationType.PUBLIC,
        event_types=["outfit_shopping"],
        description="의상 구매",
    ),
    Location(
        id="interior",
        name="인테리어점",
        capacity=3,
        location_type=LocationType.PUBLIC,
        event_types=["room_decoration"],
        description="방 꾸미기",
    ),
    Location(
        id="fountain",
        name="분수대",
        capacity=6,
        location_type=LocationType.PUBLIC,
        event_types=["donation", "morning_market", "rap_battle", "word_chain"],
        description="모금, 아침 장터, 랩배틀, 끝말잇기",
    ),
    Location(
        id="news_station",
        name="방송국",
        capacity=2,
        location_type=LocationType.PUBLIC,
        event_types=["news_briefing"],
        description="뉴스 브리핑",
    ),
    Location(
        id="park",
        name="공원",
        capacity=8,
        location_type=LocationType.PUBLIC,
        event_types=["walk", "bench_chat", "exercise", "picnic", "compatibility_check"],
        description="야외 상호작용, 상성 진단, 랭킹 보드",
    ),
    Location(
        id="cafe",
        name="카페",
        capacity=4,
        location_type=LocationType.PUBLIC,
        event_types=["small_group_chat", "date"],
        description="소규모 수다 (2~4명)",
    ),
    Location(
        id="beach",
        name="해변",
        capacity=5,
        location_type=LocationType.PUBLIC,
        event_types=["walk", "confession", "emotional_chat", "contemplation"],
        description="감성 장소, 고백, 산책",
    ),
    Location(
        id="plaza",
        name="광장",
        capacity=24,
        location_type=LocationType.PUBLIC,
        event_types=["large_gathering", "vote", "performance", "announcement"],
        description="대규모 모임, 투표, 공연",
    ),
    Location(
        id="concert_hall",
        name="콘서트홀",
        capacity=24,
        location_type=LocationType.PUBLIC,
        event_types=["solo_performance", "duet", "group_performance", "audience_reaction"],
        description="솔로/듀엣/그룹 공연, 관객 참석",
    ),
    Location(
        id="amusement_park",
        name="놀이공원",
        capacity=8,
        location_type=LocationType.PUBLIC,
        event_types=["minigame", "night_market", "date"],
        description="미니게임, 야시장",
    ),
    Location(
        id="city_hall",
        name="시청",
        capacity=6,
        location_type=LocationType.PUBLIC,
        event_types=["resident_list", "stats_check", "relationship_graph", "trait_map"],
        description="주민 목록, 관계도, 성격 분포도",
    ),
    Location(
        id="photo_studio",
        name="사진관",
        capacity=4,
        location_type=LocationType.PUBLIC,
        event_types=["photo_shoot", "gallery_view"],
        description="사진 촬영, 갤러리",
    ),
]

# 모든 기본 장소 (개인 방 제외 — 캐릭터 생성 시 동적 추가)
DEFAULT_LOCATIONS: list[Location] = _HOUSE_SHARED + _PUBLIC_LOCATIONS

# 이동 가중치 기본값 (공개 장소만)
_DEFAULT_PUBLIC_WEIGHTS: dict[str, float] = {
    "grocery": 1.0,
    "clothing": 0.5,
    "interior": 0.5,
    "fountain": 1.5,
    "news_station": 0.3,
    "park": 2.0,
    "cafe": 1.5,
    "beach": 1.0,
    "plaza": 1.0,
    "concert_hall": 0.8,
    "amusement_park": 1.2,
    "city_hall": 0.4,
    "photo_studio": 0.6,
    "living_room": 2.0,
    "balcony": 0.8,
}

# 야간에 집에 있을 확률
_NIGHT_HOME_PROB = 0.7
_NIGHT_SLOTS = {"밤"}

# 욕구 임계값
_HUNGER_HIGH = 70.0       # 배고픔 높으면 식료품점
_SATISFACTION_LOW = 20.0  # 만족도 낮으면 여가
_STRESS_HIGH = 7          # 스트레스 높으면 해변
_FRIENDSHIP_FOLLOW = 60.0  # 친구 따라가기 임계값


# ---------------------------------------------------------------------------
# LocationManager
# ---------------------------------------------------------------------------


class LocationManager:
    """모든 장소와 캐릭터 위치를 관리한다.

    - locations: {location_id: Location}
    - _positions: {char_id: location_id}  — 현재 캐릭터 위치 매핑
    """

    def __init__(self, extra_locations: list[Location] | None = None) -> None:
        self._locations: dict[str, Location] = {}
        self._positions: dict[int, str] = {}  # char_id → location_id

        # 기본 장소 등록
        for loc in DEFAULT_LOCATIONS:
            self._locations[loc.id] = loc

        # 추가 장소 (e.g. 캐릭터 개인 방)
        if extra_locations:
            for loc in extra_locations:
                self._locations[loc.id] = loc

    # ------------------------------------------------------------------
    # Location registry
    # ------------------------------------------------------------------

    def add_location(self, loc: Location) -> None:
        """장소를 동적으로 추가한다 (e.g. 개인 방)."""
        self._locations[loc.id] = loc

    def register_private_room(self, char_id: int, char_name: str) -> Location:
        """캐릭터 개인 방을 등록하고 반환한다."""
        room_id = f"room_{char_id}"
        room = Location(
            id=room_id,
            name=f"{char_name}의 방",
            capacity=2,
            location_type=LocationType.PRIVATE_ROOM,
            event_types=["sleep", "personal_event", "room_visit", "gift", "consultation"],
            description=f"{char_name}의 개인 방",
        )
        self._locations[room_id] = room
        return room

    def get_location(self, location_id: str) -> Location | None:
        """ID로 장소를 조회한다."""
        return self._locations.get(location_id)

    def get_location_by_name(self, name: str) -> Location | None:
        """이름으로 장소를 조회한다."""
        return next((loc for loc in self._locations.values() if loc.name == name), None)

    def all_locations(self) -> list[Location]:
        return list(self._locations.values())

    def public_locations(self) -> list[Location]:
        return [loc for loc in self._locations.values() if loc.location_type == LocationType.PUBLIC]

    def shared_locations(self) -> list[Location]:
        return [
            loc
            for loc in self._locations.values()
            if loc.location_type == LocationType.SHARED_ROOM
        ]

    # ------------------------------------------------------------------
    # Position queries
    # ------------------------------------------------------------------

    def get_characters_at(self, location_id: str) -> list[int]:
        """해당 장소에 있는 캐릭터 ID 목록을 반환한다."""
        return [cid for cid, lid in self._positions.items() if lid == location_id]

    def get_character_location(self, char_id: int) -> str | None:
        """캐릭터의 현재 장소 ID를 반환한다. 위치 없으면 None."""
        return self._positions.get(char_id)

    def is_at_capacity(self, location_id: str) -> bool:
        """해당 장소가 만원인지 확인한다."""
        loc = self._locations.get(location_id)
        if loc is None:
            return True
        return len(self.get_characters_at(location_id)) >= loc.capacity

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------

    def move_character(self, char_id: int, destination: str) -> bool:
        """캐릭터를 destination(location_id)으로 이동시킨다.

        destination이 존재하지 않으면 False 반환.
        정원 초과여도 강제 이동은 허용 (플레이어 물리적 간섭 포함).
        """
        if destination not in self._locations:
            # ID로 못 찾으면 이름으로 시도
            loc_by_name = self.get_location_by_name(destination)
            if loc_by_name is None:
                return False
            destination = loc_by_name.id

        self._positions[char_id] = destination
        return True

    def remove_character(self, char_id: int) -> None:
        """캐릭터를 위치 트래킹에서 제거한다."""
        self._positions.pop(char_id, None)

    # ------------------------------------------------------------------
    # Probabilistic destination choice
    # ------------------------------------------------------------------

    def choose_destination(
        self,
        char: Character,
        relationships: "RelationshipTracker | None" = None,  # noqa: F821
        time_of_day: str = "낮",
        rng: random.Random | None = None,
    ) -> str:
        """조건 기반 확률적 이동 목적지를 결정한다.

        Rules (우선순위 순):
          1. 밤 → 개인 방 (높은 확률)
          2. 배고픔 > 70 → 식료품점 가중치 대폭↑
          3. 만족도 < 20 → 공원/카페 가중치↑
          4. 친구(friendship > 60) → 친구 위치로 가중치↑
          5. 스트레스 > 7 → 해변 가중치↑
          6. 나머지: 기본 가중치

        Returns: location_id (str)
        """
        _rng = rng or random.Random()

        # 1. 밤이면 개인 방으로 돌아갈 확률
        private_room_id = f"room_{char.id}"
        if time_of_day in _NIGHT_SLOTS and private_room_id in self._locations:
            if _rng.random() < _NIGHT_HOME_PROB:
                return private_room_id

        # 가중치 테이블 복사
        weights: dict[str, float] = dict(_DEFAULT_PUBLIC_WEIGHTS)
        # 위치 없는 장소는 제외
        weights = {k: v for k, v in weights.items() if k in self._locations}

        # 2. 배고픔 — 식료품점 강하게 당김 (10배)
        if char.hunger > _HUNGER_HIGH:
            weights["grocery"] = weights.get("grocery", 1.0) * 10.0

        # 3. 만족도 낮음 — 여가 장소↑
        if char.satisfaction < _SATISFACTION_LOW:
            for loc_id in ("park", "cafe", "beach", "amusement_park"):
                if loc_id in weights:
                    weights[loc_id] *= 2.5

        # 4. 스트레스 — 해변↑
        if char.state.mood.stress > _STRESS_HIGH:
            if "beach" in weights:
                weights["beach"] *= 3.0
            if "balcony" in weights:
                weights["balcony"] *= 2.0

        # 5. 친구 따라가기
        if relationships is not None:
            for a_id, b_id, rel in relationships.all_pairs():
                if char.id not in (a_id, b_id):
                    continue
                friend_id = b_id if a_id == char.id else a_id
                if rel.friendship >= _FRIENDSHIP_FOLLOW:
                    friend_loc = self._positions.get(friend_id)
                    if friend_loc and friend_loc in weights:
                        weights[friend_loc] = weights.get(friend_loc, 1.0) * 3.0

        # 6. 정원 초과 장소 가중치 감소 (필수 제외는 아님)
        for loc_id in list(weights):
            if self.is_at_capacity(loc_id):
                weights[loc_id] *= 0.3

        # 가중 랜덤 선택
        ids = list(weights.keys())
        w = [weights[i] for i in ids]
        chosen = _rng.choices(ids, weights=w, k=1)[0]
        return chosen

    # ------------------------------------------------------------------
    # Snapshot — API 용도
    # ------------------------------------------------------------------

    def snapshot(self) -> list[dict]:
        """모든 장소와 현재 입장 캐릭터 목록을 dict 리스트로 반환한다."""
        result = []
        for loc in self._locations.values():
            result.append(
                {
                    "id": loc.id,
                    "name": loc.name,
                    "location_type": loc.location_type.value,
                    "capacity": loc.capacity,
                    "event_types": loc.event_types,
                    "description": loc.description,
                    "characters": self.get_characters_at(loc.id),
                }
            )
        return result
