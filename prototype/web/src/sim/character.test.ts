import { describe, it, expect } from "vitest";
import { calculateZodiac } from "./character";
import { loadGolden } from "./__golden__/loadGolden";

describe("calculateZodiac (golden vs Python)", () => {
  const cases = loadGolden<string, string>("zodiac");
  it.each(cases)("zodiac %#", (c) => {
    expect(calculateZodiac(c.input)).toBe(c.expected);
  });
});
