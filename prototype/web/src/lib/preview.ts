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

import { buildAvatar, type AvatarHandle } from "./figures";
import { MotionController } from "./motion";
import type { AvatarLook } from "./appearance";

let engine: Engine | null = null;
let scene: Scene | null = null;
let avatar: AvatarHandle | null = null;
let motion: MotionController | null = null;
let onResize: (() => void) | null = null;

export function initPreview(canvas: HTMLCanvasElement, look: AvatarLook): void {
  disposePreview();
  engine = new Engine(canvas, true, { preserveDrawingBuffer: true });
  scene = new Scene(engine);
  scene.clearColor = new Color4(0, 0, 0, 0); // 투명 — 패널 배경이 비치도록

  // alpha = +π/2 → 캐릭터 정면(얼굴은 +Z)을 기본 시점으로. radius 를 당겨 캐릭터를 크게.
  const cam = new ArcRotateCamera("pcam", Math.PI / 2, 1.16, 4.5, new Vector3(0, 1.05, 0), scene);
  cam.fov = 0.66;
  scene.activeCamera = cam;
  // 사용자가 직접 돌려보도록 — 드래그 회전 + 방향키 회전 + 휠 줌.
  cam.attachControl(canvas, true);
  cam.lowerRadiusLimit = 3.4;
  cam.upperRadiusLimit = 8;
  cam.lowerBetaLimit = 0.45;   // 너무 위/아래로 넘어가 바닥을 뚫지 않게
  cam.upperBetaLimit = 1.5;
  cam.wheelPrecision = 40;
  cam.panningSensibility = 0;  // 패닝 비활성(회전/줌만)
  canvas.tabIndex = 0;         // 방향키 입력을 받도록 포커스 가능하게
  canvas.addEventListener("pointerdown", () => canvas.focus());

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

  // 접지 그림자 — 캐릭터 발밑에 어두운 디스크를 깔아 무대에서 떠 보이지 않게(분홍이 배경에 묻히는 것도 완화).
  const contact = CreateCylinder("contact", { diameter: 1.25, height: 0.02, tessellation: 36 }, scene);
  const cm = new StandardMaterial("cm", scene);
  cm.diffuseColor = new Color3(0, 0, 0);
  cm.specularColor = new Color3(0, 0, 0);
  cm.alpha = 0.13;
  contact.material = cm;
  contact.position.y = 0.011;

  avatar = buildAvatar(scene, look);
  motion = new MotionController(avatar, { idle: "calm" }); // 평소엔 숨쉬듯 미세 보브

  engine.runRenderLoop(() => {
    motion?.update();
    scene!.render();
  });
  onResize = () => engine?.resize();
  window.addEventListener("resize", onResize);
}

// 리빌 등에서 주민이 신나게 콩콩 뛰는 모션을 잠깐 재생(이후 자동으로 idle 복귀).
export function playMotion(): void {
  motion?.set("celebrate");
}

export function updatePreview(look: AvatarLook): void {
  if (!scene) return;
  if (avatar) avatar.root.dispose(); // 메시만 정리 — 머티리얼은 캐시 공유라 유지
  avatar = buildAvatar(scene, look);
  motion = new MotionController(avatar, { idle: "calm" });
}

export function disposePreview(): void {
  if (onResize) { window.removeEventListener("resize", onResize); onResize = null; }
  if (avatar) { avatar.root.dispose(); avatar = null; }
  motion = null;
  if (scene) { scene.dispose(); scene = null; }
  if (engine) { engine.dispose(); engine = null; }
}
