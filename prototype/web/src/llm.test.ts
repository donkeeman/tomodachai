import { describe, it, expect } from "vitest";
import { parseJson } from "./llm";
import { loadGolden } from "./sim/__golden__/loadGolden";

describe("parseJson (golden vs Python _parse_json)", () => {
  const cases = loadGolden<string, Record<string, unknown>>("parse_json");
  it.each(cases)("input %# matches Python", (c) => {
    if (c.throws) {
      expect(() => parseJson(c.input)).toThrow();
    } else {
      expect(parseJson(c.input)).toEqual(c.expected);
    }
  });
});
