// 캐릭터 외모(아바타 룩) 정의 — 생성 UI 미리보기와 마을 렌더가 공유. 정본은 sim Character
// (profile.appearance)이며, AvatarLook↔Appearance 변환은 lookAppearance.ts 에 격리돼 있다.
import type { Character } from "./types";

export type HairStyle = "short" | "bob" | "long" | "bun";
export type EyeShape = "round" | "narrow" | "sleepy";   // 동그란 / 가는 / 졸린
export type MouthShape = "smile" | "neutral" | "pout";  // 미소 / 무표정 / 오므린

export interface AvatarLook {
  gender: "M" | "F";
  skin: string;
  hairColor: string;
  hairStyle: HairStyle;
  bodyColor: string;
  eyeColor: string;
  // 이목구비 형태(옵셔널 — 미지정 시 기본값. 기존/시드 캐릭터·백엔드 라운드트립 무영향).
  eyeShape?: EyeShape;
  eyeSize?: number;     // 0.8~1.3 배율(기본 1)
  mouthShape?: MouthShape;
  mouthSize?: number;   // 0.8~1.3 배율(기본 1)
}

export const EYE_SHAPES: { id: EyeShape; label: string }[] = [
  { id: "round", label: "동그란" },
  { id: "narrow", label: "가는" },
  { id: "sleepy", label: "졸린" },
];
export const MOUTH_SHAPES: { id: MouthShape; label: string }[] = [
  { id: "smile", label: "미소" },
  { id: "neutral", label: "무표정" },
  { id: "pout", label: "오므린" },
];

// 기존(id 파생) 룩을 보존하기 위한 팔레트 — village.ts 가 쓰던 값과 동일.
export const PALETTE = ["#e57373", "#64b5f6", "#81c784", "#ffb74d", "#ba68c8", "#4db6ac",
  "#f06292", "#7986cb", "#a1887f", "#90a4ae", "#dce775", "#4dd0e1"];
export const HAIR = ["#4e342e", "#263238", "#6d4c41", "#8d6e63", "#3e2723"];

// 생성 UI 스와치 팔레트
export const SKIN_TONES = ["#ffe0bd", "#f5cfa6", "#e8b48b", "#c98a5a", "#a3623c", "#7a4a2b"];
export const HAIR_COLORS = ["#2b2320", "#4e342e", "#6d4c41", "#8d6e63", "#c8a165", "#e7c07b",
  "#d98f6e", "#b0623f", "#9a6cc0", "#5a8fd0", "#e0719c", "#cfd3d8"];
export const BODY_COLORS = ["#e57373", "#64b5f6", "#81c784", "#ffb74d", "#ba68c8", "#4db6ac",
  "#f06292", "#7986cb", "#a1887f", "#90a4ae", "#dce775", "#4dd0e1"];
export const EYE_COLORS = ["#3a2b22", "#4e342e", "#5b8c5a", "#3f72af", "#7a5ca0", "#b0623f"];
export const HAIR_STYLES: { id: HairStyle; label: string }[] = [
  { id: "short", label: "짧은머리" },
  { id: "bob", label: "단발" },
  { id: "long", label: "긴머리" },
  { id: "bun", label: "올림머리" },
];

// id 기반 기본 룩 — 외모를 직접 만들지 않은 캐릭터(시드/기존)는 예전과 동일하게 보이도록.
export function defaultLook(id: number, gender: "M" | "F"): AvatarLook {
  return {
    gender,
    skin: "#ffe0bd",
    hairColor: HAIR[((id * 3 + 1) % HAIR.length + HAIR.length) % HAIR.length],
    hairStyle: gender === "F" ? "long" : "short",
    bodyColor: PALETTE[((id - 1) % PALETTE.length + PALETTE.length) % PALETTE.length],
    eyeColor: "#222222",
  };
}

// 외모 정본은 sim Character.profile.appearance(read-path 가 스냅샷 char.look 으로 복원).
// 여기 lookFor 는 look 이 없는 캐릭터(시드/폴백)를 위한 id 파생 기본값만 제공한다.
export function lookFor(char: Pick<Character, "id" | "gender">): AvatarLook {
  return defaultLook(char.id, char.gender);
}
