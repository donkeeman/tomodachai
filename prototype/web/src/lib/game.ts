// 인-프로세스 게임 런타임(app 레이어) — sim 코어를 브라우저 의존성(localStorage/Math.random)과
// 엮는 곳. sim/* 는 프레임워크 무의존(주입형 seam)으로 유지하고, 여기서 구체 구현을 주입한다.
//
// 현재는 "정적 read-path": 생성한 캐릭터가 마을에 등장/배치되어 보이는 것까지. step()/LLM 은
// 미구동(Ollama 비의존, 결정론). 이동/대화/이벤트는 후속.
import type { Snapshot, Character, Rankings } from "./types";
import type { Character as SimCharacter } from "../sim/character";
import { defaultCharacter } from "../sim/character";
import { GameState } from "../sim/gameState";
import { GameClock } from "../sim/clock";
import type { SimRng } from "../sim/rng";
import type { LlmClient } from "../llm";
import { serializeCharacter, deserializeCharacter } from "../sim/save";
import { DEFAULT_LOCATIONS } from "../sim/location";
import type { AvatarLook } from "./appearance";
import { applyLook, characterLook } from "./lookAppearance";
import { setPersona } from "./personality";

// 캐릭터 생성 페이로드 — UI(CharacterCreate)가 만들어 createCharacter 로 전달.
export interface CreatePayload {
  id: number;
  name: string;
  gender: string;
  personality_code: string;
  personality?: Record<string, number>; // 슬라이더 원본(movement/speech/expressiveness/attitude/overall, 0~10)
  speech_habits: Record<string, string>;
  favorite_color: string;
  birthday?: string;        // "MM-DD"
  blood_type?: string;
  voice?: { preset: string; pitch: number; speed: number }; // 0~10
  appearance?: AvatarLook;
  location?: string;
}

// 소비자(Card/Toolbar/BubbleBox)가 .error/.messages 를 읽으므로 그 형태를 유지.
type ActionResult = { error?: string; messages?: string[]; message: string; [k: string]: unknown };

const NEW_CHAR_LOCATION = "plaza"; // 신규 캐릭터 기본 등장 위치(광장)
const SLEEP_START_MIN = 23 * 60 - 5; // 22:55
const WAKE_MIN = 7 * 60; // 07:00
const STORE_KEY = "tomodachai.game.v1";
const EMPTY_RANKINGS: Rankings = { best_couple: [], popular_m: [], popular_f: [], fighters: [] };

// ---------------------------------------------------------------------------
// 주입 의존성: 브라우저 RNG + LLM 스텁(정적 경로는 호출 안 됨)
// ---------------------------------------------------------------------------

const browserRng: SimRng = {
  random: () => Math.random(),
  shuffle<T>(arr: T[]): void {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
  },
  choice<T>(arr: readonly T[]): T {
    if (arr.length === 0) throw new Error("Cannot choose from an empty sequence");
    return arr[Math.floor(Math.random() * arr.length)];
  },
  sample<T>(arr: readonly T[], k: number): T[] {
    if (k > arr.length) throw new Error("Sample larger than population");
    const copy = [...arr];
    this.shuffle(copy);
    return copy.slice(0, k);
  },
  uniform: (a: number, b: number) => a + Math.random() * (b - a),
};

// 정적 read-path 는 simulation.step()/LLM 을 호출하지 않는다. 실수로 호출되면 즉시 드러나도록 throw.
const noLlm: LlmClient = {
  chatJson() {
    return Promise.reject(new Error("LLM 비활성(정적 read-path): step 구동은 후속 Phase"));
  },
};

// ---------------------------------------------------------------------------
// 싱글톤 GameState + 영속
// ---------------------------------------------------------------------------

let _state: GameState | null = null;

function gs(): GameState {
  if (_state === null) {
    _state = new GameState({ llm: noLlm, rng: browserRng });
    loadPersisted(_state);
  }
  return _state;
}

interface PersistShape {
  characters: Record<string, unknown>[];
  day_count: number;
  money: number;
}

function loadPersisted(state: GameState): void {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (!raw) return;
    const data = JSON.parse(raw) as PersistShape;
    state.day_count = data.day_count ?? state.day_count;
    state.money = data.money ?? state.money;
    for (const cd of data.characters ?? []) {
      try {
        state.addCharacter(deserializeCharacter(cd));
      } catch {
        /* 중복/손상 캐릭터는 건너뜀 */
      }
    }
  } catch {
    /* 손상된 저장은 무시하고 빈 마을로 시작 */
  }
}

function persist(state: GameState): void {
  try {
    const data: PersistShape = {
      characters: state.characters.map(serializeCharacter),
      day_count: state.day_count,
      money: state.money,
    };
    localStorage.setItem(STORE_KEY, JSON.stringify(data));
  } catch {
    /* 저장 실패(용량/프라이빗 모드)는 무시 — 메모리 상태는 유지 */
  }
}

// ---------------------------------------------------------------------------
// read-path: GameState → Snapshot
// ---------------------------------------------------------------------------

// 모든 앵커 라벨(id → 이름) — village 가 위치 라벨로 사용.
const LOCATION_LABELS: Record<string, string> = Object.fromEntries(
  DEFAULT_LOCATIONS.map((l) => [l.id, l.name]),
);

function toLeanCharacter(c: SimCharacter): Character {
  const st = c.state;
  return {
    id: typeof c.id === "number" ? c.id : 0,
    name: c.profile.name,
    gender: c.profile.gender === "F" ? "F" : "M",
    location: st.current_location || NEW_CHAR_LOCATION,
    mood: { happiness: st.mood.happiness, energy: st.mood.energy, stress: st.mood.stress },
    hunger: st.hunger,
    satisfaction: st.satisfaction,
    lover: null,
    best_friend: null,
    enemy: null,
    crushes: [],
    food_eaten: [],
    friends: [],
    dex: [],
    look: characterLook(c),
  };
}

export async function getSnapshot(_since: number): Promise<Snapshot> {
  const state = gs();
  const clock = new GameClock(state.time_flip);
  const now = clock.now();
  const hour = clock.getGameHour();
  const minute = now.getUTCMinutes();
  const minutes = hour * 60 + minute;
  const clockStr = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
  return {
    village: state.island_name,
    provider: "ollama",
    day: state.day_count || 1,
    clock: clockStr,
    minutes,
    seq: 0, // 정적 경로 — 이벤트 없음(폴링 커서 고정)
    locations: LOCATION_LABELS,
    foods: [],
    rankings: EMPTY_RANKINGS,
    asleep: minutes >= SLEEP_START_MIN || minutes < WAKE_MIN,
    realtime: true,
    photos: [],
    dishes: [],
    characters: state.characters.map(toLeanCharacter),
    events: [],
    bubbles: [],
  };
}

// ---------------------------------------------------------------------------
// 액션
// ---------------------------------------------------------------------------

export async function createCharacter(p: CreatePayload): Promise<ActionResult> {
  const state = gs();
  const char = defaultCharacter(p.id, p.name);
  char.profile.birthday = p.birthday ?? "";
  char.profile.blood_type = p.blood_type ?? "";
  char.profile.gender = p.gender;
  char.profile.favorite_color = p.favorite_color;
  if (p.appearance) applyLook(char, p.appearance); // 외모(+ gender/favorite_color) 정본 반영
  char.state.current_location = p.location ?? NEW_CHAR_LOCATION;

  state.addCharacter(char);
  if (p.personality_code) setPersona(p.id, p.personality_code); // 모션 연동(persona 는 별도 store)
  persist(state);
  return { message: "ok", id: p.id };
}

// 정적 경로 미구현 액션 — 소비자 호출 시그니처를 유지하는 노옵(실제 메커닉은 후속 Phase).
export const feed = (_charId: number, _foodId: number): Promise<ActionResult> =>
  Promise.resolve({ message: "" });
export const give = (_charId: number, _tool: string): Promise<ActionResult> =>
  Promise.resolve({ message: "" });
export const answerBubble = (_index: number, _char: string, _allow: boolean): Promise<ActionResult> =>
  Promise.resolve({ message: "" });

export async function saveGame(): Promise<ActionResult> {
  persist(gs());
  return { message: "saved" };
}

export async function resetGame(): Promise<ActionResult> {
  _state = null;
  try {
    localStorage.removeItem(STORE_KEY);
  } catch {
    /* 무시 */
  }
  return { message: "reset" };
}
