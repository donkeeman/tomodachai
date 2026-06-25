# 클라 시뮬 Phase 5 — LLM 관찰 생성기 (conversation · fountain · news) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Phase 5는 "관찰형" 생성기 3종을 포팅. (1) `conversation.py` — `build_conversation_prompt`(순수 결정론 문자열 → 골든) + `ConversationEngine`(LLM seam), (2) `fountain.py` — 모금(결정론 상태)·랩배틀·끝말잇기(LLM seam + 결정론 후처리), (3) `news.py` — `NewsManager`(real 우선순위 선택 + summary 결정론, LLM seam) + absurd(LLM seam) + 조회. Phase 4 접근자/PersonalityType 소비.

**Architecture:** Phase 0~4 패턴 유지. **결정론(프롬프트 조립/이벤트 선택/모금액/후처리 fallback)은 골든 또는 단위 테스트로 1:1**, **LLM 호출 자체는 주입 stub `LlmClient`로 구조만 검증**(메시지 배열·max_tokens·raw 파싱). `src/sim/` 프레임워크 무의존.

**Tech Stack:** TS, vitest, 골든 하니스. 정답지: `src/tomodachai/conversation.py`, `fountain.py`, `news.py`. 소비: `personalityType.ts`(PersonalityType), `characterAccessors.ts`(name/speech_habits/backstory), `personality.ts`(personalityCode), `relationship.ts`(getStatusText/getFriendshipText), `memory.ts`(SocialEvent), `llm.ts`(LlmClient).

## Global Constraints
- **Python 정답지 수정 금지** (`src/tomodachai/**`, `tests/**`, `data/**` 읽기 전용; 덤프는 READ만). `scripts/dump_golden.py`(dev)는 수정 허용.
- **`src/sim/`는 프레임워크 무의존** (`import type`만 cross-module).
- **Node 18+** — `PATH="/c/Users/user/AppData/Roaming/nvm/v22.20.0:$PATH"` 프리픽스. npm은 `prototype/web`에서, python/git은 repo 루트. Bash CWD persists — 명시적 cd.
- **각 태스크 검증에 `npm test` AND `npm run check`(svelte-check) 둘 다 포함.**
- **사용자 WIP `git add` 금지**: `CLAUDE.md`, `docs/plan/01-character.md`, `docs/plan/03-space-and-events.md`, untracked `.mcp.json`/`godot/`/`mii.blend*`/`sh.exe.stackdump`.
- **브랜치** `feat/client-sim-migration`, main 직접 푸시 금지. base: `f6bf2f9`.
- **커밋 트레일러**: 끝에 정확히 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## 범위 밖 (Phase 5 아님)
- LLM 응답 내용을 Python과 일치시키는 것(비결정). 주입 stub로 구조/후처리만.
- GameState/simulation tick(Phase 6), save 직렬화(Phase 7).
- `game_state.add_money` 본체 — fountain 모금 테스트는 `MoneyAdder` 덕타입 스텁(`addMoney(n)`)으로 검증.

## File Structure
- `prototype/web/src/sim/conversation.ts` (생성) — `DialogueLine`/`ConversationResult` 타입, `formatMemory`/`formatSpeechHabits`(헬퍼), `SYSTEM_PROMPT`, `buildConversationPrompt`(순수), `ConversationEngine`(LLM seam).
- `prototype/web/src/sim/fountain.ts` (생성) — `DonationResult`/`RapVerse`/`RapBattleResult`/`WordChainRound`/`WordChainResult` 타입, `MoneyAdder` 인터페이스, `FountainManager`(donation 상태 + rap/wordchain seam).
- `prototype/web/src/sim/news.ts` (생성) — `NewsArticle` 타입, `buildEventSummary`(헬퍼), `NewsManager`(real/absurd seam + 조회).
- 각 `*.test.ts`, `scripts/dump_golden.py`(섹션 추가), `loadGolden.ts`(레지스트리 확장).

---

## Task 1: conversation 결정론 — 헬퍼 + build_conversation_prompt (골든)

**Files:** Modify `scripts/dump_golden.py`, `loadGolden.ts`; Create `prototype/web/src/sim/conversation.ts`(이 태스크: 타입 + 헬퍼 + SYSTEM_PROMPT + buildConversationPrompt), `prototype/web/src/sim/conversation.test.ts`.

**Interfaces (Produces):**
- `interface DialogueLine { speaker: string; text: string }`, `interface ConversationResult { dialogue: DialogueLine[]; deltas: Record<string, Record<string, number>>; summary: string }`.
- `SYSTEM_PROMPT: string` (conversation.py `_SYSTEM_PROMPT` 1:1).
- `buildConversationPrompt(charA, charB, personalityA, personalityB, relAb, relBa, memories, location, timeOfDay): string` — Python `build_conversation_prompt`(64) 1:1. 내부에서 `characterName`/`characterSpeechHabits`/`characterBackstory`(Phase4 접근자), `getStatusText(rel.stage)`/`getFriendshipText(rel.friendship)`(relationship.ts), `formatMemory`/`formatSpeechHabits` 사용.

**오라클:** `conversation.py` `build_conversation_prompt`(64-129), `_format_memory`(23-47), `_format_speech_habits`(50-58), `_SYSTEM_PROMPT`(61). f-string `{{`/`}}` → 리터럴 `{`/`}`. `behavior_guide.strip()` 주의. `rel.get_status_text()`=`getStatusText(rel.stage)`, `rel.get_friendship_text()`=`getFriendshipText(rel.friendship)`.

- [ ] **Step 1: 덤프 (`dump_conversation_prompt`)** — Python에서 Character 2개(서로 다른 personality, speech_habits 일부 채움), Relationship 2개(서로 다른 stage/friendship), memories 2~3개(일부 None 필드 포함, 빈 케이스도) 구성. `load_personalities()`로 personality_a/b 획득. `build_conversation_prompt(...)` 호출 → 결과 문자열. 최소 2케이스(memories 있음/없음). `{"input": <식별자 dict>, "expected": <prompt string>}`. `_write("conversation_prompt", cases)`. `main()` 호출.
> 주의: Character/Relationship/SocialEvent 생성자 시그니처는 해당 .py 읽어 확인. memories 없을 때 memory_text="없음", speech_habits 빈 캐릭터는 habits "없음".
- [ ] **Step 2~3:** 덤프 실행 → `loadGolden.ts` 등록(1개).
- [ ] **Step 4: 실패 테스트 (Red)** — 골든 각 케이스의 TS Character/Relationship/SocialEvent/PersonalityType를 동일 구성, `buildConversationPrompt(...)` === expected (`toBe`, 문자열 정확). `SYSTEM_PROMPT` 시작 문자열 단언. formatMemory/formatSpeechHabits 단위(빈값→"없음").
- [ ] **Step 5: 실패 확인** → FAIL.
- [ ] **Step 6: 구현** — conversation.ts에 타입 + 헬퍼 + SYSTEM_PROMPT + buildConversationPrompt. 골든이 공백/개행 오타 잡음.
- [ ] **Step 7: 통과 + check** — `npm test` PASS, `npm run check` 0.
- [ ] **Step 8: 커밋** (`feat(sim): conversation 프롬프트 빌더 (골든)` + 트레일러). Stage: conversation.ts/test, dump_golden.py, loadGolden.ts, conversation_prompt.json.

---

## Task 2: ConversationEngine (LLM seam, 구조 검증)

**Files:** Modify `prototype/web/src/sim/conversation.ts`, Create `prototype/web/src/sim/conversationEngine.test.ts`.

**Interfaces (Produces):**
- `class ConversationEngine { constructor(llm: LlmClient, personalities: Record<string, PersonalityType>); generate(charA, charB, relAb, relBa, memories, location, timeOfDay?): Promise<ConversationResult> }` — Python `ConversationEngine`(132) 1:1. personality 룩업(`personalities[characterPersonalityCode(c)]`), buildConversationPrompt, `[{system: SYSTEM_PROMPT}, {user: prompt}]` → `llm.chatJson(messages)` → `{dialogue: raw.dialogue.map(DialogueLine), deltas: raw.deltas, summary: raw.summary}`.

**오라클:** `conversation.py` `ConversationEngine.generate`(141-177). `time_of_day` 기본값 "오후". raw["dialogue"]/["deltas"]/["summary"] 직접 인덱싱(키 없으면 throw — Python KeyError 미러, 충실).

- [ ] **Step 1: 통합 테스트 (Red)** — 주입 stub llm(고정 raw 반환) + PersonalityType 딕셔너리로: (a) messages 2개(system=SYSTEM_PROMPT, user에 charA.name/장소 포함), (b) 반환 ConversationResult가 raw 매핑과 일치(dialogue 각 line speaker/text, deltas/summary 그대로), (c) timeOfDay 기본 "오후"가 프롬프트에 반영, (d) personality_code로 personalities 룩업 확인. LLM 내용 미검증.
- [ ] **Step 2~3:** 실패 확인 → 구현 → `npm test` PASS + `npm run check` 0 → 커밋 (`feat(sim): ConversationEngine (LLM seam)` + 트레일러).

---

## Task 3: fountain 모금 (결정론, 골든 + 통합)

**Files:** Modify `scripts/dump_golden.py`, `loadGolden.ts`; Create `prototype/web/src/sim/fountain.ts`(이 태스크: 결과 타입 + MoneyAdder + FountainManager 모금부), `prototype/web/src/sim/fountain.test.ts`.

**Interfaces (Produces):**
- `interface DonationResult { day: number; characterCount: number; amount: number }`.
- `interface MoneyAdder { addMoney(n: number): void }`.
- `class FountainManager { hasDonated(day): boolean; runDonation(day, characterCount, gameState: MoneyAdder): DonationResult | null }`. `DONATION_PER_CHARACTER = 100`.

**오라클:** `fountain.py` `FountainManager.__init__`(70), `has_donated`(77), `run_donation`(81-104), `_DONATION_PER_CHARACTER=100`(22). `amount = max(0, character_count) * 100`. 같은 날 재호출 → None. amount>0일 때만 add_money. `_last_donation_day` 상태.

- [ ] **Step 1: 덤프 (`dump_donation`)** — Python에서 FountainManager로 시나리오 산출: (a) day=1, count=3 → amount 300, (b) 같은 날 재호출 → None, (c) count=0 → amount 0(add_money 미호출), (d) count 음수 → max(0,_)=0. game_state는 add_money 기록하는 stub. `{"input": {...}, "expected": {"result": DonationResult|null, "money_added": int}}`. `_write("donation", cases)`.
- [ ] **Step 2~3:** 덤프 실행 → 로더 등록.
- [ ] **Step 4: 실패 테스트 (Red)** — 골든 시나리오 재현: FountainManager + MoneyAdder 스텁. runDonation 결과/None, addMoney 호출액 단언. has_donated 상태 전이. amount=0일 때 addMoney 미호출 단언.
- [ ] **Step 5~7:** 실패 확인 → 구현 → `npm test` PASS + `npm run check` 0.
- [ ] **Step 8: 커밋** (`feat(sim): fountain 모금 (결정론, 골든)` + 트레일러).

---

## Task 4: fountain 랩배틀 + 끝말잇기 (LLM seam + 결정론 후처리)

**Files:** Modify `prototype/web/src/sim/fountain.ts`, Create `prototype/web/src/sim/fountainGames.test.ts`.

**Interfaces (Produces):**
- `interface RapVerse { name: string; line: string }`, `interface RapBattleResult { participants: string[]; verses: RapVerse[]; winner: string }`.
- `interface WordChainRound { name: string; word: string }`, `interface WordChainResult { participants: string[]; rounds: WordChainRound[]; eliminated: string | null; winner: string }`.
- `FountainManager.generateRapBattle(charA, charB, llm): Promise<RapBattleResult>`, `generateWordChain(characters, itemPool, llm): Promise<WordChainResult>`.

**오라클:** `fountain.py` `generate_rap_battle`(110-147), `generate_word_chain`(153-210). **결정론 후처리(충실 핵심):** verses/rounds는 dict 항목만 필터(`isinstance dict`), name/line/word `str(...)` 변환·기본 ""; winner가 names에 없으면 `names[0]`; eliminated가 None 아니고 names에 없으면 None. word_chain 가드: 참가자<2 또는 빈 풀 → throw(ValueError 미러). max_tokens=512.

- [ ] **Step 1: 통합 테스트 (Red)** — 주입 stub llm. **랩배틀:** (a) messages 2개(system 디스 톤, user에 두 이름+personality_code), max_tokens 512 전달, (b) winner가 풀 밖 → names[0] 폴백, (c) verses 중 비-dict 항목 필터·str 변환. **끝말잇기:** (d) winner 폴백, (e) eliminated 풀 밖 → null, (f) 참가자<2 throw, 빈 풀 throw, (g) rounds 필터. raw는 stub로 주입.
- [ ] **Step 2~3:** 실패 확인 → 구현 → `npm test` PASS + `npm run check` 0 → 커밋 (`feat(sim): fountain 랩배틀+끝말잇기 (LLM seam)` + 트레일러).

---

## Task 5: news NewsManager (real 결정론 선택 + LLM seam, absurd, 조회)

**Files:** Modify `scripts/dump_golden.py`, `loadGolden.ts`; Create `prototype/web/src/sim/news.ts`, `prototype/web/src/sim/news.test.ts`.

**Interfaces (Produces):**
- `interface NewsArticle { id: number; day: number; newsType: "real" | "absurd"; headline: string; body: string }`.
- `buildEventSummary(event: SocialEvent, characters): string` (Python `_build_event_summary` 1:1).
- `class NewsManager { generateRealNews(day, events, llm, characters): Promise<NewsArticle>; generateAbsurdNews(day, llm): Promise<NewsArticle>; getTodayNews(day): NewsArticle[]; getAllNews(): NewsArticle[] }`.

**오라클:** `news.py` `NewsManager`(21-146), `_build_event_summary`(153-169). **결정론(골든 대상):** `_PRIORITY` 점수 → `max(events, key=score)` 하이라이트 선택; `_build_event_summary`(id→name 매핑, "과(와) " join, location/reason/result 조건부, " — " join); 빈 events → "마을에 특별한 일이 없었습니다.". id/next_id 증가, get_today/get_all. **LLM seam:** real headline/body는 `raw.get("headline", 기본)`/`raw.get("body", event_summary)`, absurd 동일. max_tokens=256.

- [ ] **Step 1: 덤프 (`dump_event_summary`)** — Python에서 SocialEvent 여러개 + characters로: (a) 우선순위 선택(marriage>conversation 등 섞어 max 검증), (b) `_build_event_summary` 다양 케이스(participants 1/2명, location/reason/result 유무), (c) 빈 events 요약. `{"input": {...}, "expected": {"summary": str, "highlight_type": str|null}}`. `_write("event_summary", cases)`.
> 주의: `max(events, key=score)`는 동점 시 첫 항목(Python 안정). 골든이 정확값 강제.
- [ ] **Step 2~3:** 덤프 실행 → 로더 등록.
- [ ] **Step 4: 실패 테스트 (Red)** — 골든: buildEventSummary 각 케이스 === expected. 하이라이트 선택(NewsManager.generateRealNews에 stub llm 주입, event_summary가 프롬프트에 포함되는지 + 선택된 highlight type). NewsManager 통합: real/absurd 생성(stub llm, raw 누락 시 기본값 폴백), id 1부터 증가, getTodayNews(day 필터)/getAllNews. headline/body raw.get 폴백 단언.
- [ ] **Step 5~7:** 실패 확인 → 구현 → `npm test` PASS + `npm run check` 0.
- [ ] **Step 8: 커밋** (`feat(sim): news 생성기 (real 결정론 선택 + LLM seam)` + 트레일러).

---

## Self-Review (작성자 체크)
- **커버리지:** conversation(프롬프트 골든 + 엔진 seam), fountain(모금 골든 + 게임 seam·후처리), news(요약/선택 골든 + 생성 seam). 결정론은 골든, 확률/LLM은 구조.
- **Deferred 명시:** LLM 응답 일치(비결정), GameState/tick(P6), save(P7), add_money 본체(MoneyAdder 스텁).
- **Type 일관:** Phase4 PersonalityType/접근자, Phase1 Character, Phase2 relationship/memory 소비. 신규 타입(DialogueLine/ConversationResult/DonationResult/Rap*/WordChain*/NewsArticle)은 Phase6 simulation에서 소비.
- **교훈 반영:** 각 태스크 `npm run check` 포함. f-string `{{`→`{`·`behavior_guide.strip()`·블록스칼라 골든 그대로. 후처리 fallback(winner/eliminated/dict 필터)은 결정론이므로 stub로 충실 검증.
