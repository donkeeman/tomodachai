import { describe, it, expect, vi } from "vitest";
import { loadGolden } from "./__golden__/loadGolden";
import {
  FountainManager,
  DONATION_PER_CHARACTER,
  type DonationResult,
  type MoneyAdder,
} from "./fountain";

// ────────────────────────────────────────────────────────────────────────────
// 골든 픽스처 — donation (Python fountain.py 정답지)
// ────────────────────────────────────────────────────────────────────────────
interface DonationGoldenInput {
  day: number;
  characterCount: number;
  reuse?: string;
}
interface DonationGoldenExpected {
  result: DonationResult | null;
  money_added: number;
  hasDonatedBefore?: boolean;
  hasDonatedAfter?: boolean;
  add_money_calls?: number;
}

// add_money 호출액을 기록하는 스텁.
class RecordingMoneyAdder implements MoneyAdder {
  readonly calls: number[] = [];
  addMoney(n: number): void {
    this.calls.push(n);
  }
  get total(): number {
    return this.calls.reduce((a, b) => a + b, 0);
  }
}

const cases = loadGolden<DonationGoldenInput, DonationGoldenExpected>("donation");
const caseA = cases[0];
const caseB = cases[1];
const caseC = cases[2];
const caseD = cases[3];
const expA = caseA.expected!;
const expB = caseB.expected!;
const expC = caseC.expected!;
const expD = caseD.expected!;

describe("FountainManager donation golden", () => {
  it("DONATION_PER_CHARACTER matches oracle (100)", () => {
    expect(DONATION_PER_CHARACTER).toBe(100);
  });

  it("(a) fresh manager, day=1 count=3 → amount 300, money 300", () => {
    const mgr = new FountainManager();
    const gs = new RecordingMoneyAdder();
    const before = mgr.hasDonated(caseA.input.day);
    const res = mgr.runDonation(caseA.input.day, caseA.input.characterCount, gs);
    const after = mgr.hasDonated(caseA.input.day);

    expect(res).toEqual(expA.result);
    expect(gs.total).toBe(expA.money_added);
    expect(before).toBe(expA.hasDonatedBefore);
    expect(after).toBe(expA.hasDonatedAfter);
  });

  it("(b) same manager, day=1 again → null, no second addMoney call", () => {
    const mgr = new FountainManager();
    const gs = new RecordingMoneyAdder();
    // 시나리오 a 재현 후 같은 날 재호출.
    mgr.runDonation(caseA.input.day, caseA.input.characterCount, gs);
    const res = mgr.runDonation(caseB.input.day, caseB.input.characterCount, gs);

    expect(res).toBeNull();
    expect(res).toEqual(expB.result);
    // money는 a의 300에서 변동 없음.
    expect(gs.total).toBe(expB.money_added);
    expect(gs.calls.length).toBe(1);
  });

  it("(c) fresh manager, count=0 → amount 0, addMoney NOT called", () => {
    const mgr = new FountainManager();
    const gs = new RecordingMoneyAdder();
    const spy = vi.spyOn(gs, "addMoney");
    const res = mgr.runDonation(caseC.input.day, caseC.input.characterCount, gs);

    expect(res).toEqual(expC.result);
    expect(gs.total).toBe(expC.money_added);
    expect(spy).not.toHaveBeenCalled();
    expect(gs.calls.length).toBe(expC.add_money_calls);
  });

  it("(d) fresh manager, count=-5 → max(0,_)*100=0, addMoney NOT called", () => {
    const mgr = new FountainManager();
    const gs = new RecordingMoneyAdder();
    const spy = vi.spyOn(gs, "addMoney");
    const res = mgr.runDonation(caseD.input.day, caseD.input.characterCount, gs);

    expect(res).toEqual(expD.result);
    expect(gs.total).toBe(expD.money_added);
    expect(spy).not.toHaveBeenCalled();
    expect(gs.calls.length).toBe(expD.add_money_calls);
  });
});

describe("FountainManager hasDonated state transition", () => {
  it("false before runDonation, true after (same day)", () => {
    const mgr = new FountainManager();
    const gs = new RecordingMoneyAdder();
    expect(mgr.hasDonated(2)).toBe(false);
    mgr.runDonation(2, 4, gs);
    expect(mgr.hasDonated(2)).toBe(true);
    // 다른 날은 여전히 미모금.
    expect(mgr.hasDonated(3)).toBe(false);
  });

  it("amount truthiness: 0 count produces a result but no addMoney", () => {
    const mgr = new FountainManager();
    const gs = new RecordingMoneyAdder();
    const res = mgr.runDonation(1, 0, gs);
    expect(res).not.toBeNull();
    expect(res?.amount).toBe(0);
    expect(gs.calls.length).toBe(0);
  });
});
