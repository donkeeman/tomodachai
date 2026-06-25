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
