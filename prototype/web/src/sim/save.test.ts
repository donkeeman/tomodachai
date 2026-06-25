import { describe, it, expect } from "vitest";
import { defaultCharacter, type Character } from "./character";
import { serializeCharacter, deserializeCharacter } from "./save";
import { loadGolden } from "./__golden__/loadGolden";

// ────────────────────────────────────────────────────────────────────────────
// 샘플 캐릭터 — Python dump_golden._sample_character()와 1:1 (모든 섹션 비기본값).
// ────────────────────────────────────────────────────────────────────────────
function sampleChar(): Character {
  const c = defaultCharacter(7, "민지");
  c.profile.birthday = "07-15";
  c.profile.blood_type = "A";
  c.profile.favorite_color = "#FF8800";
  c.profile.gender = "여";
  c.profile.appearance = {
    face_shape: 3,
    skin_color: "#F5D6B8",
    eye: { base: 2, lash: 1, color: "#3A2A1A", adjust: { spacing: 1, height: -2, size: 3, angle: -1 } },
    eyebrow: { id: 4, adjust: { spacing: 0, height: 1, size: -1, angle: 2 } },
    nose: { id: 2, adjust: { spacing: 0, height: 2, size: -1, angle: 0 } },
    mouth: { id: 5, adjust: { spacing: 0, height: -1, size: 1, angle: 0 } },
    hair: { front: 3, back: 2, color: "#5B3A1A" },
    glasses: 2,
    body: { height: 6, build: 4 },
  };
  c.profile.personality = { movement: 8, speech: 8, expressiveness: 7, attitude: 5, overall: 6 };
  c.profile.voice = {
    preset: "bright", pitch: 7, speed: 4, quality: "clear",
    tone: "warm", accent: null, intonation: "rising",
  };
  c.preferences = {
    food_ranks: [3, 1, 2],
    food_eaten: [true, false, true],
    clothing: { likes: "원피스", dislikes: "정장" },
    interior: { likes: "식물", dislikes: "금속" },
    personality_group: { group: "활발", is_positive: true },
  };
  c.state = {
    satisfaction: 72,
    level: 3,
    hunger: 20,
    mood: { happiness: 7, energy: 6, stress: 3 },
    sick: "감기",
    current_location: "cafe",
    current_outfit: 11,
    current_interior: 22,
    photo_frame: 5,
  };
  c.customizable = {
    speech_habits: { normal: "~지", happy: "개좋아", angry: "아오", sad: "흑", worried: "음..." },
    mini_traits: {
      walking: { owned: [1, 2], active: 1 },
      eating: { owned: [3], active: null },
      idle: { owned: [], active: null },
    },
    nicknames: { "2": "민지짱" },
    songs: [true, false, true, false, false, false, false, false],
  };
  c.records = {
    treasure_collection: [1, 5, 9],
    confession_count: { "2": 1 },
    photos: [10, 20],
  };
  return c;
}

describe("serializeCharacter (골든, _serialize_character 1:1)", () => {
  it("샘플 캐릭터 직렬화가 골든과 일치", () => {
    const golden = loadGolden<string, Record<string, unknown>>("save_character")[0];
    expect(serializeCharacter(sampleChar())).toEqual(golden.expected);
  });

  it("nose/mouth adjust는 {height,size}만 (spacing/angle 생략)", () => {
    const out = serializeCharacter(sampleChar()) as any;
    expect(Object.keys(out.profile.appearance.nose.adjust).sort()).toEqual(["height", "size"]);
    expect(Object.keys(out.profile.appearance.mouth.adjust).sort()).toEqual(["height", "size"]);
  });

  it("eye/eyebrow adjust는 4필드 모두", () => {
    const out = serializeCharacter(sampleChar()) as any;
    expect(Object.keys(out.profile.appearance.eye.adjust).sort()).toEqual(
      ["angle", "height", "size", "spacing"],
    );
    expect(Object.keys(out.profile.appearance.eyebrow.adjust).sort()).toEqual(
      ["angle", "height", "size", "spacing"],
    );
  });

  it("personality_code는 슬라이더에서 런타임 계산되어 포함됨", () => {
    const out = serializeCharacter(sampleChar()) as any;
    expect(out.personality_code).toBe("outgoing_buddy");
  });

  it("default 캐릭터: nullable 필드(null)와 빈 컬렉션을 그대로 직렬화", () => {
    const out = serializeCharacter(defaultCharacter(1, "기본")) as any;
    // nullable 필드는 null 통과 (Python None)
    expect(out.profile.appearance.glasses).toBeNull();
    expect(out.profile.voice.accent).toBeNull();
    expect(out.state.sick).toBeNull();
    expect(out.state.current_outfit).toBeNull();
    expect(out.state.current_interior).toBeNull();
    expect(out.state.photo_frame).toBeNull();
    expect(out.customizable.mini_traits.idle.active).toBeNull();
    // 빈 컬렉션 그대로
    expect(out.preferences.food_ranks).toEqual([]);
    expect(out.records.treasure_collection).toEqual([]);
    expect(out.records.confession_count).toEqual({});
    expect(out.customizable.nicknames).toEqual({});
  });

  it("직렬화 최상위 키 셋 = id/personality_code/profile/preferences/state/customizable/records", () => {
    const out = serializeCharacter(sampleChar());
    expect(Object.keys(out).sort()).toEqual(
      ["customizable", "id", "personality_code", "preferences", "profile", "records", "state"],
    );
    // 레거시 flat 필드는 직렬화하지 않음
    expect(out).not.toHaveProperty("food_preferences");
    expect(out).not.toHaveProperty("mini_personality");
  });
});

describe("deserializeCharacter (Character(**data) 의미)", () => {
  it("golden → Character → 재직렬화가 golden과 동일 (라운드트립 안정)", () => {
    const golden = loadGolden<string, Record<string, unknown>>("save_character")[0];
    const char = deserializeCharacter(golden.expected!);
    expect(serializeCharacter(char)).toEqual(golden.expected);
  });

  it("deserialize(serialize(c))는 원본과 동치", () => {
    const c = sampleChar();
    const back = deserializeCharacter(serializeCharacter(c));
    expect(serializeCharacter(back)).toEqual(serializeCharacter(c));
  });

  it("레거시 flat 필드는 기본값으로 채움 (personality_code는 저장 안 함)", () => {
    const golden = loadGolden<string, Record<string, unknown>>("save_character")[0];
    const char = deserializeCharacter(golden.expected!);
    expect(char.food_preferences).toEqual({});
    expect(char.clothing_preferences).toEqual({});
    expect(char.mini_personality).toEqual([]);
    // personality_code는 Character 인터페이스에 없음 (런타임 계산)
    expect(char).not.toHaveProperty("personality_code");
  });

  it("누락 섹션은 default로 채움 (id/profile만 줘도 복원)", () => {
    const char = deserializeCharacter({ id: 9, profile: { name: "최소" } });
    expect(char.id).toBe(9);
    expect(char.profile.name).toBe("최소");
    expect(char.state.satisfaction).toBe(50); // defaultCharacterState
    expect(char.customizable.songs.length).toBe(8);
  });
});
