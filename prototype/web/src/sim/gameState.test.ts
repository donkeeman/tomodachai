import { describe, it, expect } from "vitest";
import { defaultCharacter } from "./character";
import type { Msg, LlmClient } from "../llm";
import type { SimRng } from "./rng";
import { GameState, type GameStateDeps } from "./gameState";
import { loadGolden } from "./__golden__/loadGolden";

// ────────────────────────────────────────────────────────────────────────────
// 주입 stub: LLM은 고정 빈 응답, RNG는 sample=앞 k개/choice=첫 원소/uniform=큐.
// ────────────────────────────────────────────────────────────────────────────
class StubLlm implements LlmClient {
  async chatJson(_messages: Msg[]): Promise<Record<string, unknown>> {
    return { dialogue: [], deltas: {}, summary: "" };
  }
}
class StubRng implements SimRng {
  private ui = 0;
  constructor(private readonly uniforms: number[] = []) {}
  random(): number {
    return 0;
  }
  shuffle(): void {}
  choice<T>(arr: readonly T[]): T {
    return arr[0];
  }
  sample<T>(arr: readonly T[], k: number): T[] {
    return arr.slice(0, k);
  }
  uniform(): number {
    const v = this.uniforms[this.ui] ?? 0;
    this.ui += 1;
    return v;
  }
}
function deps(opts: { nowFn?: () => Date; uniforms?: number[] } = {}): GameStateDeps {
  return { llm: new StubLlm(), rng: new StubRng(opts.uniforms), nowFn: opts.nowFn };
}

describe("GameState 기본값 (골든, game_state.py 1:1)", () => {
  it("기본 상태가 GameState() 골든과 일치", () => {
    const gs = new GameState(deps());
    const golden = loadGolden<string, Record<string, unknown>>("game_state_defaults")[0];
    const actual = {
      island_name: gs.island_name,
      day_count: gs.day_count,
      money: gs.money,
      time_flip: gs.time_flip,
      ending_credit_seen: gs.ending_credit_seen,
      catalog: gs.catalog,
      catalog_categories_sorted: Object.keys(gs.catalog).sort(),
    };
    expect(actual).toEqual(golden.expected);
  });

  it("init로 island_name/day_count/money/time_flip 오버라이드", () => {
    const gs = new GameState(deps(), {
      islandName: "별빛마을",
      dayCount: 3,
      money: 500,
      timeFlip: true,
    });
    expect(gs.island_name).toBe("별빛마을");
    expect(gs.day_count).toBe(3);
    expect(gs.money).toBe(500);
    expect(gs.time_flip).toBe(true);
  });
});

describe("GameState 경제 헬퍼 (game_state.py 1:1)", () => {
  it("addMoney: 양수 추가, 음수 throw", () => {
    const gs = new GameState(deps(), { money: 100 });
    gs.addMoney(50);
    expect(gs.money).toBe(150);
    expect(() => gs.addMoney(-1)).toThrow(
      "amount must be non-negative; use spend_money to deduct",
    );
  });

  it("spendMoney: 성공 true/차감, 부족 false/불변, 음수 throw", () => {
    const gs = new GameState(deps(), { money: 100 });
    expect(gs.spendMoney(30)).toBe(true);
    expect(gs.money).toBe(70);
    expect(gs.spendMoney(999)).toBe(false);
    expect(gs.money).toBe(70); // 불변
    expect(() => gs.spendMoney(-1)).toThrow("amount must be non-negative");
  });
});

describe("GameState 카탈로그 (game.json §1, game_state.py 1:1)", () => {
  it("addToCatalog: 기록 + 중복 무시, isInCatalog 조회", () => {
    const gs = new GameState(deps());
    gs.addToCatalog("food", 5);
    gs.addToCatalog("food", 5); // 중복
    gs.addToCatalog("treasure", 1);
    expect(gs.catalog.food).toEqual([5]);
    expect(gs.catalog.treasure).toEqual([1]);
    expect(gs.isInCatalog("food", 5)).toBe(true);
    expect(gs.isInCatalog("food", 99)).toBe(false);
  });

  it("미지 카테고리는 정확한 메시지로 throw (양쪽 메서드)", () => {
    const gs = new GameState(deps());
    const msg = "Unknown catalog category 'weapon'. Must be one of: ['clothing', 'food', 'interior', 'treasure']";
    expect(() => gs.addToCatalog("weapon", 1)).toThrow(msg);
    expect(() => gs.isInCatalog("weapon", 1)).toThrow(msg);
  });
});

describe("GameState 캐릭터 관리 (game_state.py 1:1)", () => {
  it("addCharacter: 추가 + 개인 방 등록, 중복 id throw", () => {
    const gs = new GameState(deps());
    gs.addCharacter(defaultCharacter(1, "아리"));
    expect(gs.characters.length).toBe(1);
    expect(gs.location_manager.getLocation("room_1")).not.toBeNull();
    expect(() => gs.addCharacter(defaultCharacter(1, "중복"))).toThrow(
      "Character with id '1' already exists",
    );
  });

  it("getCharacter: 존재→객체, 없음→null", () => {
    const gs = new GameState(deps());
    const a = gs.addCharacter(defaultCharacter(1, "아리"));
    expect(gs.getCharacter(1)).toBe(a);
    expect(gs.getCharacter(999)).toBeNull();
  });

  it("removeCharacter: 제거 true / 없으면 false", () => {
    const gs = new GameState(deps());
    gs.addCharacter(defaultCharacter(1, "아리"));
    expect(gs.removeCharacter(1)).toBe(true);
    expect(gs.characters.length).toBe(0);
    expect(gs.removeCharacter(1)).toBe(false);
  });
});

describe("GameState 시뮬레이션 지연 생성/무효화", () => {
  it("simulation 게터: 동일 인스턴스 캐시", () => {
    const gs = new GameState(deps());
    const s1 = gs.simulation;
    expect(gs.simulation).toBe(s1);
  });

  it("addCharacter/removeCharacter가 simulation 무효화", () => {
    const gs = new GameState(deps());
    const s1 = gs.simulation;
    gs.addCharacter(defaultCharacter(1, "아리"));
    const s2 = gs.simulation;
    expect(s2).not.toBe(s1);
    gs.removeCharacter(1);
    expect(gs.simulation).not.toBe(s2);
  });

  it("relationships/memory가 simulation에 위임", () => {
    const gs = new GameState(deps());
    expect(gs.relationships).toBe(gs.simulation.relationships);
    expect(gs.memory).toBe(gs.simulation.memory);
  });
});

describe("GameState.step / touch", () => {
  it("캐릭터 없으면 [] (touch도 simulation도 호출 안 함 경로)", async () => {
    const gs = new GameState(deps());
    expect(await gs.step()).toEqual([]);
  });

  it("캐릭터 있으면 touch 후 simulation.step", async () => {
    let now = new Date("2026-06-24T10:00:00Z");
    const gs = new GameState(deps({ nowFn: () => now }));
    gs.addCharacter(defaultCharacter(1, "아리"));
    gs.addCharacter(defaultCharacter(2, "보리"));
    now = new Date("2026-06-24T11:00:00Z");
    const events = await gs.step();
    expect(gs.last_online.getTime()).toBe(now.getTime()); // touch됨
    expect(events.length).toBeGreaterThanOrEqual(1);
    expect(events[0].type).toBe("conversation");
  });
});

describe("GameState.connect (game_state.py 1:1, 주입 nowFn)", () => {
  it("오프라인 3h: catchup 생성, is_new_day false, day_count 불변", () => {
    let now = new Date("2026-06-24T10:00:00Z");
    const gs = new GameState(deps({ nowFn: () => now, uniforms: [5, 2] }));
    gs.addCharacter(defaultCharacter(1, "아리"));
    gs.addCharacter(defaultCharacter(2, "보리"));
    now = new Date("2026-06-24T13:00:00Z"); // +3h

    const r = gs.connect();
    expect(r.offline_hours).toBe(3);
    expect(r.is_new_day).toBe(false);
    expect(r.catchup_events.length).toBe(1); // catchupEventCount(3)=1
    expect(gs.day_count).toBe(0);
    expect(r.time_period).toBe("낮"); // 13시
    expect(gs.last_online.getTime()).toBe(now.getTime());
  });

  it("새벽 5시 경계 넘으면 is_new_day true + day_count++", () => {
    let now = new Date("2026-06-24T03:00:00Z"); // 리셋 전
    const gs = new GameState(deps({ nowFn: () => now, uniforms: [5, 2, 3, 1] }));
    gs.addCharacter(defaultCharacter(1, "아리"));
    gs.addCharacter(defaultCharacter(2, "보리"));
    now = new Date("2026-06-24T13:00:00Z"); // 리셋(05시) 넘김, +10h

    const r = gs.connect();
    expect(r.is_new_day).toBe(true);
    expect(gs.day_count).toBe(1);
    expect(r.catchup_events.length).toBe(2); // catchupEventCount(10)=2
  });

  it("5분 미만이면 catchup 없음, day_count 불변", () => {
    let now = new Date("2026-06-24T10:00:00Z");
    const gs = new GameState(deps({ nowFn: () => now }));
    gs.addCharacter(defaultCharacter(1, "아리"));
    gs.addCharacter(defaultCharacter(2, "보리"));
    now = new Date("2026-06-24T10:02:00Z"); // +2분

    const r = gs.connect();
    expect(r.catchup_events).toEqual([]);
    expect(r.offline_hours).toBe(0.03); // round2(2/60)
    expect(gs.day_count).toBe(0);
  });

  it("캐릭터 없으면 오프라인 길어도 catchup 없음", () => {
    let now = new Date("2026-06-24T10:00:00Z");
    const gs = new GameState(deps({ nowFn: () => now }));
    now = new Date("2026-06-25T10:00:00Z"); // +24h, 캐릭터 0명
    const r = gs.connect();
    expect(r.catchup_events).toEqual([]);
  });
});

describe("GameState 시간 접근자", () => {
  it("currentTimePeriod / currentGameHour는 주입 clock 기준", () => {
    const now = new Date("2026-06-24T19:00:00Z"); // 19시 → 저녁
    const gs = new GameState(deps({ nowFn: () => now }));
    expect(gs.currentGameHour).toBe(19);
    expect(gs.currentTimePeriod).toBe("저녁");
  });

  it("time_flip 시 12시간 반전", () => {
    const now = new Date("2026-06-24T19:00:00Z"); // 19→(flip)7시 아침
    const gs = new GameState(deps({ nowFn: () => now }), { timeFlip: true });
    expect(gs.currentGameHour).toBe(7);
    expect(gs.currentTimePeriod).toBe("아침");
  });
});
