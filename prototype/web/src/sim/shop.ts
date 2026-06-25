/**
 * shop.ts — ShopManager 포팅 (일일 재고, 아침 장터, 시즌 아이템, 카탈로그)
 *
 * Python src/tomodachai/shop.py 1:1 포팅.
 * 아이템 마스터 데이터는 아직 없음 — 아이템 ID만 다룬다.
 * framework-free (Babylon/Svelte/Tauri 미의존). RNG는 주입식.
 */

// ────────────────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────────────────

/** Python range(start, stop) → [start, ..., stop-1] */
function range(start: number, stop: number): number[] {
  const out: number[] = [];
  for (let i = start; i < stop; i += 1) {
    out.push(i);
  }
  return out;
}

// ────────────────────────────────────────────────────────────────────────────
// Constants
// ────────────────────────────────────────────────────────────────────────────

export const CATEGORIES = ["food", "clothing", "interior"] as const;
export type Category = (typeof CATEGORIES)[number];

/** "MM-DD" → 강제 포함 아이템 ID */
export const HOLIDAYS: Record<string, number> = { "04-14": 99 };

export const DAILY_COUNT: Record<string, number> = { food: 3, clothing: 2, interior: 1 };

export const MORNING_MARKET_DISCOUNT_RATE = 0.6;
export const MORNING_MARKET_BASE_PRICE = 2500;

/** Python _DEFAULT_POOL: food [1..100], clothing [101..200], interior [201..300] */
export const DEFAULT_POOL: Record<string, number[]> = {
  food: range(1, 101),
  clothing: range(101, 201),
  interior: range(201, 301),
};

// ────────────────────────────────────────────────────────────────────────────
// Interfaces
// ────────────────────────────────────────────────────────────────────────────

/** game_state.spend_money 덕타입 */
export interface MoneySpender {
  spendMoney(amount: number): boolean;
}

/** Python random.Random 중 refresh_daily가 쓰는 인터페이스만 추출. */
export interface ShopRng {
  sample<T>(items: T[], k: number): T[];
  choice<T>(items: T[]): T;
}

export interface MorningMarket {
  item: number;
  discount_price: number;
}

export interface ShopSnapshot {
  daily: Record<string, number[]>;
  morning_market: MorningMarket | null;
  seasonal: number[];
  catalog: Record<string, number[]>;
}

// ────────────────────────────────────────────────────────────────────────────
// ShopManager
// ────────────────────────────────────────────────────────────────────────────

export class ShopManager {
  private readonly _dailyItems: Map<string, number[]> = new Map();
  private _morningMarket: MorningMarket | null = null;
  private _seasonalItems: number[] = [];
  private readonly _catalog: Map<string, Set<number>> = new Map();

  constructor() {
    for (const c of CATEGORIES) {
      this._dailyItems.set(c, []);
      this._catalog.set(c, new Set<number>());
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Daily refresh
  // ──────────────────────────────────────────────────────────────────────────

  /**
   * 일일 재고를 재생성한다.
   *
   * @param day     게임 일자 카운터. Python에서는 기본 Random 시드로만 쓰이며 — RNG를
   *                주입하는 본 포팅에서는 미사용(API 패리티 유지용 인자).
   * @param rng     주입 RNG (Phase 0 결정: Python 난수열은 교차언어 미일치, RNG 주입).
   * @param dateStr "MM-DD" 형식 현재 날짜. 휴일 아이템 강제 포함에 사용.
   */
  refreshDaily(day: number, rng: ShopRng, dateStr?: string | null): void {
    for (const category of CATEGORIES) {
      const pool = DEFAULT_POOL[category];
      const count = DAILY_COUNT[category] ?? 3;
      const chosen = rng.sample(pool, Math.min(count, pool.length));
      this._dailyItems.set(category, chosen);
    }

    // 휴일 아이템 강제 포함 (food 마지막 원소 교체).
    if (dateStr && dateStr in HOLIDAYS) {
      const holidayItem = HOLIDAYS[dateStr];
      const foodItems = this._dailyItems.get("food")!;
      if (!foodItems.includes(holidayItem)) {
        if (foodItems.length > 0) {
          foodItems[foodItems.length - 1] = holidayItem;
        } else {
          foodItems.push(holidayItem);
        }
      }
    }

    // 아침 장터: food 한 개를 할인가에.
    const marketItem = rng.choice(DEFAULT_POOL.food);
    const discountPrice = Math.trunc(MORNING_MARKET_BASE_PRICE * MORNING_MARKET_DISCOUNT_RATE);
    this._morningMarket = { item: marketItem, discount_price: discountPrice };
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Read-only accessors (모두 복사본 반환)
  // ──────────────────────────────────────────────────────────────────────────

  getDaily(category: string): number[] {
    return [...(this._dailyItems.get(category) ?? [])];
  }

  getMorningMarket(): MorningMarket | null {
    return this._morningMarket ? { ...this._morningMarket } : null;
  }

  getSeasonal(): number[] {
    return [...this._seasonalItems];
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Purchase
  // ──────────────────────────────────────────────────────────────────────────

  buy(itemId: number, gameState: MoneySpender): boolean {
    const category = this._findDailyCategory(itemId);
    if (category === null) {
      return false;
    }

    const price = this._getItemPrice(itemId);
    if (!gameState.spendMoney(price)) {
      return false;
    }

    this.addToCatalog(category, itemId);
    return true;
  }

  buyMorningMarket(gameState: MoneySpender): boolean {
    if (this._morningMarket === null) {
      return false;
    }

    const itemId = this._morningMarket.item;
    const price = this._morningMarket.discount_price;

    if (!gameState.spendMoney(price)) {
      return false;
    }

    // 아침 장터 아이템은 food.
    this.addToCatalog("food", itemId);
    return true;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Catalog management
  // ──────────────────────────────────────────────────────────────────────────

  addToCatalog(category: string, itemId: number): void {
    let set = this._catalog.get(category);
    if (set === undefined) {
      set = new Set<number>();
      this._catalog.set(category, set);
    }
    set.add(itemId);
  }

  /** 숫자 오름차순 정렬 (JS 기본 정렬은 사전식이므로 비교자 필수). */
  getCatalog(category: string): number[] {
    const set = this._catalog.get(category) ?? new Set<number>();
    return [...set].sort((a, b) => a - b);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Serialization
  // ──────────────────────────────────────────────────────────────────────────

  serialize(): ShopSnapshot {
    const daily: Record<string, number[]> = {};
    for (const [c, ids] of this._dailyItems.entries()) {
      daily[c] = [...ids];
    }
    const catalog: Record<string, number[]> = {};
    for (const [c, ids] of this._catalog.entries()) {
      catalog[c] = [...ids].sort((a, b) => a - b);
    }
    return {
      daily,
      morning_market: this._morningMarket ? { ...this._morningMarket } : null,
      seasonal: [...this._seasonalItems],
      catalog,
    };
  }

  deserialize(data: Partial<ShopSnapshot>): void {
    const daily = data.daily ?? {};
    for (const category of CATEGORIES) {
      const raw = daily[category] ?? [];
      this._dailyItems.set(
        category,
        raw.map((i) => Number(i)),
      );
    }

    const mm = data.morning_market;
    if (mm) {
      this._morningMarket = {
        item: Number(mm.item),
        discount_price: Number(mm.discount_price),
      };
    } else {
      this._morningMarket = null;
    }

    this._seasonalItems = (data.seasonal ?? []).map((i) => Number(i));

    const catalog = data.catalog ?? {};
    for (const category of CATEGORIES) {
      const raw = catalog[category] ?? [];
      this._catalog.set(category, new Set(raw.map((i) => Number(i))));
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Private helpers
  // ──────────────────────────────────────────────────────────────────────────

  private _findDailyCategory(itemId: number): string | null {
    for (const [category, items] of this._dailyItems.entries()) {
      if (items.includes(itemId)) {
        return category;
      }
    }
    return null;
  }

  private _getItemPrice(_itemId: number): number {
    // 아이템 마스터 데이터 부재 — 일괄 1000원 (Python 동일).
    return 1000;
  }
}
