/**
 * locationManager.test.ts — LocationManager 통합 테스트
 *
 * Python src/tomodachai/location.py LocationManager 1:1 포팅 검증.
 * 손으로 유도한 기대값 기반.
 */

import { describe, it, expect } from "vitest";
import {
  LocationManager,
  defaultLocation,
  type Location,
} from "./location";

describe("LocationManager — 생성자", () => {
  it("기본 15개 장소를 시드한다", () => {
    const mgr = new LocationManager();
    expect(mgr.allLocations().length).toBe(15);
  });

  it("extraLocations를 추가한다", () => {
    const extra: Location = defaultLocation({ id: "gym", name: "헬스장" });
    const mgr = new LocationManager([extra]);
    expect(mgr.allLocations().length).toBe(16);
    expect(mgr.getLocation("gym")?.name).toBe("헬스장");
  });

  it("같은 id의 extraLocation은 덮어쓴다 (개수 유지)", () => {
    const override: Location = defaultLocation({ id: "park", name: "재정의공원" });
    const mgr = new LocationManager([override]);
    expect(mgr.allLocations().length).toBe(15);
    expect(mgr.getLocation("park")?.name).toBe("재정의공원");
  });
});

describe("LocationManager — addLocation", () => {
  it("장소를 추가한다", () => {
    const mgr = new LocationManager();
    mgr.addLocation(defaultLocation({ id: "lab", name: "연구소" }));
    expect(mgr.allLocations().length).toBe(16);
    expect(mgr.getLocation("lab")?.name).toBe("연구소");
  });

  it("같은 id의 장소를 덮어쓴다 (개수 유지)", () => {
    const mgr = new LocationManager();
    mgr.addLocation(defaultLocation({ id: "park", name: "재정의공원" }));
    expect(mgr.allLocations().length).toBe(15);
    expect(mgr.getLocation("park")?.name).toBe("재정의공원");
  });
});

describe("LocationManager — registerPrivateRoom", () => {
  it("개인 방을 정확한 필드로 생성·등록·반환한다", () => {
    const mgr = new LocationManager();
    const room = mgr.registerPrivateRoom(3, "민수");

    expect(room.id).toBe("room_3");
    expect(room.name).toBe("민수의 방");
    expect(room.capacity).toBe(2);
    expect(room.location_type).toBe("private_room");
    expect(room.event_types).toEqual([
      "sleep",
      "personal_event",
      "room_visit",
      "gift",
      "consultation",
    ]);
    expect(room.description).toBe("민수의 개인 방");

    // getLocation으로 조회 가능
    expect(mgr.getLocation("room_3")).toEqual(room);
    // allLocations 개수 증가
    expect(mgr.allLocations().length).toBe(16);
  });
});

describe("LocationManager — getLocation / getLocationByName", () => {
  it("getLocation hit + miss(null)", () => {
    const mgr = new LocationManager();
    expect(mgr.getLocation("park")?.name).toBe("공원");
    expect(mgr.getLocation("does_not_exist")).toBeNull();
  });

  it("getLocationByName hit + miss(null)", () => {
    const mgr = new LocationManager();
    expect(mgr.getLocationByName("거실")?.id).toBe("living_room");
    expect(mgr.getLocationByName("없는장소")).toBeNull();
  });
});

describe("LocationManager — public/shared 쿼리", () => {
  it("publicLocations 13개, sharedLocations 2개 (기본셋)", () => {
    const mgr = new LocationManager();
    expect(mgr.publicLocations().length).toBe(13);
    expect(mgr.sharedLocations().length).toBe(2);
  });
});

describe("LocationManager — moveCharacter", () => {
  it("id로 이동 (true, 위치 설정)", () => {
    const mgr = new LocationManager();
    expect(mgr.moveCharacter(1, "park")).toBe(true);
    expect(mgr.getCharacterLocation(1)).toBe("park");
  });

  it("이름 폴백으로 이동 (공원 → park)", () => {
    const mgr = new LocationManager();
    expect(mgr.moveCharacter(2, "공원")).toBe(true);
    expect(mgr.getCharacterLocation(2)).toBe("park");
  });

  it("알 수 없는 목적지는 false, 위치 미설정", () => {
    const mgr = new LocationManager();
    expect(mgr.moveCharacter(3, "없는곳")).toBe(false);
    expect(mgr.getCharacterLocation(3)).toBeNull();
  });
});

describe("LocationManager — getCharactersAt / getCharacterLocation", () => {
  it("여러 캐릭터를 배치하고 필터한다", () => {
    const mgr = new LocationManager();
    mgr.moveCharacter(1, "park");
    mgr.moveCharacter(2, "park");
    mgr.moveCharacter(3, "cafe");

    expect(mgr.getCharactersAt("park").sort((a, b) => a - b)).toEqual([1, 2]);
    expect(mgr.getCharactersAt("cafe")).toEqual([3]);
    expect(mgr.getCharactersAt("beach")).toEqual([]);
  });

  it("없는 캐릭터는 getCharacterLocation null", () => {
    const mgr = new LocationManager();
    expect(mgr.getCharacterLocation(999)).toBeNull();
  });
});

describe("LocationManager — isAtCapacity", () => {
  it("정원 도달/초과 시 true (news_station capacity=2)", () => {
    const mgr = new LocationManager();
    expect(mgr.isAtCapacity("news_station")).toBe(false);
    mgr.moveCharacter(1, "news_station");
    expect(mgr.isAtCapacity("news_station")).toBe(false);
    mgr.moveCharacter(2, "news_station");
    expect(mgr.isAtCapacity("news_station")).toBe(true);
  });

  it("없는 장소는 true", () => {
    const mgr = new LocationManager();
    expect(mgr.isAtCapacity("ghost_location")).toBe(true);
  });
});

describe("LocationManager — removeCharacter", () => {
  it("위치를 제거하고 getCharactersAt에서 빠진다", () => {
    const mgr = new LocationManager();
    mgr.moveCharacter(1, "park");
    mgr.moveCharacter(2, "park");
    mgr.removeCharacter(1);

    expect(mgr.getCharacterLocation(1)).toBeNull();
    expect(mgr.getCharactersAt("park")).toEqual([2]);
  });

  it("없는 캐릭터 제거는 no-op (예외 없음)", () => {
    const mgr = new LocationManager();
    expect(() => mgr.removeCharacter(12345)).not.toThrow();
  });
});

describe("LocationManager — snapshot", () => {
  it("shape/characters/길이/순서가 정확하다", () => {
    const mgr = new LocationManager();
    mgr.moveCharacter(1, "living_room");
    mgr.moveCharacter(2, "park");

    const snap = mgr.snapshot();
    expect(snap.length).toBe(15);

    // 순서가 DEFAULT_LOCATIONS 순서와 일치
    expect(snap[0].id).toBe("living_room");
    expect(snap[1].id).toBe("balcony");
    expect(snap[2].id).toBe("grocery");
    expect(snap[14].id).toBe("photo_studio");

    // living_room 엔트리 shape 검증
    const livingRoom = snap[0];
    expect(livingRoom).toEqual({
      id: "living_room",
      name: "거실",
      location_type: "shared_room",
      capacity: 10,
      event_types: ["chat", "tv", "minigame", "birthday_party"],
      description: "소파 수다, TV 시청, 여러 명 모임, 미니게임",
      characters: [1],
    });

    // park characters
    const park = snap.find((s) => s.id === "park");
    expect(park?.characters).toEqual([2]);

    // 빈 장소는 빈 배열
    const beach = snap.find((s) => s.id === "beach");
    expect(beach?.characters).toEqual([]);
  });
});
