import { describe, it, expect } from "vitest";
import { calculateZodiac } from "./character";
import {
  defaultAppearance, defaultVoice, defaultMood, defaultCharacterState,
  defaultPreferences, defaultCustomizable, defaultRecords,
} from "./character";
import { loadGolden } from "./__golden__/loadGolden";

describe("calculateZodiac (golden vs Python)", () => {
  const cases = loadGolden<string, string>("zodiac");
  it.each(cases)("zodiac %#", (c) => {
    expect(calculateZodiac(c.input)).toBe(c.expected);
  });
});

describe("Character 모델 기본값 (golden vs Python 서브모델)", () => {
  const builders: Record<string, () => unknown> = {
    Appearance: defaultAppearance,
    Voice: defaultVoice,
    Mood: defaultMood,
    CharacterState: defaultCharacterState,
    Preferences: defaultPreferences,
    Customizable: defaultCustomizable,
    Records: defaultRecords,
  };
  const cases = loadGolden<string, Record<string, unknown>>("character_defaults");
  it.each(cases)("default %s", (c) => {
    expect(builders[c.input]()).toEqual(c.expected);
  });
});
