import { describe, it, expect } from "vitest";
import { loadGolden } from "./__golden__/loadGolden";
import { PERSONALITY_TYPES, loadPersonalities } from "./personalityType";
import type { PersonalityType } from "./personalityType";

// ────────────────────────────────────────────────────────────────────────────
// PERSONALITY_TYPES 골든 검증 (data/personalities.yaml의 types 16종)
// ────────────────────────────────────────────────────────────────────────────
describe("PERSONALITY_TYPES golden", () => {
  const cases = loadGolden<string, Record<string, PersonalityType>>("personality_types");
  const golden = cases[0].expected!;

  it("should have 16 types", () => {
    expect(Object.keys(PERSONALITY_TYPES)).toHaveLength(16);
  });

  it("should match golden catalog exactly (behavior_guide byte-for-byte)", () => {
    expect(PERSONALITY_TYPES).toEqual(golden);
  });

  it("should contain every golden key", () => {
    for (const code of Object.keys(golden)) {
      expect(PERSONALITY_TYPES).toHaveProperty(code);
    }
  });
});

// ────────────────────────────────────────────────────────────────────────────
// loadPersonalities
// ────────────────────────────────────────────────────────────────────────────
describe("loadPersonalities", () => {
  const golden = loadGolden<string, Record<string, PersonalityType>>("personality_types")[0]
    .expected!;

  it("returns the same catalog object/value", () => {
    expect(loadPersonalities()).toBe(PERSONALITY_TYPES);
    expect(loadPersonalities()).toEqual(golden);
  });
});
