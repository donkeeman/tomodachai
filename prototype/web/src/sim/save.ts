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
import type { BreakupReason, RelationshipStage } from "./relationship";
import { RelationshipTracker } from "./relationshipTracker";
import { MemoryStore, type SocialEvent } from "./memory";
import { GameState, type GameStateDeps } from "./gameState";

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

// ---------------------------------------------------------------------------
// 직렬화 — RelationshipTracker (pairs/slots/ex_lover_tags/fights 전체)
// ---------------------------------------------------------------------------

/** Python _serialize_relationships — 내부 저장 전체를 단일 dict로. fights는 해결분 포함 전체. */
export function serializeRelationships(tracker: RelationshipTracker): Record<string, unknown> {
  const pairs: Record<string, unknown> = {};
  for (const [a, b, rel] of tracker.allPairs()) {
    pairs[`${a}:${b}`] = { friendship: rel.friendship, romance: rel.romance, stage: rel.stage };
  }

  const slots: Record<string, unknown> = {};
  for (const [charId, sl] of tracker.allSlots()) {
    slots[String(charId)] = { best_friend: sl.best_friend, lover: sl.lover, enemy: sl.enemy };
  }

  const ex_lover_tags: Record<string, unknown> = {};
  for (const [charId, tags] of tracker.allExLoverTags()) {
    ex_lover_tags[String(charId)] = tags.map((t) => ({
      target: t.target,
      reason: t.reason,
      day: t.day,
    }));
  }

  const fights = tracker.allFightsRaw().map((f) => ({
    participants: [f.participants[0], f.participants[1]],
    cause: f.cause,
    resolved: f.resolved,
    witnessed_by_player: f.witnessed_by_player,
  }));

  return { pairs, slots, ex_lover_tags, fights };
}

/**
 * 직렬화 데이터를 기존 tracker에 in-place 적용. load 시 GameState의 live tracker
 * (Simulation.relationships readonly)에 직접 주입하기 위해 분리.
 * pair 키 "a:b"(콜론) split, slots/fights 누락 필드는 Python .get default(null/false) 미러.
 * pairs는 get()으로 default 생성 후 in-place 세팅(저장 참조 유지).
 */
export function applyRelationshipsInto(
  tracker: RelationshipTracker,
  data: Record<string, unknown>,
): void {
  const pairs = (data.pairs ?? {}) as Record<string, { friendship: number; romance: number; stage: string }>;
  for (const [key, relData] of Object.entries(pairs)) {
    const [aStr, bStr] = key.split(":");
    const rel = tracker.get(Number(aStr), Number(bStr));
    rel.friendship = relData.friendship;
    rel.romance = relData.romance;
    rel.stage = relData.stage as RelationshipStage;
  }

  const slots = (data.slots ?? {}) as Record<
    string,
    { best_friend?: number | null; lover?: number | null; enemy?: number | null }
  >;
  for (const [charIdStr, slData] of Object.entries(slots)) {
    const sl = tracker.getSlots(Number(charIdStr));
    sl.best_friend = slData.best_friend ?? null;
    sl.lover = slData.lover ?? null;
    sl.enemy = slData.enemy ?? null;
  }

  const exTags = (data.ex_lover_tags ?? {}) as Record<
    string,
    { target: number; reason: string; day: number }[]
  >;
  for (const [charIdStr, tags] of Object.entries(exTags)) {
    const charId = Number(charIdStr);
    for (const t of tags) {
      tracker.addExLoverTag(charId, t.target, t.reason as BreakupReason, t.day);
    }
  }

  const fights = (data.fights ?? []) as {
    participants: number[];
    cause: string;
    resolved?: boolean;
    witnessed_by_player?: boolean;
  }[];
  for (const f of fights) {
    tracker.addFight({
      participants: [f.participants[0], f.participants[1]],
      cause: f.cause,
      resolved: f.resolved ?? false,
      witnessed_by_player: f.witnessed_by_player ?? false,
    });
  }
}

/** Python _deserialize_relationships — 새 tracker에 복원. */
export function deserializeRelationships(data: Record<string, unknown>): RelationshipTracker {
  const tracker = new RelationshipTracker();
  applyRelationshipsInto(tracker, data);
  return tracker;
}

// ---------------------------------------------------------------------------
// 직렬화 — MemoryStore (events 전체, None 필드 조건부 생략)
// ---------------------------------------------------------------------------

/** Python _serialize_events — 전체 이벤트, time/location/reason/result는 null이면 키 생략. */
export function serializeEvents(memory: MemoryStore): Record<string, unknown>[] {
  return memory.allEvents().map((e) => {
    const item: Record<string, unknown> = {
      id: e.id,
      type: e.type,
      participants: e.participants,
      day: e.day,
    };
    if (e.time !== null) item.time = e.time;
    if (e.location !== null) item.location = e.location;
    if (e.reason !== null) item.reason = e.reason;
    if (e.result !== null) item.result = e.result;
    return item;
  });
}

/**
 * 직렬화 데이터를 기존 store에 add_event로 적용. load 시 GameState의 live memory
 * (Simulation.memory readonly)에 직접 주입하기 위해 분리.
 * 생략된 필드는 null(SocialEvent 기본값). id≠0이라 add_event가 id 보존.
 */
export function applyEventsInto(store: MemoryStore, data: Record<string, unknown>[]): void {
  for (const item of data) {
    const e: SocialEvent = {
      id: item.id as number,
      type: item.type as string,
      participants: item.participants as number[],
      day: item.day as number,
      time: (item.time as string | undefined) ?? null,
      location: (item.location as string | undefined) ?? null,
      reason: (item.reason as string | undefined) ?? null,
      result: (item.result as string | undefined) ?? null,
    };
    store.addEvent(e);
  }
}

/** Python _deserialize_events — 새 MemoryStore에 add_event로 복원. */
export function deserializeEvents(data: Record<string, unknown>[]): MemoryStore {
  const store = new MemoryStore();
  applyEventsInto(store, data);
  return store;
}

// ===========================================================================
// SaveManager — 슬롯 관리. 파일시스템은 주입형 SaveFs seam(Tauri fs는 후속).
// 결정론 로직(슬롯검증/원자적 조립/스테일 제거/메타)만 단위검증, 시각=주입 nowFn.
// ===========================================================================

export const NUM_SLOTS = 3;
const TEMP_DIR = "_temp";
const META_FILE = "meta.json";

/** Python SlotInfo(pydantic) 미러. */
export interface SlotInfo {
  slot: number;
  exists: boolean;
  island_name: string;
  day_count: number;
  last_saved: string; // ISO 8601
}

/**
 * 파일시스템 추상화 seam. Python의 Path/shutil 연산을 주입형으로 대체.
 * 경로는 "/" 구분 문자열. 구현(실 Tauri fs / 인메모리 stub)이 JSON 포맷·원자성을 담당.
 */
export interface SaveFs {
  exists(path: string): boolean;
  /** 누락 시 throw. */
  readJson(path: string): unknown;
  /** 부모 디렉터리 자동 생성(Python _write_json의 parent.mkdir). */
  writeJson(path: string, data: unknown): void;
  /** 디렉터리 생성(parents=True, exist_ok=True). */
  mkdirp(path: string): void;
  /** 파일/디렉터리 재귀 삭제. 없으면 no-op(Python rmtree/unlink missing_ok). */
  remove(path: string): void;
  rename(src: string, dst: string): void;
  /** dir의 직속 *.json 파일 base 이름 목록. dir 없으면 []. */
  listJsonFiles(dir: string): string[];
}

function joinPath(...parts: string[]): string {
  return parts.join("/");
}

/** "1.json" → "1" (Python Path.stem). */
function jsonStem(name: string): string {
  return name.replace(/\.json$/, "");
}

export interface SaveManagerDeps {
  fs: SaveFs;
  /** load로 GameState 재구성 시 주입(llm/rng/nowFn). */
  gameStateDeps: GameStateDeps;
  /** 메타의 last_saved 타임스탬프(ISO). Python datetime.now(utc).isoformat() 대체 seam. */
  nowFn: () => string;
  /** 세이브 루트. 기본 "saves". */
  saveDir?: string;
}

export class SaveManager {
  private readonly fs: SaveFs;
  private readonly gameStateDeps: GameStateDeps;
  private readonly nowFn: () => string;
  readonly saveDir: string;

  constructor(deps: SaveManagerDeps) {
    this.fs = deps.fs;
    this.gameStateDeps = deps.gameStateDeps;
    this.nowFn = deps.nowFn;
    this.saveDir = deps.saveDir ?? "saves";
  }

  // ---- 경로/검증 -----------------------------------------------------------

  private static validateSlot(slot: number): void {
    if (slot < 1 || slot > NUM_SLOTS) {
      throw new Error(`slot must be between 1 and ${NUM_SLOTS}, got ${slot}`);
    }
  }

  private slotDir(slot: number): string {
    SaveManager.validateSlot(slot);
    return joinPath(this.saveDir, `slot_${slot}`);
  }

  private tempDir(): string {
    return joinPath(this.saveDir, TEMP_DIR);
  }

  // ---- 코어 조립/복원 ------------------------------------------------------

  /** slot_dir에 game.json/characters/events.json/relationships.json 기록. */
  private writeSlot(dir: string, gs: GameState): void {
    // 1. game.json
    this.fs.writeJson(joinPath(dir, "game.json"), {
      island_name: gs.island_name,
      day_count: gs.day_count,
      money: gs.money,
      time_flip: gs.time_flip,
    });

    // 2. characters/ — 사라진 캐릭터의 스테일 파일 제거 후 기록
    const charsDir = joinPath(dir, "characters");
    this.fs.mkdirp(charsDir);
    const existing = new Set(gs.characters.map((c) => String(c.id)));
    for (const f of this.fs.listJsonFiles(charsDir)) {
      if (!existing.has(jsonStem(f))) {
        this.fs.remove(joinPath(charsDir, f));
      }
    }
    for (const char of gs.characters) {
      this.fs.writeJson(joinPath(charsDir, `${char.id}.json`), serializeCharacter(char));
    }

    // 3. events.json
    this.fs.writeJson(joinPath(dir, "events.json"), serializeEvents(gs.memory));

    // 4. relationships.json
    this.fs.writeJson(joinPath(dir, "relationships.json"), serializeRelationships(gs.relationships));
  }

  /** slot_dir에서 GameState 재구성. 손상 파일은 건너뛰고 중단하지 않음. */
  private readSlot(dir: string): GameState {
    // 1. game.json
    const gameData = this.fs.readJson(joinPath(dir, "game.json")) as Record<string, unknown>;
    const gs = new GameState(this.gameStateDeps, {
      islandName: (gameData.island_name as string | undefined) ?? "우리 마을",
      dayCount: (gameData.day_count as number | undefined) ?? 0,
      money: (gameData.money as number | undefined) ?? 0,
      timeFlip: (gameData.time_flip as boolean | undefined) ?? false,
    });

    // 2. characters/ — 정렬된 순서로, 손상 파일은 경고 후 건너뜀
    const charsDir = joinPath(dir, "characters");
    if (this.fs.exists(charsDir)) {
      for (const f of [...this.fs.listJsonFiles(charsDir)].sort()) {
        try {
          const charData = this.fs.readJson(joinPath(charsDir, f)) as Record<string, unknown>;
          gs.addCharacter(deserializeCharacter(charData));
        } catch (exc) {
          console.warn(`Skipping corrupted character file ${f}: ${exc}`);
        }
      }
    }

    // 3. events.json — live memory(Simulation.memory readonly)에 in-place 주입
    const eventsPath = joinPath(dir, "events.json");
    if (this.fs.exists(eventsPath)) {
      try {
        applyEventsInto(gs.memory, this.fs.readJson(eventsPath) as Record<string, unknown>[]);
      } catch (exc) {
        console.warn(`Could not restore events: ${exc}`);
      }
    }

    // 4. relationships.json — live tracker에 in-place 주입
    const relPath = joinPath(dir, "relationships.json");
    if (this.fs.exists(relPath)) {
      try {
        applyRelationshipsInto(gs.relationships, this.fs.readJson(relPath) as Record<string, unknown>);
      } catch (exc) {
        console.warn(`Could not restore relationships: ${exc}`);
      }
    }

    return gs;
  }

  /** staging에 기록 → 메타 → 원자적 교체(기존 제거 후 rename). 실패 시 staging 정리. */
  private writeAtomic(target: string, gs: GameState): void {
    const staging = `${target}.staging`;
    if (this.fs.exists(staging)) this.fs.remove(staging);
    try {
      this.writeSlot(staging, gs);
      this.fs.writeJson(joinPath(staging, META_FILE), {
        island_name: gs.island_name,
        day_count: gs.day_count,
        last_saved: this.nowFn(),
      });
      if (this.fs.exists(target)) this.fs.remove(target);
      this.fs.rename(staging, target);
    } catch (exc) {
      if (this.fs.exists(staging)) this.fs.remove(staging);
      throw exc;
    }
  }

  // ---- Public API ----------------------------------------------------------

  /** slot(1~NUM_SLOTS)에 저장. sibling staging 경유 원자적 기록. */
  save(slot: number, gs: GameState): void {
    SaveManager.validateSlot(slot);
    this.writeAtomic(this.slotDir(slot), gs);
  }

  /** slot에서 로드. 없으면 throw. */
  load(slot: number): GameState {
    SaveManager.validateSlot(slot);
    const dir = this.slotDir(slot);
    if (!this.fs.exists(dir)) {
      throw new Error(`Save slot ${slot} does not exist`);
    }
    return this.readSlot(dir);
  }

  /** 슬롯 1~NUM_SLOTS의 메타 정보. */
  listSlots(): SlotInfo[] {
    const result: SlotInfo[] = [];
    for (let slot = 1; slot <= NUM_SLOTS; slot++) {
      const dir = this.slotDir(slot);
      const metaPath = joinPath(dir, META_FILE);
      if (this.fs.exists(dir) && this.fs.exists(metaPath)) {
        try {
          const meta = this.fs.readJson(metaPath) as Record<string, unknown>;
          result.push({
            slot,
            exists: true,
            island_name: (meta.island_name as string | undefined) ?? "",
            day_count: (meta.day_count as number | undefined) ?? 0,
            last_saved: (meta.last_saved as string | undefined) ?? "",
          });
          continue;
        } catch {
          // 메타 손상 → 미존재로 처리
        }
      }
      result.push({ slot, exists: false, island_name: "", day_count: 0, last_saved: "" });
    }
    return result;
  }

  /** 슬롯 삭제. 없으면 no-op. */
  deleteSlot(slot: number): void {
    SaveManager.validateSlot(slot);
    const dir = this.slotDir(slot);
    if (this.fs.exists(dir)) this.fs.remove(dir);
  }

  // ---- Temp (크래시 복구) --------------------------------------------------

  saveTemp(gs: GameState): void {
    this.writeAtomic(this.tempDir(), gs);
  }

  hasTempSave(): boolean {
    return this.fs.exists(joinPath(this.tempDir(), "game.json"));
  }

  loadTemp(): GameState {
    if (!this.hasTempSave()) {
      throw new Error("No crash-recovery save found");
    }
    return this.readSlot(this.tempDir());
  }

  clearTemp(): void {
    const dir = this.tempDir();
    if (this.fs.exists(dir)) this.fs.remove(dir);
  }
}
