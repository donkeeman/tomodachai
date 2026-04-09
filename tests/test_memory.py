from tomodachai.memory import SocialEvent, MemoryStore


def test_social_event_creation():
    event = SocialEvent(
        id=1,
        type="conversation",
        participants=[1, 2],
        day=15,
        location="living_room",
        time="14:32",
    )
    assert event.id == 1
    assert event.day == 15
    assert len(event.participants) == 2
    assert event.location == "living_room"
    assert event.time == "14:32"
    assert event.reason is None
    assert event.result is None


def test_social_event_optional_fields():
    event = SocialEvent(
        id=2,
        type="breakup",
        participants=[1, 3],
        day=42,
        reason="fight",
    )
    assert event.reason == "fight"
    assert event.time is None
    assert event.location is None
    assert event.result is None


def test_social_event_confession():
    event = SocialEvent(
        id=3,
        type="confession",
        participants=[1, 4],
        day=50,
        result="rejected",
    )
    assert event.result == "rejected"


def test_memory_store_add_and_get():
    store = MemoryStore()
    event = SocialEvent(
        id=1,
        type="conversation",
        participants=[1, 2],
        day=1,
    )
    store.add_event(event)
    events = store.get_events_for(1)
    assert len(events) == 1
    assert events[0].type == "conversation"


def test_memory_store_get_for_participant():
    store = MemoryStore()
    store.add_event(SocialEvent(id=1, type="conversation", participants=[1, 2], day=1))
    store.add_event(SocialEvent(id=2, type="conversation", participants=[2, 3], day=2))
    assert len(store.get_events_for(1)) == 1
    assert len(store.get_events_for(2)) == 2
    assert len(store.get_events_for(3)) == 1


def test_memory_store_get_between():
    store = MemoryStore()
    store.add_event(SocialEvent(id=1, type="conversation", participants=[1, 2], day=1))
    store.add_event(SocialEvent(id=2, type="conversation", participants=[1, 3], day=2))
    between = store.get_events_between(1, 2)
    assert len(between) == 1
    assert between[0].id == 1


def test_memory_store_limit():
    store = MemoryStore()
    for i in range(20):
        store.add_event(SocialEvent(id=i + 1, type="conversation", participants=[1, 2], day=i))
    events = store.get_events_for(1, limit=5)
    assert len(events) == 5
    assert events[0].day == 19  # most recent first


def test_memory_store_recent_first():
    store = MemoryStore()
    store.add_event(SocialEvent(id=1, type="solo", participants=[1], day=1))
    store.add_event(SocialEvent(id=2, type="solo", participants=[1], day=5))
    events = store.get_events_for(1)
    assert events[0].day == 5


def test_memory_store_auto_increment_id():
    store = MemoryStore()
    # id=0 triggers auto-assign
    e1 = SocialEvent(id=0, type="conversation", participants=[1, 2], day=1)
    store.add_event(e1)
    stored = store.get_events_for(1)
    assert stored[0].id == 1


def test_memory_store_str_char_id_compat():
    # backward compat: passing str IDs should still work
    store = MemoryStore()
    store.add_event(SocialEvent(id=1, type="conversation", participants=[1, 2], day=1))
    events = store.get_events_for("1")
    assert len(events) == 1
    between = store.get_events_between("1", "2")
    assert len(between) == 1
