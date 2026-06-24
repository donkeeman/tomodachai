import { describe, it, expect } from "vitest";
import { defaultCharacter, type Character } from "./character";
import type { LocationConfig } from "./config";
import type { SimRng } from "./rng";
import { assignLocations } from "./simulation";

// ────────────────────────────────────────────────────────────────────────────
// 통제형 stub SimRng — shuffle을 주입해 배정을 결정론으로 만든다.
// 기본 shuffle은 항등(순서 유지)이라 배정 결과를 손으로 예측할 수 있다.
// ────────────────────────────────────────────────────────────────────────────
class StubRng implements SimRng {
  shuffleLengths: number[] = [];
  private readonly shuffleFn: (arr: unknown[]) => void;
  constructor(shuffleFn?: (arr: unknown[]) => void) {
    this.shuffleFn = shuffleFn ?? (() => {});
  }
  random(): number {
    return 0;
  }
  shuffle<T>(arr: T[]): void {
    this.shuffleLengths.push(arr.length);
    this.shuffleFn(arr as unknown[]);
  }
  choice<T>(arr: readonly T[]): T {
    return arr[0];
  }
  sample<T>(arr: readonly T[], k: number): T[] {
    return arr.slice(0, k);
  }
  uniform(a: number): number {
    return a;
  }
}

function chars(...names: string[]): Character[] {
  return names.map((n, i) => defaultCharacter(i + 1, n));
}

function loc(name: string, capacity: number): LocationConfig {
  return { name, capacity };
}

describe("assignLocations (simulation.py 1:1, 주입 rng seam)", () => {
  it("(a) 항등 shuffle: capacity 순서대로 채움", () => {
    const cs = chars("아리", "보리", "초리"); // c1,c2,c3
    const locs = [loc("공원", 2), loc("카페", 1)];
    const res = assignLocations(cs, locs, new StubRng());

    expect(res.get("공원")!.map((c) => c.profile.name)).toEqual(["아리", "보리"]);
    expect(res.get("카페")!.map((c) => c.profile.name)).toEqual(["초리"]);
  });

  it("(b) 모든 장소가 차면 그 캐릭터는 미배정 (break 없이 종료)", () => {
    const cs = chars("아리", "보리");
    const locs = [loc("공원", 1)];
    const res = assignLocations(cs, locs, new StubRng());

    expect(res.get("공원")!.map((c) => c.profile.name)).toEqual(["아리"]);
    const total = [...res.values()].reduce((n, arr) => n + arr.length, 0);
    expect(total).toBe(1); // 보리는 드롭
  });

  it("(c) 캐릭터 0명: 모든 장소 키 존재 + 빈 배열, Map 삽입 순서 유지", () => {
    const locs = [loc("공원", 5), loc("편의점", 3), loc("카페", 4)];
    const res = assignLocations([], locs, new StubRng());

    expect([...res.keys()]).toEqual(["공원", "편의점", "카페"]);
    expect([...res.values()].every((arr) => arr.length === 0)).toBe(true);
  });

  it("(d) shuffle 호출: 캐릭터 1회 + 캐릭터마다 available 1회", () => {
    const cs = chars("아리", "보리", "초리"); // 3명
    const locs = [loc("공원", 5), loc("카페", 5)]; // 2장소
    const rng = new StubRng();
    assignLocations(cs, locs, rng);

    // 첫 호출=캐릭터 배열(len 3), 이후 3회=available(len 2)씩
    expect(rng.shuffleLengths).toEqual([3, 2, 2, 2]);
  });

  it("(e) rng가 실제 순서를 좌우: 캐릭터 역순 shuffle → 배정 순서 반전", () => {
    const cs = chars("아리", "보리", "초리");
    const locs = [loc("공원", 1), loc("카페", 1), loc("도서관", 1)];
    // 캐릭터 배열만 역순으로(available은 문자열이라 그대로) — 원소 타입으로 구분
    const rng = new StubRng((arr) => {
      if (arr.length > 0 && typeof arr[0] !== "string") arr.reverse();
    });
    const res = assignLocations(cs, locs, rng);

    // 역순(초리,보리,아리)이 공원/카페/도서관 순서로 배정
    expect(res.get("공원")!.map((c) => c.profile.name)).toEqual(["초리"]);
    expect(res.get("카페")!.map((c) => c.profile.name)).toEqual(["보리"]);
    expect(res.get("도서관")!.map((c) => c.profile.name)).toEqual(["아리"]);
  });

  it("(f) 입력 characters 배열은 변형하지 않음 (복사본 shuffle)", () => {
    const cs = chars("아리", "보리", "초리");
    const snapshot = cs.map((c) => c.profile.name);
    const rng = new StubRng((arr) => arr.reverse());
    assignLocations(cs, [loc("공원", 5)], rng);
    expect(cs.map((c) => c.profile.name)).toEqual(snapshot);
  });
});
