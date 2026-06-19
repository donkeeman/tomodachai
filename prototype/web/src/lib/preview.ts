// 캐릭터 생성 미리보기 — 모달 안의 작은 독립 Babylon 씬(턴테이블). 마을과 같은 buildAvatar 사용.
import { Engine } from "@babylonjs/core/Engines/engine";
import { Scene } from "@babylonjs/core/scene";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { ArcRotateCamera } from "@babylonjs/core/Cameras/arcRotateCamera";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";

import { buildAvatar } from "./figures";
import type { AvatarLook } from "./appearance";

let engine: Engine | null = null;
let scene: Scene | null = null;
let avatar: TransformNode | null = null;
let onResize: (() => void) | null = null;

export function initPreview(canvas: HTMLCanvasElement, look: AvatarLook): void {
  disposePreview();
  engine = new Engine(canvas, true, { preserveDrawingBuffer: true });
  scene = new Scene(engine);
  scene.clearColor = new Color4(0, 0, 0, 0); // 투명 — 패널 배경이 비치도록

  const cam = new ArcRotateCamera("pcam", -Math.PI / 2, 1.16, 5.4, new Vector3(0, 1.1, 0), scene);
  cam.fov = 0.7;
  scene.activeCamera = cam;

  const hemi = new HemisphericLight("ph", new Vector3(0.3, 1, 0.2), scene);
  hemi.intensity = 0.95;
  hemi.diffuse = Color3.FromHexString("#fff7ea");
  hemi.groundColor = Color3.FromHexString("#ffd9e8");
  const sun = new DirectionalLight("ps", new Vector3(-0.4, -1, -0.5), scene);
  sun.intensity = 1.05;

  const podium = CreateCylinder("podium", { diameterTop: 2.0, diameterBottom: 2.35, height: 0.2, tessellation: 40 }, scene);
  const pm = new StandardMaterial("pm", scene);
  pm.diffuseColor = Color3.FromHexString("#ffd9e8");
  pm.specularColor = new Color3(0, 0, 0);
  podium.material = pm;
  podium.position.y = -0.1;

  avatar = buildAvatar(scene, look);

  engine.runRenderLoop(() => {
    if (avatar) avatar.rotation.y += 0.012;
    scene!.render();
  });
  onResize = () => engine?.resize();
  window.addEventListener("resize", onResize);
}

export function updatePreview(look: AvatarLook): void {
  if (!scene) return;
  if (avatar) avatar.dispose(); // 메시만 정리 — 머티리얼은 캐시 공유라 유지
  avatar = buildAvatar(scene, look);
}

export function disposePreview(): void {
  if (onResize) { window.removeEventListener("resize", onResize); onResize = null; }
  if (avatar) { avatar.dispose(); avatar = null; }
  if (scene) { scene.dispose(); scene = null; }
  if (engine) { engine.dispose(); engine = null; }
}
