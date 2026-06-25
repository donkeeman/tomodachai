# Phase 6 — GameState + Simulation tick (RNG 주입)

base: HEAD (feat/client-sim-migration, Phase 0~5 완료, 578 vitest + check 0)
plan 작성일: 2026-06-24

## 목표

Python 오라클 `config.py`(50) / `simulation.py`(408) / `game_state.py`(215)를
`prototype/web/src/sim/`로 포팅. 시뮬레이션 루프의 마지막 결합 계층.

## 마이그레이션 원칙 (재확인)

- Python = 정답지(오라클). 규칙/공식 충실(rule fidelity).
- **순수 결정론**(상수/델타 산술/요약 문자열/임계 비교/clamp/카탈로그/머니)
  = 골든 픽스처 또는 단위 테스트로 1:1 검증.
- **확률/RNG**(shuffle/choice/sample/random/uniform)
  = 주입형 `SimRng` 인터페이스. Python Mersenne Twister와 비트일치 **안 함**.
  결정론 스텁 RNG로 **구조/후처리만** 검증.
- **LLM 호출**(ConversationEngine.generate)
  = 기존 주입형 `LlmClient` 스텁으로 구조만.
- **시각**(datetime.now) = 주입형 nowFn(기존 GameClock 패턴) / inline 계산.
- `src/sim/` 프레임워크 무의존: cross-module 타입은 `import type`만.
- Python 소스(`src/tomodachai/**`)·테스트·데이터는 read-only. 골든 덤프는 READ만.
  `scripts/dump_golden.py`는 dev 스크립트라 수정 가능.

## RNG seam 설계 (SimRng)

```ts
export interface SimRng {
  random(): number;                       // [0,1)
  shuffle<T>(arr: T[]): void;             // in-place, Python random.shuffle 의미
  choice<T>(arr: readonly T[]): T;        // 단일 선택
  sample<T>(arr: readonly T[], k: number): T[]; // 비복원 k개
  uniform(a: number, b: number): number;  // [a,b]
}
```

- 프로덕션 구현은 후속(Tauri)에서. Phase 6는 인터페이스 + 결정론 스텁 테스트.
- `Simulation` 생성자에 `rng: SimRng` 주입(기본값 줄 수도 있으나 테스트는 항상 스텁).

## 태스크 분해

### P6 T1: config.ts (골든)
- `LLMConfig`/`SimulationConfig`/`LocationConfig`/`AppConfig` 인터페이스 + 기본값 팩토리.
- 클라이언트엔 YAML 파일/env 없음 → `load_config`는 **기본 팩토리(`makeDefaultConfig()`)** 로만 포팅. (env/YAML 병합은 범위 밖, 주석 명시.)
- 기본 locations: 공원(5)/편의점(3)/카페(4). ticks_per_day=6, max_characters=10.
  llm: provider litellm / model claude-sonnet-4-20250514 / temperature 0.8 / max_tokens 1000.
- 골든: `AppConfig().model_dump()` 덤프와 1:1.

### P6 T2: assignLocations + SimRng (seam)
- `SimRng` 인터페이스 정의(simulation.ts 또는 별도 rng.ts).
- `assignLocations(characters, locations, rng)`: rng.shuffle로 캐릭터 셔플 →
  각 캐릭터마다 available 셔플 → capacity 미만 첫 장소 배정.
  (Python seed 인자 대신 주입 rng. seed→Random 변환은 프로덕션 구현 몫.)
- 결정론 스텁 rng(shuffle=항등/역순 등 통제)로 배정 결과 구조 검증 + capacity 준수.

### P6 T3: Simulation 결정론 코어 + 트리거 (seam)
- 상수: `_BIG_EVENT_TYPES`, catchup 델타 범위, FIGHT/CONFESSION 임계·확률, HUNGER/SATISFACTION.
- `_name`(char_map 폴백 str(id)), `_updateNeeds`(hunger +5 min100 / satisfaction -1 max0),
  `_checkStageTransitions`(allPairs, allow_romantic=false).
- `_triggerFight`(이미 싸움 중이면 null, Fight 추가, friendship -5 양방, fight 이벤트,
  satisfaction -10 max0, 요약 `"{a}와(과) {b}의 긴장이 폭발하여 싸움이 벌어졌다!"`).
- `_triggerConfession`(rng.random<0.5 성공 → check_stage_transition(allow_romantic=true) 양방,
  실패 → friendship-5/romance-10, confession 이벤트 result accepted/rejected, 요약).
- `_checkTriggeredEventsForPair`(단일 쌍 fight/confession 게이트).
- `_runConversation`(get rel 양방 + getEventsBetween → engine.generate → deltas name 매칭 update → conversation 이벤트).
- 골든/단위: 요약 문자열, 델타 산술, _updateNeeds clamp, _name 폴백.
  RNG 게이트(fight/confession 확률)·LLM은 주입 스텁으로 구조 검증.

### P6 T4: Simulation.step + generateCatchupEvents (seam)
- `step(timeOfDay?)`: <2명 → []. rng.sample 2명 → rng.choice 장소(없으면 "공동주택") →
  _runConversation → conversation 이벤트 → _checkTriggeredEventsForPair → _checkStageTransitions →
  detectTriangles/applyJealousy → _updateNeeds → _step_count++.
  (timeOfDay 기본은 Python처럼 get_clock().get_time_period() — 주입 또는 인자.)
- `generateCatchupEvents(offlineHours)`: GameClock.catchupEventCount → count.
  <2명 또는 count0 → []. combinations(all pairs) → count번 rng.choice(pair) →
  rng.uniform 델타 → update 양방(0.8/0.6 비대칭) → _checkStageTransitions → catchup 이벤트(round,1) → _step_count++.
- 골든: 결정론 스텁 uniform/choice로 catchup 델타·요약 구조. step은 구조 검증.

### P6 T5: GameState (골든 + 통합)
- 머니: `addMoney`(음수→throw), `spendMoney`(음수→throw, 부족→false).
- 카탈로그: `addToCatalog`/`isInCatalog`(category 검증, 미존재→throw 정확 메시지 `sorted` 목록, 중복 무시).
- 캐릭터: `addCharacter`(중복 id→throw, append, _simulation 무효화, private room 등록),
  `getCharacter`, `removeCharacter`(필터, 무효화, private room 제거, bool).
  (`abs(hash(id))` str-id 경로는 Python에서도 비결정적 → int 경로만 충실 포팅, str 경로는 주석 명시.)
- 지연 `simulation` 게터(없으면 생성, add/remove로 무효화), `relationships`/`memory` 위임.
- `connect`(주입 nowFn): offline_hours = (now-lastOnline)/3600, is_new_day,
  >=5분 && 캐릭터 있으면 generateCatchupEvents + (is_new_day면 day_count++),
  last_online 갱신, {offline_hours round2, catchup_events, time_period, is_new_day}.
- `step`/`touch`/`currentTimePeriod`/`currentGameHour`.
- 골든: 머니/카탈로그 결정론. 나머지는 주입 의존성으로 통합 검증.

## 게이트 (태스크마다)
- `npm test -- --run` (vitest) **그리고** `npm run check` (svelte-check/tsc) 둘 다 green.
- 각 태스크: TDD Red→Green, 구현 subagent → sonnet 리뷰어(오라클 충실+범위) → inline fix → ledger.
- Phase 종료: opus 최종 리뷰 → 푸시 → PR #7 갱신.

## 산출물
- `prototype/web/src/sim/config.ts` (+test)
- `prototype/web/src/sim/simulation.ts` (+test, +golden)
- `prototype/web/src/sim/gameState.ts` (+test, +golden)
- `prototype/web/src/sim/rng.ts` (SimRng, 선택적 분리)
- `scripts/dump_golden.py`에 config/catchup/money 덤프 추가
- `prototype/web/src/sim/__golden__/*.json` + `loadGolden.ts` 등록
