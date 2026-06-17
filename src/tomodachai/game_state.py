"""Central game state manager — single source of truth for a running game session."""

from __future__ import annotations

from datetime import datetime, timezone

from tomodachai.character import Character
from tomodachai.config import AppConfig, load_config
from tomodachai.fountain import FountainManager
from tomodachai.llm import LLMClient
from tomodachai.location import LocationManager
from tomodachai.memory import MemoryStore
from tomodachai.news import NewsManager
from tomodachai.personality import PersonalityType, load_personalities
from tomodachai.relationship import RelationshipTracker
from tomodachai.shop import ShopManager
from tomodachai.simulation import Simulation
from tomodachai.time_system import GameClock


class GameState:
    """Holds everything needed for one game session."""

    def __init__(
        self,
        config: AppConfig | None = None,
        island_name: str = "우리 마을",
        day_count: int = 0,
        money: int = 0,
        time_flip: bool = False,
    ):
        self.config = config or load_config()
        self.personalities: dict[str, PersonalityType] = load_personalities()
        self.characters: list[Character] = []
        self.llm = LLMClient(self.config.llm)
        self._simulation: Simulation | None = None

        # Game-level state
        self.island_name: str = island_name
        self.day_count: int = day_count
        self.money: int = money
        self.time_flip: bool = time_flip
        self.ending_credit_seen: bool = False
        # Global item acquisition catalog (persisted in game.json).
        # Keys: food, clothing, interior, treasure — values: sorted list of item IDs.
        # ShopManager reads from this; do NOT maintain a separate catalog in ShopManager.
        self.catalog: dict[str, list[int]] = {
            "food": [],
            "clothing": [],
            "interior": [],
            "treasure": [],
        }

        # Location system
        self.location_manager: LocationManager = LocationManager()

        # News system
        self.news: NewsManager = NewsManager()

        # Shop system
        self.shop: ShopManager = ShopManager()

        # Fountain events (donation / rap battle / word chain)
        self.fountain: FountainManager = FountainManager()

        # Real-time tracking
        self.last_online: datetime = datetime.now(tz=timezone.utc)
        self._clock: GameClock = GameClock(time_flip=time_flip)

        # 실시간 이벤트 로그 (snapshot since 증분 페치 기준)
        self._event_seq: int = 0
        self._event_log: list[dict] = []

        # 도구 산출물 (세션 한정 — 사진 갤러리 / 요리 카탈로그)
        self.photos: list[dict] = []
        self.dishes: list[dict] = []

    # ------------------------------------------------------------------
    # Character management
    # ------------------------------------------------------------------

    def add_character(self, char: Character) -> Character:
        if any(c.id == char.id for c in self.characters):
            raise ValueError(f"Character with id '{char.id}' already exists")
        self.characters.append(char)
        self._simulation = None  # invalidate
        # 개인 방 등록 (int ID만 지원)
        char_id = char.id if isinstance(char.id, int) else abs(hash(char.id)) % 100000
        self.location_manager.register_private_room(char_id, char.name)
        return char

    def get_character(self, char_id) -> Character | None:
        return next((c for c in self.characters if c.id == char_id), None)

    def remove_character(self, char_id) -> bool:
        before = len(self.characters)
        self.characters = [c for c in self.characters if c.id != char_id]
        if len(self.characters) < before:
            self._simulation = None
            int_id = char_id if isinstance(char_id, int) else abs(hash(char_id)) % 100000
            self.location_manager.remove_character(int_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Economy helpers
    # ------------------------------------------------------------------

    def add_money(self, amount: int) -> None:
        """Add *amount* to the player's money (amount must be positive)."""
        if amount < 0:
            raise ValueError("amount must be non-negative; use spend_money to deduct")
        self.money += amount

    def spend_money(self, amount: int) -> bool:
        """Deduct *amount* from money. Returns True on success, False if insufficient funds."""
        if amount < 0:
            raise ValueError("amount must be non-negative")
        if self.money < amount:
            return False
        self.money -= amount
        return True

    # ------------------------------------------------------------------
    # Catalog helpers (game.json §1)
    # ------------------------------------------------------------------

    _EVENT_LOG_CAP: int = 300  # 실시간 이벤트 로그 ring buffer 상한

    _CATALOG_CATEGORIES = frozenset({"food", "clothing", "interior", "treasure"})

    def add_to_catalog(self, category: str, item_id: int) -> None:
        """Record *item_id* as acquired under *category*. No-op if already present."""
        if category not in self._CATALOG_CATEGORIES:
            valid = sorted(self._CATALOG_CATEGORIES)
            raise ValueError(f"Unknown catalog category '{category}'. Must be one of: {valid}")
        if item_id not in self.catalog[category]:
            self.catalog[category].append(item_id)

    def is_in_catalog(self, category: str, item_id: int) -> bool:
        """Return True if *item_id* has been acquired in *category* before."""
        if category not in self._CATALOG_CATEGORIES:
            valid = sorted(self._CATALOG_CATEGORIES)
            raise ValueError(f"Unknown catalog category '{category}'. Must be one of: {valid}")
        return item_id in self.catalog[category]

    # ------------------------------------------------------------------
    # Simulation access
    # ------------------------------------------------------------------

    @property
    def simulation(self) -> Simulation:
        if self._simulation is None:
            self._simulation = Simulation(
                config=self.config,
                characters=self.characters,
                llm=self.llm,
                personalities=self.personalities,
            )
        return self._simulation

    @property
    def relationships(self) -> RelationshipTracker:
        return self.simulation.relationships

    @property
    def memory(self) -> MemoryStore:
        return self.simulation.memory

    @property
    def bubbles(self) -> list:
        """플레이어 응답 대기 말풍선 큐 (시뮬 소유)."""
        return self.simulation.bubbles

    # ------------------------------------------------------------------
    # Real-time interface
    # ------------------------------------------------------------------

    def _clock_str(self) -> str:
        now = self._clock.now()
        hour = self._clock.get_game_hour(now)
        return f"{hour:02d}:{now.minute:02d}"

    def record_events(self, raw_events: list[dict]) -> None:
        """raw 이벤트들에 단조 seq + 기록 시점 day/clock을 붙여 로그에 적재."""
        clock = self._clock_str()
        for raw in raw_events:
            self._event_seq += 1
            self._event_log.append(
                {"seq": self._event_seq, "day": self.day_count, "clock": clock, "raw": raw}
            )
        if len(self._event_log) > self._EVENT_LOG_CAP:
            self._event_log = self._event_log[-self._EVENT_LOG_CAP :]

    def events_since(self, since: int) -> list[dict]:
        """seq > since 인 로그 항목만 (시간순)."""
        return [e for e in self._event_log if e["seq"] > since]

    def clear_hungry_bubble(self, char_id) -> None:
        """해당 캐릭터의 배고픔 말풍선 제거 (feed 시 호출)."""
        self.bubbles[:] = [
            b for b in self.bubbles if not (b.kind == "hungry" and b.char_id == char_id)
        ]

    def answer_bubble(self, index: int, char_name: str, allow: bool) -> dict:
        """프론트 말풍선 응답 처리.

        반환: {"error": ...} | {"message": ...} | {"scene": ..., "messages": [...]}.
        """
        bubbles = self.bubbles
        if not (0 <= index < len(bubbles)):
            return {"error": "이미 처리된 말풍선입니다"}
        bubble = bubbles[index]
        owner = self.get_character(bubble.char_id)
        if owner is None or owner.name != char_name:
            return {"error": "말풍선이 갱신되었습니다. 다시 시도해 주세요"}
        if bubble.kind == "hungry":
            return {"error": "배고픔 말풍선은 밥을 주면 사라져요"}
        bubbles.pop(index)
        if bubble.kind != "confess_request":
            return {"message": "말풍선을 확인했습니다"}
        result = self.simulation.resolve_confession(bubble, approved=allow)
        self.record_events([result])
        return {"scene": result["summary"], "messages": []}

    def reset_world(self) -> None:
        """새 마을 시작: 캐릭터/시뮬/이벤트로그/seq 초기화 (config는 유지)."""
        self.characters.clear()
        self._simulation = None
        self._event_seq = 0
        self._event_log = []
        self.day_count = 0
        self.photos = []
        self.dishes = []

    def step(self) -> list[dict]:
        """실시간 단일 이벤트 스텝. 서버 백그라운드 태스크에서 호출."""
        if not self.characters:
            return []
        self.touch()
        events = self.simulation.step()
        self.record_events(events)
        return events

    def touch(self) -> None:
        """접속 시각 갱신 (플레이어가 온라인임을 표시)."""
        self.last_online = datetime.now(tz=timezone.utc)

    def connect(self) -> dict:
        """재접속 처리: 오프라인 기간 계산 후 catch-up 이벤트 생성.

        Returns:
            {
                "offline_hours": float,
                "catchup_events": list[dict],
                "time_period": str,
                "is_new_day": bool,
            }
        """
        now_utc = datetime.now(tz=timezone.utc)
        clock = self._clock

        offline_duration = clock.calculate_offline_duration(self.last_online)
        offline_hours = offline_duration.total_seconds() / 3600.0
        is_new_day = clock.is_new_day(self.last_online)

        catchup_events: list[dict] = []
        if offline_hours >= 5.0 / 60.0 and self.characters:  # 최소 5분 이상
            catchup_events = self.simulation.generate_catchup_events(offline_hours)
            if is_new_day:
                self.day_count += 1

        # 일일 리셋 처리 (상점 등 — 현재는 day_count만)
        self.last_online = now_utc

        return {
            "offline_hours": round(offline_hours, 2),
            "catchup_events": catchup_events,
            "time_period": clock.get_time_period(),
            "is_new_day": is_new_day,
        }

    @property
    def current_time_period(self) -> str:
        return self._clock.get_time_period()

    @property
    def current_game_hour(self) -> int:
        return self._clock.get_game_hour()
