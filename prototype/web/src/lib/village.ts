// Babylon.js 3D 마을 — ES 모듈(트리셰이킹) + 스토어 연동.
// 시뮬레이션/UI는 파이썬 백엔드 + Svelte 패널이 담당하고, 여기서는 그리기/연출만.
import { Engine } from "@babylonjs/core/Engines/engine";
import { Scene } from "@babylonjs/core/scene";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import "@babylonjs/core/Lights/Shadows/shadowGeneratorSceneComponent";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { Material } from "@babylonjs/core/Materials/material";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { CreateDisc } from "@babylonjs/core/Meshes/Builders/discBuilder";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { CreateTorus } from "@babylonjs/core/Meshes/Builders/torusBuilder";
import { SceneLoader } from "@babylonjs/core/Loading/sceneLoader";
import "@babylonjs/core/Culling/ray";
import "@babylonjs/loaders/glTF/2.0";

import type { Snapshot, Character, EventItem } from "./types";
import { toast, selectedId, viewMode, roomName, followName, modelLoaded, boardOpen, cardMode } from "./store";
import { buildAvatar, type AvatarHandle } from "./figures";
import { MotionController, styleForId, styleForPersonality } from "./motion";
import { personaFor, setPersona } from "./personality";
import { lookFor, type AvatarLook } from "./appearance";

let engine: Engine, scene: Scene, camera: UniversalCamera, shadow: ShadowGenerator;
let sun: DirectionalLight;
let canvasEl: HTMLCanvasElement;

// ---------- 머티리얼/메시 헬퍼 ----------

const matCache = new Map<string, StandardMaterial>();
function mat(hex: string): StandardMaterial {
  let m = matCache.get(hex);
  if (!m) {
    m = new StandardMaterial("m" + hex, scene);
    m.diffuseColor = Color3.FromHexString(hex);
    m.specularColor = new Color3(0, 0, 0);
    matCache.set(hex, m);
  }
  return m;
}
function place(m: Mesh, x: number, y: number, z: number, cast = true): Mesh {
  m.position.set(x, y, z);
  m.receiveShadows = true;
  if (cast) shadow.addShadowCaster(m);
  return m;
}
function box(w: number, h: number, d: number, hex: string, x: number, y: number, z: number, cast = true) {
  const m = CreateBox("box", { width: w, height: h, depth: d }, scene);
  m.material = mat(hex);
  return place(m, x, y, z, cast);
}
function cyl(dT: number, dB: number, h: number, hex: string, x: number, y: number, z: number, cast = true) {
  const m = CreateCylinder("cyl", { diameterTop: dT, diameterBottom: dB, height: h, tessellation: 18 }, scene);
  m.material = mat(hex);
  return place(m, x, y, z, cast);
}
function cone(d: number, h: number, hex: string, x: number, y: number, z: number, sides = 16, cast = true) {
  const m = CreateCylinder("cone", { diameterTop: 0, diameterBottom: d, height: h, tessellation: sides }, scene);
  m.material = mat(hex);
  return place(m, x, y, z, cast);
}
function sphere(d: number, hex: string, x: number, y: number, z: number, cast = true) {
  const m = CreateSphere("sph", { diameter: d, segments: 12 }, scene);
  m.material = mat(hex);
  return place(m, x, y, z, cast);
}
function disc(radius: number, hex: string, x: number, z: number, y = 0.012) {
  const m = CreateDisc("disc", { radius, tessellation: 36 }, scene);
  const mt = mat(hex).clone("d" + hex + radius);
  mt.backFaceCulling = false;
  m.material = mt;
  m.rotation.x = Math.PI / 2;
  m.position.set(x, y, z);
  m.receiveShadows = true;
  return m;
}

// ---------- 텍스트 평면 (이름표/말풍선) ----------

function makeTextPlane(draw: (g: any, w: number, h: number) => void, tw: number, th: number, pw: number, ph: number): Mesh {
  const dt = new DynamicTexture("dt", { width: tw, height: th }, scene, false);
  dt.hasAlpha = true;
  draw(dt.getContext() as any, tw, th);
  dt.update();  // invertY 기본(true) — 캔버스 텍스트가 똑바로 서도록(false면 위아래 반전)
  const plane = CreatePlane("txt", { width: pw, height: ph }, scene);
  const m = new StandardMaterial("txtm", scene);
  m.diffuseTexture = dt;
  m.diffuseTexture.hasAlpha = true;
  m.useAlphaFromDiffuseTexture = true;
  m.transparencyMode = Material.MATERIAL_ALPHABLEND;
  m.emissiveColor = new Color3(1, 1, 1);
  m.disableLighting = true;
  m.backFaceCulling = false;
  plane.material = m;
  plane.billboardMode = Mesh.BILLBOARDMODE_ALL;
  plane.isPickable = false;
  plane.renderingGroupId = 1;
  return plane;
}
// 텍스처 폭을 넘치는 긴 텍스트(예: 긴 한글 이름)는 폰트를 줄여 잘리지 않게 맞춘다.
function fitFont(g: any, text: string, maxW: number, base: number, weight = 700): void {
  const f = (s: number) => `${weight} ${s}px 'Pretendard', 'Apple SD Gothic Neo', system-ui, sans-serif`;
  g.font = f(base);
  const w = g.measureText(text).width;
  if (w > maxW) g.font = f(Math.max(15, Math.floor(base * (maxW / w))));
}
function makeNameLabel(text: string, color: string) {
  return makeTextPlane((g, w, h) => {
    g.clearRect(0, 0, w, h);
    fitFont(g, text, w - 20, 40);
    g.textAlign = "center"; g.textBaseline = "middle";
    g.lineWidth = 8; g.strokeStyle = "rgba(40,40,40,.9)";
    g.strokeText(text, w / 2, h / 2);
    g.fillStyle = color; g.fillText(text, w / 2, h / 2);
  }, 256, 72, 2.4, 0.68);
}
function makeLocLabel(text: string) {
  return makeTextPlane((g, w, h) => {
    g.clearRect(0, 0, w, h);
    fitFont(g, text, w - 24, 40);
    g.textAlign = "center"; g.textBaseline = "middle";
    g.lineWidth = 9; g.strokeStyle = "rgba(50,80,50,.7)";
    g.strokeText(text, w / 2, h / 2);
    g.fillStyle = "#fdfbe8"; g.fillText(text, w / 2, h / 2);
  }, 320, 76, 3.0, 0.71);
}
function wrapLines(g: any, text: string, maxW: number): string[] {
  const lines: string[] = []; let cur = "";
  for (const ch of text) {
    if (ch === "\n") { lines.push(cur); cur = ""; continue; }
    if (g.measureText(cur + ch).width > maxW && cur) { lines.push(cur); cur = ch; }
    else cur += ch;
  }
  if (cur) lines.push(cur);
  return lines;
}
interface BubblePlane extends Mesh { bubbleH: number; }
function makeBubble(text: string, opts: { thought?: boolean; grey?: boolean } = {}): BubblePlane {
  const probe = document.createElement("canvas").getContext("2d")!;
  const font = "500 30px 'Pretendard', 'Apple SD Gothic Neo', system-ui, sans-serif";
  probe.font = font;
  const lines = wrapLines(probe, text, 360);
  const lineH = 40, pad = 26;
  const textW = Math.max(80, ...lines.map((l) => probe.measureText(l).width));
  const w = Math.ceil(textW + pad * 2), h = Math.ceil(lines.length * lineH + pad * 2 - 10);
  const bg = opts.thought ? "rgba(255,246,216,.97)" : opts.grey ? "rgba(238,238,238,.97)" : "rgba(255,255,255,.97)";
  const plane = makeTextPlane((g) => {
    g.clearRect(0, 0, w, h);
    g.beginPath();
    if (g.roundRect) g.roundRect(3, 3, w - 6, h - 6, 22); else g.rect(3, 3, w - 6, h - 6);
    g.fillStyle = bg; g.fill();
    g.lineWidth = 3; g.strokeStyle = opts.thought ? "#e0b73e" : "rgba(70,70,70,.5)"; g.stroke();
    g.font = font; g.fillStyle = "#333"; g.textBaseline = "middle";
    lines.forEach((l, i) => g.fillText(l, pad, pad + 20 + i * lineH));
  }, w, h, w * 0.011, h * 0.011) as BubblePlane;
  plane.bubbleH = h * 0.011;
  return plane;
}

// ---------- 마을 레이아웃 ----------

const INTERIOR_X = 200;
interface Anchor { x: number; z: number; r: number; labelY: number; label?: Mesh; named?: boolean; }
// 백엔드(FastAPI)의 15개 장소를 모두 매핑. living_room/balcony 는 실내(INTERIOR_X), 나머지는 마을.
const ANCHORS: Record<string, Anchor> = {
  fountain: { x: 0, z: 0, r: 3.0, labelY: 3.2 },
  living_room: { x: INTERIOR_X, z: 0, r: 4.6, labelY: 5.2 },
  balcony: { x: INTERIOR_X + 10.8, z: 1.5, r: 1.6, labelY: 3.0 },
  park: { x: 10, z: -7, r: 3.4, labelY: 4.6 },
  cafe: { x: -10.5, z: 6.5, r: 2.4, labelY: 4.2 },
  beach: { x: 9.5, z: 10, r: 3.0, labelY: 3.4 },
  grocery: { x: -15, z: 3, r: 2.4, labelY: 4.0 },
  clothing: { x: -15, z: -4, r: 2.4, labelY: 4.0 },
  interior: { x: -4, z: 15, r: 2.4, labelY: 4.0 },
  news_station: { x: 15, z: 3, r: 2.4, labelY: 4.6 },
  plaza: { x: 1, z: -14, r: 3.0, labelY: 3.0 },
  concert_hall: { x: 9, z: -14, r: 2.6, labelY: 4.6 },
  amusement_park: { x: 16, z: -10, r: 3.0, labelY: 4.8 },
  city_hall: { x: -7, z: -14, r: 2.6, labelY: 4.8 },
  photo_studio: { x: 5, z: 15, r: 2.4, labelY: 4.0 },
};

// 마을 시야(분수대 중심)에서 너무 멀어 안개에 묻히지 않게 지면도 살짝 키운다 (radius 30→34)

let boardMesh: Mesh | null = null, houseMesh: Mesh | null = null;
let fountainWater: Mesh | null = null;
const clouds: TransformNode[] = [];

function mulberry(seed: number) {
  let a = seed;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function addTree(x: number, z: number, s = 1) {
  cyl(0.36 * s, 0.48 * s, 0.9 * s, "#8a5a3b", x, 0.45 * s, z);
  cone(1.9 * s, 1.5 * s, "#5fa463", x, 1.55 * s, z, 8);
  cone(1.4 * s, 1.15 * s, "#74bf72", x, 2.35 * s, z, 8);
}

function buildVillage() {
  disc(34, "#9ed487", 0, 0, 0.01);  // 장소 15곳 + 가장자리 나무까지 담도록 확장
  disc(4.4, "#ead9b5", 0, 0, 0.02);
  cyl(4.4, 4.8, 0.5, "#b8c4cc", 0, 0.25, 0);
  fountainWater = cyl(3.8, 3.8, 0.46, "#7fd3f0", 0, 0.32, 0, false);
  cyl(0.56, 0.8, 1.3, "#b8c4cc", 0, 0.9, 0);
  sphere(0.8, "#9fdef5", 0, 1.7, 0);

  const pk = ANCHORS.park;
  disc(3.8, "#c8e6a0", pk.x, pk.z, 0.02);
  addTree(pk.x - 1.6, pk.z - 1.2, 1.1);
  addTree(pk.x + 1.8, pk.z - 0.6, 1.35);
  addTree(pk.x + 0.4, pk.z + 1.8, 0.95);
  box(1.7, 0.14, 0.55, "#a9763f", pk.x - 0.4, 0.5, pk.z + 0.4);
  box(1.7, 0.5, 0.12, "#a9763f", pk.x - 0.4, 0.75, pk.z + 0.66);
  boardMesh = box(2.1, 1.25, 0.14, "#deb887", pk.x - 3.1, 1.45, pk.z + 2.2);
  boardMesh.metadata = { board: true };
  cyl(0.16, 0.16, 1.5, "#8a5a3b", pk.x - 3.95, 0.75, pk.z + 2.2);
  cyl(0.16, 0.16, 1.5, "#8a5a3b", pk.x - 2.25, 0.75, pk.z + 2.2);
  const bl = makeLocLabel("랭킹"); bl.scaling.scaleInPlace(0.62);
  bl.position.set(pk.x - 3.1, 2.5, pk.z + 2.2);

  const cf = ANCHORS.cafe;
  disc(2.9, "#ead9b5", cf.x, cf.z, 0.02);
  box(3.4, 2.4, 3, "#fff1e0", cf.x, 1.2, cf.z);
  box(3.8, 0.22, 3.4, "#b97f5c", cf.x, 2.5, cf.z);
  const awn = box(3.6, 0.1, 1.3, "#ff8e7a", cf.x, 2.2, cf.z + 1.95); awn.rotation.x = 0.35;
  cyl(0.12, 0.12, 1.9, "#ddd6c8", cf.x + 2.3, 0.95, cf.z + 1.4);
  cone(2.3, 0.55, "#ffd166", cf.x + 2.3, 2.0, cf.z + 1.4, 10);
  cyl(0.52, 0.6, 0.55, "#e7dccb", cf.x + 1.8, 0.27, cf.z + 1.9);

  const bh = ANCHORS.beach;
  disc(3.6, "#f3e2ae", bh.x, bh.z, 0.014);
  const sea = disc(4.6, "#6ec6ea", bh.x + 3.4, bh.z + 3.6, 0.013); sea.scaling.x = 1.5;
  cyl(0.12, 0.12, 1.9, "#eee6d4", bh.x - 1.1, 0.95, bh.z - 0.8);
  cone(2.4, 0.6, "#ff8e7a", bh.x - 1.1, 2.0, bh.z - 0.8, 10);

  buildApartment();  // 공동주택(복도식) — 입구→공용 거실, 2층+ 방문→개인 방

  // ---- 백엔드 15개 장소를 모두 채우는 추가 건물 9곳 ----
  const shop = (key: string, wall: string, roof: string, accent: string) => {
    const a = ANCHORS[key];
    disc(a.r + 0.5, "#ead9b5", a.x, a.z, 0.012);
    box(3.2, 2.2, 2.8, wall, a.x, 1.1, a.z);
    const rf = cone(4.7, 1.6, roof, a.x, 2.9, a.z, 4); rf.rotation.y = Math.PI / 4;
    box(2.6, 0.45, 0.35, accent, a.x, 1.95, a.z + 1.45);    // 차양/간판
    box(0.95, 1.4, 0.12, "#9a6b4f", a.x, 0.7, a.z + 1.42);  // 문
    box(0.8, 0.7, 0.1, "#bfe3ef", a.x - 1.0, 1.5, a.z + 1.42); // 창
  };
  shop("grocery", "#fff1e0", "#8bc34a", "#ff8e7a");
  shop("clothing", "#fde0ef", "#ba68c8", "#f06292");
  shop("interior", "#efe2c8", "#a1887f", "#8d6e63");
  shop("concert_hall", "#ede7f6", "#7e57c2", "#ffd54f");
  shop("photo_studio", "#e0f7fa", "#26a69a", "#4dd0e1");

  shop("news_station", "#eceff1", "#5c6bc0", "#fdd835");   // 방송국 + 안테나
  { const a = ANCHORS.news_station; cyl(0.1, 0.1, 2.4, "#b0bec5", a.x + 1.0, 3.4, a.z); sphere(0.42, "#ff5252", a.x + 1.0, 4.7, a.z); }

  shop("city_hall", "#f5f5f5", "#90a4ae", "#b0bec5");      // 시청 + 돔
  { const a = ANCHORS.city_hall; cyl(0.75, 0.75, 0.5, "#eceff1", a.x, 2.5, a.z); sphere(1.3, "#cfd8dc", a.x, 3.2, a.z); }

  // 광장: 트인 포장 광장 + 중앙 기념비 + 벤치
  { const a = ANCHORS.plaza;
    disc(a.r + 0.6, "#d8cdb6", a.x, a.z, 0.014);
    cyl(0.5, 0.7, 2.2, "#c9bfa6", a.x, 1.1, a.z); sphere(0.7, "#ffd166", a.x, 2.4, a.z);
    box(1.4, 0.12, 0.4, "#a9763f", a.x - 2.2, 0.45, a.z); box(1.4, 0.12, 0.4, "#a9763f", a.x + 2.2, 0.45, a.z);
  }

  // 놀이공원: 천막 + 미니 관람차
  { const a = ANCHORS.amusement_park;
    disc(a.r + 0.4, "#e8f0c8", a.x, a.z, 0.012);
    cone(3.6, 2.8, "#ff7eae", a.x - 1.2, 1.6, a.z + 0.6, 12);
    cyl(0.12, 0.12, 2.4, "#bdbdbd", a.x + 1.6, 1.2, a.z - 0.9);
    const wheel = CreateTorus("wheel", { diameter: 2.6, thickness: 0.16, tessellation: 16 }, scene);
    wheel.material = mat("#4dd0e1"); wheel.rotation.x = Math.PI / 2;
    wheel.position.set(a.x + 1.6, 2.5, a.z - 0.9);
  }

  for (const [x, z, s] of [[-22, -14, 1.2], [21, -16, 1], [25, 5, 1.3], [-25, -1, 1.1],
    [-13, 23, 1.15], [11, 24, 0.9], [23, 18, 1], [-23, 17, 0.95], [0, -25, 1.1], [-26, 9, 1]] as number[][]) addTree(x, z, s);
  const flowerColors = ["#ff8fab", "#ffd166", "#c77dff", "#ff6b6b", "#fff3b0"];
  const rng = mulberry(42);
  for (let i = 0; i < 28; i++) {
    const ang = rng() * Math.PI * 2, rad = 6 + rng() * 20;
    sphere(0.24, flowerColors[i % flowerColors.length], Math.cos(ang) * rad, 0.12, Math.sin(ang) * rad, false);
  }
  for (const [x, y, z, s] of [[-14, 13, -10, 1.6], [8, 15, -14, 2.0], [16, 12, 8, 1.4], [-6, 14, 14, 1.8]] as number[][]) {
    const g = new TransformNode("cloud", scene);
    for (const [dx, dz, r] of [[0, 0, 1], [0.9, 0.2, 0.7], [-0.85, -0.1, 0.65]]) {
      const b = sphere(2 * r * s, "#ffffff", x + dx * s, y, z + dz * s, false);
      b.scaling.set(1.3, 0.55, 0.8); b.parent = g;
    }
    clouds.push(g);
  }
  for (const key of Object.keys(ANCHORS)) {
    const a = ANCHORS[key];
    if (key === "balcony" || key === "living_room") continue;  // 실내는 buildInterior가 라벨 담당
    a.label = makeLocLabel(key);
    a.label.position.set(a.x, a.labelY, a.z);
  }
}

function buildInterior() {
  const X = INTERIOR_X;
  box(18, 0.12, 13, "#dcc09a", X, 0.06, 0, false);
  const rug = disc(2.6, "#f2b3b3", X - 1, 0.6, 0.08); rug.scaling.x = 1.2;
  box(18, 3.4, 0.25, "#f6ecd9", X, 1.7, -6.4);
  box(0.25, 3.4, 13, "#efe2c8", X - 9, 1.7, 0);
  box(3.4, 1.6, 0.1, "#a8d8ef", X - 3.4, 1.8, -6.26, false);
  box(3.4, 1.6, 0.1, "#a8d8ef", X + 2.4, 1.8, -6.26, false);
  box(3.2, 0.55, 1.0, "#e98f7f", X - 3.4, 0.4, -1.6);
  box(3.2, 0.8, 0.22, "#de8273", X - 3.4, 0.95, -2.1);
  box(1.0, 0.55, 2.4, "#e98f7f", X - 5.6, 0.4, 0.4);
  cyl(2.0, 2.0, 0.42, "#c89f6a", X - 2.6, 0.33, 0.6);
  box(2.4, 0.5, 0.5, "#8a6a4a", X - 3.2, 0.28, 2.9);
  box(2.0, 1.1, 0.12, "#33383f", X - 3.2, 1.15, 2.95);
  box(4.2, 0.9, 1.1, "#f0f0e8", X + 5.4, 0.48, -5.5);
  box(1.1, 2.4, 1.1, "#dfe8ea", X + 8.0, 1.23, -5.5);
  box(0.55, 2.0, 1.6, "#a9763f", X - 8.6, 1.03, 3.4);
  cone(1.1, 1.1, "#5fa463", X + 7.6, 1.1, 4.6, 8);
  cyl(0.18, 0.18, 2.6, "#c9a877", X + 9, 1.3, 0);
  cyl(0.18, 0.18, 2.6, "#c9a877", X + 9, 1.3, 3);
  box(3.6, 0.12, 4.2, "#e8d3b0", X + 10.8, 0.06, 1.5, false);
  box(0.14, 0.6, 4.2, "#c9a877", X + 12.5, 0.55, 1.5);
  cyl(1.0, 1.0, 0.5, "#e7dccb", X + 10.8, 0.3, 0.6);
  const il = makeLocLabel("공동주택 거실"); il.position.set(X, 5.0, 0);
}

// ---------- 공동주택(복도식) / 개인 방(별개 씬) ----------

// 공동주택 한 채: 1층 = 공용 거실 입구, 2층부터 복도식으로 주민별 방문 배치.
const APT = { x: -2, z: -9, W: 14, D: 5, floorH: 3, floors: 4, perFloor: 7 };
const FACADE_Z = APT.z + APT.D / 2;  // 정면(+z, 마을 중심을 향함)
const DOOR_TINT = ["#c98a5a", "#a86b9a", "#5a9ab0", "#8a7ec0", "#6bae6b", "#d0a24a", "#cf7aae"];

const ROOM_BASE_X = -360, ROOM_GAP = 44;
function roomOriginX(slot: number) { return ROOM_BASE_X - slot * ROOM_GAP; }

// 주민 slot → 복도식 방문 위치 (2층부터 채움)
function doorSlotPos(slot: number) {
  const floor = 2 + Math.floor(slot / APT.perFloor);
  const col = slot % APT.perFloor;
  const x = APT.x - APT.W / 2 + 1.4 + col * ((APT.W - 2.8) / (APT.perFloor - 1));
  const y = (floor - 1) * APT.floorH + 1.0;
  return { x, y, z: FACADE_Z + 0.18, floor };
}

function buildApartment() {
  const totalH = APT.floors * APT.floorH;
  disc(APT.W / 2 + 2.4, "#ead9b5", APT.x, APT.z, 0.012);
  const body = box(APT.W, totalH, APT.D, "#f1e6cf", APT.x, totalH / 2, APT.z);
  body.metadata = { apartment: true }; houseMesh = body;
  box(APT.W + 0.8, 0.4, APT.D + 0.8, "#cdbfa0", APT.x, totalH + 0.2, APT.z);   // 옥상 슬래브
  for (let f = 2; f <= APT.floors; f++) {                                       // 복도 + 난간(2층~)
    const y = (f - 1) * APT.floorH;
    box(APT.W, 0.16, 1.3, "#d8ccb0", APT.x, y + 0.02, FACADE_Z + 0.65);
    box(APT.W, 0.5, 0.12, "#b7a98a", APT.x, y + 0.55, FACADE_Z + 1.28);
  }
  for (let f = 1; f < APT.floors; f++)                                          // 층 구분 띠
    box(APT.W + 0.3, 0.1, APT.D + 0.3, "#e6dcc2", APT.x, f * APT.floorH, APT.z);
  const ent = box(1.6, 2.0, 0.2, "#9a6b4f", APT.x, 1.0, FACADE_Z + 0.12);       // 1층 입구 → 공용 거실
  ent.metadata = { house: true };
  box(1.0, 1.0, 0.06, "#bfe3ef", APT.x - 3.2, 1.6, FACADE_Z + 0.06);
  box(1.0, 1.0, 0.06, "#bfe3ef", APT.x + 3.2, 1.6, FACADE_Z + 0.06);
  const lbl = makeLocLabel("공동주택"); lbl.position.set(APT.x, totalH + 1.4, APT.z);
}

// 주민 방문(복도, 2층+) — 클릭 시 그 주민의 개인 방으로
function addResidentDoor(e: Entry, data: Character, slot: number) {
  const p = doorSlotPos(slot);
  const door = box(0.95, 1.8, 0.16, DOOR_TINT[data.id % DOOR_TINT.length], p.x, p.y, p.z);
  door.metadata = { roomDoorOf: data.id };
  box(0.6, 0.18, 0.04, "#ffe9a8", p.x, p.y + 1.02, p.z + 0.02);   // 문패 바탕
  const plate = makeNameLabel(data.name, "#5a4632"); plate.scaling.scaleInPlace(0.5);
  plate.position.set(p.x, p.y + 1.06, p.z + 0.06);
  e.door = door;
}

// 개인 방: 마을에서 멀리 떨어진 별개 공간. 진입 시 lazy 빌드(점유자 figure 포함, 그림자 캐스트 X로 섀도 프러스텀 보호)
function buildRoom(e: Entry, data: Character) {
  const X = e.roomOrigin.x, Z = 0;
  box(16, 0.12, 12, "#dcc09a", X, 0.06, Z, false);             // 바닥
  box(16, 3.2, 0.25, "#f6ecd9", X, 1.6, Z - 6, false);         // 뒷벽
  box(0.25, 3.2, 12, "#efe2c8", X - 8, 1.6, Z, false);         // 좌벽
  box(3.2, 1.5, 0.1, "#a8d8ef", X - 1, 1.85, Z - 5.88, false); // 창
  box(2.4, 0.5, 3.4, "#9fc6e8", X - 5.2, 0.3, Z - 3.0, false); // 침대
  box(2.4, 0.85, 0.3, "#cfe5f5", X - 5.2, 0.7, Z - 4.55, false); // 헤드보드
  box(1.0, 0.18, 0.7, "#ffffff", X - 5.2, 0.62, Z - 4.0, false); // 베개
  const rug = disc(2.4, "#f2b3b3", X + 1, Z + 1.2, 0.08); rug.scaling.x = 1.2;
  box(2.2, 0.5, 1.0, "#c89f6a", X + 4.4, 0.7, Z - 4.0, false); // 책상
  box(0.8, 0.55, 0.8, "#8a6a4a", X + 4.4, 0.28, Z - 2.9, false); // 의자
  cyl(0.5, 0.6, 0.5, "#e7dccb", X + 6, 0.3, Z + 3, false);     // 화분
  cone(1.0, 1.0, "#5fa463", X + 6, 1.1, Z + 3, 8, false);
  box(1.2, 0.9, 0.08, "#ffe9a8", X - 2.2, 1.95, Z - 5.9, false); // 액자
  const lbl = makeLocLabel(data.name + "의 방"); lbl.position.set(X, 4.4, Z);
  const occ = makeFigure(data, false).root;                     // 점유자(그림자 X, 정적)
  occ.position.set(X + 1, 0, Z + 0.4); occ.rotation.y = -0.5;
  e.roomOccupant = occ; e.roomBuilt = true;
}

// ---------- Blender glTF 파이프라인 ----------

const MODEL_DIR = "models/";
const MODEL_FILES = { M: "villager_m.glb", F: "villager_f.glb", any: "villager.glb" };
const modelContainers: Record<string, any> = {};
let anyModelLoaded = false;

async function tryLoad(file: string): Promise<any | null> {
  // 파일을 먼저 받아 glTF 매직바이트("glTF")를 확인하고, 진짜 glb 일 때만 SceneLoader 에 넘긴다.
  // (dev Vite 는 SPA 폴백으로 없는 경로에 index.html=200 을 주고, SceneLoader 에 HTML 을 먹이면
  //  동기 블록에 빠지므로 이렇게 선검증한다. prod 404 도 동일하게 안전하게 건너뜀.)
  let buf: ArrayBuffer;
  try {
    const res = await fetch(MODEL_DIR + file);
    if (!res.ok) return null;
    if ((res.headers.get("content-type") || "").includes("text/html")) return null;
    buf = await res.arrayBuffer();
  } catch { return null; }
  const s = new Uint8Array(buf, 0, Math.min(4, buf.byteLength));
  if (!(s[0] === 0x67 && s[1] === 0x6c && s[2] === 0x54 && s[3] === 0x46)) return null;  // "glTF"
  const url = URL.createObjectURL(new Blob([buf]));
  try { return await SceneLoader.LoadAssetContainerAsync("", url, scene, null, ".glb"); }
  catch { return null; }
  finally { URL.revokeObjectURL(url); }
}
export async function loadModels() {
  const [m, f, any] = await Promise.all([tryLoad(MODEL_FILES.M), tryLoad(MODEL_FILES.F), tryLoad(MODEL_FILES.any)]);
  modelContainers.M = m || any; modelContainers.F = f || any; modelContainers.any = any;
  anyModelLoaded = !!(m || f || any);
  modelLoaded.set(anyModelLoaded);
  if (anyModelLoaded) console.log("[Blender] glTF 빌런 모델 로드됨");
}

function buildProcedural(root: TransformNode, data: Character, cast = true): AvatarHandle {
  // 공유 아바타 빌더에 위임 — 스냅샷이 실어준 look(sim 정본) 우선, 없으면 id 파생 폴백.
  const handle = buildAvatar(scene, data.look ?? lookFor(data), { shadow: cast ? shadow : undefined });
  handle.root.parent = root;
  return handle;
}
function buildModel(root: TransformNode, data: Character, cast = true) {
  const container = modelContainers[data.gender] || modelContainers.any;
  const inst = container.instantiateModelsToScene((n: string) => n, false);
  for (const node of inst.rootNodes) node.parent = root;
  if (cast) for (const m of root.getChildMeshes()) shadow.addShadowCaster(m);
  if (inst.animationGroups && inst.animationGroups.length) inst.animationGroups[0].start(true);
}

// ---------- 캐릭터 ----------

interface Entry {
  root: TransformNode; data: Character; target: Vector3; wanderAt: number;
  bubble: Mesh | null; bubbleUntil: number; heading: number;
  appliedLoc: string; pendingLoc: string | null; px: number; pz: number;
  door: Mesh | null; doorBubble: Mesh | null; roomSlot: number;
  roomBuilt: boolean; roomOrigin: Vector3; roomOccupant: TransformNode | null;
  roomBubble: Mesh | null; roomBubbleUntil: number; worryText: string | null;
  motion: MotionController | null;
}
const entries = new Map<number, Entry>();
let roomSlotCounter = 0;
const LABEL_Y = 2.35;

function makeFigure(data: Character, cast = true): { root: TransformNode; motion: MotionController | null } {
  const root = new TransformNode("char" + data.id, scene);
  let motion: MotionController | null = null;
  if (anyModelLoaded && (modelContainers[data.gender] || modelContainers.any)) buildModel(root, data, cast);
  else {
    const handle = buildProcedural(root, data, cast);
    // 성격을 알면 그에 맞는 모션, 없으면 id 기반 폴백.
    const code = personaFor(data.id);
    motion = new MotionController(handle, code ? styleForPersonality(code, data.id) : styleForId(data.id));
  }
  for (const m of root.getChildMeshes()) { m.metadata = { charId: data.id }; m.isPickable = true; }
  const label = makeNameLabel(data.name, data.gender === "F" ? "#ffd9e8" : "#d6ecff");
  label.position.set(0, LABEL_Y, 0); label.parent = root;
  return { root, motion };
}

// 생성 UI 에서 만든 캐릭터를 즉시 마을에 등장시킨다(외모 적용 + 피규어 등록). 백엔드 POST 는 별도.
export function spawnCharacter(data: Character, look?: AvatarLook, personaCode?: string) {
  if (look) data.look = look; // 외모는 캐릭터에 직접 — localStorage 미러 제거(sim 정본 일원화)
  if (personaCode) setPersona(data.id, personaCode); // 모션이 성격을 따라가도록
  upsertChar(data);
  const e = entries.get(data.id);
  if (e && view === "village") { cardMode.set("info"); selectedId.set(data.id); focusOn(e); }
}
function anchorPoint(locKey: string): Vector3 {
  const a = ANCHORS[locKey] || ANCHORS.fountain;
  const ang = Math.random() * Math.PI * 2;
  const rad = Math.sqrt(Math.random()) * a.r * 0.85;
  return new Vector3(a.x + Math.cos(ang) * rad, 0, a.z + Math.sin(ang) * rad);
}
function moveEntryTo(e: Entry, loc: string) {
  const p = anchorPoint(loc);
  if (Vector3.Distance(p, e.root.position) > 40) e.root.position.copyFrom(p);
  e.target = p; e.appliedLoc = loc; e.pendingLoc = null;
}
function upsertChar(data: Character) {
  let e = entries.get(data.id);
  if (!e) {
    const { root, motion } = makeFigure(data);
    const p = anchorPoint(data.location);
    root.position.copyFrom(p);
    const slot = roomSlotCounter++;
    e = { root, data, target: p.clone(), wanderAt: performance.now() + 3000 + Math.random() * 5000,
      bubble: null, bubbleUntil: 0, heading: 0, appliedLoc: data.location, pendingLoc: null, px: p.x, pz: p.z,
      door: null, doorBubble: null, roomSlot: slot, roomBuilt: false,
      roomOrigin: new Vector3(roomOriginX(slot), 0, 0), roomOccupant: null, motion,
      roomBubble: null, roomBubbleUntil: 0, worryText: null };
    entries.set(data.id, e);
    addResidentDoor(e, data, slot);
  } else {
    if (e.appliedLoc !== data.location) {
      if (curSelectedId === data.id) e.pendingLoc = data.location;
      else moveEntryTo(e, data.location);
    } else e.pendingLoc = null;
    e.data = data;
  }
}
function charByName(name: string): Entry | null {
  for (const e of entries.values()) if (e.data.name === name) return e;
  return null;
}
function showBubble(e: Entry, text: string, opts: { thought?: boolean; grey?: boolean; dur?: number } = {}) {
  if (e.bubble) e.bubble.dispose();
  const plane = makeBubble(text, opts);
  plane.position.set(0, 2.95 + plane.bubbleH / 2, 0);
  plane.parent = e.root;
  e.bubble = plane;
  e.bubbleUntil = performance.now() + (opts.dur || 2600);
}
function showRoomBubble(e: Entry, text: string) {
  if (!e.roomOccupant) return;
  if (e.roomBubble) e.roomBubble.dispose();
  const plane = makeBubble(text, { thought: true });
  plane.position.set(0, 2.95 + plane.bubbleH / 2, 0);
  plane.parent = e.roomOccupant;
  e.roomBubble = plane;
  e.roomBubbleUntil = performance.now() + 6000;  // 고민은 좀 더 길게 유지
}
function setDoorWorry(e: Entry, on: boolean) {
  if (on && !e.doorBubble && e.door) {
    const b = makeBubble("💭", { thought: true });
    b.position.set(e.door.position.x, e.door.position.y + 1.5, e.door.position.z + 0.1);
    e.doorBubble = b;
  } else if (!on && e.doorBubble) {
    e.doorBubble.dispose(); e.doorBubble = null;
  }
}

// ---------- 이벤트 연출 (병렬 트랙) ----------

interface Track { ev: EventItem; idx: number; until: number; }
const tracks: Track[] = [];
export function playEvents(events: EventItem[]) {
  for (const ev of events) {
    for (const m of ev.messages) handleMessage(m);
    if (ev.dialogue.length) { tracks.push({ ev, idx: -1, until: 0 }); while (tracks.length > 5) tracks.shift(); }
  }
}
function handleMessage(m: string) {
  const mb = m.match(/^💬\s*([^:\s]+):\s*"([^"]+)"/);
  if (mb) { const e = charByName(mb[1]); if (e) showBubble(e, mb[2], { grey: true, dur: 2400 }); return; }
  if (/💘|💗|☀️|💔|💑|🎉|⚡|🍚|🖼|📒|😤|😮‍💨|💫|📸|🍳/u.test(m)) toast(m);
}
function stepPlayback(now: number) {
  for (let i = tracks.length - 1; i >= 0; i--) {
    const tr = tracks[i];
    if (now < tr.until) continue;
    tr.idx += 1;
    if (tr.idx >= tr.ev.dialogue.length) { tracks.splice(i, 1); continue; }
    const [rawSpeaker, text] = tr.ev.dialogue[tr.idx];
    const thought = rawSpeaker.startsWith("💭");
    const name = thought ? rawSpeaker.replace(/^💭\s*/u, "") : rawSpeaker;
    const e = charByName(name);
    if (e) showBubble(e, (thought ? "💭 " : "") + text, { thought, dur: 2700 });
    tr.until = now + 2700;
  }
}

// ---------- 스냅샷 반영 ----------

let locNames: Record<string, string> = {};
let curSelectedId: number | null = null;
selectedId.subscribe((v) => { curSelectedId = v; });

export function applySnapshot(snap: Snapshot) {
  locNames = snap.locations;
  for (const c of snap.characters) upsertChar(c);
  const byKind = (k: string) => snap.bubbles.filter((b) => b.kind === k);
  const hungry = new Set(byKind("hungry").map((b) => b.char));
  for (const e of entries.values()) if (hungry.has(e.data.name) && !e.bubble) showBubble(e, "배고파요...", { grey: true, dur: 2300 });
  // 고민(worry): 집 외관 힌트 + (그 방에 들어가 있으면) 방 안 표출
  const worry = new Map(byKind("worry").map((b) => [b.char, b.text] as const));
  for (const e of entries.values()) {
    const w = worry.get(e.data.name) ?? null;
    e.worryText = w;
    setDoorWorry(e, w != null);
    if (w && currentRoomId === e.data.id && e.roomBuilt && !e.roomBubble) showRoomBubble(e, "💭 " + w);
  }
  // 꿈(dream): 잠든 캐릭터 위 — 개인 방 밖(벤치 등)도 허용
  for (const b of byKind("dream")) { const e = charByName(b.char); if (e && !e.bubble) showBubble(e, "💤 " + (b.text || "Zzz..."), { thought: true, dur: 2600 }); }
  updateSky(snap.minutes);
  for (const key of Object.keys(ANCHORS)) {
    const a = ANCHORS[key];
    if (a.label && !a.named && locNames[key] && key !== "balcony") {
      a.label.dispose(); a.label = makeLocLabel(locNames[key]); a.label.position.set(a.x, a.labelY, a.z); a.named = true;
    }
  }
}

// ---------- 하늘 색 ----------

const skyDay = Color3.FromHexString("#a9d7ee");
const skySunset = Color3.FromHexString("#f2bf8f");
const skyDusk = Color3.FromHexString("#52608f");
let lastMinutes = 600;
function lerpC(a: Color3, b: Color3, t: number) { return Color3.Lerp(a, b, Math.max(0, Math.min(1, t))); }
function updateSky(minutes: number) {
  lastMinutes = minutes;
  const h = minutes / 60;
  let c: Color3;
  if (view !== "village") c = Color3.FromHexString("#f4e8d2");
  else if (h < 5) c = skyDusk.clone();
  else if (h < 7) c = lerpC(skyDusk, skyDay, (h - 5) / 2);
  else if (h <= 16) c = skyDay.clone();
  else if (h <= 19) c = lerpC(skyDay, skySunset, (h - 16) / 3);
  else c = lerpC(skySunset, skyDusk, (h - 19) / 3.5);
  scene.clearColor = new Color4(c.r, c.g, c.b, 1);
  scene.fogColor = c;
  const dim = view !== "village" ? 0.95 : h < 6 ? 0.5 : h > 17 ? Math.max(0.55, 1 - (h - 17) * 0.09) : 1;
  sun.intensity = 1.5 * dim;
}

// ---------- 카메라 조작 ----------

const camTarget = new Vector3(0, 0.6, 0);
let camTheta = -0.6, camPhi = 1.02, camRadius = 27;
function updateCamera() {
  camera.position.set(
    camTarget.x + camRadius * Math.sin(camPhi) * Math.sin(camTheta),
    camTarget.y + camRadius * Math.cos(camPhi),
    camTarget.z + camRadius * Math.sin(camPhi) * Math.cos(camTheta));
  camera.setTarget(camTarget);
}

let autoFollow: Entry | null = null;
const FOLLOW_ENGAGE = 2.2, FOLLOW_RELEASE = 3.6;
const HOME_TARGET = new Vector3(0, 0.6, 0);
const freeTarget = HOME_TARGET.clone();
let camEngaged = false;
let reticle: Mesh, reticleMat: StandardMaterial;
let view: "village" | "interior" | "room" = "village";
let currentRoomId: number | null = null;

function panCamera(dx: number, dy: number) {
  const s = camRadius * 0.0016;
  const fx = -Math.sin(camTheta), fz = -Math.cos(camTheta);
  const rx = Math.cos(camTheta), rz = -Math.sin(camTheta);
  freeTarget.x -= (rx * dx + fx * dy) * s;
  freeTarget.z -= (rz * dx + fz * dy) * s;
  let cx = 0, lim = 26;
  if (view === "interior") { cx = INTERIOR_X; lim = 12; }
  else if (view === "room" && currentRoomId != null) { const re = entries.get(currentRoomId); cx = re ? re.roomOrigin.x : 0; lim = 8; }
  const offx = freeTarget.x - cx;
  const len = Math.hypot(offx, freeTarget.z);
  if (len > lim) { freeTarget.x = cx + offx * lim / len; freeTarget.z *= lim / len; }
}

const pointers = new Map<number, { x: number; y: number; btn: number }>();
let lastPinch = 0, downPos: { x: number; y: number; btn: number } | null = null, lastCx = 0, lastCy = 0;

function setupInput() {
  canvasEl.addEventListener("contextmenu", (e) => e.preventDefault());
  canvasEl.addEventListener("dblclick", () => {
    if (view !== "village") { setView("village"); return; }
    autoFollow = null; freeTarget.copyFrom(HOME_TARGET);
  });
  canvasEl.addEventListener("pointerdown", (e) => {
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY, btn: e.button });
    downPos = { x: e.clientX, y: e.clientY, btn: e.button };
    canvasEl.setPointerCapture(e.pointerId);
    if (pointers.size === 2) { const p = [...pointers.values()]; lastCx = (p[0].x + p[1].x) / 2; lastCy = (p[0].y + p[1].y) / 2; }
  });
  canvasEl.addEventListener("pointermove", (e) => {
    if (!pointers.has(e.pointerId)) return;
    camEngaged = true;
    const prev = pointers.get(e.pointerId)!;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY, btn: prev.btn });
    if (pointers.size === 1) {
      const dx = e.clientX - prev.x, dy = e.clientY - prev.y;
      if (prev.btn === 2 || e.shiftKey) panCamera(dx, dy);
      else { camTheta -= dx * 0.005; camPhi = Math.min(1.45, Math.max(0.25, camPhi - dy * 0.004)); }
    } else if (pointers.size === 2) {
      const p = [...pointers.values()];
      const d = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
      const cx = (p[0].x + p[1].x) / 2, cy = (p[0].y + p[1].y) / 2;
      if (lastPinch) { camRadius = Math.min(55, Math.max(10, camRadius * lastPinch / d)); panCamera(cx - lastCx, cy - lastCy); }
      lastPinch = d; lastCx = cx; lastCy = cy;
    }
  });
  const endPointer = (e: PointerEvent) => {
    pointers.delete(e.pointerId);
    if (pointers.size < 2) lastPinch = 0;
    if (downPos && downPos.btn === 0 && Math.hypot(e.clientX - downPos.x, e.clientY - downPos.y) < 6) {
      const r = canvasEl.getBoundingClientRect();
      pickAt(e.clientX - r.left, e.clientY - r.top);
    }
    downPos = null;
  };
  canvasEl.addEventListener("pointerup", endPointer);
  canvasEl.addEventListener("pointercancel", endPointer);
  canvasEl.addEventListener("wheel", (e) => {
    e.preventDefault(); camEngaged = true;
    camRadius = Math.min(55, Math.max(10, camRadius * (1 + e.deltaY * 0.001)));
  }, { passive: false });
  window.addEventListener("keydown", (e) => {
    const step = 46; let moved = true;
    if (e.key === "ArrowRight" || e.key === "d") panCamera(-step, 0);
    else if (e.key === "ArrowLeft" || e.key === "a") panCamera(step, 0);
    else if (e.key === "ArrowUp" || e.key === "w") panCamera(0, -step);
    else if (e.key === "ArrowDown" || e.key === "s") panCamera(0, step);
    else if (e.key === "Escape") { if (curSelectedId != null) selectedId.set(null); else autoFollow = null; moved = false; }
    else moved = false;
    if (moved) camEngaged = true;
  });
}

function pickAt(x: number, y: number) {
  const pick = scene.pick(x, y, (m: AbstractMesh) => m.isPickable && !!m.metadata);
  if (pick && pick.hit && pick.pickedMesh && pick.pickedMesh.metadata) {
    const md: any = pick.pickedMesh.metadata;
    if (md.roomDoorOf != null) { enterRoom(md.roomDoorOf); return; }
    if (md.apartment) { focusApartment(); return; }
    if (md.house) { setView("interior"); return; }
    if (md.board) { boardOpen.update((v) => !v); return; }
    if (md.charId != null) { const e = entries.get(md.charId); if (e) { cardMode.set("info"); selectedId.set(md.charId); if (view === "village") focusOn(e); return; } }
  }
  selectedId.set(null);
}
function focusOn(e: Entry) {
  autoFollow = null;
  e.target = e.root.position.clone();
  freeTarget.set(e.root.position.x, 1.0, e.root.position.z);
  camRadius = Math.min(camRadius, 15);
}
// 공동주택 정면(복도식 방문)을 보도록 카메라를 맞춘다 — 방문 클릭이 쉬워지게
function focusApartment() {
  autoFollow = null; selectedId.set(null);
  const totalH = APT.floors * APT.floorH;
  freeTarget.set(APT.x, totalH * 0.45, FACADE_Z);
  camRadius = 17; camPhi = 1.12; camTheta = 0;
}

export function setView(v: "village" | "interior" | "room") {
  if (view === v && v !== "room") return;
  view = v;
  viewMode.set(v);
  if (v !== "room") { currentRoomId = null; roomName.set(null); }
  setTimeout(() => {
    autoFollow = null; selectedId.set(null);
    if (v === "interior") { freeTarget.set(INTERIOR_X, 0.8, 0.5); camRadius = 14; camPhi = 1.0; }
    else if (v === "village") { freeTarget.copyFrom(HOME_TARGET); camRadius = 27; }
    camTarget.copyFrom(freeTarget);
    updateCamera(); updateSky(lastMinutes);
  }, 260);
}

// 개인 방 진입 — 방 미빌드 시 lazy 빌드 후 카메라를 그 방 원점으로 이동
export function enterRoom(id: number) {
  const e = entries.get(id);
  if (!e) return;
  if (!e.roomBuilt) buildRoom(e, e.data);
  currentRoomId = id;
  view = "room";
  viewMode.set("room");
  roomName.set(e.data.name);
  setTimeout(() => {
    autoFollow = null; selectedId.set(null);
    freeTarget.set(e.roomOrigin.x, 0.8, 0);
    camRadius = 13; camPhi = 1.0; camTheta = -0.5;
    camTarget.copyFrom(freeTarget);
    updateCamera(); updateSky(lastMinutes);
    if (e.worryText) showRoomBubble(e, "💭 " + e.worryText);
  }, 260);
}

function inFollowView(e: Entry) { return (view === "interior") === (e.root.position.x > INTERIOR_X / 2); }
function updateAutoFollow(t: number) {
  const inspecting = curSelectedId != null;
  reticle.setEnabled(camEngaged && !inspecting && view === "village");
  if (view !== "village" || inspecting || !camEngaged) { if (autoFollow) { autoFollow = null; followName.set(null); } }
  else {
    if (autoFollow) {
      const cp = autoFollow.root.position;
      freeTarget.x += cp.x - autoFollow.px; freeTarget.z += cp.z - autoFollow.pz;
      const d = Math.hypot(cp.x - freeTarget.x, cp.z - freeTarget.z);
      if (d > FOLLOW_RELEASE || !inFollowView(autoFollow)) { autoFollow = null; followName.set(null); }
    }
    if (!autoFollow) {
      let best: Entry | null = null, bd = Infinity;
      for (const e of entries.values()) {
        if (!inFollowView(e)) continue;
        const d = Math.hypot(e.root.position.x - freeTarget.x, e.root.position.z - freeTarget.z);
        if (d < bd) { bd = d; best = e; }
      }
      if (best && bd < FOLLOW_ENGAGE) { autoFollow = best; followName.set(best.data.name); }
    }
    reticle.position.set(freeTarget.x, 0.12, freeTarget.z);
    const locked = !!autoFollow;
    reticleMat.emissiveColor = locked ? Color3.FromHexString("#ffd36b") : new Color3(1, 1, 1);
    reticleMat.alpha = locked ? 0.85 : 0.4;
    reticle.scaling.setAll(locked ? 1 + Math.sin(t * 5) * 0.08 : 1);
  }
  for (const e of entries.values()) { e.px = e.root.position.x; e.pz = e.root.position.z; }
}

function angleDelta(target: number, current: number) { return Math.atan2(Math.sin(target - current), Math.cos(target - current)); }

// ---------- 초기화 + 루프 ----------

export function initVillage(canvas: HTMLCanvasElement) {
  canvasEl = canvas;
  engine = new Engine(canvas, true, { preserveDrawingBuffer: true, stencil: true });
  scene = new Scene(engine);
  scene.clearColor = Color4.FromHexString("#a9d7eeff");
  scene.ambientColor = new Color3(1, 1, 1);
  scene.fogMode = Scene.FOGMODE_LINEAR;
  scene.fogStart = 52; scene.fogEnd = 120;
  scene.fogColor = Color3.FromHexString("#a9d7ee");

  camera = new UniversalCamera("cam", new Vector3(0, 10, -20), scene);
  camera.fov = 0.87; camera.minZ = 0.1; camera.maxZ = 400;
  scene.activeCamera = camera;
  updateCamera();

  const hemi = new HemisphericLight("hemi", new Vector3(0.2, 1, 0.1), scene);
  hemi.intensity = 0.85;
  hemi.diffuse = Color3.FromHexString("#fff7e8");
  hemi.groundColor = Color3.FromHexString("#8fb573");
  sun = new DirectionalLight("sun", new Vector3(-0.6, -1, -0.45), scene);
  sun.position = new Vector3(18, 28, 12);
  sun.intensity = 1.5;
  sun.diffuse = Color3.FromHexString("#fff2d8");
  shadow = new ShadowGenerator(2048, sun);
  shadow.useBlurExponentialShadowMap = true;
  shadow.blurKernel = 16;

  buildVillage();
  buildInterior();

  reticle = CreateTorus("reticle", { diameter: 2.4, thickness: 0.16, tessellation: 36 }, scene);
  reticleMat = new StandardMaterial("retm", scene);
  reticleMat.emissiveColor = new Color3(1, 1, 1);
  reticleMat.disableLighting = true; reticleMat.alpha = 0.4;
  reticle.material = reticleMat; reticle.isPickable = false; reticle.position.y = 0.12;

  setupInput();

  let prevNow = performance.now();
  const tmp = new Vector3();
  engine.runRenderLoop(() => {
    const now = performance.now();
    const dt = Math.min(0.05, (now - prevNow) / 1000); prevNow = now;
    const t = now / 1000;
    stepPlayback(now);
    for (const e of entries.values()) {
      tmp.copyFrom(e.target).subtractInPlace(e.root.position); tmp.y = 0;
      const dist = tmp.length();
      const selected = curSelectedId === e.data.id;
      if (!selected && e.pendingLoc) moveEntryTo(e, e.pendingLoc);
      const moving = dist > 0.08;
      if (moving) {
        const speed = dist > 8 ? 4.2 : 1.7;
        tmp.normalize().scaleInPlace(Math.min(dist, speed * dt));
        e.root.position.addInPlace(tmp);
        e.heading = Math.atan2(tmp.x, tmp.z);
        e.root.rotation.y += angleDelta(e.heading, e.root.rotation.y) * 0.2;
      } else {
        if (selected) {
          const toCam = Math.atan2(camera.position.x - e.root.position.x, camera.position.z - e.root.position.z);
          e.root.rotation.y += angleDelta(toCam, e.root.rotation.y) * 0.12;
          e.wanderAt = now + 2500;
        } else if (now > e.wanderAt) {
          e.target = anchorPoint(e.data.location);
          e.wanderAt = now + 4000 + Math.random() * 7000;
        }
      }
      // 모션: 걷는 중엔 walk, 멈추면 idle(대기 모션). 모델 캐릭터(motion 없음)는 기존 보브 폴백.
      if (e.motion) {
        e.motion.set(moving ? "walk" : "idle", now);
        e.motion.update(now);
      } else {
        e.root.position.y = moving ? Math.abs(Math.sin(t * 9 + e.data.id)) * 0.07 : e.root.position.y * 0.8;
      }
      if (e.bubble && now > e.bubbleUntil) { e.bubble.dispose(); e.bubble = null; }
      if (e.roomBubble && now > e.roomBubbleUntil) { e.roomBubble.dispose(); e.roomBubble = null; }
    }
    for (const c of clouds) { c.position.x += dt * 0.25; if (c.position.x > 38) c.position.x = -76; }
    if (fountainWater) fountainWater.position.y = 0.32 + Math.sin(t * 2.2) * 0.03;
    updateAutoFollow(t);
    Vector3.LerpToRef(camTarget, freeTarget, 1 - Math.pow(0.002, dt), camTarget);
    updateCamera();
    scene.render();
  });
  window.addEventListener("resize", () => engine.resize());
}

// 검증/디버깅 핸들
(window as any).__poc = {
  followByName(name: string) { const e = charByName(name); if (e) { camEngaged = true; freeTarget.set(e.root.position.x, 1.0, e.root.position.z); camRadius = Math.min(camRadius, 14); } },
  isFollowing(name: string) { return !!(autoFollow && autoFollow.data.name === name); },
  charCount() { return entries.size; },
  modelLoaded() { return anyModelLoaded; },
  enterHouse() { setView("interior"); },
  enterRoom(name: string) { const e = charByName(name); if (e) enterRoom(e.data.id); },
  exitRoom() { setView("village"); },
  roomBuilt(name: string) { const e = charByName(name); return !!(e && e.roomBuilt); },
  mockWorry(name: string, text: string) { const e = charByName(name); if (e) { e.worryText = text; setDoorWorry(e, true); if (currentRoomId === e.data.id && e.roomBuilt) showRoomBubble(e, "💭 " + text); } },
  view() { return view; },
};
