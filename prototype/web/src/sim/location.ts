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
