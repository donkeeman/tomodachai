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


class BreakupReason(str, Enum):
    MUTUAL = "mutual"                      # 합의
    FIGHT = "fight"                        # 싸움
    CHEATING = "cheating"                  # 바람
    BOREDOM = "boredom"                    # 권태
    TRIANGLE = "triangle"                  # 삼각관계
    MISUNDERSTANDING = "misunderstanding"  # 오해




class Fight(BaseModel):
    participants: tuple[int, int]
    cause: str
    resolved: bool = False
    witnessed_by_player: bool = False


class ExLoverTag(BaseModel):
    target: int
    reason: BreakupReason
    day: int


class RelationshipSlots(BaseModel):
    best_friend: int | None = None  # friendship >= 70 (양방향)
    lover: int | None = None  # 고백 성공으로 설정
    enemy: int | None = None  # friendship <= -50 (양방향)


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
    friendship: float = 0.0  # -100 ~ 100
    romance: float = 0.0  # 0 ~ 100
    stage: RelationshipStage = RelationshipStage.STRANGER

    def apply_deltas(self, deltas: dict[str, float]) -> None:
        for key, delta in deltas.items():
            if key not in ("friendship", "romance"):
                continue
            current = getattr(self, key)
            new_val = current + delta
            low, high = self._bounds(key)
            setattr(self, key, max(low, min(high, new_val)))

    @staticmethod
    def _bounds(key: str) -> tuple[float, float]:
        if key == "friendship":
            return -100.0, 100.0
        return 0.0, 100.0

    def apply_natural_decay(
        self, decay_friendship: float = 0.75, decay_romance: float = 0.5
    ) -> None:
        """
        Decay friendship and romance toward 0 by the given daily amounts.

        friendship: positive values decay downward, negative values recover upward.
        romance: always decays toward 0 (never below 0).
        """
        if self.friendship > 0:
            self.friendship = max(0.0, self.friendship - decay_friendship)
        elif self.friendship < 0:
            self.friendship = min(0.0, self.friendship + decay_friendship)

        if self.romance > 0:
            self.romance = max(0.0, self.romance - decay_romance)

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
            if self.romance < _ROMANCE_THRESHOLDS[RelationshipStage.LOVER]:
                return RelationshipStage.LOVER
            return RelationshipStage.MARRIED

        if current == RelationshipStage.LOVER:
            if (
                allow_romantic_transition
                and self.romance >= _ROMANCE_THRESHOLDS[RelationshipStage.MARRIED]
            ):
                return RelationshipStage.MARRIED
            if self.romance < _ROMANCE_THRESHOLDS[RelationshipStage.LOVER]:
                return self._friendship_stage()
            return RelationshipStage.LOVER

        # --- Friendship-based stages ---
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
        """Return friendship label based on raw value (spec §8)."""
        if self.friendship >= 80:
            return "둘도 없는 친구"
        if self.friendship >= 60:
            return "꽤 친한 사이"
        if self.friendship >= 40:
            return "친해지는 중"
        if self.friendship >= 20:
            return "알고 지내는 사이"
        if self.friendship >= -19:
            return "그저 그런 사이"
        if self.friendship >= -49:
            return "서먹서먹"
        if self.friendship >= -69:
            return "사이가 나쁨"
        return "앙숙"

    def get_romance_text(self) -> str | None:
        """Return romance label based on raw value, or None if romance == 0."""
        if self.romance <= 0:
            return None
        if self.romance >= 80:
            return "완전 반한"
        if self.romance >= 50:
            return "많이 좋아하는"
        if self.romance >= 21:
            return "좋아하는 것 같은"
        return "약간 신경 쓰이는"



def check_breakup_conditions(
    rel: "Relationship",
    has_cheating: bool = False,
    has_triangle: bool = False,
    fight_unresolved: bool = False,
    romance_threshold: float = 20.0,
) -> "BreakupReason | None":
    """
    Auto-detect the most likely breakup reason from relationship state.

    Priority order: CHEATING → TRIANGLE → FIGHT → BOREDOM.
    MUTUAL and MISUNDERSTANDING are narrative reasons; skip auto-detection.

    Returns None if no breakup condition is met (romance still healthy).
    """
    if rel.stage not in (RelationshipStage.LOVER, RelationshipStage.MARRIED):
        return None

    if has_cheating:
        return BreakupReason.CHEATING

    if has_triangle:
        return BreakupReason.TRIANGLE

    if fight_unresolved and rel.romance < romance_threshold:
        return BreakupReason.FIGHT

    if rel.romance < romance_threshold:
        return BreakupReason.BOREDOM

    return None


# ---------------------------------------------------------------------------
# RelationshipTracker
# ---------------------------------------------------------------------------


class RelationshipTracker:
    def __init__(self) -> None:
        self._relationships: dict[tuple[int, int], Relationship] = {}
        self._fights: list[Fight] = []
        self._slots: dict[int, RelationshipSlots] = {}
        self._ex_lover_tags: dict[int, list[ExLoverTag]] = {}

    def get(self, char_a: int, char_b: int) -> Relationship:
        key = (char_a, char_b)
        if key not in self._relationships:
            self._relationships[key] = Relationship()
        return self._relationships[key]

    def update(self, char_a: int, char_b: int, deltas: dict[str, float]) -> None:
        rel = self.get(char_a, char_b)
        rel.apply_deltas(deltas)

    def get_romantic_interests(
        self, char_id: int, threshold: float = 20.0
    ) -> list[tuple[int, float]]:
        results = []
        for (a, b), rel in self._relationships.items():
            if a == char_id and rel.romance >= threshold:
                results.append((b, rel.romance))
        return sorted(results, key=lambda x: -x[1])

    def get_friends(self, char_id: int, threshold: float = 50.0) -> list[tuple[int, float]]:
        results = []
        for (a, b), rel in self._relationships.items():
            if a == char_id and rel.friendship >= threshold:
                results.append((b, rel.friendship))
        return sorted(results, key=lambda x: -x[1])

    def get_rivals(self, char_id: int, threshold: float = -50.0) -> list[tuple[int, float]]:
        results = []
        for (a, b), rel in self._relationships.items():
            if a == char_id and rel.friendship <= threshold:
                results.append((b, rel.friendship))
        return sorted(results, key=lambda x: x[1])

    def all_pairs(self) -> list[tuple[int, int, Relationship]]:
        return [(a, b, rel) for (a, b), rel in self._relationships.items()]

    # ------------------------------------------------------------------
    # Natural decay (daily tick)
    # ------------------------------------------------------------------

    def apply_daily_decay(
        self,
        decay_friendship: float = 0.75,
        decay_romance: float = 0.5,
    ) -> None:
        """Apply natural decay to all tracked relationships."""
        for rel in self._relationships.values():
            rel.apply_natural_decay(decay_friendship, decay_romance)

    # ------------------------------------------------------------------
    # Slots management
    # ------------------------------------------------------------------

    def get_slots(self, char_id: int) -> RelationshipSlots:
        if char_id not in self._slots:
            self._slots[char_id] = RelationshipSlots()
        return self._slots[char_id]

    def set_lover(self, char_a: int, char_b: int) -> None:
        """Set lover slot for both characters (mutual)."""
        self.get_slots(char_a).lover = char_b
        self.get_slots(char_b).lover = char_a

    def clear_lover(self, char_a: int, char_b: int) -> None:
        """Clear lover slot for both characters."""
        slots_a = self.get_slots(char_a)
        slots_b = self.get_slots(char_b)
        if slots_a.lover == char_b:
            slots_a.lover = None
        if slots_b.lover == char_a:
            slots_b.lover = None

    def recompute_slots(self, char_id: int) -> None:
        """
        Recompute best_friend and enemy slots for char_id based on current relationship values.
        Lover slot is NOT touched — it is set only via confession events.

        best_friend: the character B where both A→B and B→A friendship >= 70,
                     picking the highest A→B value. Only one slot.
        enemy:       the character B where both A→B and B→A friendship <= -50,
                     picking the lowest A→B value. Only one slot.
        """
        slots = self.get_slots(char_id)

        best_friend_candidate: int | None = None
        best_friend_value: float = 70.0  # minimum threshold

        enemy_candidate: int | None = None
        enemy_value: float = -50.0  # maximum threshold (we want the most negative)

        all_others = {b for (a, b) in self._relationships if a == char_id}
        for other in all_others:
            rel_ab = self.get(char_id, other)
            rel_ba = self.get(other, char_id)

            # best_friend: bilateral >= 70
            if rel_ab.friendship >= 70.0 and rel_ba.friendship >= 70.0:
                if rel_ab.friendship > best_friend_value:
                    best_friend_value = rel_ab.friendship
                    best_friend_candidate = other

            # enemy: bilateral <= -50
            if rel_ab.friendship <= -50.0 and rel_ba.friendship <= -50.0:
                if rel_ab.friendship < enemy_value:
                    enemy_value = rel_ab.friendship
                    enemy_candidate = other

        slots.best_friend = best_friend_candidate
        slots.enemy = enemy_candidate

    # ------------------------------------------------------------------
    # Ex-lover tags
    # ------------------------------------------------------------------

    def add_ex_lover_tag(self, char_id: int, target: int, reason: BreakupReason, day: int) -> None:
        if char_id not in self._ex_lover_tags:
            self._ex_lover_tags[char_id] = []
        self._ex_lover_tags[char_id].append(ExLoverTag(target=target, reason=reason, day=day))

    def get_ex_lover_tags(self, char_id: int) -> list[ExLoverTag]:
        return list(self._ex_lover_tags.get(char_id, []))

    def remove_ex_lover_tag(self, char_id: int, target: int) -> None:
        """Remove ex-lover tag (e.g. on reconciliation)."""
        tags = self._ex_lover_tags.get(char_id, [])
        self._ex_lover_tags[char_id] = [t for t in tags if t.target != target]

    # ------------------------------------------------------------------
    # Fight management
    # ------------------------------------------------------------------

    def add_fight(self, fight: Fight) -> None:
        self._fights.append(fight)

    def get_fights(self) -> list[Fight]:
        """Return all unresolved fights."""
        return [f for f in self._fights if not f.resolved]

    def resolve_fight(self, participants: tuple[int, int]) -> bool:
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
    jealous: int
    target: int
    rival: int
    romance_level: float


def detect_triangles(
    tracker: RelationshipTracker,
    romance_threshold: float = 30.0,
    friendship_threshold: float = 30.0,
) -> list[Triangle]:
    triangles: list[Triangle] = []
    all_chars: set[int] = set()
    for a, b in tracker._relationships:
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
                    triangles.append(
                        Triangle(
                            jealous=a,
                            target=b,
                            rival=c,
                            romance_level=rel_ab.romance,
                        )
                    )
    return triangles


def apply_jealousy(
    tracker: RelationshipTracker,
    triangles: list[Triangle],
    jealousy_rate: float = 0.3,
) -> None:
    """
    Apply jealousy effects as friendship penalties.

    The jealous character's friendship toward the rival decreases
    (they dislike the person "stealing" their love interest).
    """
    for tri in triangles:
        friendship_delta = -(tri.romance_level * jealousy_rate * 0.1)
        tracker.update(tri.jealous, tri.rival, {"friendship": friendship_delta})


# ---------------------------------------------------------------------------
# Compatibility system
# ---------------------------------------------------------------------------

_BLOOD_COMPAT: dict[tuple[str, str], float] = {
    # High
    ("O", "A"): 0.85,
    ("A", "O"): 0.85,
    ("O", "B"): 0.75,
    ("B", "O"): 0.75,
    ("O", "O"): 0.80,
    ("A", "A"): 0.75,
    ("B", "B"): 0.75,
    ("AB", "O"): 0.70,
    ("O", "AB"): 0.70,
    # Medium
    ("AB", "A"): 0.60,
    ("A", "AB"): 0.60,
    ("AB", "B"): 0.60,
    ("B", "AB"): 0.60,
    ("AB", "AB"): 0.55,
    # Low
    ("A", "B"): 0.35,
    ("B", "A"): 0.35,
}

# Korean zodiac element groupings
_ZODIAC_ELEMENTS: dict[str, str] = {
    # 불 (Fire)
    "양자리": "불",
    "사자자리": "불",
    "사수자리": "불",
    # 땅 (Earth)
    "황소자리": "땅",
    "처녀자리": "땅",
    "염소자리": "땅",
    # 바람 (Air)
    "쌍둥이자리": "바람",
    "천칭자리": "바람",
    "물병자리": "바람",
    # 물 (Water)
    "게자리": "물",
    "전갈자리": "물",
    "물고기자리": "물",
}

# Personality group compatibility
_GROUP_COMPAT: dict[tuple[str, str], float] = {
    # Good pairs: 안정파+사교파, 신중파+주도파
    ("안정파", "사교파"): 0.85, ("사교파", "안정파"): 0.85,
    ("신중파", "주도파"): 0.85, ("주도파", "신중파"): 0.85,
    # Same group (medium)
    ("안정파", "안정파"): 0.60,
    ("사교파", "사교파"): 0.60,
    ("신중파", "신중파"): 0.60,
    ("주도파", "주도파"): 0.60,
    # Cross (lower)
    ("안정파", "신중파"): 0.40, ("신중파", "안정파"): 0.40,
    ("안정파", "주도파"): 0.35, ("주도파", "안정파"): 0.35,
    ("사교파", "신중파"): 0.45, ("신중파", "사교파"): 0.45,
    ("사교파", "주도파"): 0.40, ("주도파", "사교파"): 0.40,
}


_CODE_TO_GROUP: dict[str, str] = {
    "easygoing": "안정파",
    "outgoing": "사교파",
    "confident": "주도파",
    "independent": "신중파",
}


def _personality_group(personality: str) -> str | None:
    """Extract group name from a personality code like 'easygoing_softie' or 'confident_gogetter'."""  # noqa: E501
    prefix = personality.split("_")[0] if "_" in personality else personality
    return _CODE_TO_GROUP.get(prefix)


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
    family_a = _personality_group(personality_a)
    family_b = _personality_group(personality_b)
    if family_a and family_b:
        personality_score = _GROUP_COMPAT.get(
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
            zodiac_score = 0.80  # same element bonus
        elif {elem_a, elem_b} in (
            {"불", "바람"},
            {"땅", "물"},
        ):
            zodiac_score = 0.70  # complementary elements
        else:
            zodiac_score = 0.45  # conflicting elements
    else:
        zodiac_score = 0.55

    return round(
        personality_score * 0.50 + blood_score * 0.30 + zodiac_score * 0.20,
        4,
    )
