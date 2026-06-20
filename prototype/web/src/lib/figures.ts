// 공유 아바타 빌더 — 주어진 scene 에 외모(AvatarLook)대로 피규어를 만든다.
// village.ts(마을)와 preview.ts(생성 미리보기)가 같은 모양을 쓰도록 단일화.
import type { Scene } from "@babylonjs/core/scene";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateCapsule } from "@babylonjs/core/Meshes/Builders/capsuleBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import type { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";

import type { AvatarLook } from "./appearance";

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

// 외모대로 피규어 1구를 만들어 root(TransformNode)로 반환. 머리 꼭대기 ~1.95, 키 ~1.7.
export function buildAvatar(scene: Scene, look: AvatarLook, opts: { shadow?: ShadowGenerator } = {}): TransformNode {
  const root = new TransformNode("avatar", scene);
  const casters: Mesh[] = [];

  const body = CreateCapsule("body", { radius: 0.42, height: 1.5 }, scene);
  body.material = mat(scene, look.bodyColor); body.position.y = 0.85; body.parent = root;
  casters.push(body);

  const head = ball(scene, 0.68, look.skin, 0, 1.6, 0); head.parent = root;
  casters.push(head);

  // 눈 + 입(귀여운 인상)
  for (const dx of [-0.12, 0.12]) { const e = ball(scene, 0.07, look.eyeColor, dx, 1.64, 0.31); e.parent = root; }
  const mouth = ball(scene, 0.1, "#c4736b", 0, 1.5, 0.315); mouth.scaling.set(1, 0.5, 0.5); mouth.parent = root;

  // 헤어스타일
  const hc = look.hairColor;
  if (look.hairStyle === "short") {
    const cap = CreateSphere("hair", { diameter: 0.71, segments: 12, slice: 0.55 }, scene);
    cap.material = mat(scene, hc); cap.position.set(0, 1.6, 0); cap.parent = root; casters.push(cap);
  } else if (look.hairStyle === "bob") {
    // 윗머리를 뒤로 밀어 앞이마/얼굴이 보이게(앞면을 덮지 않도록).
    const h = ball(scene, 0.75, hc, 0, 1.68, -0.12); h.scaling.set(1, 0.95, 1.02); h.parent = root; casters.push(h);
    const side = ball(scene, 0.3, hc, 0, 1.38, -0.16); side.scaling.set(1.6, 1.1, 0.7); side.parent = root;
  } else if (look.hairStyle === "long") {
    const top = ball(scene, 0.76, hc, 0, 1.7, -0.14); top.scaling.set(1, 0.9, 1); top.parent = root; casters.push(top);
    const back = ball(scene, 0.5, hc, 0, 1.2, -0.22); back.scaling.set(1.15, 1.9, 0.7); back.parent = root; casters.push(back);
  } else { // bun
    const cap = CreateSphere("hair", { diameter: 0.72, segments: 12, slice: 0.6 }, scene);
    cap.material = mat(scene, hc); cap.position.set(0, 1.6, 0); cap.parent = root; casters.push(cap);
    const bun = ball(scene, 0.3, hc, 0, 2.02, -0.04); bun.parent = root; casters.push(bun);
  }

  if (opts.shadow) for (const m of casters) opts.shadow.addShadowCaster(m);
  return root;
}
