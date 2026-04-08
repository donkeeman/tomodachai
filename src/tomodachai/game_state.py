"""Central game state manager — single source of truth for a running game session."""

from __future__ import annotations

from datetime import datetime, timezone

from tomodachai.character import Character
from tomodachai.config import AppConfig, load_config
from tomodachai.llm import LLMClient
from tomodachai.location import LocationManager
from tomodachai.memory import MemoryStore
from tomodachai.personality import PersonalityType, load_personalities
from tomodachai.relationship import RelationshipTracker
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

        # Location system
        self.location_manager: LocationManager = LocationManager()

        # Real-time tracking
        self.last_online: datetime = datetime.now(tz=timezone.utc)
        self._clock: GameClock = GameClock(time_flip=time_flip)

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

    def tick(self, seed: int | None = None) -> list[dict]:
        if not self.characters:
            return []
        result = self.simulation.tick(seed=seed)
        self.day_count += 1
        return result

    # ------------------------------------------------------------------
    # Real-time interface
    # ------------------------------------------------------------------

    def step(self) -> list[dict]:
        """실시간 단일 이벤트 스텝. 서버 백그라운드 태스크에서 호출."""
        if not self.characters:
            return []
        self.touch()
        return self.simulation.step()

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
