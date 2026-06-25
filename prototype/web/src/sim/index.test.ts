import { describe, it, expect } from "vitest";
import { getSnapshot } from "./index";

describe("getSnapshot stub", () => {
  it("derives clock/minutes/asleep from injected time and has empty village", () => {
    // 자는 시간(02:30 UTC) 주입
    const snap = getSnapshot(0, () => new Date(Date.UTC(2026, 5, 19, 2, 30)));
    expect(snap.clock).toBe("02:30");
    expect(snap.minutes).toBe(150);
    expect(snap.asleep).toBe(true);
    expect(snap.realtime).toBe(true);
    expect(snap.characters).toEqual([]);
    expect(snap.bubbles).toEqual([]);
  });

  it("daytime is awake", () => {
    const snap = getSnapshot(0, () => new Date(Date.UTC(2026, 5, 19, 13, 0)));
    expect(snap.clock).toBe("13:00");
    expect(snap.asleep).toBe(false);
  });
});
