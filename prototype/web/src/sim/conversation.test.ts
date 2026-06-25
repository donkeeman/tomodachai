import { describe, it, expect } from "vitest";
import { defaultCharacter, type Character, type Personality } from "./character";
import { defaultSocialEvent, type SocialEvent } from "./memory";
import { loadPersonalities, type PersonalityType } from "./personalityType";
import type { Relationship, RelationshipStage } from "./relationship";
import {
  SYSTEM_PROMPT,
  formatMemory,
  formatSpeechHabits,
  buildConversationPrompt,
} from "./conversation";
import { loadGolden } from "./__golden__/loadGolden";

interface CharInput {
  id: number;
  name: string;
  personality: Personality;
  speech_habits: Record<string, string>;
}

interface RelInput {
  friendship: number;
  romance: number;
  stage: string;
}

interface MemInput {
  id: number;
  type: string;
  participants: number[];
  day: number;
  time: string | null;
  location: string | null;
  reason: string | null;
  result: string | null;
}

interface Input {
  char_a: CharInput;
  char_b: CharInput;
  code_a: string;
  code_b: string;
  rel_ab: RelInput;
  rel_ba: RelInput;
  memories: MemInput[];
  location: string;
  time_of_day: string;
}

function buildChar(ci: CharInput): Character {
  const c = defaultCharacter(ci.id, ci.name);
  c.profile.personality = { ...ci.personality };
  c.customizable.speech_habits = {
    normal: ci.speech_habits.normal ?? "",
    happy: ci.speech_habits.happy ?? "",
    angry: ci.speech_habits.angry ?? "",
    sad: ci.speech_habits.sad ?? "",
    worried: ci.speech_habits.worried ?? "",
  };
  return c;
}

function buildRel(ri: RelInput): Relationship {
  return {
    friendship: ri.friendship,
    romance: ri.romance,
    stage: ri.stage as RelationshipStage,
  };
}

function buildMem(mi: MemInput): SocialEvent {
  return defaultSocialEvent({
    id: mi.id,
    type: mi.type,
    participants: mi.participants,
    day: mi.day,
    time: mi.time,
    location: mi.location,
    reason: mi.reason,
    result: mi.result,
  });
}

describe("buildConversationPrompt (golden vs Python)", () => {
  const cases = loadGolden<Input, string>("conversation_prompt");
  const personalities = loadPersonalities();

  it.each(cases)("prompt %#", (c) => {
    const input = c.input;
    const expected = c.expected!;
    const charA = buildChar(input.char_a);
    const charB = buildChar(input.char_b);
    const personalityA = personalities[input.code_a];
    const personalityB = personalities[input.code_b];
    const relAb = buildRel(input.rel_ab);
    const relBa = buildRel(input.rel_ba);
    const memories = input.memories.map(buildMem);
    const result = buildConversationPrompt(
      charA,
      charB,
      personalityA,
      personalityB,
      relAb,
      relBa,
      memories,
      input.location,
      input.time_of_day,
    );
    expect(result).toBe(expected);
  });
});

describe("SYSTEM_PROMPT", () => {
  it("starts with the expected phrase", () => {
    expect(SYSTEM_PROMPT.startsWith("당신은 작은 마을")).toBe(true);
  });
});

describe("formatSpeechHabits", () => {
  it("empty habits → 없음", () => {
    expect(formatSpeechHabits({})).toBe("없음");
  });

  it("filtered keys, ordered normal/happy/angry/sad/worried", () => {
    expect(
      formatSpeechHabits({ worried: "걱정돼요", normal: "~이에요", happy: "신나요" }),
    ).toBe('일반: "~이에요" / 기쁠 때: "신나요" / 걱정할 때: "걱정돼요"');
  });

  it("unknown-only keys → 없음", () => {
    expect(formatSpeechHabits({ bogus: "x" })).toBe("없음");
  });
});

describe("formatMemory", () => {
  it("all optional fields present", () => {
    const m = defaultSocialEvent({
      id: 1,
      type: "conversation",
      participants: [1, 2],
      day: 3,
      location: "공원",
      result: "더 친해짐",
    });
    expect(formatMemory(m)).toBe("- (Day 3) 대화 @ 공원 → 더 친해짐");
  });

  it("only reason present", () => {
    const m = defaultSocialEvent({
      id: 2,
      type: "fight",
      participants: [1, 2],
      day: 5,
      reason: "오해",
    });
    expect(formatMemory(m)).toBe("- (Day 5) 싸움 (사유: 오해)");
  });

  it("unknown type falls back to raw type", () => {
    const m = defaultSocialEvent({
      id: 3,
      type: "unknown_type",
      participants: [1, 2],
      day: 7,
    });
    expect(formatMemory(m)).toBe("- (Day 7) unknown_type");
  });
});
