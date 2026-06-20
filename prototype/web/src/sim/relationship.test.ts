import { describe, it, expect } from "vitest";
import {
  friendshipStage, getFriendshipText, getRomanceText, getStatusText,
  computeStage, checkBreakupConditions, applyDeltas, applyNaturalDecay,
} from "./relationship";
import { loadGolden } from "./__golden__/loadGolden";

describe("friendship labels (golden)", () => {
  for (const c of loadGolden<{ friendship: number }, { stage: string; friendship_text: string }>("rel_friendship_labels")) {
    it(`f=${c.input.friendship}`, () => {
      expect(friendshipStage(c.input.friendship)).toBe(c.expected!.stage);
      expect(getFriendshipText(c.input.friendship)).toBe(c.expected!.friendship_text);
    });
  }
});
describe("romance text (golden)", () => {
  for (const c of loadGolden<{ romance: number }, { romance_text: string | null }>("rel_romance_text"))
    it(`r=${c.input.romance}`, () => expect(getRomanceText(c.input.romance)).toBe(c.expected!.romance_text));
});
describe("status text (golden)", () => {
  for (const c of loadGolden<{ stage: string }, string>("rel_status_text"))
    it(`${c.input.stage}`, () => expect(getStatusText(c.input.stage as never)).toBe(c.expected));
});
describe("computeStage (golden)", () => {
  for (const c of loadGolden<{ friendship: number; romance: number; stage: string; allow: boolean }, string>("rel_compute_stage"))
    it(`${c.input.stage}/r${c.input.romance}/a${c.input.allow}`, () =>
      expect(computeStage(c.input.friendship, c.input.romance, c.input.stage as never, c.input.allow)).toBe(c.expected));
});
describe("checkBreakupConditions (golden)", () => {
  for (const c of loadGolden<{ stage: string; romance: number; cheating: boolean; triangle: boolean; fightUnresolved: boolean }, string | null>("rel_breakup"))
    it(`${c.input.stage}/r${c.input.romance}/c${c.input.cheating}/t${c.input.triangle}/f${c.input.fightUnresolved}`, () =>
      expect(checkBreakupConditions(c.input.stage as never, c.input.romance, c.input.cheating, c.input.triangle, c.input.fightUnresolved)).toBe(c.expected));
});
describe("applyDeltas (golden)", () => {
  for (const c of loadGolden<{ friendship: number; romance: number; deltas: Record<string, number> }, { friendship: number; romance: number }>("rel_apply_deltas"))
    it(`${JSON.stringify(c.input.deltas)}`, () => {
      const out = applyDeltas({ friendship: c.input.friendship, romance: c.input.romance, stage: "stranger" }, c.input.deltas);
      expect({ friendship: out.friendship, romance: out.romance }).toEqual(c.expected);
    });
});
describe("applyNaturalDecay (golden)", () => {
  for (const c of loadGolden<{ friendship: number; romance: number }, { friendship: number; romance: number }>("rel_decay"))
    it(`f${c.input.friendship}/r${c.input.romance}`, () => {
      const out = applyNaturalDecay({ friendship: c.input.friendship, romance: c.input.romance, stage: "stranger" });
      expect({ friendship: out.friendship, romance: out.romance }).toEqual(c.expected);
    });
});
