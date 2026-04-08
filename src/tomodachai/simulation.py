from __future__ import annotations

import random
from itertools import combinations

from tomodachai.character import Character
from tomodachai.config import AppConfig, LocationConfig
from tomodachai.conversation import ConversationEngine, ConversationResult
from tomodachai.llm import LLMClient
from tomodachai.memory import MemoryStore, SocialEvent
from tomodachai.personality import PersonalityType
from tomodachai.relationship import (
    Fight,
    RelationshipEvent,
    RelationshipStage,
    RelationshipTracker,
    apply_jealousy,
    detect_triangles,
)

_TIME_SLOTS = ["아침", "오전", "점심", "오후", "저녁", "밤"]

# Thresholds for auto-triggered events
_FIGHT_FRIENDSHIP_THRESHOLD = -30.0  # friendship below this can trigger fight
_FIGHT_CHANCE = 0.3
_CONFESSION_ROMANCE_THRESHOLD = 60.0
_CONFESSION_CHANCE = 0.2
_HUNGER_PER_TICK = 5.0
_SATISFACTION_DECAY = 1.0


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
        self._char_map = {c.id: c for c in characters}
        self._rng = random.Random()

    def tick(self, seed: int | None = None) -> list[dict]:
        """Run one simulation tick. Returns a list of event dicts."""
        if seed is not None:
            self._rng = random.Random(seed)

        time_of_day = _TIME_SLOTS[self._tick_count % len(_TIME_SLOTS)]
        assignments = assign_locations(
            self.characters, self.config.locations, seed=seed,
        )

        events: list[dict] = []

        # 1. Conversations
        for loc_name, chars in assignments.items():
            for char_a, char_b in combinations(chars, 2):
                result = self._run_conversation(char_a, char_b, loc_name, time_of_day)
                events.append({
                    "type": "conversation",
                    "location": loc_name,
                    "participants": [char_a.name, char_b.name],
                    "result": result,
                })

        # 2. Check for triggered events (fights, confessions)
        triggered = self._check_triggered_events()
        events.extend(triggered)

        # 3. Update relationship stages
        self._check_stage_transitions()

        # 4. Process multi-party dynamics
        triangles = detect_triangles(self.relationships)
        if triangles:
            apply_jealousy(self.relationships, triangles)

        # 5. Update needs (hunger, satisfaction)
        self._update_needs()

        self._tick_count += 1
        return events

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
            participants=[str(char_a.id), str(char_b.id)],
            event_type="conversation",
            summary=result.summary,
            emotional_impact={
                str(char_a.id): sum(result.deltas.get(char_a.name, {}).values()),
                str(char_b.id): sum(result.deltas.get(char_b.name, {}).values()),
            },
        ))

        return result

    def _check_triggered_events(self) -> list[dict]:
        """Check relationship metrics and trigger fights/confessions."""
        events: list[dict] = []

        for a_id, b_id, rel in self.relationships.all_pairs():
            # Fight trigger: very negative friendship
            if (
                rel.friendship <= _FIGHT_FRIENDSHIP_THRESHOLD
                and self._rng.random() < _FIGHT_CHANCE
                and rel.stage not in (RelationshipStage.STRANGER,)
            ):
                fight = self._trigger_fight(a_id, b_id, rel.friendship)
                if fight:
                    events.append(fight)

            # Confession trigger: high romance + friendship stage
            if (
                rel.romance >= _CONFESSION_ROMANCE_THRESHOLD
                and rel.stage in (
                    RelationshipStage.FRIEND,
                    RelationshipStage.BEST_FRIEND,
                )
                and self._rng.random() < _CONFESSION_CHANCE
            ):
                confession = self._trigger_confession(a_id, b_id)
                if confession:
                    events.append(confession)

        return events

    def _trigger_fight(self, a_id: int, b_id: int, friendship: float) -> dict | None:
        # Don't fight if already fighting
        active_fights = self.relationships.get_fights()
        for f in active_fights:
            if set(f.participants) == {a_id, b_id}:
                return None

        fight = Fight(
            participants=(a_id, b_id),
            cause=f"우정 {friendship:.0f} — 사이가 나쁨",
        )
        self.relationships.add_fight(fight)

        # Apply fight effects
        self.relationships.update(a_id, b_id, {"friendship": -5})
        self.relationships.update(b_id, a_id, {"friendship": -5})

        # Log event
        rel = self.relationships.get(a_id, b_id)
        rel.event_log.append(RelationshipEvent(
            day=self._tick_count,
            event_type="fight",
            summary=f"긴장이 폭발하여 싸움 발생",
        ))

        self.memory.add_event(SocialEvent(
            tick=self._tick_count,
            participants=[str(a_id), str(b_id)],
            event_type="fight",
            summary=f"{self._name(a_id)}와(과) {self._name(b_id)}가 싸움",
            emotional_impact={str(a_id): -5.0, str(b_id): -5.0},
        ))

        # Satisfaction hit
        for cid in (a_id, b_id):
            if cid in self._char_map:
                self._char_map[cid].satisfaction = max(
                    0.0, self._char_map[cid].satisfaction - 10.0
                )

        a_name = self._name(a_id)
        b_name = self._name(b_id)
        return {
            "type": "fight",
            "participants": [a_name, b_name],
            "summary": f"{a_name}와(과) {b_name}의 긴장이 폭발하여 싸움이 벌어졌다!",
        }

    def _trigger_confession(self, a_id: int, b_id: int) -> dict | None:
        rel_ab = self.relationships.get(a_id, b_id)
        rel_ba = self.relationships.get(b_id, a_id)

        # Check if B has mutual feelings
        success = rel_ba.romance >= 40.0

        if success:
            # Both transition to LOVER
            rel_ab.check_stage_transition(allow_romantic_transition=True)
            rel_ba.check_stage_transition(allow_romantic_transition=True)
            event_type = "confession_success"
            summary = f"{self._name(a_id)}가 {self._name(b_id)}에게 고백하여 연인이 되었다!"
        else:
            # Rejected: friendship hit, romance decreases
            self.relationships.update(a_id, b_id, {"friendship": -5, "romance": -10})
            event_type = "confession_fail"
            summary = f"{self._name(a_id)}가 {self._name(b_id)}에게 고백했지만 거절당했다."

        rel_ab.event_log.append(RelationshipEvent(
            day=self._tick_count,
            event_type=event_type,
            summary=summary,
        ))

        self.memory.add_event(SocialEvent(
            tick=self._tick_count,
            participants=[str(a_id), str(b_id)],
            event_type=event_type,
            summary=summary,
            emotional_impact={
                str(a_id): 10.0 if success else -8.0,
                str(b_id): 5.0 if success else -2.0,
            },
        ))

        return {
            "type": event_type,
            "participants": [self._name(a_id), self._name(b_id)],
            "summary": summary,
        }

    def _check_stage_transitions(self) -> None:
        """Check all relationships for stage changes (friendship-based only)."""
        for _a, _b, rel in self.relationships.all_pairs():
            rel.check_stage_transition(allow_romantic_transition=False)

    def _update_needs(self) -> None:
        """Decay satisfaction and increase hunger each tick."""
        for char in self.characters:
            char.hunger = min(100.0, char.hunger + _HUNGER_PER_TICK)
            char.satisfaction = max(0.0, char.satisfaction - _SATISFACTION_DECAY)

    def _name(self, char_id) -> str:
        return self._char_map[char_id].name if char_id in self._char_map else str(char_id)

    def _force_encounter(
        self, char_a: Character, char_b: Character, location: str,
    ) -> ConversationResult:
        return self._run_conversation(char_a, char_b, location, "오후")

    def run(self, num_ticks: int, seed: int | None = None) -> None:
        for i in range(num_ticks):
            tick_seed = seed + i if seed is not None else None
            events = self.tick(seed=tick_seed)
            self._print_tick(i, events)

    def _print_tick(self, tick_num: int, events: list[dict]) -> None:
        time_of_day = _TIME_SLOTS[tick_num % len(_TIME_SLOTS)]
        print(f"\n{'='*60}")
        print(f"  틱 {tick_num} | {time_of_day}")
        print(f"{'='*60}")

        if not events:
            print("  (아무 일도 일어나지 않았다)")
            return

        for event in events:
            etype = event["type"]

            if etype == "conversation":
                result: ConversationResult = event["result"]
                print(f"\n  📍 {result.summary}")
                print(f"  {'-'*40}")
                for line in result.dialogue:
                    print(f"  {line.speaker}: {line.text}")
                for name, deltas in result.deltas.items():
                    parts = [f"{k}:{v:+.0f}" for k, v in deltas.items() if v != 0]
                    if parts:
                        print(f"  [{name}] {', '.join(parts)}")

            elif etype == "fight":
                print(f"\n  💥 {event['summary']}")

            elif etype.startswith("confession"):
                emoji = "💕" if etype == "confession_success" else "💔"
                print(f"\n  {emoji} {event['summary']}")

            else:
                print(f"\n  📌 {event['summary']}")
