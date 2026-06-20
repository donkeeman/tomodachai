# 클라 시뮬 Phase 2 — relationship + memory 포팅 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Python `relationship.py`/`memory.py`(둘 다 RNG/LLM/IO 0, 완전 결정론)를 TS `src/sim/`로 충실 포팅. 순수함수는 골든 대조, 상태기계(Tracker/Store)는 통합 테스트.

**Architecture:** Phase 0/1 패턴 — Python=오라클, 순수함수 골든 1:1, `src/sim/` 프레임워크 무의존. relationship/memory는 다른 tomodachai 모듈 import 없음(자립). `calculateCompatibility`만 성격코드 문자열을 입력으로 받음(Phase 1 `personalityCode` 산출물과 호출부에서 연결, 타입 의존은 없음).

**Tech Stack:** TS, vitest, 골든 하니스(`scripts/dump_golden.py` + `loadGolden.ts` 확장). 정답지: `src/tomodachai/relationship.py`, `src/tomodachai/memory.py`.

## Global Constraints
- **Python 정답지 수정 금지** (`src/tomodachai/**`, `tests/**` 읽기 전용; 덤프는 READ만).
- **`src/sim/`는 프레임워크 무의존** (Babylon/Svelte/Tauri import 금지).
- **Node 18+** — node/npm은 `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH"` 프리픽스(기본 env node v16).
- **Python 덤프**: repo 루트에서 `python scripts/dump_golden.py`.
- **작업 디렉터리 persists** — repo 루트(python/git) vs `prototype/web`(npm) 명시적 cd.
- **사용자 WIP `git add` 금지**: `CLAUDE.md`, `docs/plan/01-character.md`, `docs/plan/03-space-and-events.md`, untracked `.mcp.json`/`godot/`/`mii.blend*`/`sh.exe.stackdump`.
- **브랜치** `feat/client-sim-migration`, main 직접 푸시 금지.
- **커밋 트레일러**: 끝에 정확히 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **포팅 충실도:** Python `>=`/`<=`/`<` 비교·임계 숫자·라벨 문자열·기본값 그대로. `round(x, 4)` 4자리 반올림은 Python `round`(banker's) — 기존 `bankersRound`(clock.ts) 재사용 가능하나 4자리라 `Number(x.toFixed(4))`는 부정확할 수 있으니 **골든이 검증**; 불일치 시 banker's-round 기반 4자리 구현.
- **순수 지향:** mutating 메서드(`applyDeltas`/`applyNaturalDecay`)는 **새 객체 반환 순수함수**로 포팅(골든 검증 가능하게). Tracker/Store는 내부 가변 상태 유지.

## 범위 밖 (Phase 2 아님)
- simulation.py fight/confession 트리거(RNG 게이트) → Phase 3+
- save.py relationships.json 직렬화 → Phase 6 세이브
- conversation.py/news.py LLM 렌더링(deltas 생성·SocialEvent 서사) → LLM 후속
- `check_stage_transition` 이벤트 훅 배선(시뮬 틱) → Phase 3 (단 `computeStage` 로직 자체는 Phase 2)

## File Structure
- `prototype/web/src/sim/relationship.ts` (생성) — enums + `Relationship` 타입 + 라벨/스테이지/breakup/decay 순수함수.
- `prototype/web/src/sim/compatibility.ts` (생성) — `personalityGroup` + `calculateCompatibility`.
- `prototype/web/src/sim/relationshipTracker.ts` (생성) — `RelationshipTracker` 상태기계 + `RelationshipSlots`/`Fight`/`ExLoverTag`/`Triangle` + `detectTriangles`/`applyJealousy`.
- `prototype/web/src/sim/memory.ts` (생성) — `SocialEvent` + `MemoryStore`.
- 각 `*.test.ts`, `scripts/dump_golden.py`(섹션 추가), `loadGolden.ts`(레지스트리 확장).

---

## Task 1: Relationship 코어 — enums + 라벨/스테이지/breakup/decay (순수함수, 골든)

**Files:**
- Modify: `scripts/dump_golden.py`, `prototype/web/src/sim/__golden__/loadGolden.ts`
- Create: `prototype/web/src/sim/relationship.ts`, `prototype/web/src/sim/relationship.test.ts`

**Interfaces (Produces, export from `relationship.ts`):**
- `enum`/union `RelationshipStage = "stranger"|"acquaintance"|"friend"|"best_friend"|"lover"|"married"`
- `BreakupReason = "mutual"|"fight"|"cheating"|"boredom"|"triangle"|"misunderstanding"`
- `interface Relationship { friendship: number; romance: number; stage: RelationshipStage }`, `defaultRelationship(): Relationship` (friendship=0, romance=0, stage="stranger")
- `friendshipStage(friendship: number): RelationshipStage`
- `computeStage(friendship: number, romance: number, currentStage: RelationshipStage, allowRomantic: boolean): RelationshipStage`
- `getStatusText(stage): string`, `getFriendshipText(friendship): string`, `getRomanceText(romance): string | null`
- `checkBreakupConditions(stage, romance, hasCheating, hasTriangle, fightUnresolved, romanceThreshold=20.0): BreakupReason | null`
- `applyDeltas(rel: Relationship, deltas: {friendship?: number; romance?: number}): Relationship` (순수, 새 객체; friendship 클램프 [-100,100], romance [0,100])
- `applyNaturalDecay(rel: Relationship, decayFriendship=0.75, decayRomance=0.5): Relationship` (순수)

**오라클(정답지 = `relationship.py`) — 정확 임계 (구현·골든 모두 이 값):**
- `friendshipStage`: ≥80→best_friend, ≥40→friend, ≥10→acquaintance, else stranger.
- `getStatusText`: stranger="모르는 사이", acquaintance="아는 사이", friend="친구", best_friend="베프", lover="연인", married="부부".
- `getFriendshipText`: ≥80 "둘도 없는 친구", ≥60 "꽤 친한 사이", ≥40 "친해지는 중", ≥20 "알고 지내는 사이", ≥-19 "그저 그런 사이", ≥-49 "서먹서먹", ≥-69 "사이가 나쁨", else "앙숙".
- `getRomanceText`: ≤0 → null, ≥80 "완전 반한", ≥50 "많이 좋아하는", ≥21 "좋아하는 것 같은", else(>0) "약간 신경 쓰이는".
- `computeStage`: married→(romance<60→lover, else married); lover→(allowRomantic&&romance≥90→married, romance<60→friendshipStage, else lover); (friend|best_friend)&&allowRomantic&&romance≥60→lover; else friendshipStage.
- `checkBreakupConditions`: stage∉(lover,married)→null; hasCheating→cheating; hasTriangle→triangle; fightUnresolved&&romance<20→fight; romance<20→boredom; else null.
- `applyNaturalDecay`: friendship>0 → max(0, f-0.75); friendship<0 → min(0, f+0.75); romance>0 → max(0, r-0.5).
- `applyDeltas`: friendship/romance만 처리, 클램프, unknown 키 무시.

- [ ] **Step 1: 덤프 섹션 추가 (`dump_relationship_core`)**

`scripts/dump_golden.py`에 추가 + `main()` 호출. Python에서 직접 호출해 expected 생성:
```python
def dump_relationship_core() -> None:
    from tomodachai.relationship import (
        Relationship, RelationshipStage, check_breakup_conditions,
    )

    def mk(f, r, stage):
        rel = Relationship(friendship=f, romance=r, stage=stage)
        return rel

    # friendshipStage / status / friendship_text / romance_text — friendship/romance 격자
    f_vals = [-100, -70, -69, -50, -49, -20, -19, 0, 10, 20, 39, 40, 59, 60, 79, 80, 100]
    r_vals = [-5, 0, 1, 20, 21, 49, 50, 79, 80, 100]
    label_cases = []
    for f in f_vals:
        rel = Relationship(friendship=f, romance=0)
        label_cases.append({
            "input": {"friendship": f},
            "expected": {
                "stage": rel._friendship_stage().value,
                "friendship_text": rel.get_friendship_text(),
            },
        })
    romance_cases = [
        {"input": {"romance": r}, "expected": {"romance_text": Relationship(romance=r).get_romance_text()}}
        for r in r_vals
    ]
    status_cases = [
        {"input": {"stage": s.value}, "expected": Relationship(stage=s).get_status_text()}
        for s in RelationshipStage
    ]
    _write("rel_friendship_labels", label_cases)
    _write("rel_romance_text", romance_cases)
    _write("rel_status_text", status_cases)

    # computeStage — (f, r, stage, allowRomantic) 매트릭스
    stages = [s.value for s in RelationshipStage]
    cs_cases = []
    for stage in stages:
        for r in [0, 55, 60, 89, 90, 100]:
            for allow in (False, True):
                rel = Relationship(friendship=50, romance=r, stage=stage)
                cs_cases.append({
                    "input": {"friendship": 50, "romance": r, "stage": stage, "allow": allow},
                    "expected": rel._compute_stage(allow_romantic_transition=allow).value,
                })
    _write("rel_compute_stage", cs_cases)

    # checkBreakupConditions
    bc_cases = []
    for stage in stages:
        for r in [10, 19, 20, 30]:
            for cheat in (False, True):
                for tri in (False, True):
                    for fu in (False, True):
                        res = check_breakup_conditions(
                            Relationship(romance=r, stage=stage), cheat, tri, fu,
                        )
                        bc_cases.append({
                            "input": {"stage": stage, "romance": r, "cheating": cheat,
                                      "triangle": tri, "fightUnresolved": fu},
                            "expected": res.value if res is not None else None,
                        })
    _write("rel_breakup", bc_cases)

    # applyDeltas / applyNaturalDecay
    delta_cases = []
    for f, r, d in [(50, 50, {"friendship": 60}), (50, 50, {"romance": -70}),
                    (-90, 10, {"friendship": -30}), (50, 50, {"unknown": 5})]:
        rel = Relationship(friendship=f, romance=r)
        rel.apply_deltas(d)
        delta_cases.append({"input": {"friendship": f, "romance": r, "deltas": d},
                            "expected": {"friendship": rel.friendship, "romance": rel.romance}})
    decay_cases = []
    for f, r in [(10, 5), (-10, 0), (0.5, 0.4), (0, 0), (-0.5, 0)]:
        rel = Relationship(friendship=f, romance=r)
        rel.apply_natural_decay()
        decay_cases.append({"input": {"friendship": f, "romance": r},
                            "expected": {"friendship": rel.friendship, "romance": rel.romance}})
    _write("rel_apply_deltas", delta_cases)
    _write("rel_decay", decay_cases)
```
> 주의: `_friendship_stage`/`_compute_stage`는 밑줄 메서드지만 정답지 호출 목적이라 READ-only 사용 OK(정답지 수정 아님).

- [ ] **Step 2: 덤프 실행**

Run (repo 루트): `python scripts/dump_golden.py`
Expected: rel_friendship_labels(17)/rel_romance_text(10)/rel_status_text(6)/rel_compute_stage(72)/rel_breakup(96)/rel_apply_deltas(4)/rel_decay(5) 파일 생성.

- [ ] **Step 3: 로더에 7개 골든 등록**

`loadGolden.ts`에 import + REGISTRY 항목 추가(기존 유지).

- [ ] **Step 4: 실패 테스트 (Red)**

`prototype/web/src/sim/relationship.test.ts` — 각 골든을 로드해 해당 함수 출력과 대조:
```ts
import { describe, it, expect } from "vitest";
import {
  friendshipStage, getFriendshipText, getRomanceText, getStatusText,
  computeStage, checkBreakupConditions, applyDeltas, applyNaturalDecay,
} from "./relationship";
import { loadGolden } from "./__golden__/loadGolden";

describe("friendship labels (golden)", () => {
  for (const c of loadGolden<{ friendship: number }, { stage: string; friendship_text: string }>("rel_friendship_labels")) {
    it(`f=${c.input.friendship}`, () => {
      expect(friendshipStage(c.input.friendship)).toBe(c.expected!.stage);
      expect(getFriendshipText(c.input.friendship)).toBe(c.expected!.friendship_text);
    });
  }
});
describe("romance text (golden)", () => {
  for (const c of loadGolden<{ romance: number }, { romance_text: string | null }>("rel_romance_text"))
    it(`r=${c.input.romance}`, () => expect(getRomanceText(c.input.romance)).toBe(c.expected!.romance_text));
});
describe("status text (golden)", () => {
  for (const c of loadGolden<{ stage: string }, string>("rel_status_text"))
    it(`${c.input.stage}`, () => expect(getStatusText(c.input.stage as never)).toBe(c.expected));
});
describe("computeStage (golden)", () => {
  for (const c of loadGolden<{ friendship: number; romance: number; stage: string; allow: boolean }, string>("rel_compute_stage"))
    it(`${c.input.stage}/r${c.input.romance}/a${c.input.allow}`, () =>
      expect(computeStage(c.input.friendship, c.input.romance, c.input.stage as never, c.input.allow)).toBe(c.expected));
});
describe("checkBreakupConditions (golden)", () => {
  for (const c of loadGolden<{ stage: string; romance: number; cheating: boolean; triangle: boolean; fightUnresolved: boolean }, string | null>("rel_breakup"))
    it(`${c.input.stage}/r${c.input.romance}/c${c.input.cheating}/t${c.input.triangle}/f${c.input.fightUnresolved}`, () =>
      expect(checkBreakupConditions(c.input.stage as never, c.input.romance, c.input.cheating, c.input.triangle, c.input.fightUnresolved)).toBe(c.expected));
});
describe("applyDeltas (golden)", () => {
  for (const c of loadGolden<{ friendship: number; romance: number; deltas: Record<string, number> }, { friendship: number; romance: number }>("rel_apply_deltas"))
    it(`${JSON.stringify(c.input.deltas)}`, () => {
      const out = applyDeltas({ friendship: c.input.friendship, romance: c.input.romance, stage: "stranger" }, c.input.deltas);
      expect({ friendship: out.friendship, romance: out.romance }).toEqual(c.expected);
    });
});
describe("applyNaturalDecay (golden)", () => {
  for (const c of loadGolden<{ friendship: number; romance: number }, { friendship: number; romance: number }>("rel_decay"))
    it(`f${c.input.friendship}/r${c.input.romance}`, () => {
      const out = applyNaturalDecay({ friendship: c.input.friendship, romance: c.input.romance, stage: "stranger" });
      expect({ friendship: out.friendship, romance: out.romance }).toEqual(c.expected);
    });
});
```

- [ ] **Step 5: 실패 확인**

Run (`prototype/web`): `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH" npm test`
Expected: FAIL — relationship.ts 함수 미정의.

- [ ] **Step 6: 구현 (`relationship.ts`)**

`relationship.py`의 enum/라벨/스테이지/breakup/decay/deltas 로직을 위 "오라클 정확 임계"대로 TS 순수함수로 포팅. 클램프 헬퍼(`clamp(v, lo, hi)`) 사용. `applyDeltas`/`applyNaturalDecay`는 `{...rel}` 복사 후 수정해 반환(원본 불변).

- [ ] **Step 7: 통과 확인**

Run (`prototype/web`): `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH" npm test`
Expected: PASS — 신규 7골든 + 기존 87.

- [ ] **Step 8: 커밋**

```bash
git add scripts/dump_golden.py prototype/web/src/sim/relationship.ts prototype/web/src/sim/relationship.test.ts prototype/web/src/sim/__golden__/loadGolden.ts prototype/web/src/sim/__golden__/rel_*.json
git commit -m "feat(sim): relationship 코어 — 라벨/스테이지/breakup/decay 포팅 (골든)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: 호환성 — `personalityGroup` + `calculateCompatibility` (순수, 골든)

**Files:**
- Modify: `scripts/dump_golden.py`, `loadGolden.ts`
- Create: `prototype/web/src/sim/compatibility.ts`, `prototype/web/src/sim/compatibility.test.ts`

**Interfaces (Produces):**
- `personalityGroup(code: string): string | null` — `"<prefix>_..."` → 한글 그룹("안정파"/"사교파"/"주도파"/"신중파"), 미인식 null.
- `calculateCompatibility(pA: string, pB: string, bloodA: string, bloodB: string, zodiacA: string, zodiacB: string): number` — `round(p*0.5 + b*0.3 + z*0.2, 4)`.

**오라클 정확 테이블 (`relationship.py`):**
- `_CODE_TO_GROUP`: easygoing→안정파, outgoing→사교파, confident→주도파, independent→신중파.
- 성격(50%) `_GROUP_COMPAT` (대칭): (안정,사교)=0.85, (신중,주도)=0.85; 동일그룹 0.60; (안정,신중)=0.40; (안정,주도)=0.35; (사교,신중)=0.45; (사교,주도)=0.40. 미스/null → 0.50.
- 혈액(30%) `_BLOOD_COMPAT` (대문자, 대칭): (O,A)=0.85,(O,B)=0.75,(O,O)=0.80,(A,A)=0.75,(B,B)=0.75,(AB,O)=0.70,(AB,A)=0.60,(AB,B)=0.60,(AB,AB)=0.55,(A,B)=0.35. 미스 → 0.55.
- 별자리(20%): `_ZODIAC_ELEMENTS`(양/사자/사수=불, 황소/처녀/염소=땅, 쌍둥이/천칭/물병=바람, 게/전갈/물고기=물). 같은 원소 0.80; 상보쌍 {불,바람} 또는 {땅,물} 0.70; 그 외 0.45; 미인식 0.55.

- [ ] **Step 1: 덤프 (`dump_compatibility`)**

```python
def dump_compatibility() -> None:
    from tomodachai.relationship import _personality_group, calculate_compatibility

    codes = ["easygoing_softie", "outgoing_charmer", "confident_busybee",
             "independent_thinker", "weird_unknown"]
    group_cases = [{"input": c, "expected": _personality_group(c)} for c in codes]
    _write("personality_group", group_cases)

    # 대표 매트릭스 (성격쌍×혈액쌍×별자리쌍 일부 + null/미인식)
    samples = [
        ("easygoing_softie", "outgoing_charmer", "O", "A", "양자리", "천칭자리"),
        ("confident_busybee", "independent_thinker", "AB", "AB", "황소자리", "게자리"),
        ("easygoing_softie", "easygoing_optimist", "A", "B", "양자리", "양자리"),
        ("outgoing_charmer", "independent_thinker", "B", "B", "사자자리", "물병자리"),
        ("weird_x", "outgoing_charmer", "X", "A", "??", "양자리"),
    ]
    comp_cases = [
        {"input": {"pA": a, "pB": b, "bloodA": ba, "bloodB": bb, "zA": za, "zB": zb},
         "expected": calculate_compatibility(a, b, ba, bb, za, zb)}
        for (a, b, ba, bb, za, zb) in samples
    ]
    _write("calculate_compatibility", comp_cases)
```
`main()`에 `dump_compatibility()` 추가.

- [ ] **Step 2~5:** 덤프 실행 → 로더 등록 → 실패 테스트(`compatibility.test.ts`, 위 두 골든 대조) → 실패 확인. (Task 1과 동일 패턴, Node 22 프리픽스)

- [ ] **Step 6: 구현 (`compatibility.ts`)**

위 정확 테이블로 포팅. 4자리 반올림은 **골든이 진실** — Python `round(x,4)`(banker's, half-to-even)와 JS가 어긋나면 banker's 기반 4자리 헬퍼로 맞춘다(불일치 케이스가 골든에서 드러남).

- [ ] **Step 7~8:** 통과 확인 → 커밋(`feat(sim): 호환성 personalityGroup+calculateCompatibility 포팅 (골든)` + 트레일러). Stage: compatibility.ts/test, dump_golden.py, loadGolden.ts, personality_group.json, calculate_compatibility.json.

---

## Task 3: `RelationshipTracker` 상태기계 (통합 테스트)

**Files:**
- Create: `prototype/web/src/sim/relationshipTracker.ts`, `prototype/web/src/sim/relationshipTracker.test.ts`

**Interfaces (Produces):**
- 타입: `RelationshipSlots {best_friend: number|null; lover: number|null; enemy: number|null}`, `Fight {participants:[number,number]; cause:string; resolved:boolean; witnessed_by_player:boolean}`, `ExLoverTag {target:number; reason:BreakupReason; day:number}`, `Triangle {jealous:number; target:number; rival:number; romance_level:number}`.
- `class RelationshipTracker`: `get(a,b)`, `update(a,b,deltas)`, `applyDailyDecay(df?,dr?)`, `allPairs()`, `getSlots(id)`, `setLover(a,b)`, `clearLover(a,b)`, `recomputeSlots(id)`, `addExLoverTag/getExLoverTags/removeExLoverTag`, `addFight/getFights/resolveFight`, `getRomanticInterests(id,th=20)`, `getFriends(id,th=50)`, `getRivals(id,th=-50)`.
- `detectTriangles(tracker, romanceTh=30, friendshipTh=30): Triangle[]`, `applyJealousy(tracker, triangles, rate=0.3): void`.

**오라클 규칙 (`relationship.py`):** Plan 스코핑 §3대로. 핵심:
- 키는 **순서 있음** `(a,b)≠(b,a)`(비대칭). `get`은 없으면 default 생성. JS는 `Map<string,Relationship>` 키 `` `${a},${b}` ``.
- `setLover`: 양쪽 slots.lover 상호 설정. `clearLover`: 서로 가리킬 때만 해제.
- `recomputeSlots(id)`: best_friend = 양방향 friendship≥70 중 `id→other` 최대값(1명); enemy = 양방향 ≤-50 중 최소값(1명). lover slot 미변경. (초기 비교값 70.0/-50.0, 초과/미만 시 교체)
- `getFights`: 미해결만. `resolveFight(parts)`: set 비교 첫 미해결 resolved=True, 반환 bool.
- `getRomanticInterests/getFriends/getRivals`: `id→b` 필터 + 정렬(로맨스/우정 desc, 라이벌 asc).
- `detectTriangles`: 결정론(스코핑 §2 끝). `applyJealousy`: 각 삼각 `delta = -(romance_level*0.3*0.1)`로 `update(jealous,rival,{friendship:delta})`.

- [ ] **Step 1: 통합 테스트 (Red)**

`relationshipTracker.test.ts` — 트래커 구성→연산→단언으로 규칙 검증(골든 아님, 시나리오 기반). 최소 케이스: 비대칭 키, update 클램프, setLover/clearLover 상호성, recomputeSlots(양방향 70/-50 경계 + 단일 선택), getFights/resolveFight(set 비교), getRomanticInterests/getFriends/getRivals 정렬, applyJealousy 델타값. 각 단언의 기대값은 **`relationship.py` 규칙으로 손계산**해 명시.
> 예) `recomputeSlots`: A→B=75, B→A=72 (양방향≥70) ⇒ slots[A].best_friend=B. A→C=80 but C→A=10 (비대칭) ⇒ C는 후보 아님.

- [ ] **Step 2~7:** 실패 확인 → `relationshipTracker.ts` 구현(상태기계, Map 기반) → 통과 확인(Node 22). 풀 `npm test` 그린.

- [ ] **Step 8: 커밋** (`feat(sim): RelationshipTracker 상태기계 포팅 (통합 테스트)` + 트레일러). Stage: relationshipTracker.ts/test.

---

## Task 4: `memory.ts` — SocialEvent + MemoryStore

**Files:**
- Create: `prototype/web/src/sim/memory.ts`, `prototype/web/src/sim/memory.test.ts`

**Interfaces (Produces):**
- `interface SocialEvent {id:number; type:string; participants:number[]; day:number; time:string|null; location:string|null; reason:string|null; result:string|null}`, `defaultSocialEvent(partial): SocialEvent` (time/location/reason/result 기본 null).
- `class MemoryStore`: `addEvent(e)`, `getEventsFor(id, limit=10)`, `getEventsBetween(a, b, limit=5)`.

**오라클 규칙 (`memory.py`):**
- `addEvent`: `e.id===0` → `_nextId` 부여; `_nextId = max(_nextId, e.id)+1`; append.
- `getEventsFor`: participants에 id 포함 필터 → day desc 정렬 → 앞 limit.
- `getEventsBetween`: 양쪽 id 포함 → day desc → 앞 limit.

- [ ] **Step 1: 통합 테스트 (Red)** — `memory.test.ts`: id 자동부여 시퀀스(0→1→2, 명시 id 후 next 갱신), getEventsFor 필터·day desc·limit, getEventsBetween 양자 필터. 기대값 손계산 명시.
- [ ] **Step 2~7:** 실패 확인 → `memory.ts` 구현 → 통과(Node 22) → 풀 `npm test` 그린.
- [ ] **Step 8: 커밋** (`feat(sim): memory SocialEvent + MemoryStore 포팅` + 트레일러). Stage: memory.ts/test.

---

## Self-Review (작성자 체크)
- **커버리지:** relationship.py 라벨/스테이지/breakup/decay/deltas(골든) + 호환성(골든) + Tracker(통합) + memory(통합). detectTriangles/applyJealousy는 Tracker 통합에 포함.
- **Deferred 명시:** sim 트리거(RNG)·save 직렬화·LLM 렌더링·틱 훅.
- **Type 일관:** `RelationshipStage`/`BreakupReason`(Task1) → Task2/3 소비. `Relationship`(Task1) → Tracker 저장. 골든 케이스 모양 일치.
- **충실도 장치:** 순수함수는 Python 직접 호출 골든; 상태기계는 손계산 기대값 통합 테스트(Python 규칙 기반).
