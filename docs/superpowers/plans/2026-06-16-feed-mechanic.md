# Feed 메커닉 Implementation Plan (Plan 2/N)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 플레이어가 캐릭터에게 음식을 주면(`POST /api/feed`) 선호 구간별 반응으로 배고픔·만족도·기분이 변하고, 음식 도감(dex)이 채워진다.

**Architecture:** prototype/game/items.py 규칙을 `src/tomodachai` 모델 위에 재구현. 음식 마스터(`FOODS`)와 선호 구간/반응을 새 모듈 `food.py`에 두고, `Mood.adjust()`로 기분 조정, snapshot 집계기의 `foods`/`dex` 스텁을 채우고, compat 라우터에 `/feed`를 추가한다. 선호도(`food_ranks`)는 src에 시드 코드가 없으므로 feed 시점에 캐릭터별 결정적 시드로 lazy 초기화한다.

**Tech Stack:** Python 3.11, FastAPI, pydantic, pytest.

**기반:** Plan 1(`feat/connect-frontend-backend`) 위에 스택. 즉 `Mood.label()`·이벤트 로그·snapshot 집계기·compat 라우터가 이미 있음. PR 타깃은 `feat/connect-frontend-backend`(#3 머지되면 자동 main 재타깃).

**Spec:** `docs/superpowers/specs/2026-06-15-babylon-fastapi-connection-design.md` §4.2.

**범위 밖:** 배고픔 말풍선 자동 해소(말풍선 시스템 = Plan 2b bubble에서). 생성 시점 선호도 시드(지금은 feed lazy 시드). give/도구·rankings.

---

## 파일 구조

| 파일 | 역할 | 신규/수정 |
|---|---|---|
| `src/tomodachai/food.py` | `FOODS` 마스터, `preference_tier`, `TIER_REACTIONS`, `ensure_food_prefs`, `feed` | 신규 |
| `src/tomodachai/character.py` | `Mood.adjust()` | 수정 |
| `src/tomodachai/api/snapshot.py` | `build_snapshot` foods, `char_dict` dex 채움 | 수정 |
| `src/tomodachai/api/snapshot_routes.py` | `POST /feed` | 수정 |
| `tests/test_food.py` | food 단위 테스트 | 신규 |
| `tests/test_character.py` | `Mood.adjust` 테스트 | 수정 |
| `tests/test_snapshot.py` | foods/dex + /feed API 테스트 | 수정 |

---

## Task 1: `food.py` — FOODS 마스터 + preference_tier + TIER_REACTIONS

**Files:**
- Create: `src/tomodachai/food.py`
- Test: `tests/test_food.py` (신규)

- [ ] **Step 1: Write the failing test** — `tests/test_food.py`:

```python
"""음식 마스터 + 선호 구간 (prototype/game/items.py 규칙)."""

from tomodachai.food import FOODS, TIER_REACTIONS, preference_tier


def test_foods_master_has_ten():
    assert len(FOODS) == 10
    assert FOODS[0] == "김치찌개"
    assert FOODS[9] == "아이스크림"


def test_preference_tier_boundaries():
    # n=10 기준: rank 0,1=favorite / 2,3=like / 4,5=normal / 6,7=dislike / 8,9=worst
    assert preference_tier(0) == "favorite"
    assert preference_tier(1) == "favorite"
    assert preference_tier(2) == "like"
    assert preference_tier(3) == "like"
    assert preference_tier(4) == "normal"
    assert preference_tier(5) == "normal"
    assert preference_tier(6) == "dislike"
    assert preference_tier(7) == "dislike"
    assert preference_tier(8) == "worst"
    assert preference_tier(9) == "worst"


def test_tier_reactions_keys_and_shape():
    assert set(TIER_REACTIONS) == {"favorite", "like", "normal", "dislike", "worst"}
    text, sat, (h, e, s) = TIER_REACTIONS["favorite"]
    assert isinstance(text, str)
    assert sat == 8
    assert (h, e, s) == (2.5, 1.0, -1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_food.py -v`
Expected: FAIL — ModuleNotFoundError: tomodachai.food

- [ ] **Step 3: Write minimal implementation** — `src/tomodachai/food.py`:

```python
"""음식 마스터 데이터 + 선호 구간 (prototype/game/items.py 규칙 이식)."""

from __future__ import annotations

# 인덱스 = 음식 ID
FOODS: list[str] = [
    "김치찌개", "초밥", "햄버거", "샐러드", "라면",
    "케이크", "떡볶이", "스테이크", "두부", "아이스크림",
]

# 선호 구간별 반응: (텍스트, 만족도Δ, (happiness, energy, stress)Δ)
TIER_REACTIONS: dict[str, tuple[str, int, tuple[float, float, float]]] = {
    "favorite": ("최애예요!! (눈이 커지고 춤을 춥니다)", 8, (2.5, 1.0, -1.0)),
    "like": ("웃으며 맛있게 먹습니다.", 4, (1.5, 0.5, -0.5)),
    "normal": ("무난하게 먹습니다.", 1, (0.5, 0.3, 0.0)),
    "dislike": ("찡그리며 억지로 삼킵니다...", -3, (-1.5, 0.0, 1.0)),
    "worst": ("우웩! 쓰러질 듯 괴로워합니다!!", -6, (-2.5, -1.0, 2.0)),
}


def preference_tier(rank: int, food_count: int = len(FOODS)) -> str:
    """순위(rank, 0=가장 좋아함) → 선호 구간 (prototype 규칙)."""
    n = food_count
    if rank < 2:
        return "favorite"
    if rank < 4:
        return "like"
    if rank >= n - 2:
        return "worst"
    if rank >= n - 4:
        return "dislike"
    return "normal"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_food.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/food.py tests/test_food.py
git commit -m "feat: 음식 마스터(FOODS) + preference_tier + 반응 테이블 (prototype 규칙)"
```

---

## Task 2: `Mood.adjust()` — 3축 델타 조정 + 클램프

**Files:**
- Modify: `src/tomodachai/character.py` (class `Mood`, `label()` 아래)
- Test: `tests/test_character.py` (추가)

- [ ] **Step 1: Write the failing test** — `tests/test_character.py`에 추가:

```python
def test_mood_adjust_within_range():
    m = Mood(happiness=5, energy=5, stress=2)
    m.adjust(happiness=2, energy=1, stress=1)
    assert (m.happiness, m.energy, m.stress) == (7, 6, 3)


def test_mood_adjust_clamps_0_10():
    m = Mood(happiness=9, energy=1, stress=9)
    m.adjust(happiness=5, energy=-5, stress=5)
    assert m.happiness == 10
    assert m.energy == 0
    assert m.stress == 10


def test_mood_adjust_rounds_floats():
    m = Mood(happiness=5, energy=5, stress=5)
    m.adjust(happiness=2.5, energy=0.3, stress=-1.5)
    # round(7.5)=8(은행가 반올림 주의: round(7.5)=8? python round(7.5)=8? 실제 round(7.5)=8 아님 → 8)
    # python banker's rounding: round(7.5)=8, round(5.3)=5, round(3.5)=4
    assert m.happiness == round(7.5)
    assert m.energy == round(5.3)
    assert m.stress == round(3.5)
```

> 주의: Python `round`는 은행가 반올림(round-half-to-even). 테스트가 구현과 동일한 `round()`를 기대값에 쓰므로 일치한다. 구현도 반드시 `round()`를 사용할 것.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_character.py -k mood_adjust -v`
Expected: FAIL — Mood has no `adjust`

- [ ] **Step 3: Write minimal implementation** — `class Mood` 안 `label()` 아래에 추가:

```python
    def adjust(self, happiness: float = 0, energy: float = 0, stress: float = 0) -> None:
        """3축을 델타만큼 조정하고 0~10으로 클램프 (int 저장, round)."""

        def _clamp(v: float) -> int:
            return max(0, min(10, round(v)))

        self.happiness = _clamp(self.happiness + happiness)
        self.energy = _clamp(self.energy + energy)
        self.stress = _clamp(self.stress + stress)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_character.py -k mood_adjust -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/character.py tests/test_character.py
git commit -m "feat: Mood.adjust() 3축 델타 조정 + 0~10 클램프"
```

---

## Task 3: `food.py` — feed() + ensure_food_prefs()

**Files:**
- Modify: `src/tomodachai/food.py` (`feed`, `ensure_food_prefs` 추가)
- Test: `tests/test_food.py` (추가)

선호도(`food_ranks`)는 src에 시드가 없으므로 feed 시점에 캐릭터 id 기반 결정적 셔플로 lazy 초기화한다(멱등).

- [ ] **Step 1: Write the failing test** — `tests/test_food.py`에 추가:

```python
import pytest

from tomodachai.character import Character, CharacterState, Profile
from tomodachai.food import ensure_food_prefs, feed


def _char(cid=1, name="민수"):
    return Character(
        id=cid,
        personality_code="outgoing_dynamo",
        profile=Profile(name=name, birthday="03-15", blood_type="B", gender="남성"),
        state=CharacterState(hunger=80.0, satisfaction=50.0),
    )


def test_ensure_food_prefs_seeds_full_permutation():
    c = _char()
    ensure_food_prefs(c)
    assert sorted(c.preferences.food_ranks) == list(range(len(FOODS)))
    assert c.preferences.food_eaten == [False] * len(FOODS)


def test_ensure_food_prefs_is_deterministic_and_idempotent():
    a, b = _char(cid=7), _char(cid=7)
    ensure_food_prefs(a)
    ensure_food_prefs(b)
    assert a.preferences.food_ranks == b.preferences.food_ranks
    first = list(a.preferences.food_ranks)
    ensure_food_prefs(a)  # 두 번째 호출은 덮어쓰지 않음
    assert a.preferences.food_ranks == first


def test_feed_reduces_hunger_and_marks_dex():
    c = _char()
    msg = feed(c, food_id=0)
    assert c.state.hunger == 30.0  # 80 - 50
    assert c.preferences.food_eaten[0] is True
    assert "도감에 기록" in msg
    assert FOODS[0] in msg


def test_feed_hunger_clamps_at_zero():
    c = _char()
    c.state.hunger = 20.0
    feed(c, food_id=0)
    assert c.state.hunger == 0.0


def test_feed_second_time_no_discovery_note():
    c = _char()
    feed(c, food_id=0)
    msg2 = feed(c, food_id=0)
    assert "도감에 기록" not in msg2


def test_feed_favorite_boosts_satisfaction_and_mood():
    c = _char()
    ensure_food_prefs(c)
    # 최애(rank 0) 음식 id 찾기
    fav_id = c.preferences.food_ranks.index(0)
    before = c.state.satisfaction
    feed(c, fav_id)
    assert c.state.satisfaction == before + 8  # favorite sat delta
    assert c.state.mood.happiness >= 5  # 상승 방향


def test_feed_invalid_food_id_raises():
    c = _char()
    with pytest.raises(ValueError):
        feed(c, food_id=99)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_food.py -k "ensure_food_prefs or feed" -v`
Expected: FAIL — `feed`/`ensure_food_prefs` 미정의

- [ ] **Step 3: Write minimal implementation** — `src/tomodachai/food.py`에 추가 (상단 import도 추가):

```python
import random

from tomodachai.character import Character


def ensure_food_prefs(char: Character) -> None:
    """food_ranks/food_eaten가 비었으면 캐릭터별 결정적 시드로 초기화 (멱등)."""
    prefs = char.preferences
    n = len(FOODS)
    if len(prefs.food_ranks) != n:
        seed = char.id if isinstance(char.id, int) else abs(hash(char.id))
        ranks = list(range(n))
        random.Random(seed).shuffle(ranks)
        prefs.food_ranks = ranks
    if len(prefs.food_eaten) != n:
        prefs.food_eaten = [False] * n


def feed(char: Character, food_id: int) -> str:
    """캐릭터에게 음식을 준다 (prototype/game items.feed 규칙). 반환: 결과 메시지.

    Raises:
        ValueError: food_id가 음식 범위를 벗어날 때.
    """
    if not (0 <= food_id < len(FOODS)):
        raise ValueError(f"음식 id {food_id} 없음")
    ensure_food_prefs(char)

    tier = preference_tier(char.preferences.food_ranks[food_id])
    text, sat, (h, e, s) = TIER_REACTIONS[tier]

    st = char.state
    st.hunger = max(0.0, st.hunger - 50)
    st.satisfaction = min(100.0, st.satisfaction + sat)
    st.mood.adjust(happiness=h, energy=e, stress=s)

    discovered = ""
    if not char.preferences.food_eaten[food_id]:
        char.preferences.food_eaten[food_id] = True
        discovered = " (도감에 기록!)"

    return f"🍽 {char.name}에게 {FOODS[food_id]}을(를) 주었습니다 → {text}{discovered}"
```

> 주의: `import random`과 `from tomodachai.character import Character`를 파일 상단 import 블록으로 올려 ruff I001을 피한다. `food.py`가 `character`를 import하는데, `character.py`는 `food`를 import하지 않으므로 순환 import 없음(확인할 것).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_food.py -v`
Expected: PASS (9 tests 누적)

- [ ] **Step 5: Run full suite (순환 import 회귀 확인)**

Run: `pytest tests/ -q`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/tomodachai/food.py tests/test_food.py
git commit -m "feat: feed() + ensure_food_prefs() (선호 반응/배고픔/도감, prototype 규칙)"
```

---

## Task 4: snapshot — foods 채움 + char_dict dex 채움

**Files:**
- Modify: `src/tomodachai/api/snapshot.py`
- Test: `tests/test_snapshot.py` (추가)

- [ ] **Step 1: Write the failing test** — `tests/test_snapshot.py`에 추가:

```python
def test_snapshot_foods_is_master_list():
    from tomodachai.api.snapshot import build_snapshot
    from tomodachai.food import FOODS

    gs = _gs_with_two()
    assert build_snapshot(gs, since=0)["foods"] == FOODS


def test_char_dict_dex_filled_after_feed():
    from tomodachai.api.snapshot import char_dict
    from tomodachai.food import FOODS, feed, preference_tier

    gs = _gs_with_two()
    minsu = gs.get_character(1)
    feed(minsu, food_id=0)  # 김치찌개 먹임 → dex에 1건

    d = char_dict(gs, minsu)
    assert len(d["dex"]) == 1
    entry = d["dex"][0]
    assert entry["name"] == FOODS[0]
    assert entry["tier"] == preference_tier(minsu.preferences.food_ranks[0])


def test_char_dict_dex_empty_before_feed():
    from tomodachai.api.snapshot import char_dict

    gs = _gs_with_two()
    assert char_dict(gs, gs.get_character(2))["dex"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_snapshot.py -k "foods or dex" -v`
Expected: FAIL — foods is `[]`, dex is `[]`

- [ ] **Step 3: Write minimal implementation**

`src/tomodachai/api/snapshot.py` 상단 import에 추가:

```python
from tomodachai.food import FOODS, preference_tier
```

`char_dict` 안에서 `"dex": []` 를 실제 도감 계산으로 교체. `return {...}` 직전에 dex 계산을 추가하고 반환 dict의 `dex` 값을 바꾼다:

```python
    prefs = char.preferences
    dex = [
        {"name": FOODS[fid], "tier": preference_tier(prefs.food_ranks[fid])}
        for fid, eaten in enumerate(prefs.food_eaten)
        if eaten and fid < len(prefs.food_ranks)
    ]
```
그리고 반환 dict에서 `"dex": [],  # Plan 2(feed)에서 채움` → `"dex": dex,`.

`build_snapshot` 반환 dict에서 `"foods": [],  # Plan 2(feed)에서 채움` → `"foods": FOODS,`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_snapshot.py -v`
Expected: PASS (기존 9 + 신규 3 = 12)

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/api/snapshot.py tests/test_snapshot.py
git commit -m "feat: snapshot foods=FOODS + char_dict dex 채움"
```

---

## Task 5: `POST /api/feed` 라우트

**Files:**
- Modify: `src/tomodachai/api/snapshot_routes.py`
- Test: `tests/test_snapshot.py` (추가)

- [ ] **Step 1: Write the failing test** — `tests/test_snapshot.py`에 추가 (`client_snap` fixture 재사용):

```python
def test_api_feed_succeeds_and_fills_dex(client_snap):
    client, gs = client_snap
    resp = client.post("/api/feed", json={"char_id": 1, "food_id": 0})
    assert resp.status_code == 200
    assert "🍽" in resp.json()["message"]

    snap = client.get("/api/snapshot?since=0").json()
    minsu = next(c for c in snap["characters"] if c["id"] == 1)
    assert len(minsu["dex"]) == 1
    # feed 이벤트가 로그에 기록됨
    assert any("🍽" in e["scene"] for e in snap["events"])


def test_api_feed_unknown_char(client_snap):
    client, _gs = client_snap
    resp = client.post("/api/feed", json={"char_id": 999, "food_id": 0})
    assert resp.status_code == 404


def test_api_feed_invalid_food(client_snap):
    client, _gs = client_snap
    resp = client.post("/api/feed", json={"char_id": 1, "food_id": 99})
    assert resp.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_snapshot.py -k api_feed -v`
Expected: FAIL — 404 (route 없음) / 422

- [ ] **Step 3: Write minimal implementation** — `src/tomodachai/api/snapshot_routes.py`:

상단 import에 `from pydantic import BaseModel` 추가. 그리고 요청 모델 + 라우트 추가:

```python
class FeedRequest(BaseModel):
    char_id: int
    food_id: int


@compat_router.post("/feed")
def feed_character(body: FeedRequest):
    from tomodachai.food import feed

    gs = _gs()
    char = gs.get_character(body.char_id)
    if char is None:
        raise HTTPException(status_code=404, detail=f"Character {body.char_id} not found")
    try:
        msg = feed(char, body.food_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # 결과를 이벤트 로그에 기록 → 다음 폴링에서 피드 스트림에 재생 (scene = msg)
    gs.record_events([{"type": "feed", "participants": [char.name], "summary": msg}])
    return {"message": msg}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_snapshot.py -v`
Expected: PASS (12 + 3 = 15)

- [ ] **Step 5: Run full suite**

Run: `pytest tests/ -q`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/tomodachai/api/snapshot_routes.py tests/test_snapshot.py
git commit -m "feat: POST /api/feed (먹이기 → dex/이벤트 반영)"
```

---

## Self-Review 결과 (작성자 점검)

- **Spec 커버리지(§4.2):** preference_tier(Task1) / TIER_REACTIONS·feed 규칙(Task1·3) / hunger −50·만족도·mood.adjust·도감 기록(Task3) / dex 공개(Task4) / foods(Task4) / 먹이기 API(Task5). 배고픔 말풍선 해소는 말풍선 시스템 미구현이라 **범위 밖**으로 명시(spec §4.2의 그 부분은 Plan 2b bubble과 함께).
- **Placeholder:** 없음. 모든 step에 실제 코드/명령/기대값 포함.
- **타입 일관성:** `FOODS`/`preference_tier`/`TIER_REACTIONS`(Task1) ↔ `ensure_food_prefs`/`feed`(Task3) ↔ snapshot `FOODS`/`preference_tier` import(Task4) ↔ `feed` 호출(Task5) 일치. `feed`는 `Character`를 받고 `str` 반환. `Mood.adjust(happiness,energy,stress)` 시그니처(Task2) ↔ `feed`의 `st.mood.adjust(happiness=h,...)`(Task3) 일치. `char.preferences.food_ranks/food_eaten`/`char.state.{hunger,satisfaction,mood}`는 character.py 실재 필드.
- **순환 import 확인거리:** `food.py`가 `character`를 import. `character.py`는 `food`를 import하지 않음 → 순환 없음(Task3 Step5 전체 스위트로 검증). `snapshot.py`가 `food`를 import(Task4) — `food`는 `snapshot`을 import 안 함 → 순환 없음.
- **결정적 시드:** `ensure_food_prefs`가 `char.id` 시드 셔플 → 같은 id면 동일 선호. 테스트(`test_ensure_food_prefs_is_deterministic_and_idempotent`)로 보장.
