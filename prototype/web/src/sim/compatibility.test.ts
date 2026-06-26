import { describe, it, expect } from "vitest";
import { personalityGroup, calculateCompatibility } from "./compatibility";
import { loadGolden } from "./__golden__/loadGolden";

describe("personalityGroup (golden vs Python)", () => {
  const cases = loadGolden<string, string | null>("personality_group");
  for (const c of cases) {
    it(`personalityGroup("${c.input}")`, () => {
      expect(personalityGroup(c.input)).toBe(c.expected);
    });
  }
});

describe("calculateCompatibility (golden vs Python)", () => {
  const cases = loadGolden<
    { pA: string; pB: string; bloodA: string; bloodB: string; zA: string; zB: string },
    number
  >("calculate_compatibility");
  for (const c of cases) {
    it(`compat(${c.input.pA},${c.input.pB},${c.input.bloodA},${c.input.bloodB},${c.input.zA},${c.input.zB})`, () => {
      expect(
        calculateCompatibility(
          c.input.pA,
          c.input.pB,
          c.input.bloodA,
          c.input.bloodB,
          c.input.zA,
          c.input.zB,
        ),
      ).toBe(c.expected);
    });
  }
});
