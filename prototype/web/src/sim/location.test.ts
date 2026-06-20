import { describe, it, expect } from "vitest";
import { loadGolden } from "./__golden__/loadGolden";
import { DEFAULT_LOCATIONS, DEFAULT_PUBLIC_WEIGHTS, defaultLocation } from "./location";

// ────────────────────────────────────────────────────────────────────────────
// 골든 픽스처 타입
// ────────────────────────────────────────────────────────────────────────────
interface LocationDump {
  id: string;
  name: string;
  capacity: number;
  location_type: string;
  event_types: string[];
  description: string;
}

// ────────────────────────────────────────────────────────────────────────────
// DEFAULT_LOCATIONS 골든 검증
// ────────────────────────────────────────────────────────────────────────────
describe("DEFAULT_LOCATIONS golden", () => {
  const cases = loadGolden<string, LocationDump[]>("location_catalog");
  const goldenLocs = cases[0].expected!;

  it("should have 15 locations", () => {
    expect(DEFAULT_LOCATIONS).toHaveLength(15);
  });

  it("should match golden catalog exactly (model_dump shape)", () => {
    const dumped = DEFAULT_LOCATIONS.map((loc) => ({
      id: loc.id,
      name: loc.name,
      capacity: loc.capacity,
      location_type: loc.location_type,
      event_types: loc.event_types,
      description: loc.description,
    }));
    expect(dumped).toEqual(goldenLocs);
  });
});

// ────────────────────────────────────────────────────────────────────────────
// DEFAULT_PUBLIC_WEIGHTS 골든 검증
// ────────────────────────────────────────────────────────────────────────────
describe("DEFAULT_PUBLIC_WEIGHTS golden", () => {
  const cases = loadGolden<string, Record<string, number>>("location_weights");
  const goldenWeights = cases[0].expected!;

  it("should have 15 weight entries", () => {
    expect(Object.keys(DEFAULT_PUBLIC_WEIGHTS)).toHaveLength(15);
  });

  it("should match golden weights exactly", () => {
    expect(DEFAULT_PUBLIC_WEIGHTS).toEqual(goldenWeights);
  });
});

// ────────────────────────────────────────────────────────────────────────────
// defaultLocation 팩토리
// ────────────────────────────────────────────────────────────────────────────
describe("defaultLocation factory", () => {
  it("applies defaults: capacity=6, location_type=public, event_types=[], description=''", () => {
    const loc = defaultLocation({ id: "test", name: "테스트" });
    expect(loc).toEqual({
      id: "test",
      name: "테스트",
      capacity: 6,
      location_type: "public",
      event_types: [],
      description: "",
    });
  });

  it("allows overriding defaults", () => {
    const loc = defaultLocation({
      id: "room_1",
      name: "방",
      capacity: 2,
      location_type: "private_room",
      event_types: ["sleep"],
      description: "개인 방",
    });
    expect(loc.capacity).toBe(2);
    expect(loc.location_type).toBe("private_room");
    expect(loc.event_types).toEqual(["sleep"]);
  });
});
