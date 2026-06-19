// 캐릭터 외모(아바타 룩) — 프론트엔드 단독. 생성 UI 미리보기와 마을 렌더가 같은 정의를 공유한다.
// 백엔드가 appearance 를 저장/회신하기 전까지는 여기 스토어가 소스 오브 트루스.
import type { Character } from "./types";

export type HairStyle = "short" | "bob" | "long" | "bun";

export interface AvatarLook {
  gender: "M" | "F";
  skin: string;
  hairColor: string;
  hairStyle: HairStyle;
  bodyColor: string;
  eyeColor: string;
}

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

// 사용자가 만든 외모 저장소(캐릭터 id → 룩). 백엔드 영속 전까지 프론트 보관.
const customLooks = new Map<number, AvatarLook>();

export function setLook(id: number, look: AvatarLook): void {
  customLooks.set(id, { ...look });
}
export function lookFor(char: Pick<Character, "id" | "gender">): AvatarLook {
  return customLooks.get(char.id) ?? defaultLook(char.id, char.gender);
}
