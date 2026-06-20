# 클라 시뮬 Phase 1 — Character 모델 + personality 포팅 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Python `character.py`/`personality.py`의 캐릭터 데이터 모델과 결정론적 파생 로직(별자리·성격코드)을 TS `src/sim/`로 충실 포팅하고 골든으로 검증한다.

**Architecture:** Phase 0에서 확정된 패턴 그대로 — Python = 오라클, 순수함수는 골든 입출력 1:1 대조, `src/sim/`는 프레임워크 무의존. 모델 타입은 `character.py` 구조를 미러하고 기본값은 Python 기본 인스턴스 덤프로 검증.

**Tech Stack:** TypeScript, vitest, 골든 하니스(Phase 0의 `scripts/dump_golden.py` + `src/sim/__golden__/loadGolden.ts` 확장). 정답지: `src/tomodachai/character.py`, `src/tomodachai/personality.py`.

## Global Constraints
- **Python 정답지 수정 금지** — `src/tomodachai/**`, `tests/**`는 읽기 전용. 덤프 스크립트는 READ만.
- **`src/sim/`는 프레임워크 무의존** (Babylon/Svelte/Tauri import 금지).
- **Node 18+** — 모든 node/npm은 `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH"` 프리픽스로 (기본 env node는 v16).
- **Python 덤프**는 repo 루트에서 `python scripts/dump_golden.py` (스크립트가 `src`를 sys.path에 추가).
- **작업 디렉터리 persists** — repo 루트(Python/git) vs `prototype/web`(npm) 명시적 cd.
- **사용자 WIP 파일 `git add` 금지**: `CLAUDE.md`, `docs/plan/01-character.md`, `docs/plan/03-space-and-events.md`, untracked `.mcp.json`/`godot/`/`mii.blend*`/`sh.exe.stackdump`.
- **브랜치** `feat/client-sim-migration`, main 직접 푸시 금지.
- **커밋 트레일러**: 끝에 정확히 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **포팅 충실도 주의:** Python `<` 임계 비교, 평균 계산 순서, 기본값을 그대로. 부동소수 경계는 골든이 검증.

## 범위 밖 (Phase 1 아님)
- `match_personality` (LLM 의존 — 후속, 생성 흐름과 함께)
- `load_personalities` / `personalities.yaml` 메타데이터 로딩 (성격 설명·behavior_guide — 프롬프트 쓰는 후속 Phase)
- `Character._migrate` 구버전 save 호환 (Phase 6 세이브)
- Mood.label()/adjust() — 이 브랜치(main 기반) 오라클엔 없음(후속 feed/mood 포팅에서)

## File Structure
- `prototype/web/src/sim/character.ts` (생성) — 캐릭터 모델 타입 + 기본값 팩토리 + `calculateZodiac`.
- `prototype/web/src/sim/personality.ts` (생성) — `determinePersonality` + 테이블 + `personalityCode`.
- `prototype/web/src/sim/character.test.ts`, `personality.test.ts` (생성) — 골든 대조.
- `scripts/dump_golden.py` (수정) — `dump_zodiac` / `dump_personality` / `dump_character_defaults` 섹션 추가.
- `prototype/web/src/sim/__golden__/*.json` (생성, 덤프 산출), `loadGolden.ts` (수정) — 레지스트리 확장.

---

## Task 1: `calculateZodiac` (순수 함수)

**Files:**
- Modify: `scripts/dump_golden.py`
- Create: `prototype/web/src/sim/character.ts` (이 태스크에선 `calculateZodiac`만)
- Create: `prototype/web/src/sim/character.test.ts`
- Modify: `prototype/web/src/sim/__golden__/loadGolden.ts`

**Interfaces:**
- Consumes: Phase 0 `loadGolden`.
- Produces: `calculateZodiac(birthday: string): string` (export from `character.ts`).

- [ ] **Step 1: 덤프에 zodiac 섹션 추가**

`scripts/dump_golden.py`에 함수 추가 + `main()`에서 호출:
```python
def dump_zodiac() -> None:
    from tomodachai.character import calculate_zodiac

    # 12 별자리 각 경계 양끝 + 무효 입력
    inputs = [
        "03-21", "04-19", "04-20", "05-20", "05-21", "06-20",
        "06-21", "07-22", "07-23", "08-22", "08-23", "09-22",
        "09-23", "10-22", "10-23", "11-21", "11-22", "12-21",
        "12-22", "01-19", "01-20", "02-18", "02-19", "03-20",
        "", "bad", "13-99",
    ]
    cases = [{"input": b, "expected": calculate_zodiac(b)} for b in inputs]
    _write("zodiac", cases)
```
`main()`에 `dump_zodiac()` 추가.

- [ ] **Step 2: 덤프 실행**

Run (repo 루트): `python scripts/dump_golden.py`
Expected: `wrote .../zodiac.json (27 cases)`.

- [ ] **Step 3: 로더에 zodiac 등록**

`loadGolden.ts`에 import + REGISTRY 항목 `zodiac: zodiacCases as GoldenCase[]` 추가 (기존 패턴대로).

- [ ] **Step 4: 실패 테스트 (Red)**

`prototype/web/src/sim/character.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { calculateZodiac } from "./character";
import { loadGolden } from "./__golden__/loadGolden";

describe("calculateZodiac (golden vs Python)", () => {
  const cases = loadGolden<string, string>("zodiac");
  it.each(cases)("zodiac %#", (c) => {
    expect(calculateZodiac(c.input)).toBe(c.expected);
  });
});
```

- [ ] **Step 5: 실패 확인**

Run (`prototype/web`): `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH" npm test`
Expected: FAIL — `calculateZodiac` 미정의.

- [ ] **Step 6: 구현 (Python `calculate_zodiac` 1:1)**

`prototype/web/src/sim/character.ts`:
```ts
// Python src/tomodachai/character.py 미러 (순수 데이터 모델 + 결정론 파생).

/** 생일 "MM-DD" → 한국어 별자리. 인식 실패 시 "". Python calculate_zodiac 1:1. */
export function calculateZodiac(birthday: string): string {
  if (!birthday) return "";
  const month = Number.parseInt(birthday.slice(0, 2), 10);
  const day = Number.parseInt(birthday.slice(3, 5), 10);
  if (Number.isNaN(month) || Number.isNaN(day)) return "";

  if ((month === 3 && day >= 21) || (month === 4 && day <= 19)) return "양자리";
  if ((month === 4 && day >= 20) || (month === 5 && day <= 20)) return "황소자리";
  if ((month === 5 && day >= 21) || (month === 6 && day <= 20)) return "쌍둥이자리";
  if ((month === 6 && day >= 21) || (month === 7 && day <= 22)) return "게자리";
  if ((month === 7 && day >= 23) || (month === 8 && day <= 22)) return "사자자리";
  if ((month === 8 && day >= 23) || (month === 9 && day <= 22)) return "처녀자리";
  if ((month === 9 && day >= 23) || (month === 10 && day <= 22)) return "천칭자리";
  if ((month === 10 && day >= 23) || (month === 11 && day <= 21)) return "전갈자리";
  if ((month === 11 && day >= 22) || (month === 12 && day <= 21)) return "사수자리";
  if ((month === 12 && day >= 22) || (month === 1 && day <= 19)) return "염소자리";
  if ((month === 1 && day >= 20) || (month === 2 && day <= 18)) return "물병자리";
  if ((month === 2 && day >= 19) || (month === 3 && day <= 20)) return "물고기자리";
  return "";
}
```
> 주의: Python은 `int(birthday[:2])`가 `ValueError`면 ""를 반환한다. TS는 `Number.parseInt`가 `NaN`을 주므로 `Number.isNaN` 가드로 동등 처리. `"13-99"`는 어떤 분기에도 안 맞아 ""(Python 동일).

- [ ] **Step 7: 통과 확인**

Run (`prototype/web`): `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH" npm test`
Expected: PASS — zodiac 27케이스 통과.

- [ ] **Step 8: 커밋**

```bash
git add scripts/dump_golden.py prototype/web/src/sim/character.ts prototype/web/src/sim/character.test.ts prototype/web/src/sim/__golden__/loadGolden.ts prototype/web/src/sim/__golden__/zodiac.json
git commit -m "feat(sim): calculateZodiac 포팅 (골든 대조)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Character 모델 타입 + 기본값

**Files:**
- Modify: `scripts/dump_golden.py` (`dump_character_defaults`)
- Modify: `prototype/web/src/sim/character.ts` (모델 타입 + `defaultCharacter`)
- Modify: `prototype/web/src/sim/character.test.ts`
- Modify: `prototype/web/src/sim/__golden__/loadGolden.ts`

**Interfaces:**
- Consumes: Task 1 `character.ts`.
- Produces (export from `character.ts`): 인터페이스 `Character, Profile, Appearance, AppearanceAdjust, Eye, Eyebrow, Nose, Mouth, Hair, Body, Personality, Voice, Preferences, ClothingPreference, InteriorPreference, PersonalityGroup, Mood, CharacterState, SpeechHabits, MiniTrait, MiniTraits, Customizable, Records`; 팩토리 `defaultProfile(name: string): Profile`, `defaultCharacter(id: number, name: string): Character`.

- [ ] **Step 1: 기본값 덤프 섹션 추가**

`scripts/dump_golden.py`에 추가 + `main()` 호출:
```python
def dump_character_defaults() -> None:
    from tomodachai.character import (
        Appearance, Mood, CharacterState, Preferences, Customizable, Records, Voice,
    )

    # 각 서브모델의 기본 인스턴스를 JSON 직렬화 → TS 기본값이 일치해야 함
    cases = [
        {"input": "Appearance", "expected": Appearance().model_dump()},
        {"input": "Voice", "expected": Voice().model_dump()},
        {"input": "Mood", "expected": Mood().model_dump()},
        {"input": "CharacterState", "expected": CharacterState().model_dump()},
        {"input": "Preferences", "expected": Preferences().model_dump()},
        {"input": "Customizable", "expected": Customizable().model_dump()},
        {"input": "Records", "expected": Records().model_dump()},
    ]
    _write("character_defaults", cases)
```
> 주의: `Profile`/`Character`는 `name`이 필수라 기본 인스턴스 불가 → 서브모델 기본값만 검증.

- [ ] **Step 2: 덤프 실행**

Run (repo 루트): `python scripts/dump_golden.py`
Expected: `character_defaults` 7케이스 작성.

- [ ] **Step 3: 로더 등록**

`loadGolden.ts`에 `character_defaults` 등록.

- [ ] **Step 4: 실패 테스트 (Red)**

`character.test.ts`에 추가:
```ts
import {
  defaultAppearance, defaultVoice, defaultMood, defaultCharacterState,
  defaultPreferences, defaultCustomizable, defaultRecords,
} from "./character";

describe("Character 모델 기본값 (golden vs Python 서브모델)", () => {
  const builders: Record<string, () => unknown> = {
    Appearance: defaultAppearance,
    Voice: defaultVoice,
    Mood: defaultMood,
    CharacterState: defaultCharacterState,
    Preferences: defaultPreferences,
    Customizable: defaultCustomizable,
    Records: defaultRecords,
  };
  const cases = loadGolden<string, Record<string, unknown>>("character_defaults");
  it.each(cases)("default %s", (c) => {
    expect(builders[c.input]()).toEqual(c.expected);
  });
});
```

- [ ] **Step 5: 실패 확인**

Run (`prototype/web`): `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH" npm test`
Expected: FAIL — default* 빌더 미정의.

- [ ] **Step 6: 모델 타입 + 기본값 팩토리 구현**

`character.ts`에 `character.py`의 모든 서브모델을 TS 인터페이스로 미러하고, 각 서브모델의 기본값 팩토리를 작성한다. **`character.py`(이미 읽은 정답지)의 필드명·기본값·중첩 구조를 그대로 옮긴다.** 핵심 기본값 체크리스트(반드시 일치):
- `AppearanceAdjust`: spacing=0, height=0, size=0, angle=0
- `Eye`: base=1, lash=0, color="#000000", adjust=기본
- `Eyebrow`/`Nose`/`Mouth`: id=1, adjust=기본
- `Hair`: front=1, back=1, color="#000000"
- `Body`: height=5, build=5
- `Appearance`: face_shape=1, skin_color="#F5D6B8", eye/eyebrow/nose/mouth/hair=기본, glasses=null, body=기본
- `Personality`: movement/speech/expressiveness/attitude/overall=5
- `Voice`: preset="default", pitch=5, speed=5, quality/tone/accent/intonation=null
- `Mood`: happiness=5, energy=5, stress=2
- `CharacterState`: satisfaction=50.0, level=1, hunger=0.0, mood=기본, sick=null, current_location="", current_outfit=null, current_interior=null, photo_frame=null
- `Preferences`: food_ranks=[], food_eaten=[], clothing={likes:"",dislikes:""}, interior={likes:"",dislikes:""}, personality_group={group:"",is_positive:true}
- `SpeechHabits`: normal/happy/angry/sad/worried=""
- `MiniTrait`: owned=[], active=null; `MiniTraits`: walking/eating/idle=기본
- `Customizable`: speech_habits=기본, mini_traits=기본, nicknames={}, songs=[false]×8
- `Records`: treasure_collection=[], confession_count={}, photos=[]
- `Profile`: name(필수), birthday="", blood_type="", favorite_color="", gender="", appearance=기본, personality=기본, voice=기본
- `Character`: id, profile, preferences=기본, state=기본, customizable=기본, records=기본

> Python `None` → TS `null`, `Optional[int]` → `number | null`. JSON 직렬화 시 `model_dump()`가 null을 포함하므로 TS 팩토리도 명시적 `null`을 넣어야 `toEqual` 통과.
> `defaultCharacter(id, name)`와 `defaultProfile(name)`도 작성(테스트엔 안 쓰지만 후속 Phase·생성 UI가 소비).

- [ ] **Step 7: 통과 확인**

Run (`prototype/web`): `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH" npm test`
Expected: PASS — character_defaults 7케이스 + 기존 전부.

- [ ] **Step 8: 커밋**

```bash
git add scripts/dump_golden.py prototype/web/src/sim/character.ts prototype/web/src/sim/character.test.ts prototype/web/src/sim/__golden__/loadGolden.ts prototype/web/src/sim/__golden__/character_defaults.json
git commit -m "feat(sim): Character 모델 타입 + 기본값 팩토리 (골든 대조)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `determinePersonality` + `personalityCode`

**Files:**
- Modify: `scripts/dump_golden.py` (`dump_personality`)
- Create: `prototype/web/src/sim/personality.ts`
- Create: `prototype/web/src/sim/personality.test.ts`
- Modify: `prototype/web/src/sim/__golden__/loadGolden.ts`

**Interfaces:**
- Consumes: Task 2 `Personality` 타입 (`character.ts`).
- Produces (export from `personality.ts`): `determinePersonality(s: {movement:number; speech:number; expressiveness:number; attitude:number}): string` (입력은 0~1 float); `personalityCode(p: Personality): string` (Personality 0~10 int → /10 후 determine).

- [ ] **Step 1: 덤프에 personality 섹션 추가**

`scripts/dump_golden.py`에 추가 + `main()` 호출:
```python
def dump_personality() -> None:
    from tomodachai.character import Personality
    from tomodachai.personality import PersonalitySliders, determine_personality

    # determine_personality: 16코드 전부 커버하도록 4분면×4분면 격자
    vals = [0.1, 0.4, 0.6, 0.9]  # 각 임계 구간(<0.25,<0.5,<0.75,<1.01)을 대표
    det_cases = []
    for ms in vals:          # movement=speech=ms → ms_avg=ms
        for ea in vals:      # expr=attitude=ea → ea_avg=ea
            s = PersonalitySliders(movement=ms, speech=ms, expressiveness=ea, attitude=ea)
            det_cases.append({
                "input": {"movement": ms, "speech": ms, "expressiveness": ea, "attitude": ea},
                "expected": determine_personality(s),
            })
    _write("determine_personality", det_cases)

    # personalityCode: Personality(0~10 int) → 코드
    code_inputs = [
        {"movement": 8, "speech": 8, "expressiveness": 7, "attitude": 5, "overall": 5},
        {"movement": 2, "speech": 2, "expressiveness": 8, "attitude": 8, "overall": 5},
        {"movement": 5, "speech": 5, "expressiveness": 5, "attitude": 5, "overall": 5},
        {"movement": 0, "speech": 0, "expressiveness": 0, "attitude": 0, "overall": 0},
        {"movement": 10, "speech": 10, "expressiveness": 10, "attitude": 10, "overall": 10},
    ]
    code_cases = []
    for pi in code_inputs:
        p = Personality(**pi)
        sliders = PersonalitySliders(
            movement=p.movement / 10.0, speech=p.speech / 10.0,
            expressiveness=p.expressiveness / 10.0, attitude=p.attitude / 10.0,
        )
        code_cases.append({"input": pi, "expected": determine_personality(sliders)})
    _write("personality_code", code_cases)
```

- [ ] **Step 2: 덤프 실행**

Run (repo 루트): `python scripts/dump_golden.py`
Expected: `determine_personality` 16케이스 + `personality_code` 5케이스.

- [ ] **Step 3: 로더 등록**

`loadGolden.ts`에 `determine_personality`, `personality_code` 등록.

- [ ] **Step 4: 실패 테스트 (Red)**

`prototype/web/src/sim/personality.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { determinePersonality, personalityCode } from "./personality";
import { loadGolden } from "./__golden__/loadGolden";

describe("determinePersonality (golden vs Python)", () => {
  const cases = loadGolden<
    { movement: number; speech: number; expressiveness: number; attitude: number },
    string
  >("determine_personality");
  it.each(cases)("determine %#", (c) => {
    expect(determinePersonality(c.input)).toBe(c.expected);
  });
});

describe("personalityCode (golden vs Python)", () => {
  const cases = loadGolden<
    { movement: number; speech: number; expressiveness: number; attitude: number; overall: number },
    string
  >("personality_code");
  it.each(cases)("code %#", (c) => {
    expect(personalityCode(c.input)).toBe(c.expected);
  });
});
```

- [ ] **Step 5: 실패 확인**

Run (`prototype/web`): `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH" npm test`
Expected: FAIL — `determinePersonality`/`personalityCode` 미정의.

- [ ] **Step 6: 구현 (personality.py 1:1)**

`prototype/web/src/sim/personality.ts`:
```ts
// Python src/tomodachai/personality.py 미러 (결정론 성격코드 판정).
import type { Personality } from "./character";

const GROUP_THRESHOLDS: readonly [number, string][] = [
  [0.25, "easygoing"],
  [0.5, "independent"],
  [0.75, "confident"],
  [1.01, "outgoing"],
];

const TYPE_SUFFIXES: readonly [number, number][] = [
  [0.25, 1],
  [0.5, 2],
  [0.75, 3],
  [1.01, 4],
];

const GROUP_TYPE_CODES: Record<string, string> = {
  "easygoing,1": "easygoing_softie",
  "easygoing,2": "easygoing_optimist",
  "easygoing,3": "easygoing_carer",
  "easygoing,4": "easygoing_dreamer",
  "independent,1": "independent_dogooder",
  "independent,2": "independent_perfectionist",
  "independent,3": "independent_introvert",
  "independent,4": "independent_thinker",
  "confident,1": "confident_busybee",
  "confident,2": "confident_gogetter",
  "confident,3": "confident_freespirit",
  "confident,4": "confident_brainiac",
  "outgoing,1": "outgoing_charmer",
  "outgoing,2": "outgoing_dynamo",
  "outgoing,3": "outgoing_buddy",
  "outgoing,4": "outgoing_extrovert",
};

/** 4슬라이더(0~1) → 16 성격코드. Python determine_personality 1:1. */
export function determinePersonality(s: {
  movement: number;
  speech: number;
  expressiveness: number;
  attitude: number;
}): string {
  const msAvg = (s.movement + s.speech) / 2.0;
  const eaAvg = (s.expressiveness + s.attitude) / 2.0;
  const group = GROUP_THRESHOLDS.find(([t]) => msAvg < t)![1];
  const typeIdx = TYPE_SUFFIXES.find(([t]) => eaAvg < t)![1];
  return GROUP_TYPE_CODES[`${group},${typeIdx}`];
}

/** Personality(0~10 int) → 코드. Python Character.personality_code 1:1 (/10 후 determine). */
export function personalityCode(p: Personality): string {
  return determinePersonality({
    movement: p.movement / 10.0,
    speech: p.speech / 10.0,
    expressiveness: p.expressiveness / 10.0,
    attitude: p.attitude / 10.0,
  });
}
```
> 주의: Python `next(name for threshold, name in ... if ms_avg < threshold)` = 첫 임계 초과 항목 → TS `.find(([t]) => avg < t)`. 마지막 임계 1.01이라 avg≤1.0이면 항상 매치(`!` 안전). overall은 코드 판정에 무관(Python도 미사용).

- [ ] **Step 7: 통과 확인**

Run (`prototype/web`): `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH" npm test`
Expected: PASS — determine 16 + code 5 + 기존 전부.

- [ ] **Step 8: 커밋**

```bash
git add scripts/dump_golden.py prototype/web/src/sim/personality.ts prototype/web/src/sim/personality.test.ts prototype/web/src/sim/__golden__/loadGolden.ts prototype/web/src/sim/__golden__/determine_personality.json prototype/web/src/sim/__golden__/personality_code.json
git commit -m "feat(sim): determinePersonality + personalityCode 포팅 (골든 16+5)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (작성자 체크)
- **커버리지:** character.py 모델(서브모델 기본값 골든) ✅ / calculate_zodiac(경계 골든) ✅ / personality.py determine_personality(16격자) + personality_code(/10) ✅. Deferred 명시(match_personality·load_personalities·_migrate·Mood메서드).
- **Placeholder:** 모델 타입은 정답지 파일 참조 + 기본값 체크리스트 + 골든 default-dump로 강제 — 포팅 태스크에 적합, 미완 placeholder 아님.
- **Type 일관:** `Personality`(Task 2 정의) → Task 3 `personalityCode` 소비. `determinePersonality` 입력은 구조적 타입(0~1). 골든 케이스 모양 일치.
