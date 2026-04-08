from tomodachai.relationship import (
    ExLoverTag,
    Fight,
    BreakupReason,
    Relationship,
    RelationshipEvent,
    RelationshipSlots,
    RelationshipStage,
    RelationshipTracker,
    Triangle,
    apply_jealousy,
    calculate_compatibility,
    detect_triangles,
)


# ---------------------------------------------------------------------------
# Basic Relationship model
# ---------------------------------------------------------------------------

def test_relationship_defaults():
    r = Relationship()
    assert r.friendship == 0.0
    assert r.romance == 0.0
    assert r.stage == RelationshipStage.STRANGER


def test_apply_deltas():
    r = Relationship(friendship=50.0)
    r.apply_deltas({"friendship": 10, "romance": 5})
    assert r.friendship == 60.0
    assert r.romance == 5.0


def test_apply_deltas_ignores_unknown():
    """tension/jealousy 같은 제거된 키는 조용히 무시."""
    r = Relationship(friendship=50.0)
    r.apply_deltas({"friendship": 10, "tension": 5, "jealousy": 3})
    assert r.friendship == 60.0


def test_apply_deltas_clamps():
    r = Relationship(friendship=95.0)
    r.apply_deltas({"friendship": 20})
    assert r.friendship == 100.0

    r2 = Relationship(friendship=-95.0)
    r2.apply_deltas({"friendship": -20})
    assert r2.friendship == -100.0


def test_romance_clamps_at_zero():
    r = Relationship(romance=5.0)
    r.apply_deltas({"romance": -20})
    assert r.romance == 0.0


# ---------------------------------------------------------------------------
# Natural decay
# ---------------------------------------------------------------------------

def test_natural_decay():
    r = Relationship(friendship=50.0, romance=30.0)
    r.apply_natural_decay()
    assert r.friendship < 50.0
    assert r.romance < 30.0


def test_natural_decay_negative_friendship():
    r = Relationship(friendship=-50.0)
    r.apply_natural_decay()
    assert r.friendship > -50.0  # recovers toward 0


# ---------------------------------------------------------------------------
# Stage transitions
# ---------------------------------------------------------------------------

def test_stage_auto_promotion_friendship():
    r = Relationship(friendship=45.0)
    changed = r.check_stage_transition()
    assert changed
    assert r.stage == RelationshipStage.FRIEND


def test_stage_acquaintance():
    r = Relationship(friendship=15.0)
    r.check_stage_transition()
    assert r.stage == RelationshipStage.ACQUAINTANCE


def test_stage_best_friend():
    r = Relationship(friendship=85.0)
    r.check_stage_transition()
    assert r.stage == RelationshipStage.BEST_FRIEND


def test_stage_romantic_requires_flag():
    r = Relationship(friendship=50.0, romance=70.0, stage=RelationshipStage.FRIEND)
    r.check_stage_transition(allow_romantic_transition=False)
    assert r.stage != RelationshipStage.LOVER


def test_stage_romantic_with_flag():
    r = Relationship(friendship=50.0, romance=70.0, stage=RelationshipStage.FRIEND)
    changed = r.check_stage_transition(allow_romantic_transition=True)
    assert changed
    assert r.stage == RelationshipStage.LOVER


def test_stage_demotion():
    r = Relationship(friendship=5.0, stage=RelationshipStage.FRIEND)
    changed = r.check_stage_transition()
    assert changed
    assert r.stage == RelationshipStage.STRANGER


def test_stage_demotion_to_acquaintance():
    r = Relationship(friendship=15.0, stage=RelationshipStage.FRIEND)
    changed = r.check_stage_transition()
    assert changed
    assert r.stage == RelationshipStage.ACQUAINTANCE


def test_status_text():
    r = Relationship(stage=RelationshipStage.FRIEND)
    assert r.get_status_text() == "친구"


def test_friendship_text():
    r = Relationship(friendship=85.0)
    assert r.get_friendship_text() == "둘도 없는 친구"

    r2 = Relationship(friendship=-70.0)
    assert r2.get_friendship_text() == "앙숙"


def test_romance_text():
    assert Relationship(romance=0.0).get_romance_text() is None
    assert Relationship(romance=85.0).get_romance_text() == "완전 반한"


# ---------------------------------------------------------------------------
# Event log & reconciliation
# ---------------------------------------------------------------------------

def test_can_reconcile():
    r = Relationship()
    assert not r.can_reconcile()
    r.event_log.append(RelationshipEvent(day=10, event_type="breakup", summary="이별"))
    assert r.can_reconcile()


# ---------------------------------------------------------------------------
# Tracker basics (int IDs)
# ---------------------------------------------------------------------------

def test_tracker_get_creates_default():
    tracker = RelationshipTracker()
    rel = tracker.get(1, 2)
    assert rel.friendship == 0.0


def test_tracker_is_directional():
    tracker = RelationshipTracker()
    tracker.update(1, 2, {"friendship": 10})
    assert tracker.get(1, 2).friendship == 10.0
    assert tracker.get(2, 1).friendship == 0.0


def test_tracker_get_romantic_interests():
    tracker = RelationshipTracker()
    tracker.update(1, 2, {"romance": 50})
    tracker.update(1, 3, {"romance": 10})
    tracker.update(1, 4, {"friendship": 80})
    interests = tracker.get_romantic_interests(1, threshold=20)
    assert len(interests) == 1
    assert interests[0] == (2, 50.0)


def test_tracker_get_friends():
    tracker = RelationshipTracker()
    tracker.update(1, 2, {"friendship": 60})
    tracker.update(1, 3, {"friendship": -30})
    tracker.update(1, 4, {"friendship": 40})
    friends = tracker.get_friends(1, threshold=50)
    assert friends == [(2, 60.0)]


def test_tracker_get_rivals():
    tracker = RelationshipTracker()
    tracker.update(1, 2, {"friendship": -60})
    tracker.update(1, 3, {"friendship": 30})
    rivals = tracker.get_rivals(1, threshold=-50)
    assert rivals == [(2, -60.0)]


# ---------------------------------------------------------------------------
# Fights
# ---------------------------------------------------------------------------

def test_fight_management():
    tracker = RelationshipTracker()
    fight = Fight(participants=(1, 2), cause="음식 싸움")
    tracker.add_fight(fight)
    assert len(tracker.get_fights()) == 1
    resolved = tracker.resolve_fight((1, 2))
    assert resolved
    assert len(tracker.get_fights()) == 0


# ---------------------------------------------------------------------------
# Slots & Tags
# ---------------------------------------------------------------------------

def test_slots_recompute():
    tracker = RelationshipTracker()
    tracker.update(1, 2, {"friendship": 75})
    tracker.update(2, 1, {"friendship": 75})
    tracker.update(1, 3, {"friendship": -55})
    tracker.update(3, 1, {"friendship": -55})
    tracker.recompute_slots(1)
    slots = tracker.get_slots(1)
    assert slots.best_friend == 2
    assert slots.enemy == 3


def test_ex_lover_tags():
    tracker = RelationshipTracker()
    tracker.add_ex_lover_tag(1, target=3, reason=BreakupReason.FIGHT, day=42)
    tags = tracker.get_ex_lover_tags(1)
    assert len(tags) == 1
    assert tags[0].target == 3


# ---------------------------------------------------------------------------
# Triangles & jealousy (uses friendship instead of jealousy field)
# ---------------------------------------------------------------------------

def test_triangle_model():
    t = Triangle(jealous=1, target=2, rival=3, romance_level=60.0)
    assert t.jealous == 1
    assert t.rival == 3


def test_detect_triangles_finds_basic_triangle():
    tracker = RelationshipTracker()
    tracker.update(1, 2, {"romance": 50})
    tracker.update(2, 3, {"friendship": 60})
    triangles = detect_triangles(tracker)
    assert len(triangles) == 1
    assert triangles[0].jealous == 1
    assert triangles[0].target == 2
    assert triangles[0].rival == 3


def test_detect_triangles_no_triangle_without_romance():
    tracker = RelationshipTracker()
    tracker.update(1, 2, {"friendship": 80})
    tracker.update(2, 3, {"friendship": 60})
    triangles = detect_triangles(tracker)
    assert len(triangles) == 0


def test_detect_triangles_mutual_jealousy():
    tracker = RelationshipTracker()
    tracker.update(1, 2, {"romance": 50})
    tracker.update(3, 2, {"romance": 40})
    tracker.update(2, 1, {"friendship": 60})
    tracker.update(2, 3, {"friendship": 60})
    triangles = detect_triangles(tracker)
    assert len(triangles) == 2
    jealous_ids = {t.jealous for t in triangles}
    assert jealous_ids == {1, 3}


def test_apply_jealousy_updates():
    tracker = RelationshipTracker()
    tracker.update(1, 2, {"romance": 50})
    tracker.update(2, 3, {"friendship": 60})
    triangles = detect_triangles(tracker)
    apply_jealousy(tracker, triangles)
    # jealousy now affects friendship negatively
    rel_13 = tracker.get(1, 3)
    assert rel_13.friendship < 0


# ---------------------------------------------------------------------------
# Compatibility
# ---------------------------------------------------------------------------

def test_calculate_compatibility():
    score = calculate_compatibility(
        personality_a="nagomi_softie",
        personality_b="nori_charmer",
        blood_a="O", blood_b="A",
        zodiac_a="사자자리", zodiac_b="양자리",
    )
    assert 0.0 <= score <= 1.0
    assert score > 0.6


def test_compatibility_low_pair():
    score = calculate_compatibility(
        personality_a="nagomi_softie",
        personality_b="dry_busybee",
        blood_a="A", blood_b="B",
        zodiac_a="게자리", zodiac_b="양자리",
    )
    assert 0.0 <= score <= 1.0
    assert score < 0.5
