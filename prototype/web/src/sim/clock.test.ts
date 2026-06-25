import { describe, it, expect } from "vitest";
import { GameClock } from "./clock";
import { loadGolden } from "./__golden__/loadGolden";

describe("GameClock.getGameHour (golden)", () => {
  const clock = new GameClock();
  const cases = loadGolden<{ at: string; flip: boolean }, { hour: number; period: string | null }>(
    "game_clock_period",
  );
  it.each(cases)("hour/period %#", (c) => {
    const at = new Date(c.input.at);
    expect(clock.getGameHour(at, c.input.flip)).toBe(c.expected!.hour);
    if (c.expected!.period !== null) {
      expect(clock.getTimePeriod(at)).toBe(c.expected!.period);
    }
  });
});

describe("GameClock.isNewDay (golden)", () => {
  const cases = loadGolden<{ lastCheck: string; now: string }, boolean>("game_clock_newday");
  it.each(cases)("isNewDay %#", (c) => {
    const now = new Date(c.input.now);
    const clock = new GameClock(false, () => now);
    expect(clock.isNewDay(new Date(c.input.lastCheck))).toBe(c.expected);
  });
});

describe("GameClock.catchupEventCount (golden)", () => {
  const clock = new GameClock();
  const cases = loadGolden<number, number>("game_clock_catchup");
  it.each(cases)("catchup %#", (c) => {
    expect(clock.catchupEventCount(c.input)).toBe(c.expected);
  });
});
