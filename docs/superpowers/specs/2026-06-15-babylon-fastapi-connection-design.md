# 설계: Babylon 프론트엔드 ↔ FastAPI 백엔드 연결

- **날짜:** 2026-06-15
- **브랜치:** `feat/connect-frontend-backend`
- **상태:** 설계 승인됨 (구현 계획 대기)

## 1. 목표

`prototype/web`의 Babylon.js 3D 클라이언트를 stdlib `prototype/web_server.py` 대신
`src/tomodachai`의 FastAPI 백엔드에 연결한다. 두 스택은 그동안 따로 컸고(프론트는
관찰+개입 렌더러, FastAPI는 자율시뮬+상점/뉴스/분수대/세이브) 기능 집합이 어긋나 있으므로,
**둘 사이의 API 계약을 먼저 고정**하고 프론트/백엔드를 **병렬 트랙**으로 채운다.

## 2. 아키텍처 — 계약 seam + 병렬 트랙

```
Babylon 프론트 (Svelte/Vite/web)          FastAPI (src/tomodachai)
  거의 그대로 유지, 폴링 1.5s     ──▶   compat 라우터 (api/snapshot.py, 신규)
  GET /api/snapshot?since=N             └─ 조립/변환 ─▶ GameState + 신규 메커닉
  POST /feed /give /bubble /save /reset
```

- **계약(seam):** 기존 프론트의 `Snapshot` DTO + write 액션을 **그대로** 인터페이스로 동결.
  이것이 두 트랙의 합류점이며, 프론트는 이미 이 계약을 말하므로 거의 수정 없이 붙는다.
- **프론트 트랙(가벼움):** API 베이스 URL을 `http://127.0.0.1:8000/api`로 변경, 응답 필드 갭만 보정,
  폴링 유지. 아직 백엔드가 없는 UI 버튼은 비활성 게이팅.
- **백엔드 트랙(무거움, 내부 병렬 분할):** snapshot 집계기 + 7개 신규 메커닉. 각 메커닉은 서로 독립.
- **은퇴:** 계약이 FastAPI로 옮겨가면 `prototype/web_server.py`는 제거하거나 dev 폴백으로만 둔다.

### 결정 사항 (승인됨)
- ⓐ 계약 = 기존 프론트 `Snapshot` 스키마 그대로. ⓑ 폴링(1.5s, `since` 증분) 유지. ⓒ `web_server.py` 은퇴.
- 모든 NEW 메커닉의 공식·임계값은 **`prototype/game` 원본 규칙 그대로** 이식 (복붙이 아니라 `src/tomodachai` 모델 위에 재구현).

## 3. 계약 상세 (정답지 = `prototype/web_server.py`의 `snapshot()`/write 핸들러)

### 3.1 읽기 — `GET /api/snapshot?since=N` → `Snapshot`

프론트 `prototype/web/src/lib/types.ts`의 `Snapshot`/`Character`/`EventItem`/`Bubble`/`Rankings`
스키마와 **필드·타입이 정확히 일치**해야 한다. 분류: MAP=변환만, NEW=신규 메커닉 필요.

| 필드 | 출처 / 처리 | 분류 |
|---|---|---|
| `village` | `gs.island_name` | MAP |
| `provider` | `gs.config.llm.provider` | MAP |
| `day` | `gs.day_count` | MAP |
| `clock` `minutes` | time_system → `"HH:MM"` + 자정 기준 분 | MAP |
| `seq` | 이벤트 로그 단조 증가 인덱스 (since 증분 기준) | NEW(작음) |
| `asleep` `realtime` | 수면창(23:00–07:00) 플래그 / `true` | MAP |
| `locations` | `Record<string,string>` = 장소ID→라벨 (capacity 제외) | MAP |
| `foods` | 음식 카탈로그 이름 목록 | MAP |
| `characters[].{id,name,location,hunger,satisfaction}` | CharacterOut 직매핑 (hunger/satisfaction은 `round`) | MAP |
| `characters[].gender` | `"남성/여성" → "M"/"F"` | MAP |
| `characters[].mood` | 3축 → 한글 라벨 (§4.1) | MAP+규칙 |
| `characters[].{lover,best_friend,enemy}` | `RelationshipSlots` id→이름 | MAP |
| `characters[].crushes[]` | `spark==True AND slots.lover≠상대` (§4.3) | MAP+규칙 |
| `characters[].food_eaten[]` | `preferences.food_eaten` | MAP |
| `characters[].friends[]` | 우정 top5 + `relation_brief` 라벨 (§4.3) | MAP+규칙 |
| `characters[].dex[]` | 먹어본 음식만 `preference_tier` 공개 (§4.2) | MAP+규칙 |
| `events[]` | 이벤트 로그 → `{seq,day,clock,scene,dialogue:[[s,t]],messages[],major}` | MAP |
| `rankings` | best_couple/popular_m·f/fighters 계산 (§4.4) | NEW |
| `photos[]` `dishes[]` | 카메라/프라이팬 산출물 (§4.5) | NEW |
| `bubbles[]` | 고백 승인 대기 말풍선 (§4.6) | NEW |

### 3.2 쓰기 액션

| 엔드포인트 | 처리 | 분류 |
|---|---|---|
| `POST /api/feed {char_id, food_id}` | 먹이기 (§4.2) | NEW |
| `POST /api/give {char_id, tool}` | `camera→사진` / `frying_pan→요리` (§4.5) | NEW |
| `POST /api/bubble {index, char, answer}` | 고백 승인/거절 → 결과 이벤트 push (§4.6) | NEW |
| `POST /api/save {}` | 기존 save (기본 슬롯/temp) | MAP |
| `POST /api/reset {}` | 새 마을 재생성 + 세이브 덮어쓰기 | NEW(작음) |

> 주의: 기존 프론트는 `since=cursor`로 받은 `snap.seq`를 다음 커서로 쓴다. write 액션도
> 결과를 이벤트 로그에 push(seq 증가)하여 다음 폴링에서 3D 연출로 재생되게 한다
> (`web_server.py`의 feed/give/answer_bubble과 동일).

## 4. NEW 메커닉 — prototype/game 규칙 그대로 이식

> 모두 `src/tomodachai` 모델 위에 재구현. 아래는 `prototype/game` 원본 공식.

### 4.1 기분 라벨 (`game/models.py` `Mood.label()`, 0~10 스케일)
```
stress >= 7   → energy >= 5 ? "짜증남" : "지침"
happiness >= 7 → energy >= 6 ? "신남" : "흐뭇함"
happiness <= 3 → energy <= 4 ? "우울함" : "심술남"
energy <= 3   → "나른함"
else          → "평온함"
```
src `Mood`(happiness/energy/stress, 0~10)와 스케일 동일 → `label()` 메서드/직렬화 함수로 추가.

### 4.2 음식 — `preference_tier` / `feed` (`game/items.py`)
- tier (rank 0=최애, n=음식수): `rank<2 favorite / <4 like / ≥n-2 worst / ≥n-4 dislike / else normal`
- `TIER_REACTIONS` (텍스트, 만족도Δ, (happiness,energy,stress)Δ):
  - favorite: "최애예요!! …", +8, (+2.5,+1.0,-1.0)
  - like: "웃으며 맛있게 먹습니다.", +4, (+1.5,+0.5,-0.5)
  - normal: "무난하게 먹습니다.", +1, (+0.5,+0.3,0)
  - dislike: "찡그리며 억지로 삼킵니다...", -3, (-1.5,0,+1.0)
  - worst: "우웩! …", -6, (-2.5,-1.0,+2.0)
- `feed`: `hunger=max(0,hunger-50)`, hungry 말풍선 제거, `satisfaction=min(100,+sat)`,
  `mood.adjust(h,e,s)`, 첫 섭취 시 `food_eaten[fid]=True`(+"(도감에 기록!)"). 즉시 저장.
- src 갭: `food_ranks`/`food_eaten` 존재 ✓. 음식 마스터(`FOODS` 10종)는 `src` 카탈로그와 정합 확인.

### 4.3 관계 라벨 (`game/relationship.py`)
- `crushes`: `rel.spark==True AND slots.lover != 상대`.
- `friends` 라벨 = `relation_brief`: `friendship_label(friendship) + romance_label(romance) +`
  `[반함]`(spark&비연인) `[베프]` `[연인]` `[원수]` `[전 연인]`(ex_lover) 태그. **수치 비노출.**
- `friendship_label`/`romance_label` 임계 테이블은 `game/relationship.py`의
  `FRIENDSHIP_LABELS`/`ROMANCE_LABELS`를 원본으로 이식 (src 스케일 friendship −100~100 / romance 0~100에 정합, 양쪽 모두 베프 임계 70 기준 정렬됨).
- src 갭: `Relationship.spark` 플래그 **추가**, ex_lover 태그 **추가**(없으면 `[전 연인]`은 후속으로 deferred 가능).

### 4.4 랭킹 (`web_server.py` `_rankings`)
- `best_couple`: 연인 슬롯 쌍의 양방향 `friendship+romance` 합 내림차순 top3 (`"A ❤ B"`).
- `popular_m`/`popular_f`: 성별별, 받은 romance 합 내림차순 top3 (단 합 > 0).
- `fighters`: `fight` 이벤트 참가쌍 횟수 내림차순 top3 (`"A ✕ B (n회)"`).
- src 갭: `fight` 이벤트 집계 소스 확인(메모리/이벤트 로그), 성별·슬롯 접근 경로 매핑.

### 4.5 도구 (`web_server.py` `give` → `sim.use_tool`)
- `camera` → 사진 1장 생성 → `photos` 저장소에 `{day, author, title, subject}` append.
- `frying_pan` → 요리 1건 생성 → `dishes` 저장소에 `{day, author, dish}` append.
- 결과 메시지를 이벤트 로그에 push. 즉시 저장.
- src 갭: `records.photos`가 int 리스트뿐 → **메타데이터 photo/dish 저장소 신규**. 생성 로직(제목/소재)은
  prototype/game `use_tool`의 LLM/규칙 방식을 src LLM 추상화(litellm)로 이식.

### 4.6 고백 말풍선 (`web_server.py` `answer_bubble` → `sim.resolve_confession`)
- 시뮬이 `confess_request` 말풍선을 큐에 쌓음 → 프론트가 표시 → `POST /bubble`로 allow/stop.
- 승인 시 `resolve_confession(bubble, approved)` 결과 장면을 이벤트 로그에 push.
- `hungry` 말풍선은 feed로만 해소(승인 대상 아님).
- src 갭: 말풍선 큐(`bubbles`) + `resolve_confession` 흐름 **신규** (src의 고백은 현재 자율 이벤트로만 발생).

### 4.7 보조 (seq / reset)
- `seq`: push되는 모든 이벤트(틱·feed·give·bubble)마다 +1. `snapshot`은 `seq>since`만 반환.
- `reset`: 새 마을 재생성 + 시뮬 재초기화 + 이벤트로그 clear + 세이브 덮어쓰기.

## 5. 모듈 배치 & 병렬 분할 단위

| 트랙 | 위치 (신규/수정) | 의존 |
|---|---|---|
| ⓐ snapshot 집계기 + compat 라우터 | `src/tomodachai/api/snapshot.py` (신규) | mood라벨·slots·dex 매핑 |
| ⓑ feed 메커닉 | `src/tomodachai/food.py` (신규) + 모델 보정 | 독립 |
| ⓒ give/도구 → photos·dishes | `src/tomodachai/tools.py` (신규) + 저장소 | 독립 |
| ⓓ 고백 말풍선 승인 | `src/tomodachai/bubbles.py` (신규) + simulation 훅 | 독립 |
| ⓔ rankings | `src/tomodachai/rankings.py` (신규) | 이벤트/관계 접근 |
| ⓕ seq 이벤트로그 + reset + mood라벨/slots/spark 모델 보정 | `game_state.py` / `character.py` / `relationship.py` 수정 | ⓐ의 선행 |
| ⓖ 프론트 베이스 URL + 필드 갭 보정 + 버튼 게이팅 | `prototype/web/src/lib/{api,store,sim}.ts` | 계약 고정 후 |

**병렬 전략:** ⓕ(모델 보정: spark/seq/mood라벨)와 ⓐ(집계기 골격)를 먼저 → 계약 고정.
이후 ⓑⓒⓓⓔ는 서로 독립이라 병렬 진행 가능. ⓖ는 계약 고정 직후 착수 가능.

## 6. 테스트 전략
- 각 NEW 메커닉: pytest **TDD** (Red→Green). 공식은 §4 prototype/game 값으로 단위 검증
  (예: preference_tier 경계, mood.label 분기, rankings 정렬, feed 델타).
- 집계기: `Snapshot` **계약 스키마 일치** 테스트 — 프론트 `types.ts` 필드/타입과 대조하는 고정 테스트.
- write 액션: 엔드포인트 + 이벤트로그 push(seq 증가) 통합 테스트.
- 프론트: 베이스 URL 변경 + 폴링 유지라 **수동 스모크**(`uvicorn` + `vite dev`로 3D 마을 렌더 확인).

## 7. 범위 밖 (이번 작업 아님)
- WebSocket 전환(폴링 유지). 상점/뉴스/분수대의 snapshot 노출(별도 증분).
- `[전 연인]` 태그(ex_lover 모델 없으면 deferred). 데스크탑(Tauri) 패키징.
- CLAUDE.md를 FastAPI+Babylon 기준으로 갱신하는 건 별도 docs 작업(현재 stash 보류 중).

## 8. 위험 / 확인 필요
- src `FOODS` 카탈로그와 prototype `FOODS`(10종) 정합 — 인덱스 기반 `food_ranks`/`food_eaten` 호환 확인.
- src 시뮬의 `fight` 이벤트·슬롯 갱신이 prototype과 의미상 동일한지(랭킹 정확도).
- `resolve_confession` 흐름이 src 자율 고백 이벤트와 충돌하지 않게 훅 지점 설계.
