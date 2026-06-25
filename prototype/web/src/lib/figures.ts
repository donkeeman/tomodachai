// 공유 아바타 빌더 — 주어진 scene 에 외모(AvatarLook)대로 피규어를 만든다.
// village.ts(마을)와 preview.ts(생성 미리보기)가 같은 모양을 쓰도록 단일화.
// 얼굴/머리는 head 피벗(TransformNode) 아래로 묶어 모션 시스템이 머리를 돌리거나 끄덕일 수 있게 한다.
import type { Scene } from "@babylonjs/core/scene";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateCapsule } from "@babylonjs/core/Meshes/Builders/capsuleBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import type { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";

import type { AvatarLook } from "./appearance";

// 모션 시스템이 잡을 핸들 — root(전신)와 head(목 위 피벗).
export interface AvatarHandle {
  root: TransformNode;
  head: TransformNode;
}

const HEAD_PIVOT_Y = 1.25; // 목 위치(머리 회전 피벗). 얼굴/머리 자식은 이 값을 기준으로 배치.

// 이목구비 형태 → 기본 구(sphere)에 적용할 scaling. 절차적 표현(추후 3D 모델로 대체).
const EYE_SHAPE_SCALE: Record<string, { x: number; y: number; z: number }> = {
  round: { x: 1, y: 1, z: 1 },        // 동그란
  narrow: { x: 1.35, y: 0.5, z: 1 },  // 가는(찢어진)
  sleepy: { x: 1.2, y: 0.68, z: 1 },  // 졸린(반쯤 감은)
};
const MOUTH_SHAPE_SCALE: Record<string, { x: number; y: number; z: number }> = {
  smile: { x: 1.7, y: 0.42, z: 0.5 },   // 옆으로 넓은 미소
  neutral: { x: 1, y: 0.5, z: 0.5 },    // 무표정(기존 기본형)
  pout: { x: 0.7, y: 0.78, z: 0.5 },    // 오므린(작고 동그란)
};

// scene 별 머티리얼 캐시(색상 중복 생성 방지).
const matCaches = new WeakMap<Scene, Map<string, StandardMaterial>>();
function mat(scene: Scene, hex: string): StandardMaterial {
  let cache = matCaches.get(scene);
  if (!cache) { cache = new Map(); matCaches.set(scene, cache); }
  let m = cache.get(hex);
  if (!m) {
    m = new StandardMaterial("am" + hex, scene);
    m.diffuseColor = Color3.FromHexString(hex);
    m.specularColor = new Color3(0, 0, 0);
    cache.set(hex, m);
  }
  return m;
}
function ball(scene: Scene, d: number, hex: string, x: number, y: number, z: number): Mesh {
  const m = CreateSphere("s", { diameter: d, segments: 12 }, scene);
  m.material = mat(scene, hex); m.position.set(x, y, z);
  return m;
}

// 외모대로 피규어 1구를 만들어 핸들로 반환. 머리 꼭대기 ~1.95, 키 ~1.7.
export function buildAvatar(scene: Scene, look: AvatarLook, opts: { shadow?: ShadowGenerator } = {}): AvatarHandle {
  const root = new TransformNode("avatar", scene);
  const casters: Mesh[] = [];

  const body = CreateCapsule("body", { radius: 0.42, height: 1.5 }, scene);
  body.material = mat(scene, look.bodyColor); body.position.y = 0.85; body.parent = root;
  casters.push(body);

  // 머리/얼굴 피벗 — 자식 위치는 HEAD_PIVOT_Y 기준 로컬 좌표.
  const head = new TransformNode("head", scene);
  head.position.y = HEAD_PIVOT_Y; head.parent = root;
  const hy = (worldY: number) => worldY - HEAD_PIVOT_Y;

  const headBall = ball(scene, 0.68, look.skin, 0, hy(1.6), 0); headBall.parent = head;
  casters.push(headBall);

  // 눈 — 모양(scaling)·크기(size) 반영. 미지정 시 동그란 기본형.
  const eyeSize = look.eyeSize ?? 1;
  const eyeScale = EYE_SHAPE_SCALE[look.eyeShape ?? "round"];
  for (const dx of [-0.12, 0.12]) {
    const e = ball(scene, 0.07 * eyeSize, look.eyeColor, dx, hy(1.64), 0.31);
    e.scaling.copyFromFloats(eyeScale.x, eyeScale.y, eyeScale.z);
    e.parent = head;
  }
  // 입 — 모양(scaling)·크기(size) 반영. 미지정 시 무표정.
  const mouthSize = look.mouthSize ?? 1;
  const mouthScale = MOUTH_SHAPE_SCALE[look.mouthShape ?? "neutral"];
  const mouth = ball(scene, 0.1 * mouthSize, "#c4736b", 0, hy(1.5), 0.315);
  mouth.scaling.copyFromFloats(mouthScale.x, mouthScale.y, mouthScale.z);
  mouth.parent = head;

  // 헤어스타일
  const hc = look.hairColor;
  if (look.hairStyle === "short") {
    const cap = CreateSphere("hair", { diameter: 0.71, segments: 12, slice: 0.55 }, scene);
    cap.material = mat(scene, hc); cap.position.set(0, hy(1.6), 0); cap.parent = head; casters.push(cap);
  } else if (look.hairStyle === "bob") {
    // 윗머리를 뒤로 밀어 앞이마/얼굴이 보이게(앞면을 덮지 않도록).
    const h = ball(scene, 0.75, hc, 0, hy(1.68), -0.12); h.scaling.set(1, 0.95, 1.02); h.parent = head; casters.push(h);
    const side = ball(scene, 0.3, hc, 0, hy(1.38), -0.16); side.scaling.set(1.6, 1.1, 0.7); side.parent = head;
  } else if (look.hairStyle === "long") {
    const top = ball(scene, 0.76, hc, 0, hy(1.7), -0.14); top.scaling.set(1, 0.9, 1); top.parent = head; casters.push(top);
    const back = ball(scene, 0.5, hc, 0, hy(1.2), -0.22); back.scaling.set(1.15, 1.9, 0.7); back.parent = head; casters.push(back);
  } else { // bun
    const cap = CreateSphere("hair", { diameter: 0.72, segments: 12, slice: 0.6 }, scene);
    cap.material = mat(scene, hc); cap.position.set(0, hy(1.6), 0); cap.parent = head; casters.push(cap);
    const bun = ball(scene, 0.3, hc, 0, hy(2.02), -0.04); bun.parent = head; casters.push(bun);
  }

  if (opts.shadow) for (const m of casters) opts.shadow.addShadowCaster(m);
  return { root, head };
}
