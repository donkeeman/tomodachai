"""Central game state manager — single source of truth for a running game session."""

from __future__ import annotations

from tomodachai.character import Character
from tomodachai.config import AppConfig, load_config
from tomodachai.llm import LLMClient
from tomodachai.memory import MemoryStore
from tomodachai.personality import PersonalityType, load_personalities
from tomodachai.relationship import RelationshipTracker
from tomodachai.simulation import Simulation


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

    # ------------------------------------------------------------------
    # Character management
    # ------------------------------------------------------------------

    def add_character(self, char: Character) -> Character:
        if any(c.id == char.id for c in self.characters):
            raise ValueError(f"Character with id '{char.id}' already exists")
        self.characters.append(char)
        self._simulation = None  # invalidate
        return char

    def get_character(self, char_id) -> Character | None:
        return next((c for c in self.characters if c.id == char_id), None)

    def remove_character(self, char_id) -> bool:
        before = len(self.characters)
        self.characters = [c for c in self.characters if c.id != char_id]
        if len(self.characters) < before:
            self._simulation = None
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
