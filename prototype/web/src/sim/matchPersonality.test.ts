import { describe, it, expect } from "vitest";
import type { Msg, LlmClient } from "../llm";
import { matchPersonality, MATCHER_SYSTEM } from "./personalityType";

// LLM 비결정론 → 골든 없음. 주입된 stub LlmClient로 구조만 검증.
function makeStub(
  out: Record<string, unknown>,
): { llm: LlmClient; captured: { messages?: Msg[] } } {
  const captured: { messages?: Msg[] } = {};
  const llm: LlmClient = {
    async chatJson(messages) {
      captured.messages = messages;
      return out;
    },
  };
  return { llm, captured };
}

describe("matchPersonality (LLM seam, 구조 검증)", () => {
  it("happy path: 숫자 슬라이더 반환, reason 드롭", async () => {
    const { llm } = makeStub({
      movement: 0.7,
      speech: 0.3,
      expressiveness: 0.9,
      attitude: 0.1,
      reason: "x",
    });
    const result = await matchPersonality(llm, "활발하고 직설적");
    expect(result).toEqual({
      movement: 0.7,
      speech: 0.3,
      expressiveness: 0.9,
      attitude: 0.1,
    });
  });

  it("message 구조: system + user 2개, 프롬프트에 description/기준 포함", async () => {
    const { llm, captured } = makeStub({
      movement: 0.5,
      speech: 0.5,
      expressiveness: 0.5,
      attitude: 0.5,
    });
    await matchPersonality(llm, "느긋하고 조용한 사람");

    const messages = captured.messages!;
    expect(messages.length).toBe(2);
    expect(messages[0]).toEqual({ role: "system", content: MATCHER_SYSTEM });
    expect(MATCHER_SYSTEM.startsWith("당신은 성격 분석 전문가")).toBe(true);
    expect(messages[1].role).toBe("user");
    expect(messages[1].content).toContain("느긋하고 조용한 사람");
    expect(messages[1].content).toContain("## 슬라이더 기준");
  });

  it("string-number coercion: 문자열 숫자 → number", async () => {
    const { llm } = makeStub({
      movement: "0.5",
      speech: "0",
      expressiveness: "1",
      attitude: "0.25",
    });
    const result = await matchPersonality(llm, "아무거나");
    expect(result).toEqual({
      movement: 0.5,
      speech: 0,
      expressiveness: 1,
      attitude: 0.25,
    });
  });
});
