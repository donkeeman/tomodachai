from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums & small models
# ---------------------------------------------------------------------------

class RelationshipStage(str, Enum):
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    BEST_FRIEND = "best_friend"
    LOVER = "lover"
    MARRIED = "married"


class RelationshipEvent(BaseModel):
    day: int
    event_type: str  # "confession", "breakup", "reconciliation", "fight", "makeup", "marriage"
    summary: str


class Fight(BaseModel):
    participants: tuple[str, str]
    cause: str
    resolved: bool = False
    witnessed_by_player: bool = False


# ---------------------------------------------------------------------------
# Stage transition thresholds
# ---------------------------------------------------------------------------

_FRIENDSHIP_THRESHOLDS: dict[RelationshipStage, float] = {
    RelationshipStage.ACQUAINTANCE: 10.0,
    RelationshipStage.FRIEND: 40.0,
    RelationshipStage.BEST_FRIEND: 80.0,
}

_ROMANCE_THRESHOLDS: dict[RelationshipStage, float] = {
    RelationshipStage.LOVER: 60.0,
    RelationshipStage.MARRIED: 90.0,
}

# Friendship value required to *stay* in a stage (demotion guard)
_DEMOTION_GUARD: dict[RelationshipStage, float] = {
    RelationshipStage.ACQUAINTANCE: _FRIENDSHIP_THRESHOLDS[RelationshipStage.ACQUAINTANCE],
    RelationshipStage.FRIEND: _FRIENDSHIP_THRESHOLDS[RelationshipStage.FRIEND],
    RelationshipStage.BEST_FRIEND: _FRIENDSHIP_THRESHOLDS[RelationshipStage.BEST_FRIEND],
}

_STAGE_STATUS_TEXT: dict[RelationshipStage, str] = {
    RelationshipStage.STRANGER: "모르는 사이",
    RelationshipStage.ACQUAINTANCE: "아는 사이",
    RelationshipStage.FRIEND: "친구",
    RelationshipStage.BEST_FRIEND: "베프",
    RelationshipStage.LOVER: "연인",
    RelationshipStage.MARRIED: "부부",
}


# ---------------------------------------------------------------------------
# Relationship model
# ---------------------------------------------------------------------------

class Relationship(BaseModel):
    friendship: float = 0.0   # -100 ~ 100
    romance: float = 0.0      # 0 ~ 100
    tension: float = 0.0      # 0 ~ 100
    jealousy: float = 0.0     # 0 ~ 100
    stage: RelationshipStage = RelationshipStage.STRANGER
    event_log: list[RelationshipEvent] = Field(default_factory=list)

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

    # ------------------------------------------------------------------
    # Stage transitions
    # ------------------------------------------------------------------

    def check_stage_transition(
        self,
        allow_romantic_transition: bool = False,
    ) -> bool:
        """
        Re-evaluate and update ``stage`` based on current metric values.

        Romantic transitions (FRIEND/BEST_FRIEND → LOVER, LOVER → MARRIED)
        require ``allow_romantic_transition=True`` — this acts as the LLM
        guardrail: numeric thresholds must be met *and* an external signal
        (e.g. a confession event) must have fired before the stage changes.

        Returns True if the stage changed.
        """
        old_stage = self.stage
        new_stage = self._compute_stage(allow_romantic_transition)
        if new_stage != old_stage:
            self.stage = new_stage
            return True
        return False

    def _compute_stage(self, allow_romantic_transition: bool) -> RelationshipStage:
        current = self.stage

        # --- Romantic stages: check first so demotion works correctly ---
        if current == RelationshipStage.MARRIED:
            # MARRIED can only be demoted back to LOVER if romance drops
            if self.romance < _ROMANCE_THRESHOLDS[RelationshipStage.LOVER]:
                return RelationshipStage.LOVER
            return RelationshipStage.MARRIED

        if current == RelationshipStage.LOVER:
            # Promotion to MARRIED
            if (
                allow_romantic_transition
                and self.romance >= _ROMANCE_THRESHOLDS[RelationshipStage.MARRIED]
            ):
                return RelationshipStage.MARRIED
            # Demotion: romance dropped below LOVER threshold → back to friendship stage
            if self.romance < _ROMANCE_THRESHOLDS[RelationshipStage.LOVER]:
                return self._friendship_stage()
            return RelationshipStage.LOVER

        # --- Friendship-based stages ---
        # Check if romantic transition should happen
        if allow_romantic_transition and current in (
            RelationshipStage.FRIEND,
            RelationshipStage.BEST_FRIEND,
        ):
            if self.romance >= _ROMANCE_THRESHOLDS[RelationshipStage.LOVER]:
                return RelationshipStage.LOVER

        return self._friendship_stage()

    def _friendship_stage(self) -> RelationshipStage:
        """Return the appropriate non-romantic stage based on friendship."""
        if self.friendship >= _FRIENDSHIP_THRESHOLDS[RelationshipStage.BEST_FRIEND]:
            return RelationshipStage.BEST_FRIEND
        if self.friendship >= _FRIENDSHIP_THRESHOLDS[RelationshipStage.FRIEND]:
            return RelationshipStage.FRIEND
        if self.friendship >= _FRIENDSHIP_THRESHOLDS[RelationshipStage.ACQUAINTANCE]:
            return RelationshipStage.ACQUAINTANCE
        return RelationshipStage.STRANGER

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def get_status_text(self) -> str:
        """Return Korean display text for the current stage."""
        return _STAGE_STATUS_TEXT[self.stage]

    def get_friendship_text(self) -> str:
        """Return nuanced friendship label based on raw value."""
        if self.friendship >= 90:
            return "엄청 좋아함"
        if self.friendship >= 60:
            return "많이 좋아함"
        if self.friendship >= 30:
            return "좋아함"
        if self.friendship >= 10:
            return "조금 알아감"
        if self.friendship >= 0:
            return "별로 모름"
        if self.friendship >= -30:
            return "불편함"
        if self.friendship >= -60:
            return "싫어함"
        return "매우 싫어함"

    # ------------------------------------------------------------------
    # Reconciliation check
    # ------------------------------------------------------------------

    def can_reconcile(self) -> bool:
        """Return True if this relationship has a recorded breakup in its event log."""
        return any(e.event_type == "breakup" for e in self.event_log)


# ---------------------------------------------------------------------------
# RelationshipTracker
# ---------------------------------------------------------------------------

class RelationshipTracker:
    def __init__(self) -> None:
        self._relationships: dict[tuple[str, str], Relationship] = {}
        self._fights: list[Fight] = []

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

    # ------------------------------------------------------------------
    # Fight management
    # ------------------------------------------------------------------

    def add_fight(self, fight: Fight) -> None:
        self._fights.append(fight)

    def get_fights(self) -> list[Fight]:
        """Return all unresolved fights."""
        return [f for f in self._fights if not f.resolved]

    def resolve_fight(self, participants: tuple[str, str]) -> bool:
        """Mark the first unresolved fight between participants as resolved."""
        key = set(participants)
        for fight in self._fights:
            if not fight.resolved and set(fight.participants) == key:
                fight.resolved = True
                return True
        return False


# ---------------------------------------------------------------------------
# Triangle model & helpers
# ---------------------------------------------------------------------------

class Triangle(BaseModel):
    jealous: str
    target: str
    rival: str
    romance_level: float


def detect_triangles(
    tracker: RelationshipTracker,
    romance_threshold: float = 30.0,
    friendship_threshold: float = 30.0,
) -> list[Triangle]:
    triangles: list[Triangle] = []
    all_chars = set()
    for (a, b), _ in tracker._relationships.items():
        all_chars.add(a)
        all_chars.add(b)

    for a in all_chars:
        for b in all_chars:
            if a == b:
                continue
            rel_ab = tracker.get(a, b)
            if rel_ab.romance < romance_threshold:
                continue
            for c in all_chars:
                if c == a or c == b:
                    continue
                rel_bc = tracker.get(b, c)
                if rel_bc.friendship >= friendship_threshold:
                    triangles.append(Triangle(
                        jealous=a, target=b, rival=c,
                        romance_level=rel_ab.romance,
                    ))
    return triangles


def apply_jealousy(
    tracker: RelationshipTracker,
    triangles: list[Triangle],
    jealousy_rate: float = 0.3,
    tension_rate: float = 0.1,
) -> None:
    for tri in triangles:
        jealousy_delta = tri.romance_level * jealousy_rate * 0.1
        tracker.update(tri.jealous, tri.rival, {"jealousy": jealousy_delta})
        tension_delta = tri.romance_level * tension_rate * 0.1
        tracker.update(tri.jealous, tri.target, {"tension": tension_delta})


# ---------------------------------------------------------------------------
# Compatibility system
# ---------------------------------------------------------------------------

_BLOOD_COMPAT: dict[tuple[str, str], float] = {
    # High
    ("O", "A"): 0.85, ("A", "O"): 0.85,
    ("O", "B"): 0.75, ("B", "O"): 0.75,
    ("O", "O"): 0.80,
    ("A", "A"): 0.75,
    ("B", "B"): 0.75,
    ("AB", "O"): 0.70, ("O", "AB"): 0.70,
    # Medium
    ("AB", "A"): 0.60, ("A", "AB"): 0.60,
    ("AB", "B"): 0.60, ("B", "AB"): 0.60,
    ("AB", "AB"): 0.55,
    # Low
    ("A", "B"): 0.35, ("B", "A"): 0.35,
}

# Korean zodiac element groupings
_ZODIAC_ELEMENTS: dict[str, str] = {
    # 불 (Fire)
    "양자리": "불", "사자자리": "불", "사수자리": "불",
    # 땅 (Earth)
    "황소자리": "땅", "처녀자리": "땅", "염소자리": "땅",
    # 바람 (Air)
    "쌍둥이자리": "바람", "천칭자리": "바람", "물병자리": "바람",
    # 물 (Water)
    "게자리": "물", "전갈자리": "물", "물고기자리": "물",
}

# Personality family groupings (나고미/노리/쿨/드라이)
_PERSONALITY_FAMILIES: dict[str, str] = {
    "나고미": "나고미",
    "노리": "노리",
    "쿨": "쿨",
    "드라이": "드라이",
}

_FAMILY_COMPAT: dict[tuple[str, str], float] = {
    # Good pairs
    ("나고미", "노리"): 0.85, ("노리", "나고미"): 0.85,
    ("쿨", "드라이"): 0.85, ("드라이", "쿨"): 0.85,
    # Same family (medium)
    ("나고미", "나고미"): 0.60,
    ("노리", "노리"): 0.60,
    ("쿨", "쿨"): 0.60,
    ("드라이", "드라이"): 0.60,
    # Opposite / cross (lower)
    ("나고미", "쿨"): 0.40, ("쿨", "나고미"): 0.40,
    ("나고미", "드라이"): 0.35, ("드라이", "나고미"): 0.35,
    ("노리", "쿨"): 0.45, ("쿨", "노리"): 0.45,
    ("노리", "드라이"): 0.40, ("드라이", "노리"): 0.40,
}


_CODE_TO_FAMILY: dict[str, str] = {
    "nagomi": "나고미",
    "nori": "노리",
    "cool": "쿨",
    "dry": "드라이",
}


def _personality_family(personality: str) -> str | None:
    """Extract family name from a personality code like 'nagomi_softie' or 'cool_introvert'."""
    prefix = personality.split("_")[0] if "_" in personality else personality
    return _CODE_TO_FAMILY.get(prefix)


def calculate_compatibility(
    personality_a: str,
    personality_b: str,
    blood_a: str,
    blood_b: str,
    zodiac_a: str,
    zodiac_b: str,
) -> float:
    """
    Calculate compatibility score between two characters.

    Weights: personality 50%, blood type 30%, zodiac 20%.
    Returns a value in 0.0 ~ 1.0.
    """
    # --- Personality (50%) ---
    family_a = _personality_family(personality_a)
    family_b = _personality_family(personality_b)
    if family_a and family_b:
        personality_score = _FAMILY_COMPAT.get(
            (family_a, family_b),
            0.50,  # unknown pair → neutral
        )
    else:
        personality_score = 0.50

    # --- Blood type (30%) ---
    blood_score = _BLOOD_COMPAT.get((blood_a.upper(), blood_b.upper()), 0.55)

    # --- Zodiac (20%) ---
    elem_a = _ZODIAC_ELEMENTS.get(zodiac_a)
    elem_b = _ZODIAC_ELEMENTS.get(zodiac_b)
    if elem_a and elem_b:
        if elem_a == elem_b:
            zodiac_score = 0.80   # same element bonus
        elif {elem_a, elem_b} in (
            {"불", "바람"},
            {"땅", "물"},
        ):
            zodiac_score = 0.70   # complementary elements
        else:
            zodiac_score = 0.45   # conflicting elements
    else:
        zodiac_score = 0.55

    return round(
        personality_score * 0.50
        + blood_score * 0.30
        + zodiac_score * 0.20,
        4,
    )
