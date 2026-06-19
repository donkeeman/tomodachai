# 클라 시뮬 Phase 0 (걷는 해골) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 서버 0개로, 클라가 로컬 Ollama를 직접 호출하고 실시간 시계가 도는 빈 마을이 뜨는 C 아키텍처 골격을 세운다.

**Architecture:** `prototype/web/src/sim/`(순수 TS 시뮬, vitest)에 첫 모듈(time_system)을 포팅하고, `src/llm.ts`(LLM seam)가 Tauri HTTP 플러그인(또는 dev fetch 폴백)으로 Ollama를 때린다. 렌더러는 HTTP `/snapshot` 대신 `sim.getSnapshot()` 함수를 호출한다(DTO 모양 유지). Python 시뮬은 정답지로 보존하고 골든 픽스처를 덤프한다.

**Tech Stack:** TypeScript 5.7, Vite 5, Svelte 5, Babylon.js 7, vitest, Tauri v2 (`@tauri-apps/plugin-http`), Ollama 네이티브 `/api/chat`. 정답지: Python `src/tomodachai/{llm,time_system}.py`.

## Global Constraints

- **Python 정답지는 수정 금지** — `src/tomodachai/**`, `tests/**`는 읽기만. 검증 기준으로만 사용.
- **`Snapshot` DTO 모양 동결** — `prototype/web/src/lib/types.ts`의 필드/타입을 절대 바꾸지 않는다.
- **`src/sim/`는 프레임워크 무의존** — Babylon/Svelte/Tauri를 import하지 않는다(순수 TS, vitest 대상). Tauri 의존은 `src/llm.ts`에만.
- **Tauri는 v2** — JS 플러그인 `@tauri-apps/plugin-http`, Rust crate `tauri-plugin-http`, capabilities 권한 필요.
- **사용자 WIP 파일 건드리지 말 것** — `CLAUDE.md`, `docs/plan/01-character.md`, `docs/plan/03-space-and-events.md`(미커밋 수정) 및 untracked(`.mcp.json`, `godot/`, `mii.blend*`, `sh.exe.stackdump`)는 `git add` 금지.
- **브랜치:** 현재 `feat/client-sim-migration`에서 작업. main 직접 푸시 금지.
- **커밋 트레일러:** 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **작업 디렉터리:** 명령은 별도 표기 없으면 repo 루트(`d:\Users\user\Desktop\Projects\tomodachai`) 기준. npm 명령은 `prototype/web`에서.

---

## File Structure

- `prototype/web/vitest.config.ts` (생성) — vitest 설정(플러그인 없는 순수 node 환경).
- `prototype/web/src/sim/clock.ts` (생성) — `GameClock` 포팅 + 시간 상수.
- `prototype/web/src/sim/index.ts` (생성) — sim 공개 표면: `getSnapshot(since)` 스텁 + write 액션 no-op.
- `prototype/web/src/sim/__golden__/parse_json.json` (생성, 덤프 산출) — `_parse_json` 골든.
- `prototype/web/src/sim/__golden__/game_clock.json` (생성, 덤프 산출) — `GameClock` 골든.
- `prototype/web/src/sim/__golden__/loadGolden.ts` (생성) — 골든 JSON 로더 헬퍼.
- `prototype/web/src/sim/*.test.ts` (생성) — vitest.
- `prototype/web/src/llm.ts` (생성) — LLM seam: `parseJson` / `chat` / `chatJson` + 전송 분기.
- `prototype/web/src/llm.test.ts` (생성) — vitest(파싱 골든 + mock fetch retry).
- `prototype/web/src/lib/api.ts` (수정) — `getSnapshot`/write를 sim 함수 호출로 교체.
- `prototype/web/package.json` (수정) — vitest·@tauri-apps/plugin-http 의존 + test 스크립트.
- `scripts/dump_golden.py` (생성) — Python 정답지 → 골든 JSON 덤프 CLI.
- `prototype/desktop/src-tauri/Cargo.toml` (수정) — `tauri-plugin-http`.
- `prototype/desktop/src-tauri/src/main.rs` (수정) — 플러그인 등록.
- `prototype/desktop/src-tauri/capabilities/default.json` (생성/수정) — http 권한 + Ollama 스코프.

---

## Task 1: vitest 하니스

**Files:**
- Create: `prototype/web/vitest.config.ts`
- Modify: `prototype/web/package.json`
- Create: `prototype/web/src/sim/smoke.test.ts`

**Interfaces:**
- Consumes: 없음.
- Produces: `npm test`(= `vitest run`) 실행 환경. 이후 모든 태스크가 이 러너를 씀.

- [ ] **Step 1: vitest 설정 파일 생성**

`prototype/web/vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config";

// 순수 TS 로직(src/sim, src/llm) 단위 테스트용. Svelte/Babylon 플러그인 없이 node 환경.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
```

- [ ] **Step 2: package.json에 의존성·스크립트 추가**

`prototype/web/package.json`의 `scripts`에 추가:
```json
    "test": "vitest run",
    "test:watch": "vitest",
    "golden:gen": "python ../../scripts/dump_golden.py"
```
`devDependencies`에 추가:
```json
    "vitest": "^2.1.0"
```

- [ ] **Step 3: 의존성 설치**

Run (`prototype/web`에서): `npm install`
Expected: vitest 설치 완료, 에러 없음.

- [ ] **Step 4: 러너 동작 확인용 스모크 테스트 작성**

`prototype/web/src/sim/smoke.test.ts`:
```ts
import { describe, it, expect } from "vitest";

describe("vitest harness", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 5: 테스트 실행해 그린 확인**

Run (`prototype/web`에서): `npm test`
Expected: PASS (1 test passed).

- [ ] **Step 6: 커밋**

```bash
git add prototype/web/vitest.config.ts prototype/web/package.json prototype/web/package-lock.json prototype/web/src/sim/smoke.test.ts
git commit -m "chore(web): vitest 하니스 도입

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: 골든 덤프 스크립트 + 로더 + `parseJson` (LLM seam 1/2)

**Files:**
- Create: `scripts/dump_golden.py`
- Create: `prototype/web/src/sim/__golden__/loadGolden.ts`
- Create: `prototype/web/src/sim/__golden__/parse_json.json` (덤프 산출)
- Create: `prototype/web/src/llm.ts`
- Create: `prototype/web/src/llm.test.ts`

**Interfaces:**
- Consumes: Task 1 vitest.
- Produces:
  - `parseJson(text: string): Record<string, unknown>` (export from `src/llm.ts`) — 마크다운/중괄호/raw 순 JSON 추출, 빈 문자열·실패 시 throw.
  - `loadGolden<T>(name: string): T[]` (export from `src/sim/__golden__/loadGolden.ts`) — 골든 배열 로드.
  - 골든 케이스 모양: `{ "input": <any>, "expected": <any>, "throws"?: true }`.

- [ ] **Step 1: 덤프 스크립트 작성 (parse_json 섹션)**

`scripts/dump_golden.py`:
```python
"""Python 정답지(src/tomodachai)를 결정론 입력으로 호출해 골든 JSON을 덤프한다.

규칙 변경 시 재실행: python scripts/dump_golden.py
산출물은 prototype/web/src/sim/__golden__/*.json (커밋 대상).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# src 레이아웃 임포트 보장
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

GOLDEN_DIR = ROOT / "prototype" / "web" / "src" / "sim" / "__golden__"


def _write(name: str, cases: list[dict]) -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    path = GOLDEN_DIR / f"{name}.json"
    path.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(cases)} cases)")


def dump_parse_json() -> None:
    from tomodachai.llm import LLMClient

    inputs = [
        '{"a": 1}',
        '```json\n{"b": 2}\n```',
        '```\n{"c": 3}\n```',
        '설명입니다 {"d": 4} 끝',
        '앞 {"e": {"f": 5}} 뒤',
    ]
    throwing = ["", "no json here"]

    cases: list[dict] = []
    for text in inputs:
        cases.append({"input": text, "expected": LLMClient._parse_json(text)})
    for text in throwing:
        cases.append({"input": text, "throws": True})
    _write("parse_json", cases)


def main() -> None:
    dump_parse_json()
    # 이후 태스크에서 dump_game_clock() 추가


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 덤프 실행해 골든 생성**

Run (repo 루트에서): `python scripts/dump_golden.py`
Expected: `wrote .../parse_json.json (7 cases)`. 파일에 5개 정상 케이스(`expected` 포함) + 2개 `throws` 케이스가 들어감.

- [ ] **Step 3: 골든 로더 헬퍼 작성**

`prototype/web/src/sim/__golden__/loadGolden.ts`:
```ts
// 골든 픽스처 JSON을 읽어 케이스 배열로 반환. Python dump_golden.py가 생성.
export interface GoldenCase<I = unknown, E = unknown> {
  input: I;
  expected?: E;
  throws?: true;
}

import parseJsonCases from "./parse_json.json";

const REGISTRY: Record<string, GoldenCase[]> = {
  parse_json: parseJsonCases as GoldenCase[],
};

export function loadGolden<I = unknown, E = unknown>(name: string): GoldenCase<I, E>[] {
  const cases = REGISTRY[name];
  if (!cases) throw new Error(`unknown golden fixture: ${name}`);
  return cases as GoldenCase<I, E>[];
}
```

> 참고: vitest는 `resolveJsonModule` 기본 지원. tsconfig에 별도 설정 불필요(vite/vitest가 .json import 처리).

- [ ] **Step 4: parseJson 실패 테스트 작성 (Red)**

`prototype/web/src/llm.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { parseJson } from "./llm";
import { loadGolden } from "./sim/__golden__/loadGolden";

describe("parseJson (golden vs Python _parse_json)", () => {
  const cases = loadGolden<string, Record<string, unknown>>("parse_json");
  it.each(cases)("input %# matches Python", (c) => {
    if (c.throws) {
      expect(() => parseJson(c.input)).toThrow();
    } else {
      expect(parseJson(c.input)).toEqual(c.expected);
    }
  });
});
```

- [ ] **Step 5: 테스트 실행해 실패 확인**

Run (`prototype/web`에서): `npm test`
Expected: FAIL — `parseJson`이 `./llm`에 없음(import 에러) 또는 함수 미정의.

- [ ] **Step 6: `parseJson` 구현 (Python `_parse_json` 1:1 포팅)**

`prototype/web/src/llm.ts`:
```ts
// Python src/tomodachai/llm.py 의 LLMClient 미러 (Ollama 직통 seam).

/** LLM 응답 문자열에서 JSON 추출. Python _parse_json 1:1 포팅(순수, 결정론). */
export function parseJson(text: string): Record<string, unknown> {
  const t = text.trim();
  if (!t) throw new Error("빈 응답");
  // 마크다운 코드블록 안의 JSON (non-greedy, DOTALL 동등)
  const fence = t.match(/```(?:json)?\s*\n?([\s\S]*?)```/);
  if (fence) return JSON.parse(fence[1].trim());
  // 첫 { ... } 블록 (greedy, DOTALL 동등)
  const brace = t.match(/\{[\s\S]*\}/);
  if (brace) return JSON.parse(brace[0]);
  return JSON.parse(t);
}
```

- [ ] **Step 7: 테스트 실행해 그린 확인**

Run (`prototype/web`에서): `npm test`
Expected: PASS — parse_json 7케이스 전부 통과.

- [ ] **Step 8: 커밋**

```bash
git add scripts/dump_golden.py prototype/web/src/llm.ts prototype/web/src/llm.test.ts prototype/web/src/sim/__golden__/loadGolden.ts prototype/web/src/sim/__golden__/parse_json.json
git commit -m "feat(web): LLM seam parseJson + 골든 덤프 하니스

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: LLM seam 전송 — `chat`/`chatJson` (Ollama + retry + Tauri 분기)

**Files:**
- Modify: `prototype/web/src/llm.ts`
- Modify: `prototype/web/src/llm.test.ts`
- Modify: `prototype/web/package.json`
- Modify: `prototype/desktop/src-tauri/Cargo.toml`
- Modify: `prototype/desktop/src-tauri/src/main.rs`
- Create: `prototype/desktop/src-tauri/capabilities/default.json`

**Interfaces:**
- Consumes: `parseJson` (Task 2).
- Produces:
  - `type Msg = { role: "system" | "user" | "assistant"; content: string }`
  - `chat(messages: Msg[], opts?: ChatOpts): Promise<string>`
  - `chatJson(messages: Msg[], opts?: ChatOpts & { retries?: number }): Promise<Record<string, unknown>>`
  - `type ChatOpts = { temperature?: number; maxTokens?: number; apiBase?: string; model?: string }`

- [ ] **Step 1: chatJson retry 테스트 작성 (Red, mock fetch)**

`prototype/web/src/llm.test.ts`에 추가:
```ts
import { vi, beforeEach, afterEach } from "vitest";
import { chat, chatJson } from "./llm";

function ollamaReply(content: string) {
  return { ok: true, json: async () => ({ message: { content } }) } as unknown as Response;
}

describe("chat / chatJson (mocked fetch)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("chat returns Ollama message content", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce(ollamaReply("안녕"));
    await expect(chat([{ role: "user", content: "hi" }])).resolves.toBe("안녕");
  });

  it("chatJson retries on bad JSON then succeeds (retries=2 → 2 calls)", async () => {
    (globalThis.fetch as any)
      .mockResolvedValueOnce(ollamaReply("not json"))
      .mockResolvedValueOnce(ollamaReply('{"ok": true}'));
    await expect(chatJson([{ role: "user", content: "hi" }])).resolves.toEqual({ ok: true });
    expect((globalThis.fetch as any).mock.calls.length).toBe(2);
  });

  it("chatJson throws after exhausting retries (3 calls)", async () => {
    (globalThis.fetch as any).mockResolvedValue(ollamaReply("nope"));
    await expect(chatJson([{ role: "user", content: "hi" }])).rejects.toThrow();
    expect((globalThis.fetch as any).mock.calls.length).toBe(3);
  });
});
```

- [ ] **Step 2: 테스트 실행해 실패 확인**

Run (`prototype/web`에서): `npm test`
Expected: FAIL — `chat`/`chatJson` 미정의.

- [ ] **Step 3: 전송 + chat/chatJson 구현**

`prototype/web/src/llm.ts`에 추가:
```ts
export type Msg = { role: "system" | "user" | "assistant"; content: string };
export type ChatOpts = {
  temperature?: number;
  maxTokens?: number;
  apiBase?: string;
  model?: string;
};

const DEFAULTS = {
  apiBase: "http://localhost:11434",
  model: "llama3.1",
  temperature: 0.8,
  maxTokens: 512,
};

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

// 패키징(Tauri)에선 플러그인 fetch(CORS 우회), dev 브라우저/노드에선 전역 fetch.
async function httpFetch(url: string, init: RequestInit): Promise<Response> {
  if (isTauri()) {
    const { fetch: tauriFetch } = await import("@tauri-apps/plugin-http");
    return tauriFetch(url, init) as unknown as Response;
  }
  return globalThis.fetch(url, init);
}

export async function chat(messages: Msg[], opts: ChatOpts = {}): Promise<string> {
  const apiBase = opts.apiBase ?? DEFAULTS.apiBase;
  const body = {
    model: opts.model ?? DEFAULTS.model,
    messages,
    stream: false,
    options: {
      temperature: opts.temperature ?? DEFAULTS.temperature,
      num_predict: opts.maxTokens ?? DEFAULTS.maxTokens,
    },
  };
  const res = await httpFetch(`${apiBase}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Ollama 응답 오류: ${res.status}`);
  const data = (await res.json()) as { message?: { content?: string } };
  return data.message?.content ?? "";
}

export async function chatJson(
  messages: Msg[],
  opts: ChatOpts & { retries?: number } = {},
): Promise<Record<string, unknown>> {
  const retries = opts.retries ?? 2;
  let lastErr: unknown = null;
  let content = "";
  for (let attempt = 0; attempt <= retries; attempt++) {
    content = await chat(messages, opts);
    try {
      return parseJson(content);
    } catch (e) {
      lastErr = e;
    }
  }
  throw new Error(`JSON 파싱 실패 (${retries + 1}회 시도): ${lastErr}\n응답: ${content.slice(0, 500)}`);
}
```

- [ ] **Step 4: 테스트 실행해 그린 확인**

Run (`prototype/web`에서): `npm test`
Expected: PASS — chat 1건 + chatJson retry 2건 통과(호출 횟수 2/3 검증 포함).

- [ ] **Step 5: Tauri HTTP 플러그인 의존 추가 (JS + Rust)**

`prototype/web/package.json` `dependencies`에 추가:
```json
    "@tauri-apps/plugin-http": "^2"
```
Run (`prototype/web`에서): `npm install`
Expected: 설치 완료.

`prototype/desktop/src-tauri/Cargo.toml` `[dependencies]`에 추가:
```toml
tauri-plugin-http = "2"
```

- [ ] **Step 6: 플러그인 등록 + 권한**

`prototype/desktop/src-tauri/src/main.rs`의 빌더 체인에 `.plugin(tauri_plugin_http::init())`를 추가한다(`tauri::Builder::default()` 직후). 예:
```rust
tauri::Builder::default()
    .plugin(tauri_plugin_http::init())
    // ...기존 설정...
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
```

`prototype/desktop/src-tauri/capabilities/default.json` 생성(또는 기존 capabilities에 병합):
```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "기본 권한 + Ollama HTTP",
  "windows": ["main"],
  "permissions": [
    "core:default",
    {
      "identifier": "http:default",
      "allow": [{ "url": "http://localhost:11434/*" }, { "url": "http://127.0.0.1:11434/*" }]
    }
  ]
}
```

> Rust 컴파일/Tauri 실행 검증은 환경 의존(Rust 툴체인 필요)이라 이 태스크의 자동 테스트 대상이 아니다.
> vitest는 dev fetch 경로(mock)만 검증한다. 실제 Tauri 경로는 Task 5의 수동 스모크에서 확인.

- [ ] **Step 7: 커밋**

```bash
git add prototype/web/src/llm.ts prototype/web/src/llm.test.ts prototype/web/package.json prototype/web/package-lock.json prototype/desktop/src-tauri/Cargo.toml prototype/desktop/src-tauri/src/main.rs prototype/desktop/src-tauri/capabilities/default.json
git commit -m "feat: LLM seam chat/chatJson — Ollama 직통 + Tauri http 분기

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `time_system` 포팅 — `GameClock`

**Files:**
- Modify: `scripts/dump_golden.py`
- Create: `prototype/web/src/sim/__golden__/game_clock.json` (덤프 산출)
- Modify: `prototype/web/src/sim/__golden__/loadGolden.ts`
- Create: `prototype/web/src/sim/clock.ts`
- Create: `prototype/web/src/sim/clock.test.ts`

**Interfaces:**
- Consumes: Task 2 `loadGolden`.
- Produces (export from `src/sim/clock.ts`):
  - `class GameClock { constructor(timeFlip?: boolean, nowFn?: () => Date); now(): Date; getGameHour(at?: Date, timeFlip?: boolean): number; getTimePeriod(at?: Date): string; isNewDay(lastCheck: Date): boolean; catchupEventCount(offlineHours: number): number }`
  - 상수 export: `CATCHUP_MAX_EVENTS_PER_DAY=5`, `OFFLINE_THRESHOLD_MINUTES=5`, `EVENT_INTERVAL_MIN_SECONDS=600`, `EVENT_INTERVAL_MAX_SECONDS=1800`.

- [ ] **Step 1: 덤프 스크립트에 game_clock 섹션 추가**

`scripts/dump_golden.py`의 `dump_parse_json` 아래에 추가:
```python
def dump_game_clock() -> None:
    from datetime import datetime, timezone
    from tomodachai.time_system import GameClock

    clock = GameClock()

    def iso(y, mo, d, h, mi=0):
        return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)

    # getGameHour / getTimePeriod — (iso, flip) → {hour, period}
    period_inputs = [
        (iso(2026, 6, 19, 7), False),
        (iso(2026, 6, 19, 13), False),
        (iso(2026, 6, 19, 19), False),
        (iso(2026, 6, 19, 22), False),
        (iso(2026, 6, 19, 2), False),
        (iso(2026, 6, 19, 7), True),   # flip → 19시
        (iso(2026, 6, 19, 23), True),  # flip → 11시
    ]
    period_cases = [
        {
            "input": {"at": t.isoformat(), "flip": flip},
            "expected": {
                "hour": clock.get_game_hour(t, time_flip=flip),
                "period": clock.get_time_period(t) if not flip else None,
            },
        }
        for t, flip in period_inputs
    ]
    _write("game_clock_period", period_cases)

    # isNewDay — (lastCheck, now) → bool. now를 주입하기 위해 monkeypatch.
    new_day_inputs = [
        (iso(2026, 6, 19, 3), iso(2026, 6, 19, 6)),   # 같은날 5시 경계 넘음 → True
        (iso(2026, 6, 19, 6), iso(2026, 6, 19, 9)),   # 둘 다 리셋 이후, 다음날 안 넘음 → False
        (iso(2026, 6, 19, 6), iso(2026, 6, 20, 6)),   # 다음날 5시 도달 → True
        (iso(2026, 6, 19, 10), iso(2026, 6, 19, 9)),  # now < lastCheck → False
    ]
    nd_cases = []
    for last, now in new_day_inputs:
        # GameClock.is_new_day는 self.now()를 쓰므로, now를 주입한 임시 서브클래스로 평가
        fixed = type("Fixed", (GameClock,), {"now": lambda self, _n=now: _n})()
        nd_cases.append(
            {"input": {"lastCheck": last.isoformat(), "now": now.isoformat()},
             "expected": fixed.is_new_day(last)}
        )
    _write("game_clock_newday", nd_cases)

    # catchupEventCount — offline_hours → int (0.5 경계 회피)
    catchup_inputs = [0, 0.4, 6, 12, 24, 48, 100]
    cc_cases = [
        {"input": h, "expected": clock.catchup_event_count(h)} for h in catchup_inputs
    ]
    _write("game_clock_catchup", cc_cases)
```
그리고 `main()`에 `dump_game_clock()` 호출 추가:
```python
def main() -> None:
    dump_parse_json()
    dump_game_clock()
```

- [ ] **Step 2: 덤프 실행해 골든 생성**

Run (repo 루트에서): `python scripts/dump_golden.py`
Expected: `game_clock_period`(7), `game_clock_newday`(4), `game_clock_catchup`(7) 파일 생성 로그.

- [ ] **Step 3: 로더 레지스트리에 신규 골든 등록**

`prototype/web/src/sim/__golden__/loadGolden.ts` 상단 import + REGISTRY 확장:
```ts
import parseJsonCases from "./parse_json.json";
import periodCases from "./game_clock_period.json";
import newdayCases from "./game_clock_newday.json";
import catchupCases from "./game_clock_catchup.json";

const REGISTRY: Record<string, GoldenCase[]> = {
  parse_json: parseJsonCases as GoldenCase[],
  game_clock_period: periodCases as GoldenCase[],
  game_clock_newday: newdayCases as GoldenCase[],
  game_clock_catchup: catchupCases as GoldenCase[],
};
```

- [ ] **Step 4: GameClock 테스트 작성 (Red)**

`prototype/web/src/sim/clock.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { GameClock } from "./clock";
import { loadGolden } from "./__golden__/loadGolden";

describe("GameClock.getGameHour (golden)", () => {
  const clock = new GameClock();
  const cases = loadGolden<{ at: string; flip: boolean }, { hour: number; period: string | null }>(
    "game_clock_period",
  );
  it.each(cases)("hour/period %#", (c) => {
    const at = new Date(c.input.at);
    expect(clock.getGameHour(at, c.input.flip)).toBe(c.expected!.hour);
    if (c.expected!.period !== null) {
      expect(clock.getTimePeriod(at)).toBe(c.expected!.period);
    }
  });
});

describe("GameClock.isNewDay (golden)", () => {
  const cases = loadGolden<{ lastCheck: string; now: string }, boolean>("game_clock_newday");
  it.each(cases)("isNewDay %#", (c) => {
    const now = new Date(c.input.now);
    const clock = new GameClock(false, () => now);
    expect(clock.isNewDay(new Date(c.input.lastCheck))).toBe(c.expected);
  });
});

describe("GameClock.catchupEventCount (golden)", () => {
  const clock = new GameClock();
  const cases = loadGolden<number, number>("game_clock_catchup");
  it.each(cases)("catchup %#", (c) => {
    expect(clock.catchupEventCount(c.input)).toBe(c.expected);
  });
});
```

- [ ] **Step 5: 테스트 실행해 실패 확인**

Run (`prototype/web`에서): `npm test`
Expected: FAIL — `./clock`의 `GameClock` 미정의.

- [ ] **Step 6: GameClock 구현 (Python time_system 1:1 포팅)**

`prototype/web/src/sim/clock.ts`:
```ts
// Python src/tomodachai/time_system.py GameClock 미러. 순수 TS, now()만 주입 가능.

const DAILY_RESET_HOUR = 5;
const TIME_PERIODS: readonly [number, number, string][] = [
  [5, 12, "아침"],
  [12, 17, "낮"],
  [17, 21, "저녁"],
  [21, 24, "밤"],
  [0, 5, "밤"],
];

export const EVENT_INTERVAL_MIN_SECONDS = 10 * 60;
export const EVENT_INTERVAL_MAX_SECONDS = 30 * 60;
export const CATCHUP_MAX_EVENTS_PER_DAY = 5;
export const OFFLINE_THRESHOLD_MINUTES = 5;

export class GameClock {
  constructor(
    public timeFlip = false,
    private nowFn: () => Date = () => new Date(),
  ) {}

  now(): Date {
    return this.nowFn();
  }

  getGameHour(at?: Date, timeFlip?: boolean): number {
    const t = at ?? this.now();
    let hour = t.getUTCHours();
    const flip = timeFlip ?? this.timeFlip;
    if (flip) hour = (hour + 12) % 24;
    return hour;
  }

  getTimePeriod(at?: Date): string {
    const hour = this.getGameHour(at);
    for (const [start, end, name] of TIME_PERIODS) {
      if (start <= hour && hour < end) return name;
    }
    return "밤";
  }

  isNewDay(lastCheck: Date): boolean {
    const now = this.now();
    if (now <= lastCheck) return false;
    let reset = new Date(
      Date.UTC(
        lastCheck.getUTCFullYear(),
        lastCheck.getUTCMonth(),
        lastCheck.getUTCDate(),
        DAILY_RESET_HOUR,
        0,
        0,
        0,
      ),
    );
    if (lastCheck >= reset) reset = new Date(reset.getTime() + 86_400_000);
    return now >= reset;
  }

  catchupEventCount(offlineHours: number): number {
    if (offlineHours <= 0) return 0;
    const days = offlineHours / 24.0;
    const count = Math.round(days * CATCHUP_MAX_EVENTS_PER_DAY);
    const maxCount = Math.max(1, Math.trunc(days + 1)) * CATCHUP_MAX_EVENTS_PER_DAY;
    return Math.max(1, Math.min(count, maxCount));
  }
}
```

- [ ] **Step 7: 테스트 실행해 그린 확인**

Run (`prototype/web`에서): `npm test`
Expected: PASS — period(7) + newday(4) + catchup(7) 골든 통과.

- [ ] **Step 8: 커밋**

```bash
git add scripts/dump_golden.py prototype/web/src/sim/clock.ts prototype/web/src/sim/clock.test.ts prototype/web/src/sim/__golden__/
git commit -m "feat(sim): time_system GameClock 포팅 (골든 대조)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: 스냅샷 seam — 스텁 sim + 렌더러 인-프로세스 배선

**Files:**
- Create: `prototype/web/src/sim/index.ts`
- Create: `prototype/web/src/sim/index.test.ts`
- Modify: `prototype/web/src/lib/api.ts`

**Interfaces:**
- Consumes: `GameClock` (Task 4), `Snapshot` 타입 (`src/lib/types.ts`, 기존).
- Produces (export from `src/sim/index.ts`):
  - `getSnapshot(since: number): Snapshot`
  - `feed/give/save/reset/answerBubble` no-op — 각각 `Promise<Record<string, unknown>>` 반환(`{}`).

- [ ] **Step 1: 스텁 getSnapshot 테스트 작성 (Red)**

`prototype/web/src/sim/index.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { getSnapshot } from "./index";

describe("getSnapshot stub", () => {
  it("derives clock/minutes/asleep from injected time and has empty village", () => {
    // 자는 시간(02:30 UTC) 주입
    const snap = getSnapshot(0, () => new Date(Date.UTC(2026, 5, 19, 2, 30)));
    expect(snap.clock).toBe("02:30");
    expect(snap.minutes).toBe(150);
    expect(snap.asleep).toBe(true);
    expect(snap.realtime).toBe(true);
    expect(snap.characters).toEqual([]);
    expect(snap.bubbles).toEqual([]);
  });

  it("daytime is awake", () => {
    const snap = getSnapshot(0, () => new Date(Date.UTC(2026, 5, 19, 13, 0)));
    expect(snap.clock).toBe("13:00");
    expect(snap.asleep).toBe(false);
  });
});
```

- [ ] **Step 2: 테스트 실행해 실패 확인**

Run (`prototype/web`에서): `npm test`
Expected: FAIL — `./index`의 `getSnapshot` 미정의.

- [ ] **Step 3: 스텁 sim 구현**

`prototype/web/src/sim/index.ts`:
```ts
// Phase 0 스텁 sim: 빈 마을 + 도는 시계만. 실제 시뮬은 후속 Phase에서.
import type { Snapshot } from "../lib/types";
import { GameClock } from "./clock";

const SLEEP_START_MIN = 23 * 60 - 5; // 22:55
const WAKE_MIN = 7 * 60; // 07:00

const EMPTY_RANKINGS = { best_couple: [], popular_m: [], popular_f: [], fighters: [] };

export function getSnapshot(_since: number, nowFn?: () => Date): Snapshot {
  const clock = new GameClock(false, nowFn);
  const now = clock.now();
  const hour = clock.getGameHour();
  const minute = now.getUTCMinutes();
  const minutes = hour * 60 + minute;
  const clockStr = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
  return {
    village: "우리 마을",
    provider: "ollama",
    day: 1,
    clock: clockStr,
    minutes,
    seq: 0,
    locations: {},
    foods: [],
    rankings: EMPTY_RANKINGS,
    asleep: minutes >= SLEEP_START_MIN || minutes < WAKE_MIN,
    realtime: true,
    photos: [],
    dishes: [],
    characters: [],
    events: [],
    bubbles: [],
  };
}

const noop = async (): Promise<Record<string, unknown>> => ({});
export const feed = noop;
export const give = noop;
export const save = noop;
export const reset = noop;
export const answerBubble = noop;
```

- [ ] **Step 4: 테스트 실행해 그린 확인**

Run (`prototype/web`에서): `npm test`
Expected: PASS — 스텁 2케이스 통과(전체 스위트 그린).

- [ ] **Step 5: 렌더러 데이터 출처를 sim으로 교체**

`prototype/web/src/lib/api.ts` 전체를 아래로 교체(HTTP fetch 제거, sim 함수 위임):
```ts
import type { Snapshot } from "./types";
import * as sim from "../sim";

export async function getSnapshot(since: number): Promise<Snapshot> {
  return sim.getSnapshot(since);
}

export const feed = (char_id: number, food_id: number) => sim.feed();
export const give = (char_id: number, tool: string) => sim.give();
export const answerBubble = (index: number, char: string, allow: boolean) => sim.answerBubble();
export const saveGame = () => sim.save();
export const resetGame = () => sim.reset();
```

> `sim/index.ts`가 named export(`getSnapshot`, `feed`, ...)를 제공하므로 `import * as sim`로 받는다.
> 호출부(`sim.ts`, `components/*.svelte`)의 시그니처는 그대로 유지된다(인자만 무시).

- [ ] **Step 6: 타입체크 통과 확인**

Run (`prototype/web`에서): `npm run check`
Expected: svelte-check 0 errors(기존 경고 외 신규 에러 없음).

- [ ] **Step 7: 수동 스모크 — 걷는 해골**

Run (`prototype/web`에서): `npm run vite`
브라우저에서 확인(성공 기준):
- 빈 마을(캐릭터 0)이 렌더되고 **HUD 시계가 실시간으로 흐른다**(분 단위 갱신, 하늘색/수면 라벨 반영).
- 네트워크 탭에 `/api/snapshot` 폴링 요청이 **없다**(서버 프로세스 0개).
- (선택) Ollama 기동 상태에서 devtools 콘솔에 `import("./src/llm").then(m=>m.chat([{role:"user",content:"hi"}])).then(console.log)` 실행 → 응답 문자열 반환(브라우저 CORS 허용 시). CORS로 막히면 Tauri(`prototype/desktop`에서 `npm run dev`) 경로로 확인.

- [ ] **Step 8: 커밋**

```bash
git add prototype/web/src/sim/index.ts prototype/web/src/sim/index.test.ts prototype/web/src/lib/api.ts
git commit -m "feat(web): 스냅샷 seam — 스텁 sim 인-프로세스 배선(서버 제거)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (작성자 체크 결과)

**1. Spec coverage:**
- §4 LLM seam(parseJson/chat/chatJson/전송/Ollama/retry) → Task 2,3 ✅
- §5 스냅샷 seam(DTO 유지, 함수 호출, 스텁, village.ts 최소 수정) → Task 5 ✅
- §6 time_system(GameClock, 주입 now, clock/minutes/asleep 파생) → Task 4 + Task 5 스텁 ✅
- §7 오라클 하니스(dump_golden.py, __golden__, vitest 로더) → Task 1,2,4 ✅
- §8 성공 기준(vitest 그린/걷는 해골/Ollama 호출/Python 미수정) → Task 1~5 + Task 5 수동 스모크 ✅
- §3 구조(sim 순수 TS, 단방향 의존, 픽스처 위치) → Global Constraints + File Structure ✅
- 갭 없음.

**2. Placeholder scan:** "TBD/이후 추가" 류 없음. dump_golden의 `main()`은 Task 2에서 parse_json만, Task 4에서 game_clock 추가 — 각 단계 코드 명시(점진 확장이며 미완 placeholder 아님). ✅

**3. Type consistency:** `parseJson`/`chat`/`chatJson`/`GameClock`/`getSnapshot`/`loadGolden`/`GoldenCase` 이름·시그니처가 정의 태스크와 소비 태스크에서 일치. `getSnapshot`는 Task 5에서 `nowFn?` 2번째 인자 추가(테스트 주입용) — `api.ts`는 1인자만 호출(기본 now 사용)로 호환. ✅
