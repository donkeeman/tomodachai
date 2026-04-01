from __future__ import annotations

from pydantic import BaseModel


class Relationship(BaseModel):
    friendship: float = 0.0   # -100 ~ 100
    romance: float = 0.0      # 0 ~ 100
    tension: float = 0.0      # 0 ~ 100
    jealousy: float = 0.0     # 0 ~ 100

    def apply_deltas(self, deltas: dict[str, float]) -> None:
        for key, delta in deltas.items():
            current = getattr(self, key)
            new_val = current + delta
            low, high = self._bounds(key)
            setattr(self, key, max(low, min(high, new_val)))

    @staticmethod
    def _bounds(key: str) -> tuple[float, float]:
        if key == "friendship":
            return -100.0, 100.0
        return 0.0, 100.0


class RelationshipTracker:
    def __init__(self) -> None:
        self._relationships: dict[tuple[str, str], Relationship] = {}

    def get(self, char_a: str, char_b: str) -> Relationship:
        key = (char_a, char_b)
        if key not in self._relationships:
            self._relationships[key] = Relationship()
        return self._relationships[key]

    def update(self, char_a: str, char_b: str, deltas: dict[str, float]) -> None:
        rel = self.get(char_a, char_b)
        rel.apply_deltas(deltas)

    def get_romantic_interests(
        self, char_id: str, threshold: float = 20.0
    ) -> list[tuple[str, float]]:
        results = []
        for (a, b), rel in self._relationships.items():
            if a == char_id and rel.romance >= threshold:
                results.append((b, rel.romance))
        return sorted(results, key=lambda x: -x[1])

    def get_friends(
        self, char_id: str, threshold: float = 50.0
    ) -> list[tuple[str, float]]:
        results = []
        for (a, b), rel in self._relationships.items():
            if a == char_id and rel.friendship >= threshold:
                results.append((b, rel.friendship))
        return sorted(results, key=lambda x: -x[1])

    def get_rivals(
        self, char_id: str, threshold: float = -50.0
    ) -> list[tuple[str, float]]:
        results = []
        for (a, b), rel in self._relationships.items():
            if a == char_id and rel.friendship <= threshold:
                results.append((b, rel.friendship))
        return sorted(results, key=lambda x: x[1])

    def all_pairs(self) -> list[tuple[str, str, Relationship]]:
        return [(a, b, rel) for (a, b), rel in self._relationships.items()]
