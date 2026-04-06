from tomodachai.relationship import (
    Fight,
    Relationship,
    RelationshipEvent,
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
    assert r.tension == 0.0
    assert r.jealousy == 0.0
    assert r.stage == RelationshipStage.STRANGER


def test_apply_deltas():
    r = Relationship(friendship=50.0)
    r.apply_deltas({"friendship": 10, "tension": 5})
    assert r.friendship == 60.0
    assert r.tension == 5.0


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
    """연애 전환은 allow_romantic_transition 없으면 안 됨 (가드레일)."""
    r = Relationship(friendship=50.0, romance=70.0, stage=RelationshipStage.FRIEND)
    changed = r.check_stage_transition(allow_romantic_transition=False)
    assert not changed or r.stage != RelationshipStage.LOVER


def test_stage_romantic_with_flag():
    r = Relationship(friendship=50.0, romance=70.0, stage=RelationshipStage.FRIEND)
    changed = r.check_stage_transition(allow_romantic_transition=True)
    assert changed
    assert r.stage == RelationshipStage.LOVER


def test_stage_demotion():
    r = Relationship(friendship=5.0, stage=RelationshipStage.FRIEND)
    changed = r.check_stage_transition()
    assert changed
    assert r.stage == RelationshipStage.STRANGER  # friendship=5 < ACQUAINTANCE(10)


def test_stage_demotion_to_acquaintance():
    r = Relationship(friendship=15.0, stage=RelationshipStage.FRIEND)
    changed = r.check_stage_transition()
    assert changed
    assert r.stage == RelationshipStage.ACQUAINTANCE


def test_status_text():
    r = Relationship(stage=RelationshipStage.FRIEND)
    assert r.get_status_text() == "친구"


def test_friendship_text():
    r = Relationship(friendship=95.0)
    assert r.get_friendship_text() == "엄청 좋아함"

    r2 = Relationship(friendship=-70.0)
    assert r2.get_friendship_text() == "매우 싫어함"


# ---------------------------------------------------------------------------
# Event log & reconciliation
# ---------------------------------------------------------------------------

def test_can_reconcile():
    r = Relationship()
    assert not r.can_reconcile()
    r.event_log.append(RelationshipEvent(day=10, event_type="breakup", summary="이별"))
    assert r.can_reconcile()


# ---------------------------------------------------------------------------
# Tracker basics
# ---------------------------------------------------------------------------

def test_tracker_get_creates_default():
    tracker = RelationshipTracker()
    rel = tracker.get("a", "b")
    assert rel.friendship == 0.0


def test_tracker_is_directional():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"friendship": 10})
    assert tracker.get("a", "b").friendship == 10.0
    assert tracker.get("b", "a").friendship == 0.0


def test_tracker_get_romantic_interests():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"romance": 50})
    tracker.update("a", "c", {"romance": 10})
    tracker.update("a", "d", {"friendship": 80})
    interests = tracker.get_romantic_interests("a", threshold=20)
    assert len(interests) == 1
    assert interests[0] == ("b", 50.0)


def test_tracker_get_friends():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"friendship": 60})
    tracker.update("a", "c", {"friendship": -30})
    tracker.update("a", "d", {"friendship": 40})
    friends = tracker.get_friends("a", threshold=50)
    assert friends == [("b", 60.0)]


def test_tracker_get_rivals():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"friendship": -60})
    tracker.update("a", "c", {"friendship": 30})
    rivals = tracker.get_rivals("a", threshold=-50)
    assert rivals == [("b", -60.0)]


# ---------------------------------------------------------------------------
# Fights
# ---------------------------------------------------------------------------

def test_fight_management():
    tracker = RelationshipTracker()
    fight = Fight(participants=("a", "b"), cause="음식 싸움")
    tracker.add_fight(fight)
    assert len(tracker.get_fights()) == 1
    resolved = tracker.resolve_fight(("a", "b"))
    assert resolved
    assert len(tracker.get_fights()) == 0


# ---------------------------------------------------------------------------
# Triangles & jealousy
# ---------------------------------------------------------------------------

def test_triangle_model():
    t = Triangle(jealous="a", target="b", rival="c", romance_level=60.0)
    assert t.jealous == "a"
    assert t.rival == "c"


def test_detect_triangles_finds_basic_triangle():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"romance": 50})
    tracker.update("b", "c", {"friendship": 60})
    triangles = detect_triangles(tracker)
    assert len(triangles) == 1
    assert triangles[0].jealous == "a"
    assert triangles[0].target == "b"
    assert triangles[0].rival == "c"


def test_detect_triangles_no_triangle_without_romance():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"friendship": 80})
    tracker.update("b", "c", {"friendship": 60})
    triangles = detect_triangles(tracker)
    assert len(triangles) == 0


def test_detect_triangles_mutual_jealousy():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"romance": 50})
    tracker.update("c", "b", {"romance": 40})
    tracker.update("b", "a", {"friendship": 60})
    tracker.update("b", "c", {"friendship": 60})
    triangles = detect_triangles(tracker)
    assert len(triangles) == 2
    jealous_ids = {t.jealous for t in triangles}
    assert jealous_ids == {"a", "c"}


def test_apply_jealousy_updates():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"romance": 50})
    tracker.update("b", "c", {"friendship": 60})
    triangles = detect_triangles(tracker)
    apply_jealousy(tracker, triangles)
    rel_ac = tracker.get("a", "c")
    assert rel_ac.jealousy > 0
    rel_ab = tracker.get("a", "b")
    assert rel_ab.tension > 0


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
    # 나고미+노리 = good pair, O+A = high, 불+불 = same element
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
