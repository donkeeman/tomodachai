import { describe, it, expect } from "vitest";
import { loadGolden } from "./__golden__/loadGolden";
import {
  LocationManager,
  buildDestinationWeights,
  chooseDestination,
  type DestinationActor,
  type Rng,
} from "./location";

// ────────────────────────────────────────────────────────────────────────────
// 시나리오별 매니저 + 액터 + allPairs 구성 (Python dump_destination_weights와 1:1)
// ────────────────────────────────────────────────────────────────────────────
type AllPairs = [number, number, { friendship: number }][];

function setup(name: string): {
  char: DestinationActor;
  allPairs: AllPairs;
  manager: LocationManager;
} {
  const manager = new LocationManager();
  let char: DestinationActor = { id: 1, hunger: 0.0, satisfaction: 50.0, stress: 2 };
  let allPairs: AllPairs = [];

  switch (name) {
    case "baseline":
      break;
    case "hungry":
      char = { id: 1, hunger: 80.0, satisfaction: 50.0, stress: 2 };
      break;
    case "unsatisfied":
      char = { id: 1, hunger: 0.0, satisfaction: 10.0, stress: 2 };
      break;
    case "stressed":
      char = { id: 1, hunger: 0.0, satisfaction: 50.0, stress: 9 };
      break;
    case "follow_friend":
      manager.moveCharacter(2, "park");
      allPairs = [[1, 2, { friendship: 65.0 }]];
      break;
    case "capacity":
      manager.moveCharacter(10, "news_station");
      manager.moveCharacter(11, "news_station");
      break;
    case "combined":
      manager.moveCharacter(2, "beach");
      for (const cid of [20, 21, 22, 23]) {
        manager.moveCharacter(cid, "grocery");
      }
      allPairs = [[1, 2, { friendship: 70.0 }]];
      char = { id: 1, hunger: 80.0, satisfaction: 10.0, stress: 9 };
      break;
    default:
      throw new Error(`unknown scenario: ${name}`);
  }

  return { char, allPairs, manager };
}

// ────────────────────────────────────────────────────────────────────────────
// buildDestinationWeights 골든 검증
// ────────────────────────────────────────────────────────────────────────────
describe("buildDestinationWeights golden", () => {
  const cases = loadGolden<string, Record<string, number>>("destination_weights");

  for (const c of cases) {
    it(`matches golden weights: ${c.input}`, () => {
      const expected = c.expected!;
      const { char, allPairs, manager } = setup(c.input);
      const result = buildDestinationWeights(char, allPairs, manager);

      expect(new Set(Object.keys(result))).toEqual(new Set(Object.keys(expected)));
      for (const k of Object.keys(expected)) {
        expect(result[k]).toBeCloseTo(expected[k], 10);
      }
    });
  }
});

// ────────────────────────────────────────────────────────────────────────────
// chooseDestination 구조 검증 (주입 stub rng — Python 난수열 미일치)
// ────────────────────────────────────────────────────────────────────────────
function stubRng(randomValue: number): Rng & {
  lastChoices: { ids: string[]; weights: number[] } | null;
} {
  return {
    lastChoices: null,
    random(): number {
      return randomValue;
    },
    choices<T>(items: T[], weights: number[]): T {
      this.lastChoices = { ids: items as unknown as string[], weights };
      return items[0];
    },
  };
}

describe("chooseDestination structural", () => {
  it("night + room registered + random()<0.7 → returns room_1", () => {
    const manager = new LocationManager();
    manager.registerPrivateRoom(1, "x");
    const char: DestinationActor = { id: 1, hunger: 0, satisfaction: 50, stress: 2 };
    const rng = stubRng(0.5);
    expect(chooseDestination(char, [], "밤", manager, rng)).toBe("room_1");
    expect(rng.lastChoices).toBeNull(); // weighted choice 미호출
  });

  it("night + room registered + random()>=0.7 → does NOT return room, returns choices pick", () => {
    const manager = new LocationManager();
    manager.registerPrivateRoom(1, "x");
    const char: DestinationActor = { id: 1, hunger: 0, satisfaction: 50, stress: 2 };
    const rng = stubRng(0.8);
    const result = chooseDestination(char, [], "밤", manager, rng);
    expect(result).not.toBe("room_1");
    expect(rng.lastChoices).not.toBeNull();
    expect(result).toBe(rng.lastChoices!.ids[0]);
  });

  it("night + NO room registered → skips room branch → returns choices pick", () => {
    const manager = new LocationManager();
    const char: DestinationActor = { id: 1, hunger: 0, satisfaction: 50, stress: 2 };
    const rng = stubRng(0.5); // <0.7 would trigger room, but no room exists
    const result = chooseDestination(char, [], "밤", manager, rng);
    expect(result).not.toBe("room_1");
    expect(rng.lastChoices).not.toBeNull();
    expect(result).toBe(rng.lastChoices!.ids[0]);
  });

  it("day (낮) → ignores night branch; returns stub choices first id, args match buildDestinationWeights", () => {
    const manager = new LocationManager();
    manager.registerPrivateRoom(1, "x");
    const char: DestinationActor = { id: 1, hunger: 0, satisfaction: 50, stress: 2 };
    const rng = stubRng(0.5);
    const result = chooseDestination(char, [], "낮", manager, rng);

    const weights = buildDestinationWeights(char, [], manager);
    const ids = Object.keys(weights);
    const w = ids.map((i) => weights[i]);

    expect(result).toBe(ids[0]);
    expect(rng.lastChoices!.ids).toEqual(ids);
    expect(rng.lastChoices!.weights).toEqual(w);
  });
});
