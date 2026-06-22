import { describe, it, expect } from "vitest";
import { defaultCharacter, type Character, type Personality, type SpeechHabits } from "./character";
import {
  characterName,
  characterPersonalityCode,
  characterSpeechHabits,
  characterBackstory,
} from "./characterAccessors";
import { loadGolden } from "./__golden__/loadGolden";

interface Expected {
  name: string;
  personality_code: string;
  speech_habits: Record<string, string>;
  backstory: string;
}

// 골든 픽스처(Python)와 동일한 TS Character를 재구성.
const FIXTURES: Record<string, { personality: Personality; speech: SpeechHabits }> = {
  민수: {
    personality: { movement: 8, speech: 8, expressiveness: 7, attitude: 5, overall: 5 },
    speech: { normal: "~이에요", happy: "신나요", angry: "", sad: "", worried: "걱정돼요" },
  },
  지은: {
    personality: { movement: 2, speech: 2, expressiveness: 8, attitude: 8, overall: 5 },
    speech: { normal: "", happy: "", angry: "", sad: "", worried: "" },
  },
  현우: {
    personality: { movement: 5, speech: 5, expressiveness: 2, attitude: 2, overall: 5 },
    speech: { normal: "안녕하세요", happy: "기뻐요", angry: "", sad: "", worried: "" },
  },
};

function buildChar(id: number, name: string): Character {
  const c = defaultCharacter(id, name);
  const f = FIXTURES[name];
  c.profile.personality = { ...f.personality };
  c.customizable.speech_habits = { ...f.speech };
  return c;
}

describe("characterAccessors (golden vs Python)", () => {
  const cases = loadGolden<string, Expected>("character_accessors");

  it.each(cases)("accessors %#", (c) => {
    const expected = c.expected!;
    const ch = buildChar(1, expected.name);
    expect(characterName(ch)).toBe(expected.name);
    expect(characterPersonalityCode(ch)).toBe(expected.personality_code);
    expect(characterSpeechHabits(ch)).toEqual(expected.speech_habits);
    expect(characterBackstory(ch)).toBe(expected.backstory);
  });

  it("case1: drops empty angry/sad keys", () => {
    const ch = buildChar(1, "민수");
    const habits = characterSpeechHabits(ch);
    expect(habits).not.toHaveProperty("angry");
    expect(habits).not.toHaveProperty("sad");
    expect(habits).toEqual({ normal: "~이에요", happy: "신나요", worried: "걱정돼요" });
  });

  it("case2: all-empty habits → {}", () => {
    const ch = buildChar(2, "지은");
    expect(characterSpeechHabits(ch)).toEqual({});
  });
});
