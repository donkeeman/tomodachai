# Snapshot 읽기경로 토대 Implementation Plan (Plan 1/N)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Babylon 프론트가 `GET /api/snapshot`으로 FastAPI 실데이터(캐릭터 이동·이벤트·시간)를 받아 3D 마을을 렌더하게 만든다.

**Architecture:** 기존 프론트 `Snapshot` 계약을 그대로 FastAPI에 구현한다. 모델 보정(Mood.label·Relationship.spark·이벤트 로그 seq)을 먼저 깔고, 무상태 집계기 `api/snapshot.py`가 GameState를 읽어 계약 DTO로 변환한다. rankings/photos/dishes/bubbles/foods는 이번 단계에서 **빈 값**으로 두고(후속 Plan), 프론트는 베이스 URL만 바꾸고 미구현 버튼은 게이팅한다.

**Tech Stack:** Python 3.11, FastAPI, pydantic, pytest. 프론트: Svelte/Vite/TS (Babylon).

**범위 밖 (후속 Plan 2+):** feed / give·도구 / 고백 말풍선 / rankings 계산. 본 spec: `docs/superpowers/specs/2026-06-15-babylon-fastapi-connection-design.md`.

---

## 파일 구조

| 파일 | 역할 | 신규/수정 |
|---|---|---|
| `src/tomodachai/character.py` | `Mood.label()` 추가 | 수정 |
| `src/tomodachai/relationship.py` | `Relationship.spark` 필드 추가 | 수정 |
| `src/tomodachai/game_state.py` | 이벤트 로그(seq) + `record_events`/`events_since` + `reset_world` | 수정 |
| `src/tomodachai/api/snapshot.py` | 무상태 집계기 `build_snapshot` + 헬퍼 | 신규 |
| `src/tomodachai/api/snapshot_routes.py` | `GET /snapshot`, `POST /save`, `POST /reset` | 신규 |
| `src/tomodachai/server.py` | snapshot 라우터 등록 | 수정 |
| `tests/test_snapshot.py` | 집계기 + 라우터 테스트 | 신규 |
| `tests/test_event_log.py` | 이벤트 로그 테스트 | 신규 |
| `prototype/web/src/lib/api.ts` | 베이스 URL → FastAPI | 수정 |
| `prototype/web/src/lib/store.ts` 또는 UI | 미구현 버튼 게이팅 | 수정 |

---

## Task 1: `Mood.label()` — 3축 감정 → 한글 라벨

**Files:**
- Modify: `src/tomodachai/character.py` (class `Mood`, 현재 line 183-187)
- Test: `tests/test_character.py` (기존 파일에 추가)

- [ ] **Step 1: Write the failing test**

`tests/test_character.py` 끝에 추가:

```python
from tomodachai.character import Mood


def test_mood_label_stressed():
    assert Mood(happiness=5, energy=6, stress=8).label() == "짜증남"
    assert Mood(happiness=5, energy=3, stress=8).label() == "지침"


def test_mood_label_happy():
    assert Mood(happiness=8, energy=7, stress=2).label() == "신남"
    assert Mood(happiness=8, energy=4, stress=2).label() == "흐뭇함"


def test_mood_label_sad():
    assert Mood(happiness=2, energy=3, stress=2).label() == "우울함"
    assert Mood(happiness=2, energy=6, stress=2).label() == "심술남"


def test_mood_label_tired_and_calm():
    assert Mood(happiness=5, energy=2, stress=2).label() == "나른함"
    assert Mood(happiness=5, energy=5, stress=2).label() == "평온함"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_character.py -k mood_label -v`
Expected: FAIL — `AttributeError: 'Mood' object has no attribute 'label'`

- [ ] **Step 3: Write minimal implementation**

`src/tomodachai/character.py`의 `class Mood` 안 (필드 선언 아래)에 메서드 추가:

```python
    def label(self) -> str:
        """3축 조합을 한 단어 한글 감정으로 (prototype/game Mood.label 규칙)."""
        if self.stress >= 7:
            return "짜증남" if self.energy >= 5 else "지침"
        if self.happiness >= 7:
            return "신남" if self.energy >= 6 else "흐뭇함"
        if self.happiness <= 3:
            return "우울함" if self.energy <= 4 else "심술남"
        if self.energy <= 3:
            return "나른함"
        return "평온함"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_character.py -k mood_label -v`
Expected: PASS (8 assertions across 4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/character.py tests/test_character.py
git commit -m "feat: Mood.label() 3축→한글 감정 라벨 (prototype 규칙)"
```

---

## Task 2: `Relationship.spark` 필드 추가

**Files:**
- Modify: `src/tomodachai/relationship.py` (class `Relationship`, 현재 line 81-83)
- Test: `tests/test_relationship.py` (기존 파일에 추가)

- [ ] **Step 1: Write the failing test**

`tests/test_relationship.py` 끝에 추가:

```python
from tomodachai.relationship import Relationship


def test_relationship_spark_defaults_false():
    rel = Relationship()
    assert rel.spark is False


def test_relationship_spark_settable():
    rel = Relationship(spark=True)
    assert rel.spark is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_relationship.py -k spark -v`
Expected: FAIL — `Relationship` rejects `spark` kwarg / attribute missing

- [ ] **Step 3: Write minimal implementation**

`src/tomodachai/relationship.py`의 `class Relationship`에 필드 추가 (friendship/romance 선언 바로 아래):

```python
    spark: bool = False  # 반함(짝사랑 점화) 플래그. 연인 성사/문맥 반함 시 True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_relationship.py -k spark -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/relationship.py tests/test_relationship.py
git commit -m "feat: Relationship.spark 필드 (반함 플래그)"
```

---

## Task 3: GameState 이벤트 로그 (seq) + reset_world

**Files:**
- Modify: `src/tomodachai/game_state.py` (`__init__` 끝, `step()` 메서드 line 164-169)
- Test: `tests/test_event_log.py` (신규)

이벤트 로그는 폴링 `since` 증분 페치의 기준이다. `step()`이 내는 raw 이벤트마다 단조 증가
`seq`와 기록 시점 `day`/`clock`을 붙여 ring buffer(최대 300)에 저장한다.

- [ ] **Step 1: Write the failing test**

`tests/test_event_log.py` (신규):

```python
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
    # seq도 0으로 리셋되어 다음 기록이 1부터
    gs.record_events([{"type": "e2"}])
    assert gs.events_since(0)[0]["seq"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_event_log.py -v`
Expected: FAIL — `GameState` has no `record_events`/`events_since`/`reset_world`

- [ ] **Step 3: Write minimal implementation**

`src/tomodachai/game_state.py` `__init__` 끝(line 68 `self._clock = ...` 아래)에 추가:

```python
        # 실시간 이벤트 로그 (snapshot since 증분 페치 기준)
        self._event_seq: int = 0
        self._event_log: list[dict] = []
        self._EVENT_LOG_CAP = 300
```

같은 파일에 메서드 추가 (`step()` 위, real-time interface 섹션):

```python
    def _clock_str(self) -> str:
        now = self._clock.now()
        hour = self._clock.get_game_hour(now)
        return f"{hour:02d}:{now.minute:02d}"

    def record_events(self, raw_events: list[dict]) -> None:
        """raw 이벤트들에 단조 seq + 기록 시점 day/clock을 붙여 로그에 적재."""
        clock = self._clock_str()
        for raw in raw_events:
            self._event_seq += 1
            self._event_log.append(
                {"seq": self._event_seq, "day": self.day_count, "clock": clock, "raw": raw}
            )
        if len(self._event_log) > self._EVENT_LOG_CAP:
            self._event_log = self._event_log[-self._EVENT_LOG_CAP :]

    def events_since(self, since: int) -> list[dict]:
        """seq > since 인 로그 항목만 (시간순)."""
        return [e for e in self._event_log if e["seq"] > since]

    def reset_world(self) -> None:
        """새 마을 시작 준비: 시뮬/이벤트로그/seq 초기화 (캐릭터·config는 호출측 책임)."""
        self._simulation = None
        self._event_seq = 0
        self._event_log = []
        self.day_count = 0
```

그리고 기존 `step()` (line 164-169)를 수정하여 로그에 적재:

```python
    def step(self) -> list[dict]:
        """실시간 단일 이벤트 스텝. 서버 백그라운드 태스크에서 호출."""
        if not self.characters:
            return []
        self.touch()
        events = self.simulation.step()
        self.record_events(events)
        return events
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_event_log.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run full suite (회귀 확인 — step() 변경)**

Run: `pytest tests/ -q`
Expected: 기존 + 신규 전부 PASS

- [ ] **Step 6: Commit**

```bash
git add src/tomodachai/game_state.py tests/test_event_log.py
git commit -m "feat: GameState 이벤트 로그(seq 증분) + reset_world"
```

---

## Task 4: snapshot 집계기 — 캐릭터 매핑

**Files:**
- Create: `src/tomodachai/api/snapshot.py`
- Test: `tests/test_snapshot.py` (신규)

캐릭터 1명을 프론트 `Character` DTO(dict)로 변환. mood 라벨, gender M/F, 슬롯(id→이름),
crushes(spark), food_eaten. friends/dex는 이번 단계 최소 구현(friends는 상태텍스트, dex는 빈 리스트).

- [ ] **Step 1: Write the failing test**

`tests/test_snapshot.py` (신규):

```python
"""snapshot 집계기 — 계약 DTO 변환."""

import pytest

from tomodachai.character import (
    Character, CharacterState, Customizable, Profile, SpeechHabits,
)
from tomodachai.config import AppConfig, LLMConfig, LocationConfig, SimulationConfig
from tomodachai.game_state import GameState


def _gs_with_two():
    cfg = AppConfig(
        llm=LLMConfig(provider="litellm", model="ollama/gemma3", temperature=0.8),
        simulation=SimulationConfig(),
        locations=[LocationConfig(id="fountain", name="분수대")],
    )
    gs = GameState(config=cfg)
    for cid, name, gender in [(1, "민수", "남성"), (2, "지은", "여성")]:
        gs.add_character(
            Character(
                id=cid,
                personality_code="outgoing_dynamo",
                profile=Profile(name=name, birthday="03-15", blood_type="B", gender=gender),
                state=CharacterState(current_location="분수대"),
                customizable=Customizable(speech_habits=SpeechHabits(normal="~")),
            )
        )
    return gs


def test_char_dict_basic_fields():
    from tomodachai.api.snapshot import char_dict

    gs = _gs_with_two()
    minsu = gs.get_character(1)
    minsu.state.mood.happiness = 8
    minsu.state.mood.energy = 7
    minsu.state.mood.stress = 2

    d = char_dict(gs, minsu)
    assert d["id"] == 1
    assert d["name"] == "민수"
    assert d["gender"] == "M"
    assert d["mood"] == "신남"
    assert d["hunger"] == 0
    assert d["satisfaction"] == 50
    assert d["lover"] is None
    assert d["best_friend"] is None
    assert d["enemy"] is None
    assert d["crushes"] == []
    assert isinstance(d["friends"], list)
    assert isinstance(d["dex"], list)
    assert isinstance(d["food_eaten"], list)


def test_char_dict_gender_female():
    from tomodachai.api.snapshot import char_dict

    gs = _gs_with_two()
    assert char_dict(gs, gs.get_character(2))["gender"] == "F"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_snapshot.py -v`
Expected: FAIL — `ModuleNotFoundError: tomodachai.api.snapshot`

- [ ] **Step 3: Write minimal implementation**

`src/tomodachai/api/snapshot.py` (신규):

```python
"""Babylon 프론트 계약(Snapshot) 집계기.

prototype/web_server.py snapshot()의 직렬화 규칙을 src/tomodachai 모델 위에서 재현한다.
무상태 — GameState를 읽기만 한다.
"""

from __future__ import annotations

from tomodachai.character import Character
from tomodachai.game_state import GameState


def _gender(text: str) -> str:
    """자유텍스트 성별 → 'M'/'F' (기타는 'M' 폴백)."""
    return "F" if "여" in text else "M"


def _int_id(char_id) -> int:
    return char_id if isinstance(char_id, int) else abs(hash(char_id)) % 100000


def _name_of(gs: GameState, char_id: int | None) -> str | None:
    if char_id is None:
        return None
    c = gs.get_character(char_id)
    return c.name if c else None


def char_dict(gs: GameState, char: Character) -> dict:
    """캐릭터 1명을 프론트 Character DTO(dict)로 변환."""
    int_id = _int_id(char.id)
    slots = gs.relationships.get_slots(int_id)

    # crushes: spark==True AND 현재 연인이 아닌 상대
    crushes: list[str] = []
    for other in gs.characters:
        oid = _int_id(other.id)
        if oid == int_id:
            continue
        rel = gs.relationships.get(int_id, oid)
        if rel.spark and slots.lover != oid:
            crushes.append(other.name)

    # friends: 만나본 상대를 우정 내림차순 top5, 라벨은 상태텍스트 (수치 비노출)
    met = []
    for other in gs.characters:
        oid = _int_id(other.id)
        if oid == int_id:
            continue
        rel = gs.relationships.get(int_id, oid)
        met.append((rel.friendship, other.name, rel.get_status_text()))
    met.sort(key=lambda t: t[0], reverse=True)
    friends = [{"name": n, "label": lbl} for _f, n, lbl in met[:5]]

    loc_id = gs.location_manager.get_character_location(int_id) or char.state.current_location

    return {
        "id": int_id,
        "name": char.name,
        "gender": _gender(char.gender),
        "location": loc_id,
        "mood": char.state.mood.label(),
        "hunger": round(char.state.hunger),
        "satisfaction": round(char.state.satisfaction),
        "lover": _name_of(gs, slots.lover),
        "best_friend": _name_of(gs, slots.best_friend),
        "enemy": _name_of(gs, slots.enemy),
        "crushes": crushes,
        "food_eaten": list(char.preferences.food_eaten),
        "friends": friends,
        "dex": [],  # Plan 2(feed)에서 채움
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_snapshot.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/api/snapshot.py tests/test_snapshot.py
git commit -m "feat: snapshot 집계기 캐릭터 매핑 (mood라벨/성별/슬롯/crush)"
```

---

## Task 5: snapshot 집계기 — 이벤트 매핑 + 전체 조립

**Files:**
- Modify: `src/tomodachai/api/snapshot.py` (`map_event`, `build_snapshot` 추가)
- Test: `tests/test_snapshot.py` (추가)

- [ ] **Step 1: Write the failing test**

`tests/test_snapshot.py`에 추가:

```python
def test_map_event_conversation_shape():
    from tomodachai.api.snapshot import map_event

    gs = _gs_with_two()
    entry = {
        "seq": 1, "day": 2, "clock": "09:30",
        "raw": {"type": "conversation", "participants": [1, 2],
                "location": "분수대", "reason": "우연히 만남"},
    }
    ev = map_event(gs, entry)
    assert ev["seq"] == 1
    assert ev["day"] == 2
    assert ev["clock"] == "09:30"
    assert isinstance(ev["dialogue"], list)
    assert isinstance(ev["messages"], list)
    assert ev["major"] is False


def test_map_event_fight_is_major():
    from tomodachai.api.snapshot import map_event

    gs = _gs_with_two()
    entry = {"seq": 5, "day": 1, "clock": "10:00",
             "raw": {"type": "fight", "participants": [1, 2]}}
    assert map_event(gs, entry)["major"] is True


def test_build_snapshot_contract_keys():
    from tomodachai.api.snapshot import build_snapshot

    gs = _gs_with_two()
    snap = build_snapshot(gs, since=0)
    # 프론트 types.ts Snapshot 필드 전부 존재
    for key in ("village", "provider", "day", "clock", "minutes", "seq",
                "locations", "foods", "rankings", "asleep", "realtime",
                "photos", "dishes", "characters", "events", "bubbles"):
        assert key in snap, f"missing {key}"
    assert len(snap["characters"]) == 2
    assert snap["locations"]["fountain"] == "분수대"
    # 이번 단계 빈 값 스텁
    assert snap["rankings"] == {"best_couple": [], "popular_m": [],
                                "popular_f": [], "fighters": []}
    assert snap["photos"] == [] and snap["dishes"] == [] and snap["bubbles"] == []


def test_build_snapshot_events_since():
    from tomodachai.api.snapshot import build_snapshot

    gs = _gs_with_two()
    gs.record_events([{"type": "conversation", "participants": [1, 2]}])
    snap = build_snapshot(gs, since=0)
    assert snap["seq"] == 1
    assert len(snap["events"]) == 1
    assert build_snapshot(gs, since=1)["events"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_snapshot.py -k "map_event or build_snapshot" -v`
Expected: FAIL — `map_event`/`build_snapshot` 미정의

- [ ] **Step 3: Write minimal implementation**

`src/tomodachai/api/snapshot.py`에 추가:

```python
# 메이저(자동 일시정지/강조) 이벤트 타입
_MAJOR_TYPES = {"fight", "confession", "breakup", "new_lover", "new_best_friend", "spark"}

# 23:00(-5분)~07:00 수면창
_SLEEP_START_MIN = 23 * 60 - 5
_WAKE_MIN = 7 * 60


def map_event(gs: GameState, entry: dict) -> dict:
    """이벤트 로그 항목 → 프론트 EventItem dict."""
    raw = entry["raw"]
    etype = raw.get("type", "")

    dialogue: list[list[str]] = []
    result = raw.get("result")
    if etype == "conversation" and result is not None and not isinstance(result, str):
        dialogue = [[ln.speaker, ln.text] for ln in getattr(result, "dialogue", [])]

    summary = None
    if isinstance(result, str):
        summary = result
    elif result is not None and getattr(result, "summary", None):
        summary = result.summary

    scene = summary or raw.get("reason") or ""
    return {
        "seq": entry["seq"],
        "day": entry["day"],
        "clock": entry["clock"],
        "scene": scene,
        "dialogue": dialogue,
        "messages": [],
        "major": etype in _MAJOR_TYPES,
    }


def _clock_and_minutes(gs: GameState) -> tuple[str, int]:
    now = gs._clock.now()
    hour = gs._clock.get_game_hour(now)
    return f"{hour:02d}:{now.minute:02d}", hour * 60 + now.minute


def build_snapshot(gs: GameState, since: int) -> dict:
    """프론트 계약 Snapshot 전체 조립."""
    clock, minutes = _clock_and_minutes(gs)
    locations = {e["id"]: e["name"] for e in gs.location_manager.snapshot()}
    return {
        "village": gs.island_name,
        "provider": gs.config.llm.provider,
        "day": gs.day_count,
        "clock": clock,
        "minutes": minutes,
        "seq": gs._event_seq,
        "locations": locations,
        "foods": [],  # Plan 2(feed)에서 채움
        "rankings": {"best_couple": [], "popular_m": [], "popular_f": [], "fighters": []},
        "asleep": minutes >= _SLEEP_START_MIN or minutes < _WAKE_MIN,
        "realtime": True,
        "photos": [],   # Plan 2(give)에서 채움
        "dishes": [],   # Plan 2(give)에서 채움
        "characters": [char_dict(gs, c) for c in gs.characters],
        "events": [map_event(gs, e) for e in gs.events_since(since)],
        "bubbles": [],  # Plan 2(bubble)에서 채움
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_snapshot.py -v`
Expected: PASS (6 tests 누적)

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/api/snapshot.py tests/test_snapshot.py
git commit -m "feat: snapshot 이벤트 매핑 + 전체 Snapshot 조립"
```

---

## Task 6: compat 라우터 — GET /snapshot, POST /save, POST /reset

**Files:**
- Create: `src/tomodachai/api/snapshot_routes.py`
- Modify: `src/tomodachai/server.py` (라우터 등록)
- Test: `tests/test_snapshot.py` (API 테스트 추가)

- [ ] **Step 1: Write the failing test**

`tests/test_snapshot.py`에 추가:

```python
@pytest.fixture
def client_snap():
    from fastapi.testclient import TestClient
    from tomodachai.api.routes import set_game_state
    from tomodachai.server import create_app

    gs = _gs_with_two()
    app = create_app()
    set_game_state(gs)
    return TestClient(app), gs


def test_api_snapshot_returns_contract(client_snap):
    client, _gs = client_snap
    resp = client.get("/api/snapshot?since=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["characters"]) == 2
    assert "events" in data and "seq" in data


def test_api_reset_clears(client_snap):
    client, gs = client_snap
    gs.record_events([{"type": "x"}])
    resp = client.post("/api/reset", json={})
    assert resp.status_code == 200
    assert client.get("/api/snapshot?since=0").json()["seq"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_snapshot.py -k "api_snapshot or api_reset" -v`
Expected: FAIL — 404 (라우트 없음)

- [ ] **Step 3: Write minimal implementation**

`src/tomodachai/api/snapshot_routes.py` (신규):

```python
"""Babylon 프론트 계약 라우터 (snapshot 폴링 + save/reset).

prototype/web_server.py의 HTTP 계약을 FastAPI로 옮긴 것.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tomodachai.api.routes import _gs, _save_manager
from tomodachai.api.snapshot import build_snapshot

compat_router = APIRouter()


@compat_router.get("/snapshot")
def get_snapshot(since: int = 0):
    return build_snapshot(_gs(), since)


@compat_router.post("/save")
def save_snapshot():
    gs = _gs()
    try:
        _save_manager.save_temp(gs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"저장 실패: {e}")
    return {"message": f"💾 저장 완료 (Day {gs.day_count})"}


@compat_router.post("/reset")
def reset_world():
    gs = _gs()
    gs.characters.clear()
    gs.reset_world()
    return {"message": "🔄 새 마을이 시작되었습니다"}
```

> 주의: `_save_manager`는 `routes.py`의 모듈 전역. import 시점 값이 아니라 호출 시점 값을
> 쓰도록, save 핸들러 안에서 `from tomodachai.api import routes; routes._save_manager` 형태가
> 더 안전하다. 단순화를 위해 본 단계는 위 import로 두되, 교체가 필요하면 후속에서 조정.

`src/tomodachai/server.py`의 `create_app` 안, `app.include_router(router, prefix="/api")`
(line 110) 바로 아래에 추가:

```python
    from tomodachai.api.snapshot_routes import compat_router
    app.include_router(compat_router, prefix="/api")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_snapshot.py -v`
Expected: PASS (8 tests 누적)

- [ ] **Step 5: Run full suite**

Run: `pytest tests/ -q`
Expected: 전부 PASS

- [ ] **Step 6: Commit**

```bash
git add src/tomodachai/api/snapshot_routes.py src/tomodachai/server.py tests/test_snapshot.py
git commit -m "feat: compat 라우터 (GET /snapshot, POST /save, /reset)"
```

---

## Task 7: 프론트 배선 — 베이스 URL + 미구현 버튼 게이팅

**Files:**
- Modify: `prototype/web/src/lib/api.ts`
- Test: 수동 스모크 (pytest 없음)

기존 프론트는 상대경로(`/api/...`)로 호출하며 vite dev 프록시/동일 출처를 가정한다.
FastAPI(`:8000`)를 절대 URL로 가리키게 하고, 아직 백엔드가 없는 액션(feed/give/bubble)은
호출이 무해하도록 둔다(서버가 404를 반환하면 프론트는 조용히 무시 — `sim.ts`는 이미 try/catch).

- [ ] **Step 1: 베이스 URL 상수화**

`prototype/web/src/lib/api.ts` 상단을 수정:

```typescript
import type { Snapshot } from "./types";

const BASE = "http://127.0.0.1:8000/api";

export async function getSnapshot(since: number): Promise<Snapshot> {
  const res = await fetch(`${BASE}/snapshot?since=${since}`);
  return res.json();
}

async function post(url: string, body: unknown): Promise<any> {
  const res = await fetch(`${BASE}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export const feed = (char_id: number, food_id: number) => post("/feed", { char_id, food_id });
export const give = (char_id: number, tool: string) => post("/give", { char_id, tool });
export const answerBubble = (index: number, char: string, allow: boolean) =>
  post("/bubble", { index, char, answer: allow ? "allow" : "stop" });
export const saveGame = () => post("/save", {});
export const resetGame = () => post("/reset", {});
```

- [ ] **Step 2: 백엔드 기동**

Run: `uvicorn tomodachai.server:app --host 127.0.0.1 --port 8000 --reload`
(별도 터미널) 캐릭터가 0명이면 `POST /api/characters`로 2명 생성하거나 세이브 로드.

- [ ] **Step 3: 프론트 기동 + 스모크**

Run (`prototype/web`에서): `npm install && npm run vite`
브라우저에서 vite URL 열기. 확인:
- 3D 마을이 뜨고 캐릭터가 장소에 배치됨 (location id 정렬 확인)
- 우측 로그/HUD에 day·clock 표시
- step 발생 시(또는 `POST /api/step` 수동 호출 시) 말풍선/로그 갱신
- feed/give/bubble 버튼은 눌러도 앱이 깨지지 않음 (404 무시)

- [ ] **Step 4: Commit**

```bash
git add prototype/web/src/lib/api.ts
git commit -m "feat(web): API 베이스를 FastAPI(:8000)로 전환"
```

---

## Self-Review 결과 (작성자 점검)

- **Spec 커버리지:** §3.1 읽기 계약 전 필드 → Task 4/5에서 매핑(NEW 필드는 빈 스텁, 후속 Plan 명시). §3.2 중 `/save`·`/reset` → Task 6. feed/give/bubble/rankings는 **범위 밖(Plan 2+)** 으로 명시. §4.1 mood→Task1, spark→Task2, seq→Task3.
- **Placeholder:** 없음. 빈 스텁(rankings/photos/dishes/bubbles/foods/dex)은 "Plan 2에서 채움" 주석으로 의도 명시 — 미완성이 아니라 증분 경계.
- **타입 일관성:** `record_events`/`events_since`/`reset_world`/`_event_seq`/`_event_log`(Task3) ↔ `build_snapshot`/`map_event`/`char_dict`(Task4/5) ↔ 라우터(Task6) 시그니처 일치. `slots.lover/best_friend/enemy`는 `RelationshipSlots`(relationship.py:46-48) 실제 필드명과 일치. `gs.relationships.get_slots`/`get`/`get_status_text`/`location_manager.get_character_location`/`snapshot` 모두 실재 메서드.
- **알려진 확인거리(구현 중):** `location_manager.snapshot()` 항목 키가 `id`/`name`인지 첫 실행 시 확인(아니면 Task5 locations 컴프리헨션 키 조정). conversation `result.dialogue` 라인 객체의 `.speaker/.text` 속성명 확인(routes.py:390과 동일 가정).
