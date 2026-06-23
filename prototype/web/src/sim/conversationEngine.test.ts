import { describe, it, expect } from "vitest";
import { defaultCharacter, type Character } from "./character";
import { defaultSocialEvent } from "./memory";
import { loadPersonalities } from "./personalityType";
import { defaultRelationship } from "./relationship";
import { ConversationEngine, SYSTEM_PROMPT } from "./conversation";
import { characterPersonalityCode } from "./characterAccessors";
import type { Msg, LlmClient, ChatOpts } from "../llm";

// ────────────────────────────────────────────────────────────────────────────
// 주입형 stub LlmClient — 받은 messages를 기록하고 고정 raw dict를 반환.
// LLM 응답 내용 자체는 비결정적이므로 검증하지 않는다 (구조만 검증).
// ────────────────────────────────────────────────────────────────────────────
class StubLlm implements LlmClient {
  received: Msg[] | null = null;
  constructor(private readonly raw: Record<string, unknown>) {}
  async chatJson(
    messages: Msg[],
    _opts?: ChatOpts & { retries?: number },
  ): Promise<Record<string, unknown>> {
    this.received = messages;
    return this.raw;
  }
}

const FIXED_RAW: Record<string, unknown> = {
  dialogue: [
    { speaker: "아리", text: "안녕하세요!" },
    { speaker: "보리", text: "반가워요!" },
  ],
  deltas: {
    아리: { friendship: 3, romance: 0, tension: -1 },
    보리: { friendship: 2, romance: 1, tension: 0 },
  },
  summary: "두 사람이 인사를 나눴어요",
};

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

describe("ConversationEngine.generate (구조 검증, LLM seam)", () => {
  const personalities = loadPersonalities();

  it("(a) chatJson에 정확히 2개 메시지 — system=SYSTEM_PROMPT, user=프롬프트", async () => {
    const llm = new StubLlm(FIXED_RAW);
    const engine = new ConversationEngine(llm, personalities);
    const charA = buildChar(1, "아리", 0); // easygoing_softie
    const charB = buildChar(2, "보리", 10); // outgoing_extrovert

    await engine.generate(
      charA,
      charB,
      defaultRelationship(),
      defaultRelationship(),
      [],
      "공원",
    );

    expect(llm.received).not.toBeNull();
    const msgs = llm.received!;
    expect(msgs).toHaveLength(2);
    expect(msgs[0]).toEqual({ role: "system", content: SYSTEM_PROMPT });
    expect(msgs[1].role).toBe("user");
    // buildConversationPrompt가 사용됐다는 증거: 이름 + 장소 포함
    expect(msgs[1].content).toContain("아리");
    expect(msgs[1].content).toContain("보리");
    expect(msgs[1].content).toContain("공원");
  });

  it("(b) 반환 ConversationResult가 stub raw를 그대로 매핑", async () => {
    const llm = new StubLlm(FIXED_RAW);
    const engine = new ConversationEngine(llm, personalities);
    const charA = buildChar(1, "아리", 0);
    const charB = buildChar(2, "보리", 10);

    const result = await engine.generate(
      charA,
      charB,
      defaultRelationship(),
      defaultRelationship(),
      [],
      "공원",
    );

    expect(result.dialogue).toEqual([
      { speaker: "아리", text: "안녕하세요!" },
      { speaker: "보리", text: "반가워요!" },
    ]);
    expect(result.deltas).toEqual({
      아리: { friendship: 3, romance: 0, tension: -1 },
      보리: { friendship: 2, romance: 1, tension: 0 },
    });
    expect(result.summary).toBe("두 사람이 인사를 나눴어요");
  });

  it("(c) timeOfDay 기본값 '오후'가 user 메시지에 포함", async () => {
    const llm = new StubLlm(FIXED_RAW);
    const engine = new ConversationEngine(llm, personalities);
    const charA = buildChar(1, "아리", 0);
    const charB = buildChar(2, "보리", 10);

    await engine.generate(
      charA,
      charB,
      defaultRelationship(),
      defaultRelationship(),
      [],
      "공원",
    );

    expect(llm.received![1].content).toContain("시간대: 오후");
  });

  it("(c) 커스텀 timeOfDay '아침'이 전달되면 user 메시지에 포함", async () => {
    const llm = new StubLlm(FIXED_RAW);
    const engine = new ConversationEngine(llm, personalities);
    const charA = buildChar(1, "아리", 0);
    const charB = buildChar(2, "보리", 10);

    await engine.generate(
      charA,
      charB,
      defaultRelationship(),
      defaultRelationship(),
      [],
      "공원",
      "아침",
    );

    expect(llm.received![1].content).toContain("시간대: 아침");
  });

  it("(d) personality 룩업: char의 personality_code로 주입 dict 항목을 사용", async () => {
    const llm = new StubLlm(FIXED_RAW);
    const engine = new ConversationEngine(llm, personalities);
    const charA = buildChar(1, "아리", 0); // easygoing_softie
    const charB = buildChar(2, "보리", 10); // outgoing_extrovert

    const codeA = characterPersonalityCode(charA);
    const codeB = characterPersonalityCode(charB);
    expect(codeA).toBe("easygoing_softie");
    expect(codeB).toBe("outgoing_extrovert");

    await engine.generate(
      charA,
      charB,
      defaultRelationship(),
      defaultRelationship(),
      [],
      "공원",
    );

    const content = llm.received![1].content;
    expect(content).toContain(personalities[codeA].name); // 외유내강형
    expect(content).toContain(personalities[codeB].name); // 명랑쾌활형
  });

  it("memories가 프롬프트에 반영된다", async () => {
    const llm = new StubLlm(FIXED_RAW);
    const engine = new ConversationEngine(llm, personalities);
    const charA = buildChar(1, "아리", 0);
    const charB = buildChar(2, "보리", 10);
    const mem = defaultSocialEvent({
      id: 1,
      type: "conversation",
      participants: [1, 2],
      day: 3,
      location: "공원",
      result: "더 친해짐",
    });

    await engine.generate(
      charA,
      charB,
      defaultRelationship(),
      defaultRelationship(),
      [mem],
      "공원",
    );

    expect(llm.received![1].content).toContain("- (Day 3) 대화 @ 공원 → 더 친해짐");
  });
});
