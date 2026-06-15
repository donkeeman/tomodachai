export interface CharFriend { name: string; label: string; }
export interface DexItem { name: string; tier: string; }

export interface Character {
  id: number;
  name: string;
  gender: "M" | "F";
  location: string;
  mood: string;
  hunger: number;
  satisfaction: number;
  lover: string | null;
  best_friend: string | null;
  enemy: string | null;
  crushes: string[];
  food_eaten: boolean[];
  friends: CharFriend[];
  dex: DexItem[];
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
