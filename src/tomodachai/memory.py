from __future__ import annotations

from pydantic import BaseModel


class SocialEvent(BaseModel):
    id: int
    type: str
    participants: list[int]
    day: int
    time: str | None = None
    location: str | None = None
    reason: str | None = None
    result: str | None = None


class MemoryStore:
    def __init__(self) -> None:
        self._events: list[SocialEvent] = []
        self._next_id: int = 1

    def add_event(self, event: SocialEvent) -> None:
        if event.id == 0:
            event = event.model_copy(update={"id": self._next_id})
        self._next_id = max(self._next_id, event.id) + 1
        self._events.append(event)

    def get_events_for(
        self, char_id: int | str, limit: int = 10
    ) -> list[SocialEvent]:
        key = int(char_id)
        relevant = [e for e in self._events if key in e.participants]
        relevant.sort(key=lambda e: e.day, reverse=True)
        return relevant[:limit]

    def get_events_between(
        self, char_a: int | str, char_b: int | str, limit: int = 5
    ) -> list[SocialEvent]:
        key_a, key_b = int(char_a), int(char_b)
        relevant = [
            e for e in self._events
            if key_a in e.participants and key_b in e.participants
        ]
        relevant.sort(key=lambda e: e.day, reverse=True)
        return relevant[:limit]
