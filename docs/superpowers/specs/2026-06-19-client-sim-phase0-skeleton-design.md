# 설계: 클라이언트 시뮬 마이그레이션 — Phase 0 (걷는 해골)

- **날짜:** 2026-06-19
- **상태:** 설계 승인됨 (구현 계획 대기)
- **상위 결정:** 아키텍처를 **C안(서버 0개)**으로 전환 — 시뮬을 클라(TS)로 이전, LLM은 클라가 로컬 Ollama 직접 호출, Python 백엔드는 정답지(레퍼런스)로만 보존.

## 1. 배경 / 동기

이 게임은 **싱글플레이어 관찰형 시뮬 + 클라 렌더링 + 로컬 Ollama** 타겟이다. 이 조합에서 서버가
구조적으로 꼭 필요한 일은 사실상 없다(캐릭터 생성·needs·관계·mood·이벤트·세이브는 전부 결정론적
게임 로직, 멀티플레이어/공유상태/무거운 연산 없음). 현재의 두꺼운 Python FastAPI 백엔드는 프로토타입이
Python 우선으로 자란 **경로 의존성**의 결과지 요구사항이 아니다.

Tauri 데스크탑 + 로컬 Ollama 환경에서는 클라가 Ollama를 직접 호출할 수 있으므로 Python 서버는
**장기적으로 죽은 무게**다. 따라서 시뮬을 클라(TS)로 옮기고 서버를 제거한다(C안).

### 확정된 상위 결정 (이번 brainstorming)
- **C안 채택:** 서버 0개. Tauri webview가 Ollama를 (HTTP 플러그인 경유) 직접 호출. 순수 웹 빌드는 범위 밖.
- **이전 전략:** **점진 포팅, Python = 정답지.** Python 시뮬 + 테스트를 정답지로 보존(삭제X), 모듈 단위로 TS 포팅.
- **검증 수준:** **규칙 충실(공식 일치).** 순수함수는 Python 골든 입출력 테이블로 1:1 검증. 확률 이벤트는 RNG 주입해 결정론 부분만 검증, 난수열 자체는 언어간 일치 안 쫓음.
- **LLM 전송:** **Tauri HTTP 플러그인 + dev fetch 폴백.** 패키징 앱은 Rust-backed fetch로 CORS 우회, dev(순수 브라우저)는 전역 fetch.

## 2. 범위 — Phase 0만

이 스펙은 **Phase 0(걷는 해골)** 하나만 다룬다. 전체 마이그레이션은 단계로 분해되며(아래 로드맵),
각 단계는 자기 spec → plan → 구현 사이클을 가진다.

Phase 0의 목표: **캐릭터 모델·생성 UI를 1도 안 건드리고**(그 영역은 사용자가 클라에서 작업 중),
C 아키텍처를 end-to-end로 증명하는 최소 골격을 세운다.

### 전체 로드맵 (참고 — 이번 구현 대상 아님)
| Phase | 내용 | 의존 |
|---|---|---|
| **0. 골격** ← 이번 | LLM seam + 오라클 하니스 + 렌더러 인-프로세스 배선 + time_system 포팅 | — |
| 1. 결정론 코어 | character·personality·mood (TS 모델 정의 = 사용자 생성 UI의 계약, 외형·목소리 신규 필드 흡수) | 0 |
| 2. 관계·기억 | relationship, memory | 1 |
| 3. 욕구·도구 | food, tools (+LLM 콘텐츠는 seam 경유) | 1,0 |
| 4. 사회 시스템 | conversation, news, fountain, shop | 2,3 |
| 5. 틱 루프 | simulation 오케스트레이션 + bubbles·rankings 재이식 | 4 |
| 6. 세이브 | 클라 영속화 (Tauri fs / localStorage) | 5 |
| 7. Python 은퇴 | api/server 런타임 제거, Python은 레퍼런스로만 | 6 |

> **경계 메모:** 사용자는 클라에서 **캐릭터 생성 UI**(성격·외형(눈·코·입 등)·목소리 선택 로직 포함)를
> 작업 중이다. Character 데이터 **모델 소유권은 sim 포팅(이 작업)에 있다** — Python `character.py`(정답지)의
> 충실한 TS 포팅으로 정의하고, 사용자의 생성 UI가 그 모델에 **맞춘다**(협의가 아니라 모델이 기준).
> 단 생성 UI가 다루는 외형(눈·코·입)·목소리 중 Python 모델에 아직 없는 **신규 필드**는 Phase 1에서 TS
> 모델을 정의할 때 흡수한다(UI가 필요로 하는 필드를 모델에 반영). Phase 0는 모델을 정의하지 않는다
> (캐릭터 의존성 0인 것만 다룸); 모델 정의는 Phase 1. 그 전까지 사용자 UI는 `character.py` 형태를
> 참조 기준으로 삼을 수 있다.

## 3. 아키텍처 & 프로젝트 구조

서버 프로세스 0개:
```
prototype/desktop (Tauri 셸, Rust)
   └─ webview ─▶ prototype/web (Vite/Svelte/Babylon)
                   ├─ src/sim/      ← 순수 TS 시뮬 (Babylon/Svelte import 금지, vitest 대상)
                   │    └─ __golden__/*.json  ← Python이 덤프한 골든 픽스처(커밋)
                   ├─ src/llm.ts    ← LLM seam (Tauri http + dev fetch 폴백)
                   ├─ src/lib/      ← 렌더러(village.ts)·store (기존)
                   └─ src/components ← Svelte UI (기존 + 사용자 캐릭터 생성 UI)
                          │
                          └─▶ Ollama (localhost:11434)  ※ Tauri http 경유
```

**의존 방향 (단방향):**
- `lib/`(렌더러) → `sim/`(스냅샷 읽기). 역방향 금지. sim은 렌더러를 모른다.
- `sim/`은 프레임워크 무의존 순수 TS → vitest 단독 테스트 + 오라클 대조 가능.
- `llm.ts`는 sim이 의존하는 seam.

**네이밍:** `prototype/web`·`prototype/desktop` 이름은 당분간 유지(이름 정리는 나중에 git mv 한 번).

**골든 픽스처 위치:** `scripts/dump_golden.py`(Python 덤프) → `prototype/web/src/sim/__golden__/*.json`(커밋) → vitest 로드.

## 4. LLM seam (`prototype/web/src/llm.ts`)

Python `LLMClient`(src/tomodachai/llm.py) 미러.

**공개 API:**
```ts
chat(messages: Msg[], opts?: {temperature?: number, maxTokens?: number}): Promise<string>
chatJson(messages: Msg[], opts?: {retries?: number} & ChatOpts): Promise<Record<string, unknown>>
parseJson(text: string): Record<string, unknown>   // 순수, export (오라클 대상)
```

**`parseJson` — `_parse_json` 1:1 이식 (순수, 결정론):**
1. trim → 빈 문자열이면 throw
2. ` ```json ... ``` ` 코드블록 매치 시 그 안을 파싱
3. 아니면 첫 `{ ... }` 블록 정규식 추출
4. 아니면 raw 파싱
→ 골든 입출력 테이블로 검증.

**`chatJson` retry:** Python처럼 `retries=2`(총 3회). 파싱 실패 시 재호출, 마지막 실패면 throw.
retry 카운팅은 (네트워크 mock 위에서) 결정론 검증.

**전송 — 환경 감지 분기:**
```ts
const httpFetch = isTauri() ? tauriFetch : globalThis.fetch
```
둘 다 Ollama 네이티브 엔드포인트:
`POST {apiBase}/api/chat` body `{model, messages, stream:false, options:{temperature, num_predict:maxTokens}}`
→ 응답 `{message:{content}}`에서 content 추출.

**설정:** `{apiBase: "http://localhost:11434", model, temperature, maxTokens}`.
Python의 `claude-cli`/`codex-cli` provider 분기는 **버린다**(Python 개발용 핵, 클라 Ollama엔 무의미).

**에러:** 네트워크 실패 → throw. 호출부가 "Ollama 연결 안 됨" 토스트 등으로 처리.
비결정론(실제 네트워크/LLM 출력)은 mock으로만 검증.

## 5. 스냅샷 seam (sim ↔ 렌더러, 인-프로세스)

기존 HTTP 계약(`Snapshot` DTO)을 **모양 그대로 유지**하고 전송만 함수 호출로 바꾼다.

- `api.ts`의 `getSnapshot(since)`(기존 `fetch`) → `sim.getSnapshot(since)` **함수 호출**로 교체.
- write 액션(`feed/give/bubble/save/reset`)도 sim 함수 호출로(Phase 0엔 no-op 스텁).
- **Phase 0 sim 스텁:** 빈 마을(characters=[]) + 도는 시계만 든 `Snapshot` 반환. `clock`/`minutes`/`asleep`는
  실제 포팅된 time_system이 채운다.
- `village.ts`는 거의 안 건드림 — 데이터 출처만 바뀜.

## 6. `time_system` 포팅 (첫 실전 모듈)

Python `time_system.GameClock` 미러.

- TS `GameClock`: `getGameHour(at?, flip?)` / `getTimePeriod(at?)`(아침·낮·저녁·밤) / `isNewDay(lastCheck)` /
  `catchupEventCount(offlineHours)` + 상수(리셋 5시, 시간대 테이블, catchup 상한, offline 임계).
- `now()`만 `Date` 사용하며 **주입 가능**(테스트는 고정 시각 주입). 로직 함수는 전부 `at` 인자를 받아 결정론.
- 스냅샷의 `clock`(HH:MM) / `minutes`(자정 기준 분) / `asleep`(23:00–07:00 수면창)를 이 GameClock에서 파생.

## 7. 오라클 하니스

- `scripts/dump_golden.py`: 정답지 모듈을 결정론 입력으로 호출해 `{input, expected}` 케이스를 JSON 배열로 덤프.
  Phase 0 대상: `_parse_json` 케이스 + `GameClock`(getGameHour/getTimePeriod/isNewDay/catchupEventCount) 케이스.
- 출력 → `prototype/web/src/sim/__golden__/{parse_json,game_clock}.json`(커밋).
- vitest 로더: 픽스처를 읽어 `it.each`로 TS 함수 출력과 `expected`를 1:1 assert.
- 규칙 변경 시 `python scripts/dump_golden.py` 재실행으로 픽스처 갱신(npm script `golden:gen` 래핑).

## 8. 테스트 & 성공 기준

1. `vitest` 그린: `parseJson`·`GameClock` 골든 대조 통과.
2. **걷는 해골:** `vite dev`로 빈 마을이 뜨고 **시계가 실시간으로 돈다**(하늘색/수면 반영). 서버 프로세스 0개.
3. `llm.ts`로 Ollama 한 번 실제 호출 성공(연결 확인) + Ollama 미기동 시 에러 토스트.
4. Python/api 서버는 **안 건드림**(은퇴는 Phase 7).

## 9. 범위 밖 (Phase 0 아님)
- Character 데이터 모델 정의 / 캐릭터 생성 UI (사용자 작업 + Phase 1).
- 실제 시뮬 로직(needs/관계/mood/이벤트/틱 루프) 포팅 (Phase 1~5).
- 세이브 영속화 (Phase 6). Python api/server 제거 (Phase 7).
- 클라우드 LLM provider / 키 보관 / 순수 웹 빌드 (현재 로컬 Ollama 전제).
- `prototype/` → 정식 이름 디렉터리 정리.

## 10. 위험 / 확인 필요
- Tauri HTTP 플러그인의 dev/패키징 fetch 동작 차이 — `isTauri()` 감지 신뢰성 스모크 확인.
- Ollama 네이티브 `/api/chat` 응답 스키마(스트리밍 off)와 content 추출 경로 확인.
- `GameClock.now()`가 벽시계 의존 — 골든 대조는 반드시 `at` 주입 케이스로만(현재시각 의존 케이스 금지).
- Character 모델은 sim 포팅이 소유·정의(character.py 포팅)하고 사용자 생성 UI가 거기 맞춘다. Phase 1에서
  TS 모델 정의가 곧 생성 UI의 계약이 되며, 외형(눈·코·입)·목소리 등 Python 모델에 없는 신규 필드를 흡수해야 함.
