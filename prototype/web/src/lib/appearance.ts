// 캐릭터 외모(아바타 룩) — 프론트엔드 단독. 생성 UI 미리보기와 마을 렌더가 같은 정의를 공유한다.
// 백엔드가 appearance 를 저장/회신하기 전까지는 여기 스토어가 소스 오브 트루스.
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

// 사용자가 만든 외모 저장소(캐릭터 id → 룩). 백엔드 영속 전까지 프론트 보관.
// localStorage 에 미러링 — 새로고침해도 만든 외모가 유지되도록.
const LOOKS_KEY = "tomodachai.looks.v1";

function loadLooks(): Map<number, AvatarLook> {
  try {
    const raw = localStorage.getItem(LOOKS_KEY);
    if (!raw) return new Map();
    const obj = JSON.parse(raw) as Record<string, AvatarLook>;
    return new Map(Object.entries(obj).map(([k, v]) => [Number(k), v]));
  } catch {
    return new Map(); // 손상된 데이터는 무시하고 빈 저장소로 시작
  }
}

function persistLooks(): void {
  try {
    const obj: Record<number, AvatarLook> = {};
    for (const [id, look] of customLooks) obj[id] = look;
    localStorage.setItem(LOOKS_KEY, JSON.stringify(obj));
  } catch {
    // 저장 실패(용량 초과/프라이빗 모드)는 무시 — 메모리 저장소는 그대로 동작
  }
}

const customLooks = loadLooks();

export function setLook(id: number, look: AvatarLook): void {
  customLooks.set(id, { ...look });
  persistLooks();
}
export function lookFor(char: Pick<Character, "id" | "gender">): AvatarLook {
  return customLooks.get(char.id) ?? defaultLook(char.id, char.gender);
}
