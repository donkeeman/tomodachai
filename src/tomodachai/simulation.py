from __future__ import annotations

import random
from itertools import combinations

from tomodachai.character import Character
from tomodachai.config import AppConfig, LocationConfig
from tomodachai.conversation import ConversationEngine, ConversationResult
from tomodachai.llm import LLMClient
from tomodachai.memory import MemoryStore, SocialEvent
from tomodachai.personality import PersonalityType
from tomodachai.relationship import RelationshipTracker, detect_triangles, apply_jealousy

_TIME_SLOTS = ["아침", "오전", "점심", "오후", "저녁", "밤"]


def assign_locations(
    characters: list[Character],
    locations: list[LocationConfig],
    seed: int | None = None,
) -> dict[str, list[Character]]:
    rng = random.Random(seed)
    assignments: dict[str, list[Character]] = {loc.name: [] for loc in locations}
    capacity_map = {loc.name: loc.capacity for loc in locations}

    shuffled = list(characters)
    rng.shuffle(shuffled)

    available = [loc.name for loc in locations]
    for char in shuffled:
        rng.shuffle(available)
        for loc_name in available:
            if len(assignments[loc_name]) < capacity_map[loc_name]:
                assignments[loc_name].append(char)
                break

    return assignments


class Simulation:
    def __init__(
        self,
        config: AppConfig,
        characters: list[Character],
        llm: LLMClient,
        personalities: dict[str, PersonalityType],
    ):
        self.config = config
        self.characters = characters
        self.conversation_engine = ConversationEngine(llm, personalities)
        self.relationships = RelationshipTracker()
        self.memory = MemoryStore()
        self._tick_count = 0

    def tick(self, seed: int | None = None) -> list[ConversationResult]:
        time_of_day = _TIME_SLOTS[self._tick_count % len(_TIME_SLOTS)]
        assignments = assign_locations(
            self.characters, self.config.locations, seed=seed,
        )

        results = []
        for loc_name, chars in assignments.items():
            for char_a, char_b in combinations(chars, 2):
                result = self._run_conversation(char_a, char_b, loc_name, time_of_day)
                results.append(result)

        # Process multi-party dynamics
        triangles = detect_triangles(self.relationships)
        if triangles:
            apply_jealousy(self.relationships, triangles)

        self._tick_count += 1
        return results

    def _run_conversation(
        self,
        char_a: Character,
        char_b: Character,
        location: str,
        time_of_day: str,
    ) -> ConversationResult:
        rel_ab = self.relationships.get(char_a.id, char_b.id)
        rel_ba = self.relationships.get(char_b.id, char_a.id)
        memories = self.memory.get_events_between(char_a.id, char_b.id)

        result = self.conversation_engine.generate(
            char_a=char_a,
            char_b=char_b,
            rel_ab=rel_ab,
            rel_ba=rel_ba,
            memories=memories,
            location=location,
            time_of_day=time_of_day,
        )

        for name, deltas in result.deltas.items():
            if name == char_a.name:
                self.relationships.update(char_a.id, char_b.id, deltas)
            elif name == char_b.name:
                self.relationships.update(char_b.id, char_a.id, deltas)

        self.memory.add_event(SocialEvent(
            tick=self._tick_count,
            participants=[char_a.id, char_b.id],
            event_type="conversation",
            summary=result.summary,
            emotional_impact={
                char_a.id: sum(result.deltas.get(char_a.name, {}).values()),
                char_b.id: sum(result.deltas.get(char_b.name, {}).values()),
            },
        ))

        return result

    def _force_encounter(
        self, char_a: Character, char_b: Character, location: str,
    ) -> ConversationResult:
        return self._run_conversation(char_a, char_b, location, "오후")

    def run(self, num_ticks: int, seed: int | None = None) -> None:
        for i in range(num_ticks):
            tick_seed = seed + i if seed is not None else None
            results = self.tick(seed=tick_seed)
            self._print_tick(i, results)

    def _print_tick(self, tick_num: int, results: list[ConversationResult]) -> None:
        time_of_day = _TIME_SLOTS[tick_num % len(_TIME_SLOTS)]
        print(f"\n{'='*60}")
        print(f"  틱 {tick_num} | {time_of_day}")
        print(f"{'='*60}")

        if not results:
            print("  (아무 일도 일어나지 않았다)")
            return

        for result in results:
            print(f"\n  📍 {result.summary}")
            print(f"  {'-'*40}")
            for line in result.dialogue:
                print(f"  {line.speaker}: {line.text}")
            for name, deltas in result.deltas.items():
                parts = [f"{k}:{v:+.0f}" for k, v in deltas.items() if v != 0]
                if parts:
                    print(f"  [{name}] {', '.join(parts)}")
