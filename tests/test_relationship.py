from tomodachai.relationship import Relationship, RelationshipTracker


def test_relationship_defaults():
    r = Relationship()
    assert r.friendship == 0.0
    assert r.romance == 0.0
    assert r.tension == 0.0
    assert r.jealousy == 0.0


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
