// Python src/tomodachai/character.py 미러 (순수 데이터 모델 + 결정론 파생).

/** 생일 "MM-DD" → 한국어 별자리. 인식 실패 시 "". Python calculate_zodiac 1:1. */
export function calculateZodiac(birthday: string): string {
  if (!birthday) return "";
  const month = Number.parseInt(birthday.slice(0, 2), 10);
  const day = Number.parseInt(birthday.slice(3, 5), 10);
  if (Number.isNaN(month) || Number.isNaN(day)) return "";

  if ((month === 3 && day >= 21) || (month === 4 && day <= 19)) return "양자리";
  if ((month === 4 && day >= 20) || (month === 5 && day <= 20)) return "황소자리";
  if ((month === 5 && day >= 21) || (month === 6 && day <= 20)) return "쌍둥이자리";
  if ((month === 6 && day >= 21) || (month === 7 && day <= 22)) return "게자리";
  if ((month === 7 && day >= 23) || (month === 8 && day <= 22)) return "사자자리";
  if ((month === 8 && day >= 23) || (month === 9 && day <= 22)) return "처녀자리";
  if ((month === 9 && day >= 23) || (month === 10 && day <= 22)) return "천칭자리";
  if ((month === 10 && day >= 23) || (month === 11 && day <= 21)) return "전갈자리";
  if ((month === 11 && day >= 22) || (month === 12 && day <= 21)) return "사수자리";
  if ((month === 12 && day >= 22) || (month === 1 && day <= 19)) return "염소자리";
  if ((month === 1 && day >= 20) || (month === 2 && day <= 18)) return "물병자리";
  if ((month === 2 && day >= 19) || (month === 3 && day <= 20)) return "물고기자리";
  return "";
}

// ---------------------------------------------------------------------------
// Appearance sub-models
// ---------------------------------------------------------------------------

export interface AppearanceAdjust {
  spacing: number;
  height: number;
  size: number;
  angle: number;
}

export interface Eye {
  base: number;
  lash: number;
  color: string;
  adjust: AppearanceAdjust;
}

export interface Eyebrow {
  id: number;
  adjust: AppearanceAdjust;
}

export interface Nose {
  id: number;
  adjust: AppearanceAdjust;
}

export interface Mouth {
  id: number;
  adjust: AppearanceAdjust;
}

export interface Hair {
  front: number;
  back: number;
  color: string;
}

export interface Body {
  height: number;
  build: number;
}

export interface Appearance {
  face_shape: number;
  skin_color: string;
  eye: Eye;
  eyebrow: Eyebrow;
  nose: Nose;
  mouth: Mouth;
  hair: Hair;
  glasses: number | null;
  body: Body;
}

// ---------------------------------------------------------------------------
// Personality & Voice sub-models
// ---------------------------------------------------------------------------

export interface Personality {
  movement: number;
  speech: number;
  expressiveness: number;
  attitude: number;
  overall: number;
}

export interface Voice {
  preset: string;
  pitch: number;
  speed: number;
  quality: string | null;
  tone: string | null;
  accent: string | null;
  intonation: string | null;
}

// ---------------------------------------------------------------------------
// Profile sub-model
// ---------------------------------------------------------------------------

export interface Profile {
  name: string;
  birthday: string;
  blood_type: string;
  favorite_color: string;
  gender: string;
  appearance: Appearance;
  personality: Personality;
  voice: Voice;
}

// ---------------------------------------------------------------------------
// Preferences sub-models
// ---------------------------------------------------------------------------

export interface ClothingPreference {
  likes: string;
  dislikes: string;
}

export interface InteriorPreference {
  likes: string;
  dislikes: string;
}

export interface PersonalityGroup {
  group: string;
  is_positive: boolean;
}

export interface Preferences {
  food_ranks: number[];
  food_eaten: boolean[];
  clothing: ClothingPreference;
  interior: InteriorPreference;
  personality_group: PersonalityGroup;
}

// ---------------------------------------------------------------------------
// State sub-models
// ---------------------------------------------------------------------------

export interface Mood {
  happiness: number;
  energy: number;
  stress: number;
}

export interface CharacterState {
  satisfaction: number;
  level: number;
  hunger: number;
  mood: Mood;
  sick: string | null;
  current_location: string;
  current_outfit: number | null;
  current_interior: number | null;
  photo_frame: number | null;
}

// ---------------------------------------------------------------------------
// Customizable sub-models
// ---------------------------------------------------------------------------

export interface SpeechHabits {
  normal: string;
  happy: string;
  angry: string;
  sad: string;
  worried: string;
}

export interface MiniTrait {
  owned: number[];
  active: number | null;
}

export interface MiniTraits {
  walking: MiniTrait;
  eating: MiniTrait;
  idle: MiniTrait;
}

export interface Customizable {
  speech_habits: SpeechHabits;
  mini_traits: MiniTraits;
  nicknames: Record<string, string>;
  songs: boolean[];
}

// ---------------------------------------------------------------------------
// Records sub-model
// ---------------------------------------------------------------------------

export interface Records {
  treasure_collection: number[];
  confession_count: Record<string, number>;
  photos: number[];
}

// ---------------------------------------------------------------------------
// Character (top-level)
// ---------------------------------------------------------------------------

export interface Character {
  id: number | string;
  profile: Profile;
  preferences: Preferences;
  state: CharacterState;
  customizable: Customizable;
  records: Records;
}

// ---------------------------------------------------------------------------
// Default factories
// ---------------------------------------------------------------------------

export function defaultAppearanceAdjust(): AppearanceAdjust {
  return { spacing: 0, height: 0, size: 0, angle: 0 };
}

export function defaultEye(): Eye {
  return { base: 1, lash: 0, color: "#000000", adjust: defaultAppearanceAdjust() };
}

export function defaultEyebrow(): Eyebrow {
  return { id: 1, adjust: defaultAppearanceAdjust() };
}

export function defaultNose(): Nose {
  return { id: 1, adjust: defaultAppearanceAdjust() };
}

export function defaultMouth(): Mouth {
  return { id: 1, adjust: defaultAppearanceAdjust() };
}

export function defaultHair(): Hair {
  return { front: 1, back: 1, color: "#000000" };
}

export function defaultBody(): Body {
  return { height: 5, build: 5 };
}

export function defaultAppearance(): Appearance {
  return {
    face_shape: 1,
    skin_color: "#F5D6B8",
    eye: defaultEye(),
    eyebrow: defaultEyebrow(),
    nose: defaultNose(),
    mouth: defaultMouth(),
    hair: defaultHair(),
    glasses: null,
    body: defaultBody(),
  };
}

export function defaultPersonality(): Personality {
  return { movement: 5, speech: 5, expressiveness: 5, attitude: 5, overall: 5 };
}

export function defaultVoice(): Voice {
  return {
    preset: "default",
    pitch: 5,
    speed: 5,
    quality: null,
    tone: null,
    accent: null,
    intonation: null,
  };
}

export function defaultMood(): Mood {
  return { happiness: 5, energy: 5, stress: 2 };
}

export function defaultCharacterState(): CharacterState {
  return {
    satisfaction: 50,
    level: 1,
    hunger: 0,
    mood: defaultMood(),
    sick: null,
    current_location: "",
    current_outfit: null,
    current_interior: null,
    photo_frame: null,
  };
}

export function defaultClothingPreference(): ClothingPreference {
  return { likes: "", dislikes: "" };
}

export function defaultInteriorPreference(): InteriorPreference {
  return { likes: "", dislikes: "" };
}

export function defaultPersonalityGroup(): PersonalityGroup {
  return { group: "", is_positive: true };
}

export function defaultPreferences(): Preferences {
  return {
    food_ranks: [],
    food_eaten: [],
    clothing: defaultClothingPreference(),
    interior: defaultInteriorPreference(),
    personality_group: defaultPersonalityGroup(),
  };
}

export function defaultSpeechHabits(): SpeechHabits {
  return { normal: "", happy: "", angry: "", sad: "", worried: "" };
}

export function defaultMiniTrait(): MiniTrait {
  return { owned: [], active: null };
}

export function defaultMiniTraits(): MiniTraits {
  return {
    walking: defaultMiniTrait(),
    eating: defaultMiniTrait(),
    idle: defaultMiniTrait(),
  };
}

export function defaultCustomizable(): Customizable {
  return {
    speech_habits: defaultSpeechHabits(),
    mini_traits: defaultMiniTraits(),
    nicknames: {},
    songs: [false, false, false, false, false, false, false, false],
  };
}

export function defaultRecords(): Records {
  return {
    treasure_collection: [],
    confession_count: {},
    photos: [],
  };
}

export function defaultProfile(name: string): Profile {
  return {
    name,
    birthday: "",
    blood_type: "",
    favorite_color: "",
    gender: "",
    appearance: defaultAppearance(),
    personality: defaultPersonality(),
    voice: defaultVoice(),
  };
}

export function defaultCharacter(id: number, name: string): Character {
  return {
    id,
    profile: defaultProfile(name),
    preferences: defaultPreferences(),
    state: defaultCharacterState(),
    customizable: defaultCustomizable(),
    records: defaultRecords(),
  };
}
