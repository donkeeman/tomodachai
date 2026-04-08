from __future__ import annotations

from pydantic import BaseModel


class SocialEvent(BaseModel):
    tick: int
    participants: list[str]
    event_type: str
    summary: str
    emotional_impact: dict[str, float]


class MemoryStore:
    def __init__(self) -> None:
        self._events: list[SocialEvent] = []

    def add_event(self, event: SocialEvent) -> None:
        self._events.append(event)

    def get_events_for(
        self, char_id: str | int, limit: int = 10
    ) -> list[SocialEvent]:
        key = str(char_id)
        relevant = [
            e for e in self._events if key in e.participants
        ]
        relevant.sort(key=lambda e: e.tick, reverse=True)
        return relevant[:limit]

    def get_events_between(
        self, char_a: str | int, char_b: str | int, limit: int = 5
    ) -> list[SocialEvent]:
        key_a, key_b = str(char_a), str(char_b)
        relevant = [
            e for e in self._events
            if key_a in e.participants and key_b in e.participants
        ]
        relevant.sort(key=lambda e: e.tick, reverse=True)
        return relevant[:limit]
