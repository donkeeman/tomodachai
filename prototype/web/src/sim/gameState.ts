// Python src/tomodachai/game_state.py 미러 — 한 게임 세션의 단일 진실원.
//
// 의존성(LlmClient/SimRng/nowFn)은 주입형 seam. Python은 GameState 내부에서
// LLMClient(config.llm)를 직접 생성하지만, sim 모듈을 프레임워크 무의존으로 유지하기
// 위해 클라이언트(Ollama LlmClient)와 RNG, 시각을 외부에서 주입한다.

import type { AppConfig } from "./config";
import { makeDefaultConfig } from "./config";
import type { Character } from "./character";
import type { LlmClient } from "../llm";
import type { SimRng } from "./rng";
import type { PersonalityType } from "./personalityType";
import { loadPersonalities } from "./personalityType";
import { LocationManager } from "./location";
import { NewsManager } from "./news";
import { ShopManager } from "./shop";
import { FountainManager } from "./fountain";
import { GameClock } from "./clock";
import { Simulation } from "./simulation";
import type { SimEvent, CatchupEvent } from "./simulation";
import type { RelationshipTracker } from "./relationshipTracker";
import type { MemoryStore } from "./memory";

export interface Catalog {
  food: number[];
  clothing: number[];
  interior: number[];
  treasure: number[];
}
export type CatalogCategory = keyof Catalog;

export interface ConnectResult {
  offline_hours: number;
  catchup_events: CatchupEvent[];
  time_period: string;
  is_new_day: boolean;
}

export interface GameStateDeps {
  llm: LlmClient;
  rng: SimRng;
  nowFn?: () => Date;
}

export interface GameStateInit {
  config?: AppConfig;
  islandName?: string;
  dayCount?: number;
  money?: number;
  timeFlip?: boolean;
}

// game.json §1 카탈로그 카테고리 (frozenset 미러)
const CATALOG_CATEGORIES = new Set<string>(["food", "clothing", "interior", "treasure"]);
// Python f-string이 sorted(list)를 그대로 repr하므로 에러 메시지도 동일 포맷 유지.
const CATEGORY_ERR_LIST = "['clothing', 'food', 'interior', 'treasure']";

/** Python round(x, 2) 근사 — 실시간 차이값 파생이라 비트일치 비보장(허용). */
function round2(x: number): number {
  return Math.round(x * 100) / 100;
}

/**
 * 개인 방 등록용 int ID. Python: `id if isinstance(id, int) else abs(hash(id)) % 100000`.
 * Python hash()는 실행마다 salt가 달라 str 경로 자체가 비결정적 → 이식 불가.
 * 게임은 int id만 쓰므로(게임_state.py 주석 "int ID만 지원") number 경로만 충실 포팅,
 * str은 결정론 폴백만 제공(Python과 값 불일치 허용).
 */
function privateRoomId(id: number | string): number {
  if (typeof id === "number") return id;
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0;
  return Math.abs(h) % 100000;
}

export class GameState {
  config: AppConfig;
  readonly personalities: Record<string, PersonalityType>;
  characters: Character[] = [];

  // 게임 레벨 상태 (save 직렬화 대상 — snake_case 유지)
  island_name: string;
  day_count: number;
  money: number;
  time_flip: boolean;
  ending_credit_seen = false;
  catalog: Catalog = { food: [], clothing: [], interior: [], treasure: [] };

  readonly location_manager: LocationManager;
  readonly news: NewsManager;
  readonly shop: ShopManager;
  readonly fountain: FountainManager;
  last_online: Date;

  private readonly llm: LlmClient;
  private readonly rng: SimRng;
  private readonly _clock: GameClock;
  private _simulation: Simulation | null = null;

  constructor(deps: GameStateDeps, init: GameStateInit = {}) {
    this.config = init.config ?? makeDefaultConfig();
    this.personalities = loadPersonalities();
    this.island_name = init.islandName ?? "우리 마을";
    this.day_count = init.dayCount ?? 0;
    this.money = init.money ?? 0;
    this.time_flip = init.timeFlip ?? false;

    this.llm = deps.llm;
    this.rng = deps.rng;

    this.location_manager = new LocationManager();
    this.news = new NewsManager();
    this.shop = new ShopManager();
    this.fountain = new FountainManager();

    this._clock = new GameClock(this.time_flip, deps.nowFn);
    this.last_online = this._clock.now();
  }

  // ------------------------------------------------------------------
  // 캐릭터 관리
  // ------------------------------------------------------------------

  addCharacter(char: Character): Character {
    if (this.characters.some((c) => c.id === char.id)) {
      throw new Error(`Character with id '${char.id}' already exists`);
    }
    this.characters.push(char);
    this._simulation = null; // 무효화
    this.location_manager.registerPrivateRoom(privateRoomId(char.id), char.profile.name);
    return char;
  }

  getCharacter(charId: number | string): Character | null {
    return this.characters.find((c) => c.id === charId) ?? null;
  }

  removeCharacter(charId: number | string): boolean {
    const before = this.characters.length;
    this.characters = this.characters.filter((c) => c.id !== charId);
    if (this.characters.length < before) {
      this._simulation = null;
      this.location_manager.removeCharacter(privateRoomId(charId));
      return true;
    }
    return false;
  }

  // ------------------------------------------------------------------
  // 경제 헬퍼
  // ------------------------------------------------------------------

  /** 양수 금액 추가. 음수면 throw (차감은 spendMoney). */
  addMoney(amount: number): void {
    if (amount < 0) {
      throw new Error("amount must be non-negative; use spend_money to deduct");
    }
    this.money += amount;
  }

  /** 금액 차감. 성공 시 true, 잔액 부족이면 false. 음수면 throw. */
  spendMoney(amount: number): boolean {
    if (amount < 0) {
      throw new Error("amount must be non-negative");
    }
    if (this.money < amount) {
      return false;
    }
    this.money -= amount;
    return true;
  }

  // ------------------------------------------------------------------
  // 카탈로그 헬퍼 (game.json §1)
  // ------------------------------------------------------------------

  /** category 아래에 item_id를 획득 기록. 이미 있으면 무시. */
  addToCatalog(category: string, itemId: number): void {
    if (!CATALOG_CATEGORIES.has(category)) {
      throw new Error(`Unknown catalog category '${category}'. Must be one of: ${CATEGORY_ERR_LIST}`);
    }
    const list = this.catalog[category as CatalogCategory];
    if (!list.includes(itemId)) {
      list.push(itemId);
    }
  }

  /** category에서 item_id를 전에 획득했으면 true. */
  isInCatalog(category: string, itemId: number): boolean {
    if (!CATALOG_CATEGORIES.has(category)) {
      throw new Error(`Unknown catalog category '${category}'. Must be one of: ${CATEGORY_ERR_LIST}`);
    }
    return this.catalog[category as CatalogCategory].includes(itemId);
  }

  // ------------------------------------------------------------------
  // 시뮬레이션 접근
  // ------------------------------------------------------------------

  get simulation(): Simulation {
    if (this._simulation === null) {
      this._simulation = new Simulation(
        this.config,
        this.characters,
        this.llm,
        this.personalities,
        this.rng,
      );
    }
    return this._simulation;
  }

  get relationships(): RelationshipTracker {
    return this.simulation.relationships;
  }

  get memory(): MemoryStore {
    return this.simulation.memory;
  }

  // ------------------------------------------------------------------
  // 실시간 인터페이스
  // ------------------------------------------------------------------

  /** 실시간 단일 이벤트 스텝. */
  async step(): Promise<SimEvent[]> {
    if (this.characters.length === 0) return [];
    this.touch();
    return this.simulation.step();
  }

  /** 접속 시각 갱신. */
  touch(): void {
    this.last_online = this._clock.now();
  }

  /** 재접속 처리: 오프라인 기간 계산 후 catch-up 이벤트 생성. */
  connect(): ConnectResult {
    const nowUtc = this._clock.now();
    const offlineHours = (nowUtc.getTime() - this.last_online.getTime()) / 3_600_000;
    const isNewDay = this._clock.isNewDay(this.last_online);

    let catchupEvents: CatchupEvent[] = [];
    if (offlineHours >= 5.0 / 60.0 && this.characters.length > 0) {
      // 최소 5분 이상
      catchupEvents = this.simulation.generateCatchupEvents(offlineHours);
      if (isNewDay) {
        this.day_count += 1;
      }
    }

    this.last_online = nowUtc;

    return {
      offline_hours: round2(offlineHours),
      catchup_events: catchupEvents,
      time_period: this._clock.getTimePeriod(),
      is_new_day: isNewDay,
    };
  }

  get currentTimePeriod(): string {
    return this._clock.getTimePeriod();
  }

  get currentGameHour(): number {
    return this._clock.getGameHour();
  }
}
