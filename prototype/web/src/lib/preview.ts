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
let motionUntil = 0; // 모션(콩콩 점프+좌우 흔들) 종료 시각(ms). 0이면 정지.

export function initPreview(canvas: HTMLCanvasElement, look: AvatarLook): void {
  disposePreview();
  engine = new Engine(canvas, true, { preserveDrawingBuffer: true });
  scene = new Scene(engine);
  scene.clearColor = new Color4(0, 0, 0, 0); // 투명 — 패널 배경이 비치도록

  // alpha = +π/2 → 캐릭터 정면(얼굴은 +Z)을 기본 시점으로.
  const cam = new ArcRotateCamera("pcam", Math.PI / 2, 1.16, 5.4, new Vector3(0, 1.1, 0), scene);
  cam.fov = 0.7;
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

  avatar = buildAvatar(scene, look);

  engine.runRenderLoop(() => {
    // 평소엔 정지(카메라만 사용자 조작). 모션 중에는 콩콩 점프 + 살짝 흔들.
    if (avatar) {
      const now = performance.now();
      if (now < motionUntil) {
        const t = now / 1000;
        avatar.position.y = Math.abs(Math.sin(t * 7)) * 0.28;
        avatar.rotation.y = Math.sin(t * 9) * 0.18;
      } else if (avatar.position.y !== 0 || avatar.rotation.y !== 0) {
        avatar.position.y = 0; avatar.rotation.y = 0;
      }
    }
    scene!.render();
  });
  onResize = () => engine?.resize();
  window.addEventListener("resize", onResize);
}

// 리빌 등에서 주민이 신나게 콩콩 뛰는 모션을 잠깐 재생.
export function playMotion(ms = 2600): void {
  motionUntil = performance.now() + ms;
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
