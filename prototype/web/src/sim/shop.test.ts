import { describe, it, expect, vi } from "vitest";
import { loadGolden } from "./__golden__/loadGolden";
import {
  CATEGORIES,
  HOLIDAYS,
  DAILY_COUNT,
  DEFAULT_POOL,
  MORNING_MARKET_DISCOUNT_RATE,
  MORNING_MARKET_BASE_PRICE,
  ShopManager,
  type ShopRng,
  type ShopSnapshot,
} from "./shop";

// ────────────────────────────────────────────────────────────────────────────
// 골든 픽스처 — shop_constants
// ────────────────────────────────────────────────────────────────────────────
type GoldenExpected =
  | string[]
  | Record<string, number>
  | Record<string, number[]>
  | number
  | number[]
  | ShopSnapshot;

function golden(input: string): GoldenExpected {
  const cases = loadGolden<string, GoldenExpected>("shop_constants");
  const found = cases.find((c) => c.input === input);
  if (!found) throw new Error(`missing golden case: ${input}`);
  return found.expected!;
}

describe("shop constants golden", () => {
  it("CATEGORIES matches", () => {
    expect([...CATEGORIES]).toEqual(golden("categories"));
  });

  it("HOLIDAYS matches", () => {
    expect(HOLIDAYS).toEqual(golden("holidays"));
  });

  it("DAILY_COUNT matches", () => {
    expect(DAILY_COUNT).toEqual(golden("daily_count"));
  });

  it("DEFAULT_POOL bounds match (min, max, len)", () => {
    const bounds = golden("pool_bounds") as Record<string, number[]>;
    for (const c of CATEGORIES) {
      const pool = DEFAULT_POOL[c];
      expect([Math.min(...pool), Math.max(...pool), pool.length]).toEqual(bounds[c]);
    }
  });

  it("discount_price = trunc(base * rate) matches", () => {
    expect(Math.trunc(MORNING_MARKET_BASE_PRICE * MORNING_MARKET_DISCOUNT_RATE)).toBe(
      golden("discount_price"),
    );
  });

  it("MORNING_MARKET_DISCOUNT_RATE matches", () => {
    expect(MORNING_MARKET_DISCOUNT_RATE).toBe(golden("discount_rate"));
  });

  it("MORNING_MARKET_BASE_PRICE matches", () => {
    expect(MORNING_MARKET_BASE_PRICE).toBe(golden("base_price"));
  });

  it("getCatalog numeric-sorted matches", () => {
    const sm = new ShopManager();
    sm.addToCatalog("food", 5);
    sm.addToCatalog("food", 1);
    sm.addToCatalog("clothing", 150);
    expect(sm.getCatalog("food")).toEqual(golden("catalog_food_sorted"));
  });

  it("getCatalog는 사전식이 아닌 숫자 오름차순 (lexicographic 무력화)", () => {
    // 10/100이 있으면 lexicographic은 [1,10,100,5], 숫자정렬은 [1,5,10,100].
    // (a,b)=>a-b 비교자가 제거되면 이 케이스만 깨진다 — 회귀 보호.
    const sm = new ShopManager();
    for (const id of [100, 5, 10, 1]) sm.addToCatalog("food", id);
    expect(sm.getCatalog("food")).toEqual([1, 5, 10, 100]);
  });

  it("serialize after adds matches", () => {
    const sm = new ShopManager();
    sm.addToCatalog("food", 5);
    sm.addToCatalog("food", 1);
    sm.addToCatalog("clothing", 150);
    expect(sm.serialize()).toEqual(golden("serialize_after_adds"));
  });

  it("deserialize → serialize roundtrip matches", () => {
    const sample: ShopSnapshot = {
      daily: { food: [1, 2, 3], clothing: [101, 102], interior: [201] },
      morning_market: { item: 7, discount_price: 1500 },
      seasonal: [301, 302],
      catalog: { food: [1, 5], clothing: [150], interior: [] },
    };
    const sm = new ShopManager();
    sm.deserialize(sample);
    expect(sm.serialize()).toEqual(golden("deserialize_roundtrip"));
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 통합 — buy / buyMorningMarket / refreshDaily / 복사 보장
// ────────────────────────────────────────────────────────────────────────────
function stockedShop(): ShopManager {
  const sm = new ShopManager();
  sm.deserialize({
    daily: { food: [1, 2, 3], clothing: [101, 102], interior: [201] },
    morning_market: null,
    seasonal: [],
    catalog: { food: [], clothing: [], interior: [] },
  });
  return sm;
}

describe("buy", () => {
  it("succeeds: spends 1000, records in catalog", () => {
    const sm = stockedShop();
    const stub = { spendMoney: vi.fn(() => true) };
    expect(sm.buy(2, stub)).toBe(true);
    expect(stub.spendMoney).toHaveBeenCalledWith(1000);
    expect(sm.getCatalog("food")).toContain(2);
  });

  it("returns false and does not spend when item not in daily stock", () => {
    const sm = stockedShop();
    const stub = { spendMoney: vi.fn(() => true) };
    expect(sm.buy(999, stub)).toBe(false);
    expect(stub.spendMoney).not.toHaveBeenCalled();
  });

  it("returns false and does not update catalog when funds insufficient", () => {
    const sm = stockedShop();
    const stub = { spendMoney: vi.fn(() => false) };
    expect(sm.buy(2, stub)).toBe(false);
    expect(sm.getCatalog("food")).not.toContain(2);
  });
});

describe("buyMorningMarket", () => {
  it("returns false when no market active", () => {
    const sm = stockedShop();
    const stub = { spendMoney: vi.fn(() => true) };
    expect(sm.buyMorningMarket(stub)).toBe(false);
    expect(stub.spendMoney).not.toHaveBeenCalled();
  });

  it("succeeds: spends discount_price, records food item", () => {
    const sm = new ShopManager();
    sm.deserialize({
      daily: { food: [], clothing: [], interior: [] },
      morning_market: { item: 7, discount_price: 1500 },
      seasonal: [],
      catalog: { food: [], clothing: [], interior: [] },
    });
    const stub = { spendMoney: vi.fn(() => true) };
    expect(sm.buyMorningMarket(stub)).toBe(true);
    expect(stub.spendMoney).toHaveBeenCalledWith(1500);
    expect(sm.getCatalog("food")).toContain(7);
  });

  it("returns false when funds insufficient", () => {
    const sm = new ShopManager();
    sm.deserialize({
      daily: { food: [], clothing: [], interior: [] },
      morning_market: { item: 7, discount_price: 1500 },
      seasonal: [],
      catalog: { food: [], clothing: [], interior: [] },
    });
    const stub = { spendMoney: vi.fn(() => false) };
    expect(sm.buyMorningMarket(stub)).toBe(false);
    expect(sm.getCatalog("food")).not.toContain(7);
  });
});

describe("refreshDaily (injected rng, structural)", () => {
  const stubRng: ShopRng = {
    sample: <T>(items: T[], k: number): T[] => items.slice(0, k),
    choice: <T>(items: T[]): T => items[0],
  };

  it("fills daily per DAILY_COUNT and sets morning market", () => {
    const sm = new ShopManager();
    sm.refreshDaily(1, stubRng);
    expect(sm.getDaily("food")).toEqual([1, 2, 3]);
    expect(sm.getDaily("clothing")).toEqual([101, 102]);
    expect(sm.getDaily("interior")).toEqual([201]);
    expect(sm.getMorningMarket()).toEqual({ item: 1, discount_price: 1500 });
  });

  it("replaces last food item on holiday dateStr", () => {
    const sm = new ShopManager();
    sm.refreshDaily(1, stubRng, "04-14");
    expect(sm.getDaily("food")).toEqual([1, 2, 99]);
  });
});

describe("accessors return copies", () => {
  it("getDaily copy does not mutate internal state", () => {
    const sm = stockedShop();
    const daily = sm.getDaily("food");
    daily.push(9999);
    expect(sm.getDaily("food")).toEqual([1, 2, 3]);
  });

  it("getMorningMarket copy does not mutate internal state", () => {
    const sm = new ShopManager();
    sm.deserialize({
      daily: { food: [], clothing: [], interior: [] },
      morning_market: { item: 7, discount_price: 1500 },
      seasonal: [],
      catalog: { food: [], clothing: [], interior: [] },
    });
    const mm = sm.getMorningMarket()!;
    mm.item = 0;
    expect(sm.getMorningMarket()).toEqual({ item: 7, discount_price: 1500 });
  });
});
