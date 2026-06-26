// AvatarLook(프론트 커스터마이저) ↔ sim Character.profile.appearance(정본) 어댑터.
//
// sim Appearance 는 Python 1:1 미러(골든 잠금)라 숫자 id 모델이고, 우리 커스터마이저는
// 문자열 enum 모델이다. 두 모델의 변환을 이 한 곳에 격리해 figures.ts(AvatarLook 소비)와
// sim 코어(Appearance 소비) 양쪽을 손대지 않는다.
//
// 매핑:
//   skin/eyeColor/hairColor → skin_color / eye.color / hair.color (직결)
//   eyeSize/mouthSize       → eye.adjust.size / mouth.adjust.size (배율 1 == adjust 0)
//   eyeShape/mouthShape     → eye.base / mouth.id                  (enum↔int 코덱)
//   hairStyle               → hair.front                            (enum↔int 코덱)
//   bodyColor               → profile.favorite_color                (몸통=좋아하는 색)
//   gender                  → profile.gender
import type { AvatarLook, HairStyle, EyeShape, MouthShape } from "./appearance";
import { HAIR_STYLES, EYE_SHAPES, MOUTH_SHAPES } from "./appearance";
import type { Character } from "../sim/character";

// enum 순서를 단일 출처(스와치 배열)에서 파생 — UI/코덱 동기 유지. int 는 1-based(sim 기본 1).
const HAIR_IDS: HairStyle[] = HAIR_STYLES.map((h) => h.id);
const EYE_IDS: EyeShape[] = EYE_SHAPES.map((e) => e.id);
const MOUTH_IDS: MouthShape[] = MOUTH_SHAPES.map((m) => m.id);

const idxToInt = <T,>(arr: T[], v: T): number => {
  const i = arr.indexOf(v);
  return (i < 0 ? 0 : i) + 1; // 미발견 시 첫 항목(1)
};
const intToId = <T,>(arr: T[], n: number, fallback: T): T => arr[n - 1] ?? fallback;

/** AvatarLook 을 기존 sim Character 에 반영(profile.appearance + favorite_color + gender 변형). */
export function applyLook(char: Character, look: AvatarLook): void {
  const app = char.profile.appearance;
  app.skin_color = look.skin;
  app.eye.color = look.eyeColor;
  app.eye.base = idxToInt(EYE_IDS, look.eyeShape ?? "round");
  app.eye.adjust.size = (look.eyeSize ?? 1) - 1;
  app.mouth.id = idxToInt(MOUTH_IDS, look.mouthShape ?? "neutral");
  app.mouth.adjust.size = (look.mouthSize ?? 1) - 1;
  app.hair.color = look.hairColor;
  app.hair.front = idxToInt(HAIR_IDS, look.hairStyle);
  app.hair.back = app.hair.front; // 단순 아바타는 front/back 구분 없음 — 동기화
  char.profile.gender = look.gender;
  char.profile.favorite_color = look.bodyColor; // 몸통 색 == 좋아하는 색
}

/** sim Character 에서 AvatarLook 복원(read-path 가 스냅샷에 실어 figures.ts 가 소비). */
export function characterLook(char: Character): AvatarLook {
  const app = char.profile.appearance;
  return {
    gender: char.profile.gender === "F" ? "F" : "M",
    skin: app.skin_color,
    hairColor: app.hair.color,
    hairStyle: intToId(HAIR_IDS, app.hair.front, "short"),
    bodyColor: char.profile.favorite_color,
    eyeColor: app.eye.color,
    eyeShape: intToId(EYE_IDS, app.eye.base, "round"),
    eyeSize: 1 + app.eye.adjust.size,
    mouthShape: intToId(MOUTH_IDS, app.mouth.id, "neutral"),
    mouthSize: 1 + app.mouth.adjust.size,
  };
}
