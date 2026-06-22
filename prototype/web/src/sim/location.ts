/**
 * location.ts — Location 모델 + 장소 카탈로그
 *
 * Python src/tomodachai/location.py 의 Location 모델 + DEFAULT_LOCATIONS + _DEFAULT_PUBLIC_WEIGHTS 를 포팅.
 * LocationManager는 Task 2에서 구현.
 */

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

export type LocationType = "private_room" | "shared_room" | "public";

export interface Location {
  id: string;
  name: string;
  capacity: number;
  location_type: LocationType;
  event_types: string[];
  description: string;
}

// ────────────────────────────────────────────────────────────────────────────
// Factory
// ────────────────────────────────────────────────────────────────────────────

/** Python Location(BaseModel) 기본값과 동일한 팩토리 */
export function defaultLocation(partial: Partial<Location> & Pick<Location, "id" | "name">): Location {
  return {
    capacity: 6,
    location_type: "public",
    event_types: [],
    description: "",
    ...partial,
  };
}

// ────────────────────────────────────────────────────────────────────────────
// Default locations catalog (15개)
// _HOUSE_SHARED (2) + _PUBLIC_LOCATIONS (13)
// ────────────────────────────────────────────────────────────────────────────

export const DEFAULT_LOCATIONS: Location[] = [
  // _HOUSE_SHARED
  {
    id: "living_room",
    name: "거실",
    capacity: 10,
    location_type: "shared_room",
    event_types: ["chat", "tv", "minigame", "birthday_party"],
    description: "소파 수다, TV 시청, 여러 명 모임, 미니게임",
  },
  {
    id: "balcony",
    name: "발코니",
    capacity: 3,
    location_type: "shared_room",
    event_types: ["one_on_one_chat", "confession", "night_event", "contemplation"],
    description: "혼자 생각, 1:1 대화, 밤 이벤트, 고백 장소",
  },
  // _PUBLIC_LOCATIONS (13개)
  {
    id: "grocery",
    name: "식료품점",
    capacity: 4,
    location_type: "public",
    event_types: ["food_shopping", "morning_market"],
    description: "음식 구매",
  },
  {
    id: "clothing",
    name: "의류점",
    capacity: 3,
    location_type: "public",
    event_types: ["outfit_shopping"],
    description: "의상 구매",
  },
  {
    id: "interior",
    name: "인테리어점",
    capacity: 3,
    location_type: "public",
    event_types: ["room_decoration"],
    description: "방 꾸미기",
  },
  {
    id: "fountain",
    name: "분수대",
    capacity: 6,
    location_type: "public",
    event_types: ["donation", "morning_market", "rap_battle", "word_chain"],
    description: "모금, 아침 장터, 랩배틀, 끝말잇기",
  },
  {
    id: "news_station",
    name: "방송국",
    capacity: 2,
    location_type: "public",
    event_types: ["news_briefing"],
    description: "뉴스 브리핑",
  },
  {
    id: "park",
    name: "공원",
    capacity: 8,
    location_type: "public",
    event_types: ["walk", "bench_chat", "exercise", "picnic", "compatibility_check"],
    description: "야외 상호작용, 상성 진단, 랭킹 보드",
  },
  {
    id: "cafe",
    name: "카페",
    capacity: 4,
    location_type: "public",
    event_types: ["small_group_chat", "date"],
    description: "소규모 수다 (2~4명)",
  },
  {
    id: "beach",
    name: "해변",
    capacity: 5,
    location_type: "public",
    event_types: ["walk", "confession", "emotional_chat", "contemplation"],
    description: "감성 장소, 고백, 산책",
  },
  {
    id: "plaza",
    name: "광장",
    capacity: 24,
    location_type: "public",
    event_types: ["large_gathering", "vote", "performance", "announcement"],
    description: "대규모 모임, 투표, 공연",
  },
  {
    id: "concert_hall",
    name: "콘서트홀",
    capacity: 24,
    location_type: "public",
    event_types: ["solo_performance", "duet", "group_performance", "audience_reaction"],
    description: "솔로/듀엣/그룹 공연, 관객 참석",
  },
  {
    id: "amusement_park",
    name: "놀이공원",
    capacity: 8,
    location_type: "public",
    event_types: ["minigame", "night_market", "date"],
    description: "미니게임, 야시장",
  },
  {
    id: "city_hall",
    name: "시청",
    capacity: 6,
    location_type: "public",
    event_types: ["resident_list", "stats_check", "relationship_graph", "trait_map"],
    description: "주민 목록, 관계도, 성격 분포도",
  },
  {
    id: "photo_studio",
    name: "사진관",
    capacity: 4,
    location_type: "public",
    event_types: ["photo_shoot", "gallery_view"],
    description: "사진 촬영, 갤러리",
  },
];

// ────────────────────────────────────────────────────────────────────────────
// Default public weights (15개 — public 13 + shared 2)
// Python: _DEFAULT_PUBLIC_WEIGHTS
// ────────────────────────────────────────────────────────────────────────────

export const DEFAULT_PUBLIC_WEIGHTS: Record<string, number> = {
  grocery: 1.0,
  clothing: 0.5,
  interior: 0.5,
  fountain: 1.5,
  news_station: 0.3,
  park: 2.0,
  cafe: 1.5,
  beach: 1.0,
  plaza: 1.0,
  concert_hall: 0.8,
  amusement_park: 1.2,
  city_hall: 0.4,
  photo_studio: 0.6,
  living_room: 2.0,
  balcony: 0.8,
};

// ────────────────────────────────────────────────────────────────────────────
// LocationManager — 레지스트리 + 쿼리 + 이동/스냅샷
// Python src/tomodachai/location.py LocationManager 1:1 포팅.
// (choose_destination은 Task 3에서 구현)
// ────────────────────────────────────────────────────────────────────────────

/** snapshot() 한 항목의 형태 */
export interface LocationSnapshot {
  id: string;
  name: string;
  location_type: LocationType;
  capacity: number;
  event_types: string[];
  description: string;
  characters: number[];
}

export class LocationManager {
  // Map은 삽입 순서를 보존 → Python dict 반복 순서와 일치.
  private readonly _locations: Map<string, Location> = new Map();
  private readonly _positions: Map<number, string> = new Map(); // charId → locationId

  constructor(extraLocations?: Location[]) {
    for (const loc of DEFAULT_LOCATIONS) {
      this._locations.set(loc.id, loc);
    }
    if (extraLocations) {
      for (const loc of extraLocations) {
        this._locations.set(loc.id, loc);
      }
    }
  }

  addLocation(loc: Location): void {
    this._locations.set(loc.id, loc);
  }

  registerPrivateRoom(charId: number, charName: string): Location {
    const roomId = `room_${charId}`;
    const room: Location = {
      id: roomId,
      name: `${charName}의 방`,
      capacity: 2,
      location_type: "private_room",
      event_types: ["sleep", "personal_event", "room_visit", "gift", "consultation"],
      description: `${charName}의 개인 방`,
    };
    this._locations.set(roomId, room);
    return room;
  }

  getLocation(id: string): Location | null {
    return this._locations.get(id) ?? null;
  }

  getLocationByName(name: string): Location | null {
    for (const loc of this._locations.values()) {
      if (loc.name === name) {
        return loc;
      }
    }
    return null;
  }

  allLocations(): Location[] {
    return [...this._locations.values()];
  }

  publicLocations(): Location[] {
    return [...this._locations.values()].filter((loc) => loc.location_type === "public");
  }

  sharedLocations(): Location[] {
    return [...this._locations.values()].filter((loc) => loc.location_type === "shared_room");
  }

  getCharactersAt(id: string): number[] {
    const result: number[] = [];
    for (const [cid, lid] of this._positions.entries()) {
      if (lid === id) {
        result.push(cid);
      }
    }
    return result;
  }

  getCharacterLocation(charId: number): string | null {
    return this._positions.get(charId) ?? null;
  }

  isAtCapacity(id: string): boolean {
    const loc = this._locations.get(id);
    if (loc === undefined) {
      return true;
    }
    return this.getCharactersAt(id).length >= loc.capacity;
  }

  moveCharacter(charId: number, destination: string): boolean {
    let dest = destination;
    if (!this._locations.has(dest)) {
      const locByName = this.getLocationByName(dest);
      if (locByName === null) {
        return false;
      }
      dest = locByName.id;
    }
    this._positions.set(charId, dest);
    return true;
  }

  removeCharacter(charId: number): void {
    this._positions.delete(charId);
  }

  snapshot(): LocationSnapshot[] {
    const result: LocationSnapshot[] = [];
    for (const loc of this._locations.values()) {
      result.push({
        id: loc.id,
        name: loc.name,
        location_type: loc.location_type,
        capacity: loc.capacity,
        event_types: loc.event_types,
        description: loc.description,
        characters: this.getCharactersAt(loc.id),
      });
    }
    return result;
  }
}

// ────────────────────────────────────────────────────────────────────────────
// choose_destination — 확률적 목적지 결정
// Python src/tomodachai/location.py LocationManager.choose_destination 포팅.
// rng는 주입식(framework-free 유지): random()과 choices(단일 픽).
// ────────────────────────────────────────────────────────────────────────────

/** Python random.Random 중 choose_destination이 쓰는 인터페이스만 추출. */
export interface Rng {
  random(): number;
  /** Python rng.choices(population, weights=w, k=1)[0] 와 동일한 단일 픽. */
  choices<T>(items: T[], weights: number[]): T;
}

/** choose_destination이 필요로 하는 char 필드만 추린 덕타입(full Character 미의존). */
export interface DestinationActor {
  id: number;
  hunger: number;
  satisfaction: number;
  /** Python char.state.mood.stress 에 대응. */
  stress: number;
}

// Python 상수
const _NIGHT_HOME_PROB = 0.7;
const _NIGHT_SLOTS = new Set(["밤"]);
const _HUNGER_HIGH = 70.0;
const _SATISFACTION_LOW = 20.0;
const _STRESS_HIGH = 7;
const _FRIENDSHIP_FOLLOW = 60.0;

/**
 * 조건 기반 가중치 테이블을 산출한다(순수). 밤 분기는 제외 — chooseDestination이 담당.
 *
 * 규칙 적용 순서는 Python과 동일(hunger → satisfaction → stress → friends → capacity)하여
 * 부동소수 곱 결과가 비트 단위로 일치한다.
 */
export function buildDestinationWeights(
  char: DestinationActor,
  allPairs: [number, number, { friendship: number }][],
  manager: LocationManager,
): Record<string, number> {
  // 기본 가중치 복사 후, 존재하는 장소만 남김 (삽입 순서 보존)
  const weights: Record<string, number> = {};
  for (const k of Object.keys(DEFAULT_PUBLIC_WEIGHTS)) {
    if (manager.getLocation(k) !== null) {
      weights[k] = DEFAULT_PUBLIC_WEIGHTS[k];
    }
  }

  // 2. 배고픔 — 식료품점 10배
  if (char.hunger > _HUNGER_HIGH) {
    weights["grocery"] = (weights["grocery"] ?? 1.0) * 10.0;
  }

  // 3. 만족도 낮음 — 여가 장소↑
  if (char.satisfaction < _SATISFACTION_LOW) {
    for (const locId of ["park", "cafe", "beach", "amusement_park"]) {
      if (locId in weights) {
        weights[locId] *= 2.5;
      }
    }
  }

  // 4. 스트레스 — 해변/발코니↑
  if (char.stress > _STRESS_HIGH) {
    if ("beach" in weights) {
      weights["beach"] *= 3.0;
    }
    if ("balcony" in weights) {
      weights["balcony"] *= 2.0;
    }
  }

  // 5. 친구 따라가기
  for (const [aId, bId, rel] of allPairs) {
    if (char.id !== aId && char.id !== bId) {
      continue;
    }
    const friendId = aId === char.id ? bId : aId;
    if (rel.friendship >= _FRIENDSHIP_FOLLOW) {
      const friendLoc = manager.getCharacterLocation(friendId);
      if (friendLoc && friendLoc in weights) {
        weights[friendLoc] = (weights[friendLoc] ?? 1.0) * 3.0;
      }
    }
  }

  // 6. 정원 초과 장소 가중치 감소
  for (const locId of Object.keys(weights)) {
    if (manager.isAtCapacity(locId)) {
      weights[locId] *= 0.3;
    }
  }

  return weights;
}

/**
 * 확률적 이동 목적지를 결정한다.
 *  - 밤 분기 우선: "밤" && 개인 방 등록됨 && rng.random() < 0.7 → 개인 방
 *  - 그 외: buildDestinationWeights 후 가중 랜덤 선택.
 */
export function chooseDestination(
  char: DestinationActor,
  allPairs: [number, number, { friendship: number }][],
  timeOfDay: string,
  manager: LocationManager,
  rng: Rng,
): string {
  const privateRoomId = `room_${char.id}`;
  if (
    _NIGHT_SLOTS.has(timeOfDay) &&
    manager.getLocation(privateRoomId) !== null &&
    rng.random() < _NIGHT_HOME_PROB
  ) {
    return privateRoomId;
  }

  const weights = buildDestinationWeights(char, allPairs, manager);
  const ids = Object.keys(weights);
  const w = ids.map((i) => weights[i]);
  return rng.choices(ids, w);
}
