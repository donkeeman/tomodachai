import { describe, it, expect } from "vitest";
import {
  makeDefaultConfig,
  makeLocationConfig,
  makeDefaultLocations,
} from "./config";
import { loadGolden } from "./__golden__/loadGolden";

describe("config 기본값 (골든, config.py AppConfig() 1:1)", () => {
  it("makeDefaultConfig() == AppConfig().model_dump()", () => {
    const cases = loadGolden<string, Record<string, unknown>>("config_defaults");
    expect(cases.length).toBe(1);
    expect(cases[0].input).toBe("AppConfig");
    expect(makeDefaultConfig()).toEqual(cases[0].expected);
  });

  it("기본 locations: 공원(5)/편의점(3)/카페(4) — 순서 유지", () => {
    expect(makeDefaultLocations()).toEqual([
      { name: "공원", capacity: 5 },
      { name: "편의점", capacity: 3 },
      { name: "카페", capacity: 4 },
    ]);
  });

  it("makeLocationConfig: capacity 기본값 4 (config.py LocationConfig 미러)", () => {
    expect(makeLocationConfig("호수")).toEqual({ name: "호수", capacity: 4 });
    expect(makeLocationConfig("바다", 8)).toEqual({ name: "바다", capacity: 8 });
  });

  it("팩토리는 매번 새 객체 — 공유 변형 없음", () => {
    const a = makeDefaultConfig();
    const b = makeDefaultConfig();
    a.locations.push({ name: "변형", capacity: 1 });
    a.llm.temperature = 9;
    expect(b.locations.length).toBe(3);
    expect(b.llm.temperature).toBe(0.8);
  });
});
