# 클라 시뮬 Phase 4 — personality 데이터 + Character 접근자 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** LLM 관찰 생성기(Phase 5: conversation/news/fountain)의 **데이터·접근자 기반**을 포팅. `PersonalityType` 16종 카탈로그(`data/personalities.yaml` + `load_personalities`)와 Python `Character`의 backward-compat 플랫 프로퍼티(`name`/`personality_code`/`speech_habits`/`backstory`)를 TS 헬퍼로. `match_personality`(LLM seam)도 포함.

**Architecture:** Phase 0~3 패턴 — Python=오라클, 결정론 데이터/함수는 골든 1:1, `src/sim/` 프레임워크 무의존. RNG 없음. LLM(`match_personality`)은 `llm.ts` seam + 주입 stub 구조검증.

**Tech Stack:** TS, vitest, 골든 하니스. 정답지: `src/tomodachai/personality.py`, `src/tomodachai/character.py`, 데이터 `data/personalities.yaml`.

## Global Constraints
- **Python 정답지 수정 금지** (`src/tomodachai/**`, `tests/**`, `data/**` 읽기 전용; 덤프는 READ만). `scripts/dump_golden.py`(dev 스크립트)는 수정 허용.
- **`src/sim/`는 프레임워크 무의존**.
- **Node 18+** — node/npm은 `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH"` 프리픽스. npm은 `prototype/web`에서, python/git은 repo 루트에서. Bash CWD persists — 명시적 cd.
- **각 태스크 검증에 `npm run check`(svelte-check) 포함**.
- **사용자 WIP `git add` 금지**: `CLAUDE.md`, `docs/plan/01-character.md`, `docs/plan/03-space-and-events.md`, untracked `.mcp.json`/`godot/`/`mii.blend*`/`sh.exe.stackdump`.
- **브랜치** `feat/client-sim-migration`, main 직접 푸시 금지.
- **커밋 트레일러**: 끝에 정확히 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## 범위 밖 (Phase 4 아님)
- `match_personality`의 LLM 응답을 Python과 일치시키는 것(LLM 비결정). 주입 stub로 구조만.
- conversation/news/fountain 본체(Phase 5).
- `groups:` 메타데이터의 별도 모델(현재 `load_personalities`는 `types`만 읽음 — group은 PersonalityType.group 문자열).

## File Structure
- `prototype/web/src/sim/personalityType.ts` (생성) — `PersonalityType` 인터페이스 + `PERSONALITY_TYPES`(16) + `loadPersonalities()` + `matchPersonality`(주입 rng 아님, llm seam).
- `prototype/web/src/sim/characterAccessors.ts` (생성) — `characterName`/`characterPersonalityCode`/`characterSpeechHabits`/`characterBackstory`.
- 각 `*.test.ts`, `scripts/dump_golden.py`(섹션 추가), `loadGolden.ts`(레지스트리 확장).

---

## Task 1: PersonalityType 모델 + 16종 카탈로그 (골든)

**Files:** Modify `scripts/dump_golden.py`, `loadGolden.ts`; Create `prototype/web/src/sim/personalityType.ts`(이 태스크: 타입+카탈로그+loadPersonalities), `prototype/web/src/sim/personalityType.test.ts`.

**Interfaces (Produces):**
- `interface PersonalityType { code: string; name: string; group: string; description: string; behavior_guide: string }`.
- `PERSONALITY_TYPES: Record<string, PersonalityType>` (16종, `data/personalities.yaml`의 `types` 그대로). `loadPersonalities(): Record<string, PersonalityType>` (PERSONALITY_TYPES 반환).

**오라클:** `personality.py` `load_personalities()` → `dict[code, PersonalityType]`. **정확 값은 `load_personalities()`를 덤프해 그대로**(16종 code/name/group/description/behavior_guide). 골든이 충실도 강제. behavior_guide는 yaml `>` 블록 스칼라(개행/공백 주의) — 골든값 그대로 매칭.

- [ ] **Step 1: 덤프 (`dump_personality_types`)** — `from tomodachai.personality import load_personalities; types = {code: pt.model_dump() for code, pt in load_personalities().items()}`. `_write("personality_types", [{"input":"load","expected": types}])`. `main()`에 호출.
- [ ] **Step 2: 덤프 실행** → personality_types(1, 16키).
- [ ] **Step 3: 로더 등록** — `loadGolden.ts`에 1개.
- [ ] **Step 4: 실패 테스트 (Red)** — `PERSONALITY_TYPES` === golden expected (`toEqual`). 16개 키 존재 단언.
- [ ] **Step 5: 실패 확인** → FAIL.
- [ ] **Step 6: 구현** — `personalityType.ts`에 16종 카탈로그(골든 JSON에서 값 복사) + loadPersonalities. 골든이 오타를 잡음.
- [ ] **Step 7: 통과 + check** — `npm test` PASS, `npm run check` 0.
- [ ] **Step 8: 커밋** (`feat(sim): PersonalityType 모델 + 16종 카탈로그 (골든)` + 트레일러). Stage: personalityType.ts/test, dump_golden.py, loadGolden.ts, personality_types.json.

---

## Task 2: Character 플랫 접근자 (골든 + 통합)

**Files:** Modify `scripts/dump_golden.py`, `loadGolden.ts`; Create `prototype/web/src/sim/characterAccessors.ts`, `prototype/web/src/sim/characterAccessors.test.ts`.

**Interfaces (Produces):**
- `characterName(c: Character): string` = `c.profile.name`.
- `characterPersonalityCode(c: Character): string` = `personalityCode(c.profile.personality)` (기존 personality.ts 재사용; Python: 슬라이더/10 → determine_personality).
- `characterSpeechHabits(c: Character): Record<string,string>` = `c.customizable.speech_habits` 중 **비어있지 않은 값만**, 키 순서 normal/happy/angry/sad/worried (Python `SpeechHabits.as_dict`).
- `characterBackstory(c: Character): string` = `""` (Python: backstory 필드 제거됨, 항상 빈 문자열).

**오라클:** `character.py` Character 프로퍼티 `name`(368), `personality_code`(351), `speech_habits`(392→`as_dict` 214: model_dump 중 truthy만), `backstory`(402→"").

- [ ] **Step 1: 덤프 (`dump_character_accessors`)** — Python에서 Character 2~3개를 구성(서로 다른 personality 슬라이더, speech_habits 일부 채움/일부 빈값), 각 `{"input": <식별자>, "expected": {"name":..., "personality_code":..., "speech_habits":..., "backstory":...}}`. 예: `Character(id=1, profile=Profile(name="민수", personality=Personality(movement=8,speech=8,expressiveness=7,attitude=5,overall=5)), customizable=Customizable(speech_habits=SpeechHabits(normal="~다", happy="신난다", angry="", sad="", worried="")))`. 최소 2케이스(빈 speech_habits 포함). `_write("character_accessors", cases)`.
> 주의: Character 생성자 인자(Profile/Personality/Customizable/SpeechHabits) 정확한 시그니처는 character.py 읽어 확인. personality_code는 슬라이더(0~10)/10 → determine_personality.
- [ ] **Step 2~3:** 덤프 실행 → 로더 등록.
- [ ] **Step 4: 실패 테스트 (Red)** — 골든 각 케이스의 TS Character를 동일하게 구성(`defaultCharacter` + 필드 오버라이드), 4개 접근자 호출 === expected. speech_habits 빈값 필터링 단언. `toEqual`.
- [ ] **Step 5~7:** 실패 확인 → 구현 → `npm test` PASS + `npm run check` 0.
- [ ] **Step 8: 커밋** (`feat(sim): Character 플랫 접근자 (name/personality_code/speech_habits/backstory)` + 트레일러).

---

## Task 3: matchPersonality (LLM seam, 구조 검증)

**Files:** Modify `prototype/web/src/sim/personalityType.ts`, Create `prototype/web/src/sim/matchPersonality.test.ts`.

**Interfaces (Produces):**
- `matchPersonality(llm, description): Promise<PersonalitySliders>` — `_MATCHER_SYSTEM` + 프롬프트(슬라이더 기준 + description) → `llm.chatJson(messages)` → `{movement,speech,expressiveness,attitude}` float 변환. `PersonalitySliders = {movement,speech,expressiveness,attitude}` (personality.ts에 있으면 재사용, 없으면 정의).

**오라클:** `personality.py` `match_personality`(111). 프롬프트 문자열·시스템 메시지 그대로. 결과는 `float(result[k])` 4개.

- [ ] **Step 1: 통합 테스트 (Red)** — 주입 stub llm(`chatJson`이 고정 dict 반환)으로: (a) messages 2개(system=_MATCHER_SYSTEM, user에 description 포함) 전달 확인, (b) 반환 PersonalitySliders가 stub 값의 float 변환과 일치, (c) 문자열 숫자("0.7")도 Number 변환되는지. LLM 응답 내용 자체는 미검증(비결정).
- [ ] **Step 2~3:** 실패 확인 → 구현 → `npm test` PASS + `npm run check` 0 → 커밋 (`feat(sim): matchPersonality (LLM seam, 구조 검증)` + 트레일러).

---

## Self-Review (작성자 체크)
- **커버리지:** PersonalityType 카탈로그(골든) + Character 접근자(골든) + matchPersonality(구조). 
- **Deferred 명시:** LLM 응답 일치, conversation/news/fountain 본체(Phase 5), groups 메타 별도 모델.
- **Type 일관:** `PersonalityType`(T1) → Phase 5 conversation 소비. 접근자(T2)는 Phase 1 Character 소비, personality.ts `personalityCode` 재사용. `PersonalitySliders`(T3).
- **교훈 반영:** 각 태스크 `npm run check` 포함. behavior_guide 블록스칼라 골든 그대로(개행 주의).
