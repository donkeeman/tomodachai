import { describe, it, expect } from "vitest";
import { defaultCharacter, type Character } from "./character";
import { FountainManager } from "./fountain";
import type { Msg, LlmClient, ChatOpts } from "../llm";

// ────────────────────────────────────────────────────────────────────────────
// 주입형 stub LlmClient — 받은 messages/opts를 기록하고 고정 raw dict를 반환.
// LLM 응답 내용 자체는 비결정적이므로 검증하지 않는다 (후처리 결정론만 검증).
// ────────────────────────────────────────────────────────────────────────────
class StubLlm implements LlmClient {
  received: Msg[] | null = null;
  receivedOpts: (ChatOpts & { retries?: number }) | undefined = undefined;
  constructor(private readonly raw: Record<string, unknown>) {}
  async chatJson(
    messages: Msg[],
    opts?: ChatOpts & { retries?: number },
  ): Promise<Record<string, unknown>> {
    this.received = messages;
    this.receivedOpts = opts;
    return this.raw;
  }
}

/** 슬라이더(0~10)를 지정해 personality_code를 통제하는 캐릭터 빌더. */
function buildChar(id: number, name: string, slider: number): Character {
  const c = defaultCharacter(id, name);
  c.profile.personality = {
    movement: slider,
    speech: slider,
    expressiveness: slider,
    attitude: slider,
    overall: slider,
  };
  return c;
}

describe("FountainManager.generateRapBattle (LLM seam, 구조 검증)", () => {
  it("(a) chatJson 메시지 2개 + maxTokens 512 + 이름/성격코드 포함", async () => {
    const llm = new StubLlm({
      verses: [{ name: "아리", line: "라임1" }],
      winner: "아리",
    });
    const mgr = new FountainManager();
    const charA = buildChar(1, "아리", 0); // easygoing_softie
    const charB = buildChar(2, "보리", 10); // outgoing_extrovert

    await mgr.generateRapBattle(charA, charB, llm);

    const messages = llm.received!;
    expect(messages.length).toBe(2);
    expect(messages[0].role).toBe("system");
    expect(messages[0].content).toContain("랩배틀");
    expect(messages[0].content).toContain("디스");
    expect(messages[1].role).toBe("user");
    expect(messages[1].content).toContain("'아리'");
    expect(messages[1].content).toContain("'보리'");
    expect(messages[1].content).toContain("easygoing_softie");
    expect(messages[1].content).toContain("outgoing_extrovert");
    expect(llm.receivedOpts?.maxTokens).toBe(512);
  });

  it("(b) winner가 names에 없으면 names[0]으로 폴백", async () => {
    const llm = new StubLlm({ verses: [], winner: "없는사람" });
    const mgr = new FountainManager();
    const charA = buildChar(1, "아리", 0);
    const charB = buildChar(2, "보리", 10);

    const result = await mgr.generateRapBattle(charA, charB, llm);
    expect(result.participants).toEqual(["아리", "보리"]);
    expect(result.winner).toBe("아리");
  });

  it("(c) winner가 names에 있으면 유지", async () => {
    const llm = new StubLlm({ verses: [], winner: "보리" });
    const mgr = new FountainManager();
    const charA = buildChar(1, "아리", 0);
    const charB = buildChar(2, "보리", 10);

    const result = await mgr.generateRapBattle(charA, charB, llm);
    expect(result.winner).toBe("보리");
  });

  it("(d) verses: 비-객체 필터링 + str 강제변환 (숫자 line→\"123\", 없는 name→\"\")", async () => {
    const llm = new StubLlm({
      verses: [
        { name: "아리", line: 123 },
        { line: "name 없음" },
        "그냥 문자열",
        42,
        null,
      ],
      winner: "아리",
    });
    const mgr = new FountainManager();
    const charA = buildChar(1, "아리", 0);
    const charB = buildChar(2, "보리", 10);

    const result = await mgr.generateRapBattle(charA, charB, llm);
    expect(result.verses).toEqual([
      { name: "아리", line: "123" },
      { name: "", line: "name 없음" },
    ]);
  });

  it("(d2) raw.verses 누락/배열 아님 → 빈 리스트", async () => {
    const llm = new StubLlm({ winner: "아리" });
    const mgr = new FountainManager();
    const charA = buildChar(1, "아리", 0);
    const charB = buildChar(2, "보리", 10);

    const result = await mgr.generateRapBattle(charA, charB, llm);
    expect(result.verses).toEqual([]);
  });
});

describe("FountainManager.generateWordChain (LLM seam, 구조 검증)", () => {
  const itemPool = ["사과", "과일", "일기"];

  it("(e) winner 폴백/유지", async () => {
    const chars = [buildChar(1, "아리", 0), buildChar(2, "보리", 10)];

    const fallback = await new FountainManager().generateWordChain(
      chars,
      itemPool,
      new StubLlm({ rounds: [], winner: "없는사람" }),
    );
    expect(fallback.participants).toEqual(["아리", "보리"]);
    expect(fallback.winner).toBe("아리");

    const kept = await new FountainManager().generateWordChain(
      chars,
      itemPool,
      new StubLlm({ rounds: [], winner: "보리" }),
    );
    expect(kept.winner).toBe("보리");
  });

  it("(f) eliminated: 없는이름→null, 유효이름→유지, key 없음→null", async () => {
    const chars = [buildChar(1, "아리", 0), buildChar(2, "보리", 10)];

    const invalid = await new FountainManager().generateWordChain(
      chars,
      itemPool,
      new StubLlm({ rounds: [], winner: "아리", eliminated: "없는사람" }),
    );
    expect(invalid.eliminated).toBeNull();

    const valid = await new FountainManager().generateWordChain(
      chars,
      itemPool,
      new StubLlm({ rounds: [], winner: "아리", eliminated: "보리" }),
    );
    expect(valid.eliminated).toBe("보리");

    const missing = await new FountainManager().generateWordChain(
      chars,
      itemPool,
      new StubLlm({ rounds: [], winner: "아리" }),
    );
    expect(missing.eliminated).toBeNull();
  });

  it("(g) 참가자 2명 미만 / 빈 아이템 풀 → throw (정확한 메시지)", async () => {
    const chars = [buildChar(1, "아리", 0), buildChar(2, "보리", 10)];
    const llm = new StubLlm({ rounds: [], winner: "아리" });

    await expect(
      new FountainManager().generateWordChain([chars[0]], itemPool, llm),
    ).rejects.toThrow("끝말잇기는 최소 2명이 필요합니다.");

    await expect(
      new FountainManager().generateWordChain(chars, [], llm),
    ).rejects.toThrow("끝말잇기 아이템 풀이 비어 있습니다.");
  });

  it("(h) rounds: 비-객체 필터링 + str 강제변환, 메시지에 참가자/풀 포함, maxTokens 512", async () => {
    const chars = [buildChar(1, "아리", 0), buildChar(2, "보리", 10)];
    const llm = new StubLlm({
      rounds: [
        { name: "아리", word: 99 },
        { word: "name 없음" },
        "문자열",
        7,
      ],
      winner: "아리",
    });

    const result = await new FountainManager().generateWordChain(chars, itemPool, llm);
    expect(result.rounds).toEqual([
      { name: "아리", word: "99" },
      { name: "", word: "name 없음" },
    ]);

    const messages = llm.received!;
    expect(messages.length).toBe(2);
    expect(messages[0].role).toBe("system");
    expect(messages[0].content).toContain("끝말잇기");
    expect(messages[1].role).toBe("user");
    expect(messages[1].content).toContain("참가자: 아리, 보리");
    expect(messages[1].content).toContain("사과, 과일, 일기");
    expect(llm.receivedOpts?.maxTokens).toBe(512);
  });
});
