import { describe, it, expect, vi } from "vitest";
import { defaultCharacter } from "./character";
import { GameState, type GameStateDeps } from "./gameState";
import type { Msg, LlmClient } from "../llm";
import type { SimRng } from "./rng";
import { SaveManager, type SaveFs } from "./save";

// ────────────────────────────────────────────────────────────────────────────
// 인메모리 SaveFs stub — Python Path/shutil 의미 재현(JSON 클론, 재귀 remove/rename).
// ────────────────────────────────────────────────────────────────────────────
class MemoryFs implements SaveFs {
  files = new Map<string, unknown>();
  dirs = new Set<string>();

  private clone<T>(v: T): T {
    return JSON.parse(JSON.stringify(v));
  }
  private registerParents(path: string): void {
    const parts = path.split("/");
    for (let i = 1; i < parts.length; i++) this.dirs.add(parts.slice(0, i).join("/"));
  }

  exists(path: string): boolean {
    if (this.files.has(path) || this.dirs.has(path)) return true;
    const prefix = path + "/";
    for (const k of this.files.keys()) if (k.startsWith(prefix)) return true;
    for (const d of this.dirs) if (d.startsWith(prefix)) return true;
    return false;
  }
  readJson(path: string): unknown {
    if (!this.files.has(path)) throw new Error(`ENOENT: ${path}`);
    return this.clone(this.files.get(path));
  }
  writeJson(path: string, data: unknown): void {
    this.registerParents(path);
    this.files.set(path, this.clone(data));
  }
  mkdirp(path: string): void {
    this.dirs.add(path);
    this.registerParents(path);
  }
  remove(path: string): void {
    const prefix = path + "/";
    for (const k of [...this.files.keys()]) {
      if (k === path || k.startsWith(prefix)) this.files.delete(k);
    }
    for (const d of [...this.dirs]) {
      if (d === path || d.startsWith(prefix)) this.dirs.delete(d);
    }
  }
  rename(src: string, dst: string): void {
    const prefix = src + "/";
    for (const k of [...this.files.keys()]) {
      if (k === src || k.startsWith(prefix)) {
        this.files.set(dst + k.slice(src.length), this.files.get(k));
        this.files.delete(k);
      }
    }
    for (const d of [...this.dirs]) {
      if (d === src || d.startsWith(prefix)) {
        this.dirs.add(dst + d.slice(src.length));
        this.dirs.delete(d);
      }
    }
    this.registerParents(dst);
  }
  listJsonFiles(dir: string): string[] {
    const prefix = dir + "/";
    const out: string[] = [];
    for (const k of this.files.keys()) {
      if (k.startsWith(prefix)) {
        const rest = k.slice(prefix.length);
        if (!rest.includes("/") && rest.endsWith(".json")) out.push(rest);
      }
    }
    return out;
  }
}

class StubLlm implements LlmClient {
  async chatJson(_m: Msg[]): Promise<Record<string, unknown>> {
    return { dialogue: [], deltas: {}, summary: "" };
  }
}
class StubRng implements SimRng {
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
    return 0;
  }
}
function deps(): GameStateDeps {
  return { llm: new StubLlm(), rng: new StubRng() };
}
function makeManager(fs: MemoryFs, now = "2026-06-24T10:00:00+00:00"): SaveManager {
  return new SaveManager({ fs, gameStateDeps: deps(), nowFn: () => now });
}

// 풍부한 GameState 픽스처 (캐릭터/관계/이벤트/머니/카탈로그).
function richGame(): GameState {
  const gs = new GameState(deps(), { islandName: "별빛마을", dayCount: 4, money: 1200, timeFlip: true });
  gs.addCharacter(defaultCharacter(1, "아리"));
  gs.addCharacter(defaultCharacter(2, "보리"));
  gs.addToCatalog("food", 5);
  const r = gs.relationships.get(1, 2);
  r.friendship = 55;
  r.romance = 30;
  r.stage = "friend";
  gs.relationships.addFight({ participants: [1, 2], cause: "x", resolved: true, witnessed_by_player: false });
  gs.memory.addEvent({
    id: 1, type: "conversation", participants: [1, 2], day: 4,
    time: null, location: "공원", reason: null, result: null,
  });
  return gs;
}

describe("SaveManager 슬롯 검증", () => {
  it("1~3 밖이면 정확한 메시지로 throw (save/load/delete)", () => {
    const mgr = makeManager(new MemoryFs());
    const gs = richGame();
    expect(() => mgr.save(0, gs)).toThrow("slot must be between 1 and 3, got 0");
    expect(() => mgr.save(4, gs)).toThrow("slot must be between 1 and 3, got 4");
    expect(() => mgr.load(0)).toThrow("slot must be between 1 and 3, got 0");
    expect(() => mgr.deleteSlot(9)).toThrow("slot must be between 1 and 3, got 9");
  });
});

describe("SaveManager save/load 라운드트립", () => {
  it("저장 후 로드하면 게임 상태가 동등 복원", () => {
    const fs = new MemoryFs();
    const mgr = makeManager(fs);
    mgr.save(1, richGame());

    const gs = mgr.load(1);
    expect(gs.island_name).toBe("별빛마을");
    expect(gs.day_count).toBe(4);
    expect(gs.money).toBe(1200);
    expect(gs.time_flip).toBe(true);
    expect(gs.characters.map((c) => c.id).sort()).toEqual([1, 2]);
    // 관계 복원
    expect(gs.relationships.get(1, 2)).toEqual({ friendship: 55, romance: 30, stage: "friend" });
    expect(gs.relationships.allFightsRaw().length).toBe(1); // resolved 포함
    // 이벤트 복원
    expect(gs.memory.allEvents().length).toBe(1);
    expect(gs.memory.allEvents()[0].location).toBe("공원");
  });

  it("저장 파일 레이아웃: game/characters/{id}/events/relationships/meta", () => {
    const fs = new MemoryFs();
    makeManager(fs).save(2, richGame());
    expect(fs.exists("saves/slot_2/game.json")).toBe(true);
    expect(fs.exists("saves/slot_2/characters/1.json")).toBe(true);
    expect(fs.exists("saves/slot_2/characters/2.json")).toBe(true);
    expect(fs.exists("saves/slot_2/events.json")).toBe(true);
    expect(fs.exists("saves/slot_2/relationships.json")).toBe(true);
    expect(fs.exists("saves/slot_2/meta.json")).toBe(true);
    // game.json 내용
    expect(fs.readJson("saves/slot_2/game.json")).toEqual({
      island_name: "별빛마을", day_count: 4, money: 1200, time_flip: true,
    });
    // staging은 rename 후 사라짐
    expect(fs.exists("saves/slot_2.staging")).toBe(false);
  });

  it("없는 슬롯 로드는 throw", () => {
    expect(() => makeManager(new MemoryFs()).load(3)).toThrow("Save slot 3 does not exist");
  });
});

describe("SaveManager 메타/목록", () => {
  it("listSlots: 저장된 슬롯만 exists=true + 메타, nowFn 타임스탬프", () => {
    const fs = new MemoryFs();
    const mgr = makeManager(fs, "2026-06-24T12:00:00+00:00");
    mgr.save(2, richGame());

    const slots = mgr.listSlots();
    expect(slots.map((s) => s.exists)).toEqual([false, true, false]);
    const s2 = slots[1];
    expect(s2).toEqual({
      slot: 2, exists: true, island_name: "별빛마을", day_count: 4,
      last_saved: "2026-06-24T12:00:00+00:00",
    });
  });

  it("deleteSlot: 제거 후 listSlots에서 미존재, 미존재 슬롯 삭제는 no-op", () => {
    const fs = new MemoryFs();
    const mgr = makeManager(fs);
    mgr.save(1, richGame());
    expect(mgr.listSlots()[0].exists).toBe(true);
    mgr.deleteSlot(1);
    expect(mgr.listSlots()[0].exists).toBe(false);
    expect(() => mgr.deleteSlot(1)).not.toThrow(); // no-op
  });
});

describe("SaveManager 원자성/스테일 제거", () => {
  it("재저장 시 캐릭터 삭제분의 스테일 파일 제거", () => {
    const fs = new MemoryFs();
    const mgr = makeManager(fs);
    mgr.save(1, richGame()); // 캐릭터 1,2
    expect(fs.exists("saves/slot_1/characters/2.json")).toBe(true);

    const gs2 = richGame();
    gs2.removeCharacter(2); // 1만 남김
    mgr.save(1, gs2);
    expect(fs.exists("saves/slot_1/characters/1.json")).toBe(true);
    expect(fs.exists("saves/slot_1/characters/2.json")).toBe(false); // 스테일 제거됨
  });

  it("0 캐릭터 save/load: 빈 characters 디렉터리 처리, 무캐릭터 복원", () => {
    const fs = new MemoryFs();
    const mgr = makeManager(fs);
    const gs = new GameState(deps(), { islandName: "무인도", money: 0 });
    mgr.save(1, gs);
    expect(fs.exists("saves/slot_1/characters")).toBe(true); // mkdirp로 빈 디렉터리 존재
    const loaded = mgr.load(1);
    expect(loaded.characters.length).toBe(0);
    expect(loaded.island_name).toBe("무인도");
  });

  it("mid-write 예외(events.json) 시 staging 정리하고 기존 슬롯 보존", () => {
    const fs = new MemoryFs();
    const mgr = makeManager(fs);
    mgr.save(1, richGame());
    const original = fs.readJson("saves/slot_1/game.json");

    // game.json/characters는 기록되고 events.json 단계에서 실패 → staging 부분 존재
    const spy = vi.spyOn(fs, "writeJson").mockImplementation((path: string, data: unknown) => {
      if (path.endsWith("events.json")) throw new Error("disk full");
      MemoryFs.prototype.writeJson.call(fs, path, data);
    });
    expect(() => mgr.save(1, richGame())).toThrow("disk full");
    spy.mockRestore();

    expect(fs.exists("saves/slot_1.staging")).toBe(false); // 부분 staging 정리됨
    expect(fs.readJson("saves/slot_1/game.json")).toEqual(original); // 기존 보존
  });

  it("writeSlot 중 예외 시 staging 정리하고 기존 슬롯 보존", () => {
    const fs = new MemoryFs();
    const mgr = makeManager(fs);
    mgr.save(1, richGame());
    const original = fs.readJson("saves/slot_1/game.json");

    // writeJson이 특정 경로에서 실패하도록 강제
    const spy = vi.spyOn(fs, "writeJson").mockImplementationOnce(() => {
      throw new Error("disk full");
    });
    expect(() => mgr.save(1, richGame())).toThrow("disk full");
    spy.mockRestore();

    expect(fs.exists("saves/slot_1.staging")).toBe(false); // staging 정리됨
    expect(fs.readJson("saves/slot_1/game.json")).toEqual(original); // 기존 보존
  });
});

describe("SaveManager 손상 캐릭터 파일 건너뛰기", () => {
  it("깨진 캐릭터 json은 경고 후 스킵, 나머지는 로드", () => {
    const fs = new MemoryFs();
    const mgr = makeManager(fs);
    mgr.save(1, richGame());
    // 2.json을 역직렬화 불가 형태로 오염 (profile.name 접근 시 throw 유도용 대신
    // deserialize는 관대하므로, addCharacter 중복 id 충돌로 throw 유발)
    fs.writeJson("saves/slot_1/characters/2.json", { id: 1, profile: { name: "중복" } });
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

    const gs = mgr.load(1);
    // 1.json(정상) + 2.json(id=1 중복 → addCharacter throw → 스킵)
    expect(gs.characters.map((c) => c.id)).toEqual([1]);
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });
});

describe("SaveManager temp(크래시 복구)", () => {
  it("saveTemp/hasTempSave/loadTemp/clearTemp 라이프사이클", () => {
    const fs = new MemoryFs();
    const mgr = makeManager(fs);
    expect(mgr.hasTempSave()).toBe(false);
    expect(() => mgr.loadTemp()).toThrow("No crash-recovery save found");

    mgr.saveTemp(richGame());
    expect(mgr.hasTempSave()).toBe(true);
    expect(fs.exists("saves/_temp/game.json")).toBe(true);

    const gs = mgr.loadTemp();
    expect(gs.island_name).toBe("별빛마을");
    expect(gs.characters.length).toBe(2);

    mgr.clearTemp();
    expect(mgr.hasTempSave()).toBe(false);
  });
});
