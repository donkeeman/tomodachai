"""GameState 이벤트 로그 (seq 단조 증가 + since 증분)."""

from tomodachai.game_state import GameState


def test_record_events_assigns_monotonic_seq():
    gs = GameState()
    gs.record_events([{"type": "conversation"}, {"type": "fight"}])
    log = gs.events_since(0)
    assert [e["seq"] for e in log] == [1, 2]
    assert log[0]["raw"]["type"] == "conversation"


def test_events_since_filters_by_seq():
    gs = GameState()
    gs.record_events([{"type": "a"}])
    gs.record_events([{"type": "b"}])
    assert [e["raw"]["type"] for e in gs.events_since(1)] == ["b"]
    assert gs.events_since(2) == []


def test_record_events_tags_day_and_clock():
    gs = GameState()
    gs.day_count = 3
    gs.record_events([{"type": "x"}])
    entry = gs.events_since(0)[0]
    assert entry["day"] == 3
    assert isinstance(entry["clock"], str) and ":" in entry["clock"]


def test_event_log_capped_at_300():
    gs = GameState()
    gs.record_events([{"type": "e"} for _ in range(350)])
    log = gs.events_since(0)
    assert len(log) == 300
    # 가장 오래된 50개가 밀려나 seq는 51부터 시작
    assert log[0]["seq"] == 51


def test_reset_world_clears_log_and_seq():
    gs = GameState()
    gs.record_events([{"type": "e"}])
    gs.reset_world()
    assert gs.events_since(0) == []
    gs.record_events([{"type": "e2"}])
    assert gs.events_since(0)[0]["seq"] == 1
