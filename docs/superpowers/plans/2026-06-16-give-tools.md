# Give·도구 메커닉 Implementation Plan (Plan 3/N)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 플레이어가 캐릭터에게 도구를 주면(`POST /api/give`) 카메라는 사진을, 프라이팬은 요리를 만들어 갤러리/카탈로그(snapshot `photos`/`dishes`)에 쌓인다.

**Architecture:** prototype/game `use_tool` 규칙을 `src/tomodachai` 모델 위에 재구현. 새 모듈 `tools.py`가 LLM(`gs.llm.chat_json`)으로 사진 제목/요리 이름을 생성하고, 게임 레벨 저장소 `gs.photos`/`gs.dishes`(세션 한정)에 적재한다. snapshot의 `photos`/`dishes` 스텁을 채우고 compat 라우터에 `/give`를 추가한다.

**Tech Stack:** Python 3.11, FastAPI, pydantic, pytest.

**기반:** Plan 2(`feat/feed-mechanic`) 위 스택. `Mood.adjust()`·이벤트 로그·snapshot 집계기·compat 라우터·snapshot 일부 필드가 이미 있음. PR 타깃 `feat/feed-mechanic`(상위 PR들 머지되면 자동 재타깃).

**Spec:** `docs/superpowers/specs/2026-06-15-babylon-fastapi-connection-design.md` §4.5.

**범위 밖:** 배고픔 말풍선 자동 해소(말풍선 시스템 미구현). photos/dishes의 세이브 영속화(세션 한정 — shop/뉴스/분수대와 동일 정책). rankings.

---

## 파일 구조

| 파일 | 역할 | 신규/수정 |
|---|---|---|
| `src/tomodachai/game_state.py` | `photos`/`dishes` 저장소 + `reset_world` 정리 | 수정 |
| `src/tomodachai/tools.py` | `use_tool`(camera/frying_pan), LLM 생성 + 적재 | 신규 |
| `src/tomodachai/api/snapshot.py` | `build_snapshot` photos/dishes 채움 | 수정 |
| `src/tomodachai/api/snapshot_routes.py` | `POST /give` | 수정 |
| `tests/test_tools.py` | tools 단위 테스트 | 신규 |
| `tests/test_event_log.py` | photos/dishes reset 테스트 | 수정 |
| `tests/test_snapshot.py` | photos/dishes snapshot + /give API 테스트 | 수정 |

---

## Task 1: GameState `photos`/`dishes` 저장소 + reset 정리

**Files:**
- Modify: `src/tomodachai/game_state.py`
- Test: `tests/test_event_log.py` (추가)

게임 레벨 사진/요리 저장소(세션 한정). 프론트 snapshot이 `list(reversed(...[-40:]))`로 읽는다.

- [ ] **Step 1: Write the failing test** — `tests/test_event_log.py`에 추가:

```python
def test_game_state_has_photo_dish_stores():
    gs = GameState()
    assert gs.photos == []
    assert gs.dishes == []


def test_reset_world_clears_photos_and_dishes():
    gs = GameState()
    gs.photos.append({"day": 1, "author": "민수", "title": "노을", "subject": "공원"})
    gs.dishes.append({"day": 1, "author": "지은", "dish": "수상한 볶음"})
    gs.reset_world()
    assert gs.photos == []
    assert gs.dishes == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_event_log.py -k "photo_dish or photos_and_dishes" -v`
Expected: FAIL — `GameState` has no `photos`/`dishes`

- [ ] **Step 3: Write minimal implementation**

`src/tomodachai/game_state.py` `__init__`에서 이벤트 로그 초기화 블록 바로 아래에 추가:
```python
        # 도구 산출물 (세션 한정 — 사진 갤러리 / 요리 카탈로그)
        self.photos: list[dict] = []
        self.dishes: list[dict] = []
```

`reset_world()` 메서드에 두 줄 추가 (기존 초기화 라인들과 함께):
```python
        self.photos = []
        self.dishes = []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_event_log.py -v`
Expected: PASS (기존 + 신규 2)

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/game_state.py tests/test_event_log.py
git commit -m "feat: GameState photos/dishes 저장소 + reset 정리"
```

---

## Task 2: `tools.py` — use_tool(camera / frying_pan)

**Files:**
- Create: `src/tomodachai/tools.py`
- Test: `tests/test_tools.py` (신규)

prototype `use_tool` 규칙: 카메라(같은 장소 주민 50% / 풍경 피사체 → 사진 제목·감상, 기분+1), 프라이팬(요리 이름·소감, hunger −40, 기분+1·에너지+0.5). LLM 실패 시 폴백 제목/요리명.

- [ ] **Step 1: Write the failing test** — `tests/test_tools.py` (신규):

```python
"""도구 메커닉 — 카메라/프라이팬 (prototype use_tool 규칙)."""

import pytest

from tomodachai.character import (
    Character, CharacterState, Customizable, Profile, SpeechHabits,
)
from tomodachai.config import AppConfig, LLMConfig, LocationConfig, SimulationConfig
from tomodachai.game_state import GameState
from tomodachai.tools import use_tool


class _MockLLM:
    def __init__(self, response: dict):
        self._response = response
        self.calls = 0

    def chat_json(self, messages, **kwargs) -> dict:
        self.calls += 1
        return self._response


def _gs():
    cfg = AppConfig(
        llm=LLMConfig(provider="litellm", model="ollama/gemma3", temperature=0.8),
        simulation=SimulationConfig(),
        locations=[LocationConfig(id="fountain", name="분수대")],
    )
    gs = GameState(config=cfg)
    gs.add_character(
        Character(
            id=1,
            personality_code="outgoing_dynamo",
            profile=Profile(name="민수", birthday="03-15", blood_type="B", gender="남성"),
            state=CharacterState(hunger=80.0, current_location="분수대"),
            customizable=Customizable(speech_habits=SpeechHabits(normal="~")),
        )
    )
    return gs


def test_camera_stores_photo_and_boosts_mood():
    gs = _gs()
    gs.llm = _MockLLM({"title": "분수대의 오후", "caption": "찰칵!"})
    char = gs.get_character(1)
    before = char.state.mood.happiness

    msg = use_tool(gs, char, "camera")

    assert len(gs.photos) == 1
    photo = gs.photos[0]
    assert set(photo) == {"day", "author", "title", "subject"}
    assert photo["author"] == "민수"
    assert photo["title"] == "분수대의 오후"
    assert char.state.mood.happiness == min(10, before + 1)
    assert "분수대의 오후" in msg


def test_camera_falls_back_when_llm_empty():
    gs = _gs()
    gs.llm = _MockLLM({})  # title/caption 없음
    char = gs.get_character(1)

    use_tool(gs, char, "camera")
    assert len(gs.photos) == 1
    assert gs.photos[0]["title"].startswith("무제")


def test_frying_pan_stores_dish_and_reduces_hunger():
    gs = _gs()
    gs.llm = _MockLLM({"dish": "민수표 폭탄볶음", "comment": "완성!"})
    char = gs.get_character(1)

    msg = use_tool(gs, char, "frying_pan")

    assert len(gs.dishes) == 1
    dish = gs.dishes[0]
    assert set(dish) == {"day", "author", "dish"}
    assert dish["author"] == "민수"
    assert dish["dish"] == "민수표 폭탄볶음"
    assert char.state.hunger == 40.0  # 80 - 40
    assert "민수표 폭탄볶음" in msg


def test_frying_pan_falls_back_when_llm_empty():
    gs = _gs()
    gs.llm = _MockLLM({})
    char = gs.get_character(1)
    use_tool(gs, char, "frying_pan")
    assert gs.dishes[0]["dish"] == "정체불명 볶음"


def test_unknown_tool_raises():
    gs = _gs()
    char = gs.get_character(1)
    with pytest.raises(ValueError):
        use_tool(gs, char, "hammer")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL — ModuleNotFoundError: tomodachai.tools

- [ ] **Step 3: Write minimal implementation** — `src/tomodachai/tools.py` (신규):

```python
"""도구 아이템 — 카메라(사진) / 프라이팬(요리). prototype/game use_tool 규칙 이식.

LLM(gs.llm.chat_json)으로 제목/요리명을 생성하고 게임 레벨 저장소에 적재한다.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tomodachai.character import Character
    from tomodachai.game_state import GameState

TOOLS = ("camera", "frying_pan")


def _int_id(char) -> int:
    return char.id if isinstance(char.id, int) else abs(hash(char.id)) % 100000


def use_tool(gs: GameState, char: Character, tool: str) -> str:
    """캐릭터가 도구를 사용한다. 반환: 결과 메시지.

    Raises:
        ValueError: 알 수 없는 도구일 때.
    """
    if tool == "camera":
        return _camera(gs, char)
    if tool == "frying_pan":
        return _frying_pan(gs, char)
    raise ValueError(f"알 수 없는 도구: {tool}")


def _camera(gs: GameState, char: Character) -> str:
    int_id = _int_id(char)
    loc_id = gs.location_manager.get_character_location(int_id) or ""
    loc = gs.location_manager.get_location(loc_id)
    loc_name = loc.name if loc else (char.state.current_location or "어딘가")

    # 피사체: 같은 장소 주민 50% / 풍경
    mates = [
        c
        for c in gs.characters
        if _int_id(c) != int_id
        and gs.location_manager.get_character_location(_int_id(c)) == loc_id
        and loc_id
    ]
    if mates and random.random() < 0.5:
        m = random.choice(mates)
        subject = f"{loc_name}에 있는 주민 {m.name}의 자연스러운 한 컷"
        subj_label = m.name
    else:
        subject = f"{loc_name}의 풍경"
        subj_label = loc_name

    messages = [
        {
            "role": "system",
            "content": (
                "너는 관찰형 시뮬레이션 게임의 콘텐츠 생성기다. 주민이 카메라로 사진을 한 장 찍었다. "
                "사진 제목은 캐릭터 성격이 묻어나는 짧은 한 문장(10자 내외, 엉뚱해도 좋음), "
                "감상은 캐릭터 말투로 1문장. "
                'JSON만 출력: {"title": "...", "caption": "..."}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"캐릭터: {char.name} ({char.personality_code}), 기분: {char.state.mood.label()}\n"
                f"피사체: {subject}"
            ),
        },
    ]
    data = gs.llm.chat_json(messages, max_tokens=200)
    title = str((data or {}).get("title") or f"무제 ({subj_label})")
    caption = str((data or {}).get("caption") or "").strip()

    gs.photos.append(
        {"day": gs.day_count, "author": char.name, "title": title, "subject": subj_label}
    )
    char.state.mood.adjust(happiness=1)

    msg = f"📸 {char.name}의 촬영 — 사진 '{title}' 갤러리에 저장"
    if caption:
        msg += f" ({char.name}: {caption})"
    return msg


def _frying_pan(gs: GameState, char: Character) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "너는 관찰형 시뮬레이션 게임의 콘텐츠 생성기다. 주민이 프라이팬으로 즉흥 요리를 했다. "
                "요리 이름은 캐릭터 성격이 드러나는 창작 요리(15자 내외, 실존 요리 비틀기도 가능), "
                "완성 소감은 캐릭터 말투로 1문장(요리 실력은 복불복). "
                'JSON만 출력: {"dish": "...", "comment": "..."}'
            ),
        },
        {
            "role": "user",
            "content": f"캐릭터: {char.name} ({char.personality_code}), 기분: {char.state.mood.label()}",
        },
    ]
    data = gs.llm.chat_json(messages, max_tokens=200)
    dish = str((data or {}).get("dish") or "정체불명 볶음")
    comment = str((data or {}).get("comment") or "").strip()

    st = char.state
    st.hunger = max(0.0, st.hunger - 40)
    st.mood.adjust(happiness=1, energy=0.5)
    gs.dishes.append({"day": gs.day_count, "author": char.name, "dish": dish})

    msg = f"🍳 {char.name}의 즉흥 요리 — '{dish}' 카탈로그에 추가"
    if comment:
        msg += f" ({char.name}: {comment})"
    return msg
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run full suite (순환 import 확인 — tools가 character/game_state 타입만 TYPE_CHECKING import)**

Run: `pytest tests/ -q`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/tomodachai/tools.py tests/test_tools.py
git commit -m "feat: tools.py use_tool (카메라→사진/프라이팬→요리, prototype 규칙)"
```

---

## Task 3: snapshot `photos`/`dishes` 채움

**Files:**
- Modify: `src/tomodachai/api/snapshot.py`
- Test: `tests/test_snapshot.py` (추가)

prototype web_server snapshot과 동일: `list(reversed(store[-40:]))` (최신 우선, 최대 40개).

- [ ] **Step 1: Write the failing test** — `tests/test_snapshot.py`에 추가:

```python
def test_snapshot_photos_dishes_newest_first_capped():
    from tomodachai.api.snapshot import build_snapshot

    gs = _gs_with_two()
    for i in range(45):
        gs.photos.append({"day": 1, "author": "민수", "title": f"p{i}", "subject": "공원"})
    gs.dishes.append({"day": 1, "author": "지은", "dish": "수상한 볶음"})

    snap = build_snapshot(gs, since=0)
    assert len(snap["photos"]) == 40            # 최대 40개
    assert snap["photos"][0]["title"] == "p44"  # 최신 우선
    assert snap["dishes"][0]["dish"] == "수상한 볶음"


def test_snapshot_photos_dishes_empty_by_default():
    from tomodachai.api.snapshot import build_snapshot

    gs = _gs_with_two()
    snap = build_snapshot(gs, since=0)
    assert snap["photos"] == []
    assert snap["dishes"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_snapshot.py -k "photos_dishes" -v`
Expected: FAIL — photos/dishes are hardcoded `[]`

- [ ] **Step 3: Write minimal implementation**

`src/tomodachai/api/snapshot.py` `build_snapshot` 반환 dict에서:
- `"photos": [],  # Plan 2(give)에서 채움` → `"photos": list(reversed(gs.photos[-40:])),`
- `"dishes": [],  # Plan 2(give)에서 채움` → `"dishes": list(reversed(gs.dishes[-40:])),`

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_snapshot.py -v`
Expected: PASS (기존 + 신규 2)

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/api/snapshot.py tests/test_snapshot.py
git commit -m "feat: snapshot photos/dishes 채움 (최신 우선 40개)"
```

---

## Task 4: `POST /api/give` 라우트

**Files:**
- Modify: `src/tomodachai/api/snapshot_routes.py`
- Test: `tests/test_snapshot.py` (추가)

- [ ] **Step 1: Write the failing test** — `tests/test_snapshot.py`에 추가:

```python
class _GiveMockLLM:
    def chat_json(self, messages, **kwargs) -> dict:
        return {"title": "한 컷", "caption": "찰칵", "dish": "민수볶음", "comment": "완성"}


def test_api_give_camera(client_snap):
    client, gs = client_snap
    gs.llm = _GiveMockLLM()
    resp = client.post("/api/give", json={"char_id": 1, "tool": "camera"})
    assert resp.status_code == 200
    assert "📸" in resp.json()["message"]

    snap = client.get("/api/snapshot?since=0").json()
    assert len(snap["photos"]) == 1
    assert snap["photos"][0]["author"] == "민수"
    assert any("📸" in e["scene"] for e in snap["events"])


def test_api_give_frying_pan(client_snap):
    client, gs = client_snap
    gs.llm = _GiveMockLLM()
    resp = client.post("/api/give", json={"char_id": 1, "tool": "frying_pan"})
    assert resp.status_code == 200
    snap = client.get("/api/snapshot?since=0").json()
    assert len(snap["dishes"]) == 1
    assert snap["dishes"][0]["dish"] == "민수볶음"


def test_api_give_unknown_char(client_snap):
    client, _gs = client_snap
    resp = client.post("/api/give", json={"char_id": 999, "tool": "camera"})
    assert resp.status_code == 404


def test_api_give_unknown_tool(client_snap):
    client, gs = client_snap
    gs.llm = _GiveMockLLM()
    resp = client.post("/api/give", json={"char_id": 1, "tool": "hammer"})
    assert resp.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_snapshot.py -k api_give -v`
Expected: FAIL — 404/422 (route 없음)

- [ ] **Step 3: Write minimal implementation** — `src/tomodachai/api/snapshot_routes.py`:

`FeedRequest` 아래에 요청 모델 + 라우트 추가 (`BaseModel`은 이미 import됨):
```python
class GiveRequest(BaseModel):
    char_id: int
    tool: str


@compat_router.post("/give")
def give_tool(body: GiveRequest):
    from tomodachai.tools import use_tool

    gs = _gs()
    char = gs.get_character(body.char_id)
    if char is None:
        raise HTTPException(status_code=404, detail=f"Character {body.char_id} not found")
    try:
        msg = use_tool(gs, char, body.tool)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    event_type = "photo" if body.tool == "camera" else "cooking"
    gs.record_events([{"type": event_type, "participants": [char.name], "summary": msg}])
    return {"message": msg}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_snapshot.py -v`
Expected: PASS (기존 + 신규 4)

- [ ] **Step 5: Run full suite**

Run: `pytest tests/ -q`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/tomodachai/api/snapshot_routes.py tests/test_snapshot.py
git commit -m "feat: POST /api/give (카메라/프라이팬 → photos/dishes/이벤트)"
```

---

## Self-Review 결과 (작성자 점검)

- **Spec 커버리지(§4.5):** camera→사진(Task2), frying_pan→요리(Task2), photos/dishes 저장소(Task1)·snapshot 노출(Task3), 도구 API(Task4). LLM 생성은 `gs.llm.chat_json`로 이식하고 키 없으면 폴백("무제 (...)", "정체불명 볶음") — prototype `(data or {}).get(...)` 패턴 동일. 배고픔 말풍선 해소는 말풍선 시스템 미구현이라 **범위 밖** 명시.
- **Placeholder:** 없음. 모든 step에 실제 코드/명령/기대값.
- **타입 일관성:** `use_tool(gs, char, tool)->str`(Task2) ↔ 라우트 호출(Task4) 일치. `gs.photos`/`gs.dishes`(Task1) ↔ tools append(Task2) ↔ snapshot 읽기(Task3) 일치. Photo dict 키 `{day,author,title,subject}`·Dish `{day,author,dish}` ↔ 프론트 `types.ts` `Photo`/`Dish` 인터페이스 정합. `Mood.adjust`(Plan 2 기존)·`char.state.hunger`·`location_manager.get_character_location/get_location(.name)` 실재.
- **순환 import:** `tools.py`는 `character`/`game_state`를 `TYPE_CHECKING`으로만 import → 런타임 순환 없음. `snapshot_routes`는 `use_tool`을 함수 내부 import(`/feed` 패턴 동일).
- **이벤트 매핑:** give 이벤트 type `photo`/`cooking`은 `_MAJOR_TYPES`에 없어 `major=false`, scene은 `summary`(msg)에서 채워짐(Plan 1 map_event 재사용).
- **세션 한정:** photos/dishes는 save.py 비대상(shop/뉴스/분수대와 동일). reset_world가 정리(Task1).
