from tomodachai.memory import SocialEvent, MemoryStore


def test_social_event_creation():
    event = SocialEvent(
        tick=1,
        participants=["a", "b"],
        event_type="conversation",
        summary="공원에서 만나 날씨 이야기를 했다",
        emotional_impact={"a": 0.5, "b": 0.3},
    )
    assert event.tick == 1
    assert len(event.participants) == 2


def test_memory_store_add_and_get():
    store = MemoryStore()
    event = SocialEvent(
        tick=1,
        participants=["a", "b"],
        event_type="conversation",
        summary="인사를 나눴다",
        emotional_impact={"a": 0.2, "b": 0.1},
    )
    store.add_event(event)
    events = store.get_events_for("a")
    assert len(events) == 1
    assert events[0].summary == "인사를 나눴다"


def test_memory_store_get_for_participant():
    store = MemoryStore()
    store.add_event(SocialEvent(
        tick=1, participants=["a", "b"],
        event_type="conversation", summary="a와 b 대화",
        emotional_impact={},
    ))
    store.add_event(SocialEvent(
        tick=2, participants=["b", "c"],
        event_type="conversation", summary="b와 c 대화",
        emotional_impact={},
    ))
    assert len(store.get_events_for("a")) == 1
    assert len(store.get_events_for("b")) == 2
    assert len(store.get_events_for("c")) == 1


def test_memory_store_get_between():
    store = MemoryStore()
    store.add_event(SocialEvent(
        tick=1, participants=["a", "b"],
        event_type="conversation", summary="a-b 대화",
        emotional_impact={},
    ))
    store.add_event(SocialEvent(
        tick=2, participants=["a", "c"],
        event_type="conversation", summary="a-c 대화",
        emotional_impact={},
    ))
    between = store.get_events_between("a", "b")
    assert len(between) == 1
    assert between[0].summary == "a-b 대화"


def test_memory_store_limit():
    store = MemoryStore()
    for i in range(20):
        store.add_event(SocialEvent(
            tick=i, participants=["a", "b"],
            event_type="conversation", summary=f"대화 {i}",
            emotional_impact={},
        ))
    events = store.get_events_for("a", limit=5)
    assert len(events) == 5
    assert events[0].tick == 19  # most recent first


def test_memory_store_recent_first():
    store = MemoryStore()
    store.add_event(SocialEvent(
        tick=1, participants=["a"], event_type="solo",
        summary="첫 번째", emotional_impact={},
    ))
    store.add_event(SocialEvent(
        tick=5, participants=["a"], event_type="solo",
        summary="두 번째", emotional_impact={},
    ))
    events = store.get_events_for("a")
    assert events[0].summary == "두 번째"
