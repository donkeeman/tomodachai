import type { AvatarLook } from "./appearance";

export interface CharFriend { name: string; label: string; }
export interface DexItem { name: string; tier: string; }

// sim Character.state.mood(0~10 구조체)와 동일 형태 — 라벨로 압축하지 않고 구조 그대로 전달.
export interface Mood { happiness: number; energy: number; stress: number; }

export interface Character {
  id: number;
  name: string;
  gender: "M" | "F";
  location: string;
  mood: Mood;
  hunger: number;
  satisfaction: number;
  lover: string | null;
  best_friend: string | null;
  enemy: string | null;
  crushes: string[];
  food_eaten: boolean[];
  friends: CharFriend[];
  dex: DexItem[];
  // read-path 가 sim Appearance 에서 복원해 실어줌(figures.ts 가 소비). 시드/폴백은 미지정.
  look?: AvatarLook;
}

export interface EventItem {
  seq: number;
  day: number;
  clock: string;
  scene: string;
  dialogue: [string, string][];
  messages: string[];
  major: boolean;
}

export interface Bubble {
  kind: string;
  char: string;
  target: string | null;
  text: string;
}

export interface Rankings {
  best_couple: string[];
  popular_m: string[];
  popular_f: string[];
  fighters: string[];
}

export interface Photo { day: number; author: string; title: string; subject: string; }
export interface Dish { day: number; author: string; dish: string; }

export interface Snapshot {
  village: string;
  provider: string;
  day: number;
  clock: string;
  minutes: number;
  seq: number;
  locations: Record<string, string>;
  foods: string[];
  rankings: Rankings;
  asleep: boolean;
  realtime: boolean;
  photos: Photo[];
  dishes: Dish[];
  characters: Character[];
  events: EventItem[];
  bubbles: Bubble[];
}
