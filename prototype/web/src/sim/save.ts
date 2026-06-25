// Python src/tomodachai/save.py 직렬화 헬퍼 미러.
//
// _serialize_character는 model_dump이 아니라 손수 만든 중첩 dict("mock format").
// _deserialize_character는 Character(**data) — pydantic이 누락 필드를 deep-default로 채우고
// personality_code(런타임 계산)는 폐기한다. TS는 defaultCharacter 위에 deep-merge로 재현.

import {
  defaultCharacter,
  type AppearanceAdjust,
  type Character,
} from "./character";
import { characterPersonalityCode } from "./characterAccessors";

// ---------------------------------------------------------------------------
// 직렬화 — Character → char_{id}.json mock format
// ---------------------------------------------------------------------------

/** AppearanceAdjust 4필드 (eye/eyebrow용). Python _adj 1:1. */
function adj4(a: AppearanceAdjust): Record<string, number> {
  return { spacing: a.spacing, height: a.height, size: a.size, angle: a.angle };
}

/** Python _serialize_character — 중첩 dict 빌드. personality_code는 런타임 계산 포함. */
export function serializeCharacter(char: Character): Record<string, unknown> {
  const p = char.profile;
  const app = p.appearance;

  const appearance = {
    face_shape: app.face_shape,
    skin_color: app.skin_color,
    eye: {
      base: app.eye.base,
      lash: app.eye.lash,
      color: app.eye.color,
      adjust: adj4(app.eye.adjust),
    },
    eyebrow: {
      id: app.eyebrow.id,
      adjust: adj4(app.eyebrow.adjust),
    },
    nose: {
      id: app.nose.id,
      // nose/mouth adjust는 {height,size}만 (Python save.py 117/121).
      adjust: { height: app.nose.adjust.height, size: app.nose.adjust.size },
    },
    mouth: {
      id: app.mouth.id,
      adjust: { height: app.mouth.adjust.height, size: app.mouth.adjust.size },
    },
    hair: {
      front: app.hair.front,
      back: app.hair.back,
      color: app.hair.color,
    },
    glasses: app.glasses,
    body: { height: app.body.height, build: app.body.build },
  };

  const profile = {
    name: p.name,
    birthday: p.birthday,
    blood_type: p.blood_type,
    favorite_color: p.favorite_color,
    gender: p.gender,
    appearance,
    personality: {
      movement: p.personality.movement,
      speech: p.personality.speech,
      expressiveness: p.personality.expressiveness,
      attitude: p.personality.attitude,
      overall: p.personality.overall,
    },
    voice: {
      preset: p.voice.preset,
      pitch: p.voice.pitch,
      speed: p.voice.speed,
      quality: p.voice.quality,
      tone: p.voice.tone,
      accent: p.voice.accent,
      intonation: p.voice.intonation,
    },
  };

  const pref = char.preferences;
  const preferences = {
    food_ranks: pref.food_ranks,
    food_eaten: pref.food_eaten,
    clothing: { likes: pref.clothing.likes, dislikes: pref.clothing.dislikes },
    interior: { likes: pref.interior.likes, dislikes: pref.interior.dislikes },
    personality_group: {
      group: pref.personality_group.group,
      is_positive: pref.personality_group.is_positive,
    },
  };

  const st = char.state;
  const state = {
    satisfaction: st.satisfaction,
    level: st.level,
    hunger: st.hunger,
    mood: {
      happiness: st.mood.happiness,
      energy: st.mood.energy,
      stress: st.mood.stress,
    },
    sick: st.sick,
    current_location: st.current_location,
    current_outfit: st.current_outfit,
    current_interior: st.current_interior,
    photo_frame: st.photo_frame,
  };

  const cust = char.customizable;
  const sh = cust.speech_habits;
  const mt = cust.mini_traits;
  const customizable = {
    speech_habits: {
      normal: sh.normal,
      happy: sh.happy,
      angry: sh.angry,
      sad: sh.sad,
      worried: sh.worried,
    },
    mini_traits: {
      walking: { owned: mt.walking.owned, active: mt.walking.active },
      eating: { owned: mt.eating.owned, active: mt.eating.active },
      idle: { owned: mt.idle.owned, active: mt.idle.active },
    },
    nicknames: cust.nicknames,
    songs: cust.songs,
  };

  const rec = char.records;
  const records = {
    treasure_collection: rec.treasure_collection,
    confession_count: rec.confession_count,
    photos: rec.photos,
  };

  return {
    id: char.id,
    personality_code: characterPersonalityCode(char),
    profile,
    preferences,
    state,
    customizable,
    records,
  };
}

// ---------------------------------------------------------------------------
// 역직렬화 — char_{id}.json → Character (Character(**data) 의미)
// ---------------------------------------------------------------------------

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/**
 * base(기본값) 위에 patch를 deep-merge한 새 객체.
 * 둘 다 plain object면 키별 재귀, 그 외(배열/원시/null)는 patch로 교체.
 * pydantic이 누락 필드를 모델 default로 채우는 의미를 재현.
 */
function deepMerge(base: unknown, patch: unknown): unknown {
  if (!isPlainObject(base) || !isPlainObject(patch)) return patch;
  const out: Record<string, unknown> = { ...base };
  for (const key of Object.keys(patch)) {
    out[key] = key in base ? deepMerge(base[key], patch[key]) : patch[key];
  }
  return out;
}

/**
 * Python _deserialize_character = Character(**data).
 * defaultCharacter 위에 data를 deep-merge. personality_code(런타임 계산)는 폐기,
 * 레거시 flat 필드(food_preferences 등)는 default(빈값) 유지.
 */
export function deserializeCharacter(data: Record<string, unknown>): Character {
  const profile = data.profile as Record<string, unknown> | undefined;
  const name = (profile?.name as string | undefined) ?? "";

  // personality_code는 저장 대상 아님 — 병합 전에 제거 (Character 인터페이스에 없음).
  // base의 id(0)는 rest.id가 deep-merge로 덮어쓰므로 무관.
  const { personality_code: _ignored, ...rest } = data;

  return deepMerge(defaultCharacter(0, name), rest) as Character;
}
