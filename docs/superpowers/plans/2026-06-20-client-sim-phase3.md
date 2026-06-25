# 클라 시뮬 Phase 3 — location + shop 포팅 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Python `location.py`/`shop.py`의 결정론적 로직(장소 카탈로그·레지스트리·쿼리·이동·스냅샷, 상점 카탈로그·접근자·직렬화, 목적지 가중치 산출)을 TS `src/sim/`로 충실 포팅. 순수함수·데이터는 골든, 상태기계는 통합 테스트. RNG는 **주입식**, 난수열 자체는 언어간 미일치(Phase 0 결정).

**Architecture:** Phase 0~2 패턴 — Python=오라클, 결정론 골든 1:1, `src/sim/` 프레임워크 무의존. location/shop은 `Character`(Phase1)·`RelationshipTracker`(Phase2) 타입을 일부 소비. RNG-사용 메서드(`choose_destination`·`refresh_daily`)는 (a)결정론 부분(가중치 산출/카운트/카테고리)만 검증, (b)최종 난수선택은 주입된 rng로 구조만 통합 테스트(Python 난수열과 안 맞춤).

**Tech Stack:** TS, vitest, 골든 하니스. 정답지: `src/tomodachai/location.py`, `src/tomodachai/shop.py`.

## Global Constraints
- **Python 정답지 수정 금지** (`src/tomodachai/**`, `tests/**` 읽기 전용; 덤프는 READ만).
- **`src/sim/`는 프레임워크 무의존**.
- **Node 18+** — node/npm은 `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH"` 프리픽스.
- **Python 덤프**: repo 루트 `python scripts/dump_golden.py`.
- **작업 디렉터리 persists** — repo 루트(python/git) vs `prototype/web`(npm) 명시적 cd.
- **각 태스크 검증에 `npm run check`(svelte-check) 포함** — vitest는 타입체크를 안 하므로 테스트파일 타입에러를 잡으려면 필수(Phase 2 교훈).
- **사용자 WIP `git add` 금지**: `CLAUDE.md`, `docs/plan/01-character.md`, `docs/plan/03-space-and-events.md`, untracked `.mcp.json`/`godot/`/`mii.blend*`/`sh.exe.stackdump`.
- **브랜치** `feat/client-sim-migration`, main 직접 푸시 금지.
- **커밋 트레일러**: 끝에 정확히 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **포팅 충실도:** 임계 숫자·라벨·기본값·카탈로그 항목 그대로. RNG는 주입 인터페이스로 분리.

## 범위 밖 (Phase 3 아님)
- `choose_destination`/`refresh_daily`의 최종 난수 선택을 Python 난수열과 일치시키는 것(비트정확 RNG는 Phase 0에서 기각). 주입 rng로 구조만 검증.
- 아이템 마스터/실제 가격(`_get_item_price`는 항상 1000 placeholder — 그대로 포팅, 확장 금지).
- `_seasonal_items` 생성 로직(이 파일에 없음 — 이벤트 시스템 후속).
- 전체 `GameState` 포팅 — shop은 `spend_money(amount)->bool` 덕타입만 필요.
- save.py 디스크 라운드트립(serialize/deserialize 단위 검증만).

## File Structure
- `prototype/web/src/sim/location.ts` (생성) — `LocationType`·`Location`·`DEFAULT_LOCATIONS`·`DEFAULT_PUBLIC_WEIGHTS` + `LocationManager` + `buildDestinationWeights`/`chooseDestination`.
- `prototype/web/src/sim/shop.ts` (생성) — 상수 + `ShopManager`.
- 각 `*.test.ts`, `scripts/dump_golden.py`(섹션 추가), `loadGolden.ts`(레지스트리 확장).

---

## Task 1: Location 모델 + 카탈로그 (골든)

**Files:** Modify `scripts/dump_golden.py`, `loadGolden.ts`; Create `prototype/web/src/sim/location.ts`(이 태스크: 타입+카탈로그만), `prototype/web/src/sim/location.test.ts`.

**Interfaces (Produces):**
- `LocationType = "private_room" | "shared_room" | "public"`.
- `interface Location { id: string; name: string; capacity: number; location_type: LocationType; event_types: string[]; description: string }`, `defaultLocation(partial): Location` (capacity=6, location_type="public", event_types=[], description="").
- `DEFAULT_LOCATIONS: Location[]` (15개), `DEFAULT_PUBLIC_WEIGHTS: Record<string, number>` (15개).

**오라클:** `location.py`의 `_HOUSE_SHARED`(2) + `_PUBLIC_LOCATIONS`(13) = `DEFAULT_LOCATIONS`(15), `_DEFAULT_PUBLIC_WEIGHTS`. **정확 값은 정답지 파일을 읽어 그대로**(15개 항목 id/name/capacity/type/event_types/description). 골든 default-dump가 충실도 강제.

- [ ] **Step 1: 덤프 (`dump_location_catalog`)** — Python `DEFAULT_LOCATIONS`/`_DEFAULT_PUBLIC_WEIGHTS`를 직렬화:
```python
def dump_location_catalog() -> None:
    from tomodachai.location import DEFAULT_LOCATIONS, _DEFAULT_PUBLIC_WEIGHTS
    locs = [loc.model_dump() for loc in DEFAULT_LOCATIONS]
    # location_type은 enum → .value 로 직렬화됨 확인 (model_dump가 str enum을 value로)
    _write("location_catalog", [{"input": "DEFAULT_LOCATIONS", "expected": locs}])
    _write("location_weights", [{"input": "weights", "expected": dict(_DEFAULT_PUBLIC_WEIGHTS)}])
```
`main()`에 호출 추가.
> 주의: `DEFAULT_LOCATIONS`가 모듈 최상위에 노출돼 있는지 확인(없으면 `LocationManager().all_locations()`의 기본 15개로 덤프). enum str 직렬화 형태 확인.

- [ ] **Step 2: 덤프 실행** — `python scripts/dump_golden.py` → location_catalog(1, 15항목)/location_weights(1).
- [ ] **Step 3: 로더 등록** — `loadGolden.ts`에 2개 추가.
- [ ] **Step 4: 실패 테스트 (Red)** — `location.test.ts`: `DEFAULT_LOCATIONS.map(model_dump 형태)` === golden expected, `DEFAULT_PUBLIC_WEIGHTS` === golden. `toEqual`.
- [ ] **Step 5: 실패 확인** — `PATH=...v22.20.0:$PATH npm test` → FAIL.
- [ ] **Step 6: 구현** — `location.ts`에 타입 + `DEFAULT_LOCATIONS`(15개, 정답지 그대로) + `DEFAULT_PUBLIC_WEIGHTS`. 골든이 누락/오타를 잡는다.
- [ ] **Step 7: 통과 + check** — `npm test` PASS, `npm run check` 0 errors.
- [ ] **Step 8: 커밋** (`feat(sim): Location 모델 + 장소 카탈로그 (골든)` + 트레일러). Stage: location.ts/test, dump_golden.py, loadGolden.ts, location_catalog.json, location_weights.json.

---

## Task 2: LocationManager 레지스트리 + 쿼리 + 이동/스냅샷 (통합)

**Files:** Modify `prototype/web/src/sim/location.ts`, Create `prototype/web/src/sim/locationManager.test.ts`.

**Interfaces (Produces):** `class LocationManager` (`location.ts`에 추가):
- ctor(extraLocations?: Location[]) → `_locations: Map<string,Location>`(15 기본 + extra), `_positions: Map<number,string>`.
- `addLocation(loc)`, `registerPrivateRoom(charId, charName): Location`, `getLocation(id)`, `getLocationByName(name)`, `allLocations()`, `publicLocations()`, `sharedLocations()`, `getCharactersAt(id): number[]`, `getCharacterLocation(charId): string|null`, `isAtCapacity(id): boolean`(loc 없으면 true), `moveCharacter(charId, dest): boolean`(id→name fallback, 없으면 false), `removeCharacter(charId)`, `snapshot(): dict[]`(키 id/name/location_type/capacity/event_types/description/characters).

**오라클:** `location.py` `LocationManager` 메서드대로. `registerPrivateRoom`: id=`room_{charId}`, name=`{charName}의 방`, capacity=2, type=private_room, event_types=["sleep","personal_event","room_visit","gift","consultation"], description=`{charName}의 개인 방`.

- [ ] **Step 1: 통합 테스트 (Red)** — 손계산 기대값: ctor 15개, registerPrivateRoom 포맷, move id/name/실패, isAtCapacity(정원/없음), getCharactersAt 필터, public/shared 필터, snapshot 구조. `registerPrivateRoom` 포맷은 golden으로도 1케이스 덤프 가능(원하면).
- [ ] **Step 2~7:** 실패 확인 → 구현 → `npm test` PASS + `npm run check` 0.
- [ ] **Step 8: 커밋** (`feat(sim): LocationManager 레지스트리/쿼리/이동/스냅샷 (통합)` + 트레일러).

---

## Task 3: `buildDestinationWeights` (골든) + `chooseDestination` (주입 rng)

**Files:** Modify `prototype/web/src/sim/location.ts`, `scripts/dump_golden.py`, `loadGolden.ts`, Create `prototype/web/src/sim/destination.test.ts`.

**Interfaces (Produces):**
- `buildDestinationWeights(char, allPairs, positions, manager): Record<string,number>` — 순수. `_DEFAULT_PUBLIC_WEIGHTS` 복사 후 규칙 적용(아래). char는 `{id, hunger, satisfaction, stress}` 덕타입(또는 Character + state 접근), allPairs는 `[a,b,{friendship}][]`.
- `chooseDestination(char, allPairs, timeOfDay, manager, rng): string` — 밤 분기(rng.random()<0.7→`room_{id}`) + buildWeights + `rng.choices(ids, weights)`. rng는 `{random():number; choices(items, weights):T}` 주입 인터페이스.

**오라클 가중치 규칙 (`location.py` `choose_destination`):**
1. 배고픔 hunger>70 → weights["grocery"]*=10
2. 불만족 satisfaction<20 → park/cafe/beach/amusement_park *=2.5
3. 스트레스 stress>7 → beach*=3, balcony*=2
4. 친구: allPairs 중 char.id 포함 & friendship>=60 → 상대 위치 weights*=3 (상대가 weights에 있으면)
5. 정원초과: isAtCapacity인 loc → *=0.3
(밤 분기는 chooseDestination에서; buildWeights는 2~5만)

- [ ] **Step 1: 덤프 (`dump_destination_weights`)** — `choose_destination` 내부 가중치 산출은 Python에 분리 함수가 없으니, **buildWeights 동등 계산을 Python에서 인라인 재현**해 골든 생성(또는 시나리오별 char/positions 고정 후 기대 weights를 손계산). 권장: Python에서 동일 규칙을 적용하는 작은 헬퍼를 **덤프 스크립트 안에** 작성(정답지 미수정) — char state·friendship·capacity 시나리오 3~4개 → expected weights dict. 단, capacity 룰은 positions 고정 필요.
> 대안(단순): buildWeights를 골든 없이 **통합 테스트**(손계산 기대 weights)로 검증. 가중치 규칙이 명확한 곱셈이라 손계산이 신뢰할 만함. 이 경우 Step1~3·골든 생략하고 destination.test.ts에서 직접 단언.
- [ ] **Step 2: 구현 + 테스트** — `buildDestinationWeights` 순수 구현 + 위 규칙 통합(또는 골든) 테스트. `chooseDestination`은 주입 rng로 밤 분기·최종 선택을 **구조 검증**(예: stub rng가 random()=0.5 반환 시 밤이면 room, choices가 첫 항목 반환하도록 → 결정성 확보). Python 난수열 미일치.
- [ ] **Step 3: 통과 + check + 커밋** (`feat(sim): 목적지 가중치 buildDestinationWeights + chooseDestination(주입 rng)` + 트레일러).

---

## Task 4: ShopManager (골든 + 통합)

**Files:** Modify `scripts/dump_golden.py`, `loadGolden.ts`; Create `prototype/web/src/sim/shop.ts`, `prototype/web/src/sim/shop.test.ts`.

**Interfaces (Produces):**
- 상수 export: `CATEGORIES=["food","clothing","interior"]`, `HOLIDAYS={"04-14":99}`, `DEFAULT_POOL`(food 1..100, clothing 101..200, interior 201..300), `DAILY_COUNT={food:3,clothing:2,interior:1}`, `MORNING_MARKET_DISCOUNT_RATE=0.6`, `MORNING_MARKET_BASE_PRICE=2500`.
- `class ShopManager`: `_dailyItems`, `_morningMarket`, `_seasonalItems`, `_catalog`(Map<string,Set<number>>). 메서드: `getDaily(cat)`, `getMorningMarket()`, `getSeasonal()`, `getCatalog(cat)`(sorted), `addToCatalog(cat,id)`, `buy(itemId, gameState)`(spend_money 덕타입, 가격 1000, 카탈로그 추가), `buyMorningMarket(gameState)`(food 분류, 가격=morningMarket.discount_price), `refreshDaily(day, rng?, dateStr?)`(주입 rng — 구조만), `serialize()`, `deserialize(data)`.
- `interface MoneySpender { spendMoney(amount: number): boolean }` (GameState 덕타입).

**오라클:** `shop.py`대로. `_get_item_price`는 항상 1000(placeholder 그대로). morning market discount_price = int(2500*0.6)=1500. `get_catalog`은 sorted. `serialize` 구조 §스코핑대로.

- [ ] **Step 1: 덤프 (`dump_shop_constants`)** — 상수·discount price·serialize(빈 상태)·deserialize 라운드트립 expected를 Python에서 덤프:
```python
def dump_shop_constants() -> None:
    from tomodachai.shop import (
        CATEGORIES, HOLIDAYS, _DAILY_COUNT, _MORNING_MARKET_DISCOUNT_RATE,
        _MORNING_MARKET_BASE_PRICE, ShopManager,
    )
    sm = ShopManager()
    sm.add_to_catalog("food", 5); sm.add_to_catalog("food", 1)
    cases = [
        {"input": "categories", "expected": list(CATEGORIES)},
        {"input": "holidays", "expected": dict(HOLIDAYS)},
        {"input": "daily_count", "expected": dict(_DAILY_COUNT)},
        {"input": "discount_price", "expected": int(_MORNING_MARKET_BASE_PRICE * _MORNING_MARKET_DISCOUNT_RATE)},
        {"input": "catalog_sorted", "expected": sm.get_catalog("food")},  # [1,5]
        {"input": "serialize_empty_then_food15", "expected": sm.serialize()},
    ]
    _write("shop_constants", cases)
```
`main()`에 호출.
- [ ] **Step 2~5:** 덤프 → 로더 등록 → 실패 테스트(`shop.test.ts`: 상수·discount·get_catalog sort·serialize 골든 + addToCatalog/getDaily/deserialize 통합) → 실패 확인.
- [ ] **Step 6: 구현** — `shop.ts`. `_get_item_price`=1000 그대로. `refreshDaily`는 주입 rng의 `sample`/`choice`로 구조(카운트·풀 범위)만 검증(Python 난수열 미일치). `buy`/`buyMorningMarket`는 `MoneySpender` 스텁으로 통합 테스트(잔액부족 false, 성공 시 catalog 추가).
- [ ] **Step 7: 통과 + check** — `npm test` PASS, `npm run check` 0.
- [ ] **Step 8: 커밋** (`feat(sim): ShopManager 포팅 (골든 상수/직렬화 + 통합)` + 트레일러). Stage: shop.ts/test, dump_golden.py, loadGolden.ts, shop_constants.json.

---

## Self-Review (작성자 체크)
- **커버리지:** location 카탈로그(골든) + Manager(통합) + 목적지 가중치(골든/통합) ; shop 상수·직렬화(골든) + Manager(통합). RNG 최종선택은 주입·구조검증(Phase 0 결정 일관).
- **Deferred 명시:** 난수열 일치·아이템 가격·seasonal·전체 GameState·디스크 IO.
- **Type 일관:** `Location`/`LocationType`(T1) → Manager(T2)/weights(T3). `Character`(Phase1)·allPairs(Phase2 `RelationshipTracker.allPairs()` 형태) 소비. shop `MoneySpender` 덕타입.
- **교훈 반영:** 각 태스크 검증에 `npm run check` 포함.
