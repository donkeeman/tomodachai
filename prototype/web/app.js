// AI 우리 동네 이야기 — Babylon.js 3D 마을 뷰
// 백엔드(web_server.py)가 시뮬레이션을 돌리고, 여기서는 그리기/연출만 담당한다.
// 3D 레이어는 Babylon(UMD 전역 BABYLON), UI 패널은 DOM 그대로.
// 캐릭터/소품은 Blender → glTF(.glb)를 models/ 에 두면 자동 로드, 없으면 프리미티브 폴백.
"use strict";

const canvas = document.getElementById("renderCanvas");
const engine = new BABYLON.Engine(canvas, true, { preserveDrawingBuffer: true, stencil: true });
const scene = new BABYLON.Scene(engine);
scene.clearColor = BABYLON.Color4.FromHexString("#a9d7eeff");
scene.ambientColor = new BABYLON.Color3(1, 1, 1);
scene.fogMode = BABYLON.Scene.FOGMODE_LINEAR;
scene.fogStart = 40; scene.fogEnd = 110;
scene.fogColor = BABYLON.Color3.FromHexString("#a9d7ee");

// ---------- 카메라 (수동 구면 좌표: 회전/줌/패닝/따라가기 직접 제어) ----------

const camera = new BABYLON.UniversalCamera("cam", new BABYLON.Vector3(0, 10, -20), scene);
camera.fov = 0.87;
camera.minZ = 0.1;
camera.maxZ = 400;
scene.activeCamera = camera;

const camTarget = new BABYLON.Vector3(0, 0.6, 0);
let camTheta = -0.6, camPhi = 1.02, camRadius = 27;
function updateCamera() {
  camera.position.set(
    camTarget.x + camRadius * Math.sin(camPhi) * Math.sin(camTheta),
    camTarget.y + camRadius * Math.cos(camPhi),
    camTarget.z + camRadius * Math.sin(camPhi) * Math.cos(camTheta),
  );
  camera.setTarget(camTarget);
}
updateCamera();

// ---------- 조명 / 그림자 ----------

const hemi = new BABYLON.HemisphericLight("hemi", new BABYLON.Vector3(0.2, 1, 0.1), scene);
hemi.intensity = 0.85;
hemi.diffuse = BABYLON.Color3.FromHexString("#fff7e8");
hemi.groundColor = BABYLON.Color3.FromHexString("#8fb573");

const sun = new BABYLON.DirectionalLight("sun", new BABYLON.Vector3(-0.6, -1, -0.45), scene);
sun.position = new BABYLON.Vector3(18, 28, 12);
sun.intensity = 1.5;
sun.diffuse = BABYLON.Color3.FromHexString("#fff2d8");
const shadow = new BABYLON.ShadowGenerator(2048, sun);
shadow.useBlurExponentialShadowMap = true;
shadow.blurKernel = 16;

// ---------- 머티리얼/메시 헬퍼 ----------

const matCache = new Map();
function mat(hex) {
  if (matCache.has(hex)) return matCache.get(hex);
  const m = new BABYLON.StandardMaterial("m" + hex, scene);
  m.diffuseColor = BABYLON.Color3.FromHexString(hex);
  m.specularColor = new BABYLON.Color3(0, 0, 0);  // 무광 로우폴리 톤
  matCache.set(hex, m);
  return m;
}
function place(m, x, y, z, cast) {
  m.position.set(x, y, z);
  m.receiveShadows = true;
  if (cast !== false) shadow.addShadowCaster(m);
  return m;
}
function box(w, h, d, hex, x, y, z, cast) {
  const m = BABYLON.MeshBuilder.CreateBox("box", { width: w, height: h, depth: d }, scene);
  m.material = mat(hex);
  return place(m, x, y, z, cast);
}
function cyl(dTop, dBot, h, hex, x, y, z, cast) {
  const m = BABYLON.MeshBuilder.CreateCylinder("cyl",
    { diameterTop: dTop, diameterBottom: dBot, height: h, tessellation: 18 }, scene);
  m.material = mat(hex);
  return place(m, x, y, z, cast);
}
function cone(d, h, hex, x, y, z, sides, cast) {
  const m = BABYLON.MeshBuilder.CreateCylinder("cone",
    { diameterTop: 0, diameterBottom: d, height: h, tessellation: sides || 16 }, scene);
  m.material = mat(hex);
  return place(m, x, y, z, cast);
}
function sphere(d, hex, x, y, z, cast) {
  const m = BABYLON.MeshBuilder.CreateSphere("sph", { diameter: d, segments: 12 }, scene);
  m.material = mat(hex);
  return place(m, x, y, z, cast);
}
function disc(radius, hex, x, z, y) {
  const m = BABYLON.MeshBuilder.CreateDisc("disc", { radius, tessellation: 36 }, scene);
  m.material = mat(hex);
  m.material.backFaceCulling = false;
  m.rotation.x = Math.PI / 2;
  m.position.set(x, y || 0.012, z);
  m.receiveShadows = true;
  return m;
}

// ---------- 텍스트 평면 (이름표 / 말풍선): 캔버스 그려서 빌보드 ----------

function makeTextPlane(drawFn, texW, texH, planeW, planeH) {
  const dt = new BABYLON.DynamicTexture("dt", { width: texW, height: texH }, scene, false);
  dt.hasAlpha = true;
  drawFn(dt.getContext(), texW, texH);
  dt.update(false);
  const plane = BABYLON.MeshBuilder.CreatePlane("txt", { width: planeW, height: planeH }, scene);
  const m = new BABYLON.StandardMaterial("txtm", scene);
  m.diffuseTexture = dt;
  m.diffuseTexture.hasAlpha = true;
  m.useAlphaFromDiffuseTexture = true;
  m.transparencyMode = BABYLON.Material.MATERIAL_ALPHABLEND;
  m.emissiveColor = new BABYLON.Color3(1, 1, 1);
  m.disableLighting = true;
  m.backFaceCulling = false;
  plane.material = m;
  plane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;
  plane.isPickable = false;
  plane.renderingGroupId = 1;  // 지오메트리 위에 그림
  return plane;
}

function makeNameLabel(text, color) {
  return makeTextPlane((g, w, h) => {
    g.clearRect(0, 0, w, h);
    g.font = "700 40px 'Apple SD Gothic Neo', system-ui, sans-serif";
    g.textAlign = "center"; g.textBaseline = "middle";
    g.lineWidth = 8; g.strokeStyle = "rgba(40,40,40,.9)";
    g.strokeText(text, w / 2, h / 2);
    g.fillStyle = color || "#ffffff";
    g.fillText(text, w / 2, h / 2);
  }, 256, 72, 2.4, 0.68);
}

function makeLocLabel(text) {
  return makeTextPlane((g, w, h) => {
    g.clearRect(0, 0, w, h);
    g.font = "700 40px 'Apple SD Gothic Neo', system-ui, sans-serif";
    g.textAlign = "center"; g.textBaseline = "middle";
    g.lineWidth = 9; g.strokeStyle = "rgba(50,80,50,.7)";
    g.strokeText(text, w / 2, h / 2);
    g.fillStyle = "#fdfbe8";
    g.fillText(text, w / 2, h / 2);
  }, 320, 76, 3.0, 0.71);
}

function wrapLines(g, text, maxW) {
  const lines = []; let cur = "";
  for (const ch of text) {
    if (ch === "\n") { lines.push(cur); cur = ""; continue; }
    if (g.measureText(cur + ch).width > maxW && cur) { lines.push(cur); cur = ch; }
    else cur += ch;
  }
  if (cur) lines.push(cur);
  return lines;
}

function makeBubble(text, opts) {
  opts = opts || {};
  const probe = document.createElement("canvas").getContext("2d");
  const font = "500 30px 'Apple SD Gothic Neo', system-ui, sans-serif";
  probe.font = font;
  const lines = wrapLines(probe, text, 360);
  const lineH = 40, pad = 26;
  const textW = Math.max(80, ...lines.map((l) => probe.measureText(l).width));
  const w = Math.ceil(textW + pad * 2), h = Math.ceil(lines.length * lineH + pad * 2 - 10);
  const bg = opts.thought ? "rgba(255,246,216,.97)" : opts.grey ? "rgba(238,238,238,.97)" : "rgba(255,255,255,.97)";
  const plane = makeTextPlane((g) => {
    g.clearRect(0, 0, w, h);
    const r = 22;
    g.beginPath();
    if (g.roundRect) g.roundRect(3, 3, w - 6, h - 6, r); else g.rect(3, 3, w - 6, h - 6);
    g.fillStyle = bg; g.fill();
    g.lineWidth = 3;
    g.strokeStyle = opts.thought ? "#e0b73e" : "rgba(70,70,70,.5)";
    g.stroke();
    g.font = font; g.fillStyle = "#333"; g.textBaseline = "middle";
    lines.forEach((l, i) => g.fillText(l, pad, pad + 20 + i * lineH));
  }, w, h, w * 0.011, h * 0.011);
  plane.bubbleH = h * 0.011;
  return plane;
}

// ---------- 마을 레이아웃 ----------

const INTERIOR_X = 200;  // 실내(공동주택)는 마을에서 멀리 떨어진 별개 공간
const ANCHORS = {
  fountain:    { x: 0, z: 0, r: 3.0, labelY: 3.2 },
  living_room: { x: INTERIOR_X, z: 0, r: 4.6, labelY: 5.2 },
  balcony:     { x: INTERIOR_X + 10.8, z: 1.5, r: 1.6, labelY: 3.0 },
  park:        { x: 10, z: -7, r: 3.4, labelY: 4.6 },
  cafe:        { x: -10.5, z: 6.5, r: 2.4, labelY: 4.2 },
  beach:       { x: 9.5, z: 10, r: 3.0, labelY: 3.4 },
};

let boardMesh = null, houseMesh = null;
const hitHouse = [];
let fountainWater = null;
const clouds = [];

function mulberry(seed) {
  let a = seed;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function addTree(x, z, s) {
  s = s || 1;
  cyl(0.36 * s, 0.48 * s, 0.9 * s, "#8a5a3b", x, 0.45 * s, z);
  cone(1.9 * s, 1.5 * s, "#5fa463", x, 1.55 * s, z, 8);
  cone(1.4 * s, 1.15 * s, "#74bf72", x, 2.35 * s, z, 8);
}

function buildVillage() {
  disc(30, "#9ed487", 0, 0, 0.01);

  // 분수대
  disc(4.4, "#ead9b5", 0, 0, 0.02);
  cyl(4.4, 4.8, 0.5, "#b8c4cc", 0, 0.25, 0);
  fountainWater = cyl(3.8, 3.8, 0.46, "#7fd3f0", 0, 0.32, 0, false);
  cyl(0.56, 0.8, 1.3, "#b8c4cc", 0, 0.9, 0);
  sphere(0.8, "#9fdef5", 0, 1.7, 0);

  // 공원 + 랭킹 게시판
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
  const bl = makeLocLabel("🏆 랭킹"); bl.scaling.scaleInPlace(0.62);
  bl.position.set(pk.x - 3.1, 2.5, pk.z + 2.2);

  // 카페
  const cf = ANCHORS.cafe;
  disc(2.9, "#ead9b5", cf.x, cf.z, 0.02);
  box(3.4, 2.4, 3, "#fff1e0", cf.x, 1.2, cf.z);
  box(3.8, 0.22, 3.4, "#b97f5c", cf.x, 2.5, cf.z);
  const awn = box(3.6, 0.1, 1.3, "#ff8e7a", cf.x, 2.2, cf.z + 1.95); awn.rotation.x = 0.35;
  cyl(0.12, 0.12, 1.9, "#ddd6c8", cf.x + 2.3, 0.95, cf.z + 1.4);
  cone(2.3, 0.55, "#ffd166", cf.x + 2.3, 2.0, cf.z + 1.4, 10);
  cyl(0.52, 0.6, 0.55, "#e7dccb", cf.x + 1.8, 0.27, cf.z + 1.9);

  // 해변
  const bh = ANCHORS.beach;
  disc(3.6, "#f3e2ae", bh.x, bh.z, 0.014);
  const sea = disc(4.6, "#6ec6ea", bh.x + 3.4, bh.z + 3.6, 0.013); sea.scaling.x = 1.5;
  cyl(0.12, 0.12, 1.9, "#eee6d4", bh.x - 1.1, 0.95, bh.z - 0.8);
  cone(2.4, 0.6, "#ff8e7a", bh.x - 1.1, 2.0, bh.z - 0.8, 10);

  // 공동주택 외관 (클릭 시 내부 공간으로 입장) — 마을 좌표
  const hp = { x: -11, z: -8 };
  disc(4.2, "#ead9b5", hp.x, hp.z, 0.012);
  houseMesh = box(6, 3, 4.6, "#f5e6c8", hp.x, 1.5, hp.z);
  houseMesh.metadata = { house: true };
  const roof = cone(8.8, 2.2, "#d98f6e", hp.x, 4.1, hp.z, 4); roof.rotation.y = Math.PI / 4;
  const door = box(1.1, 1.7, 0.15, "#9a6b4f", hp.x + 1.2, 0.85, hp.z + 2.33);
  door.metadata = { house: true };
  hitHouse.push(houseMesh, door);
  box(1.2, 1.0, 0.1, "#bfe3ef", hp.x - 1.4, 1.9, hp.z + 2.32);
  const hl = makeLocLabel("공동주택 🚪클릭"); hl.position.set(hp.x, 6.0, hp.z);

  // 가로수 + 꽃 + 구름
  for (const [x, z, s] of [[-3, -12, 1.2], [4, -11, 1], [16, 2, 1.3], [-16, -1, 1.1],
                           [-4, 13, 1.15], [3, 14, 0.9], [15, -13, 1], [-15, 12, 0.95]]) addTree(x, z, s);
  const flowerColors = ["#ff8fab", "#ffd166", "#c77dff", "#ff6b6b", "#fff3b0"];
  const rng = mulberry(42);
  for (let i = 0; i < 28; i++) {
    const ang = rng() * Math.PI * 2, rad = 6 + rng() * 20;
    sphere(0.24, flowerColors[i % flowerColors.length], Math.cos(ang) * rad, 0.12, Math.sin(ang) * rad, false);
  }
  for (const [x, y, z, s] of [[-14, 13, -10, 1.6], [8, 15, -14, 2.0], [16, 12, 8, 1.4], [-6, 14, 14, 1.8]]) {
    const g = new BABYLON.TransformNode("cloud", scene);
    for (const [dx, dz, r] of [[0, 0, 1], [0.9, 0.2, 0.7], [-0.85, -0.1, 0.65]]) {
      const b = sphere(2 * r * s, "#ffffff", x + dx * s, y, z + dz * s, false);
      b.scaling.set(1.3, 0.55, 0.8); b.parent = g;
    }
    clouds.push(g);
  }

  // 장소 라벨
  for (const key of Object.keys(ANCHORS)) {
    const a = ANCHORS[key];
    if (key === "balcony") continue;
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
  // 발코니
  cyl(0.18, 0.18, 2.6, "#c9a877", X + 9, 1.3, 0);
  cyl(0.18, 0.18, 2.6, "#c9a877", X + 9, 1.3, 3);
  box(3.6, 0.12, 4.2, "#e8d3b0", X + 10.8, 0.06, 1.5, false);
  box(0.14, 0.6, 4.2, "#c9a877", X + 12.5, 0.55, 1.5);
  cyl(1.0, 1.0, 0.5, "#e7dccb", X + 10.8, 0.3, 0.6);
  const il = makeLocLabel("공동주택 거실"); il.position.set(X, 5.0, 0);
}

// ---------- Blender glTF 파이프라인 ----------
// models/ 에 .glb 를 두면 자동 사용. 우선순위: 성별 모델 → 공용 모델 → 프리미티브.
// Blender: File ▸ Export ▸ glTF 2.0 (.glb), +Y Up, 본/애니메이션 포함 가능. (web/models/README.md 참고)

const MODEL_DIR = "models/";
const MODEL_FILES = { M: "villager_m.glb", F: "villager_f.glb", any: "villager.glb" };
const modelContainers = {};   // gender -> AssetContainer | null (null=없음, 폴백)
let anyModelLoaded = false;

async function tryLoadContainer(file) {
  try {
    return await BABYLON.SceneLoader.LoadAssetContainerAsync(MODEL_DIR, file, scene);
  } catch (e) {
    return null;  // 파일 없음/로드 실패 → 폴백
  }
}

async function loadVillagerModels() {
  const [m, f, any] = await Promise.all([
    tryLoadContainer(MODEL_FILES.M),
    tryLoadContainer(MODEL_FILES.F),
    tryLoadContainer(MODEL_FILES.any),
  ]);
  modelContainers.M = m || any;
  modelContainers.F = f || any;
  modelContainers.any = any;
  anyModelLoaded = !!(m || f || any);
  if (anyModelLoaded) console.log("[Blender] glTF 빌런 모델 로드됨");
}

const PALETTE = ["#e57373", "#64b5f6", "#81c784", "#ffb74d", "#ba68c8", "#4db6ac",
                 "#f06292", "#7986cb", "#a1887f", "#90a4ae", "#dce775", "#4dd0e1"];
const HAIR = ["#4e342e", "#263238", "#6d4c41", "#8d6e63", "#3e2723"];

function buildProceduralFigure(root, data) {
  const color = PALETTE[(data.id - 1) % PALETTE.length];
  const body = BABYLON.MeshBuilder.CreateCapsule("body", { radius: 0.42, height: 1.5 }, scene);
  body.material = mat(color); body.position.y = 0.85; body.parent = root;
  shadow.addShadowCaster(body);
  const head = sphere(0.68, "#ffe0bd", 0, 1.6, 0); head.parent = root;
  const hairColor = HAIR[(data.id * 3 + 1) % HAIR.length];
  if (data.gender === "F") {
    const h = sphere(0.74, hairColor, 0, 1.7, -0.03); h.scaling.y = 0.85; h.parent = root;
  } else {
    const h = BABYLON.MeshBuilder.CreateSphere("hair", { diameter: 0.71, segments: 12, slice: 0.5 }, scene);
    h.material = mat(hairColor); h.position.set(0, 1.62, 0); h.parent = root;
  }
  for (const dx of [-0.12, 0.12]) {
    const eye = sphere(0.07, "#222222", dx, 1.64, 0.31, false); eye.parent = root;
  }
  return body;
}

function buildModelFigure(root, data) {
  const container = modelContainers[data.gender] || modelContainers.any;
  const inst = container.instantiateModelsToScene((n) => n, false);
  for (const node of inst.rootNodes) node.parent = root;
  for (const m of root.getChildMeshes()) shadow.addShadowCaster(m);
  if (inst.animationGroups && inst.animationGroups.length) inst.animationGroups[0].start(true);
  root.modelInstance = inst;
  return root.getChildMeshes()[0];
}

// ---------- 캐릭터 ----------

const entries = new Map();
const labelOffset = 2.35;

function makeFigure(data) {
  const root = new BABYLON.TransformNode("char" + data.id, scene);
  if (anyModelLoaded && (modelContainers[data.gender] || modelContainers.any)) buildModelFigure(root, data);
  else buildProceduralFigure(root, data);
  for (const m of root.getChildMeshes()) { m.metadata = { charId: data.id }; m.isPickable = true; }
  const label = makeNameLabel(data.name, data.gender === "F" ? "#ffd9e8" : "#d6ecff");
  label.position.set(0, labelOffset, 0);
  label.parent = root;
  return root;
}

function anchorPoint(locKey) {
  const a = ANCHORS[locKey] || ANCHORS.fountain;
  const ang = Math.random() * Math.PI * 2;
  const rad = Math.sqrt(Math.random()) * a.r * 0.85;
  return new BABYLON.Vector3(a.x + Math.cos(ang) * rad, 0, a.z + Math.sin(ang) * rad);
}

function moveEntryTo(e, loc) {
  const p = anchorPoint(loc);
  if (BABYLON.Vector3.Distance(p, e.root.position) > 40) e.root.position.copyFrom(p);
  e.target = p; e.appliedLoc = loc; e.pendingLoc = null;
}

function upsertChar(data) {
  let e = entries.get(data.id);
  if (!e) {
    const root = makeFigure(data);
    const p = anchorPoint(data.location);
    root.position.copyFrom(p);
    e = { root, data, target: p.clone(), wanderAt: performance.now() + 3000 + Math.random() * 5000,
          bubble: null, heading: 0, appliedLoc: data.location, pendingLoc: null, px: p.x, pz: p.z };
    entries.set(data.id, e);
  } else {
    if (e.appliedLoc !== data.location) {
      if (cardCharId === data.id && !cardEl.hidden) e.pendingLoc = data.location;
      else moveEntryTo(e, data.location);
    } else e.pendingLoc = null;
    e.data = data;
  }
}

function charByName(name) {
  for (const e of entries.values()) if (e.data.name === name) return e;
  return null;
}

function showBubble(e, text, opts) {
  if (e.bubble) e.bubble.dispose();
  const plane = makeBubble(text, opts);
  plane.position.set(0, 2.95 + plane.bubbleH / 2, 0);
  plane.parent = e.root;
  e.bubble = plane;
  e.bubbleUntil = performance.now() + ((opts && opts.dur) || 2600);
}

// ---------- 이벤트 연출 (병렬 트랙: 시야에 들어온 대화는 항상 보임) ----------

const tracks = [];
function acceptEvent(ev) {
  logEvent(ev);
  for (const m of ev.messages) handleMessage(m);
  if (ev.dialogue.length) { tracks.push({ ev, idx: -1, until: 0 }); while (tracks.length > 5) tracks.shift(); }
}
function handleMessage(m) {
  const mb = m.match(/^💬\s*([^:\s]+):\s*"([^"]+)"/);
  if (mb) { const e = charByName(mb[1]); if (e) showBubble(e, mb[2], { grey: true, dur: 2400 }); return; }
  if (/💘|💗|☀️|💔|💑|🎉|⚡|🍚|🖼|📒|😤|😮‍💨|💫|📸|🍳/u.test(m)) toast(m);
}
function stepPlayback(now) {
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

// ---------- DOM: HUD / 로그 / 토스트 / 카드 ----------

const hudEl = document.getElementById("hud");
const hudSub = hudEl.querySelector(".sub");
const logEl = document.getElementById("log");
const toastEl = document.getElementById("toast");
const cardEl = document.getElementById("card");
let toastTimer = null;

function toast(text) {
  toastEl.textContent = text; toastEl.style.opacity = "1";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toastEl.style.opacity = "0"; }, 3400);
}
function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function logEvent(ev) {
  const div = document.createElement("div");
  div.className = "ev";
  let html = `<span class="time">Day ${ev.day} ${ev.clock}</span><br>`;
  if (ev.scene) html += `<span class="scene">${escapeHtml(ev.scene)}</span><br>`;
  for (const m of ev.messages) html += `<span class="msg">${escapeHtml(m)}</span><br>`;
  for (const [s, t] of ev.dialogue) html += `<span class="line"><span class="who">${escapeHtml(s)}</span> ${escapeHtml(t)}</span><br>`;
  div.innerHTML = html;
  logEl.appendChild(div);
  while (logEl.children.length > 90) logEl.removeChild(logEl.children[1]);
  logEl.scrollTop = logEl.scrollHeight;
}

let locNames = {}, foods = [], rankings = null;
let cardCharId = null, cardMode = "info";

function gaugeRow(label, pct, color) {
  return `<div class="row gauge"><span class="glabel">${label}</span>` +
         `<span class="bar"><i style="width:${pct}%;background:${color}"></i></span></div>`;
}
const TIER_ORDER = { favorite: 0, like: 1, normal: 2, dislike: 3, worst: 4 };
const TIER_EMOJI = { favorite: "💖", like: "🙂", normal: "😐", dislike: "😖", worst: "🤢" };
function dexChips(data) {
  const dex = (data.dex || []).slice().sort((a, b) => TIER_ORDER[a.tier] - TIER_ORDER[b.tier]);
  const chips = dex.map((d) => `${TIER_EMOJI[d.tier]}${escapeHtml(d.name)}`).join(" ");
  const unknown = foods.length - dex.length;
  if (!dex.length) return `아직 먹여본 음식이 없어요 (???×${unknown})`;
  return chips + (unknown > 0 ? ` · ???×${unknown}` : "");
}

function showCard(data) {
  if (cardCharId !== data.id) cardMode = "info";
  cardCharId = data.id;
  cardEl.innerHTML = `<div class="cstats"></div><div class="cacts"></div>`;
  renderCardStats(data); renderCardActions(data);
  cardEl.hidden = false;
}
function renderCardStats(data) {
  const box = cardEl.querySelector(".cstats");
  if (!box) return;
  const heart = data.lover ? `❤️ 연인: ${data.lover}` : (data.crushes.length ? `💘 반함: ${data.crushes.join(", ")}` : "");
  box.innerHTML = `
    <h2>${data.gender === "F" ? "👩" : "👨"} ${escapeHtml(data.name)}</h2>
    <div class="row">기분: <b>${escapeHtml(data.mood)}</b>${data.satisfaction < 0 ? " · <b>😱 절망</b>" : ""}
      · <b>${escapeHtml(locNames[data.location] || data.location)}</b></div>
    ${gaugeRow("🧡 만족도", Math.max(0, Math.min(100, data.satisfaction)),
               data.satisfaction < 20 ? "#e57373" : data.satisfaction < 50 ? "#ffb74d" : "#7ec77e")}
    ${gaugeRow("🍚 배고픔", Math.max(0, Math.min(100, data.hunger)),
               data.hunger >= 70 ? "#e57373" : data.hunger >= 40 ? "#ffb74d" : "#a5d6a7")}
    ${heart ? `<div class="row">${escapeHtml(heart)}</div>` : ""}
    ${data.best_friend ? `<div class="row">⭐ 베프: ${escapeHtml(data.best_friend)}</div>` : ""}
    ${data.enemy ? `<div class="row">⚡ 앙숙: ${escapeHtml(data.enemy)}</div>` : ""}
    <div class="sect">👥 친구 순위</div>
    ${(data.friends && data.friends.length)
      ? data.friends.map((f, i) => `<div class="row small">${i + 1}. <b>${escapeHtml(f.name)}</b> · ${escapeHtml(f.label)}</div>`).join("")
      : `<div class="row small">아직 만난 주민이 없어요</div>`}
    <div class="sect">🍽 좋아하는 음식 (도감)</div>
    <div class="row small">${dexChips(data)}</div>`;
}
function renderCardActions(data) {
  const box = cardEl.querySelector(".cacts");
  if (!box) return;
  if (cardMode === "foods" && foods.length) {
    const btns = foods.map((f, i) => `<button data-fid="${i}" class="${data.food_eaten && data.food_eaten[i] ? "tried" : ""}">${escapeHtml(f)}</button>`).join("");
    box.innerHTML = `<div class="foods">${btns}<button class="back">← 돌아가기</button></div>`;
    box.querySelector(".back").onclick = () => { cardMode = "info"; showCard(data); };
    for (const b of box.querySelectorAll("button[data-fid]")) b.onclick = () => feedChar(data.id, parseInt(b.dataset.fid, 10));
  } else if (cardMode === "tools") {
    box.innerHTML = `<div class="foods">
      <button class="wide" data-tool="camera">📷 카메라 — 사진 찍어오기</button>
      <button class="wide" data-tool="frying_pan">🍳 프라이팬 — 즉흥 요리</button>
      <button class="back">← 돌아가기</button></div>`;
    box.querySelector(".back").onclick = () => { cardMode = "info"; showCard(data); };
    for (const b of box.querySelectorAll("button[data-tool]")) b.onclick = () => giveTool(data.id, b.dataset.tool);
  } else {
    box.innerHTML = `<div class="actions">
      <button class="feed">🍙 밥 주기</button>
      <button class="tools">🎁 도구</button></div>`;
    box.querySelector(".feed").onclick = () => { cardMode = "foods"; renderCardActions(data); };
    box.querySelector(".tools").onclick = () => { cardMode = "tools"; renderCardActions(data); };
  }
}

async function postJson(url, body) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return res.json();
}
async function feedChar(id, foodId) {
  try {
    const out = await postJson("/api/feed", { char_id: id, food_id: foodId });
    if (out.error) { toast("⚠️ " + out.error); return; }
    const e = entries.get(id);
    if (e) { const m = out.message.match(/→ (.+)$/); showBubble(e, m ? m[1] : out.message, { grey: true, dur: 3400 }); }
  } catch (err) { toast("⚠️ 서버 연결 실패"); }
  cardMode = "info";
  const ce = entries.get(id); if (ce) showCard(ce.data);
  poll();
}
async function giveTool(id, tool) {
  try {
    const out = await postJson("/api/give", { char_id: id, tool });
    if (out.error) { toast("⚠️ " + out.error); return; }
    if (out.messages && out.messages.length) toast(out.messages[out.messages.length - 1]);
  } catch (err) { toast("⚠️ 서버 연결 실패"); }
  cardMode = "info";
  const ce = entries.get(id); if (ce) showCard(ce.data);
  poll();
}

// ---------- 기록(사진/요리) + 랭킹 + 저장/리셋 ----------

const albumEl = document.getElementById("album");
let photos = [], dishes = [], lastAlbumJson = "";
function renderAlbum() {
  const ph = photos.length
    ? photos.map((p) => `<div class="item">🖼 <b>${escapeHtml(p.title)}</b><br><span class="sub">Day ${p.day} · ${escapeHtml(p.author)} 촬영 · 피사체: ${escapeHtml(p.subject || "?")}</span></div>`).join("")
    : `<div class="item empty">아직 사진이 없어요 — 주민에게 📷 카메라를 줘 보세요</div>`;
  const di = dishes.length
    ? dishes.map((d) => `<div class="item">🍳 <b>${escapeHtml(d.dish)}</b> <span class="sub">Day ${d.day} · ${escapeHtml(d.author)}</span></div>`).join("")
    : `<div class="item empty">아직 요리가 없어요 — 🍳 프라이팬을 줘 보세요</div>`;
  albumEl.innerHTML = `<h3>📒 마을 기록</h3><div class="cat">🖼 사진 갤러리</div>${ph}<div class="cat">🍳 요리 카탈로그</div>${di}<button class="closeb">닫기</button>`;
  albumEl.querySelector(".closeb").onclick = () => { albumEl.hidden = true; };
}
document.getElementById("albumbtn").onclick = () => { if (albumEl.hidden) { renderAlbum(); albumEl.hidden = false; } else albumEl.hidden = true; };
document.getElementById("savebtn").onclick = async () => {
  try { const out = await postJson("/api/save", {}); toast(out.error ? "⚠️ " + out.error : out.message); }
  catch (err) { toast("⚠️ 서버 연결 실패"); }
};
document.getElementById("resetbtn").onclick = async () => {
  if (!window.confirm("정말 새 마을로 시작할까요? 지금 마을은 사라집니다!")) return;
  try { await postJson("/api/reset", {}); location.reload(); } catch (err) { toast("⚠️ 서버 연결 실패"); }
};

const boardEl = document.getElementById("rankboard");
let lastRankJson = "";
function renderBoard() {
  if (!rankings) return;
  const sec = (title, arr) => `<div class="cat">${title}</div>` +
    (arr && arr.length ? arr.map((x, i) => `<div class="item">${["🥇", "🥈", "🥉"][i] || "·"} ${escapeHtml(x)}</div>`).join("") : `<div class="item empty">아직 없음</div>`);
  const empty = !((rankings.best_couple || []).length || (rankings.popular_m || []).length || (rankings.popular_f || []).length || (rankings.fighters || []).length);
  boardEl.innerHTML = `<h3>🏆 마을 랭킹보드</h3>
    ${empty ? `<div class="item empty" style="text-align:center">마을이 아직 어려요!<br>반함·커플·싸움이 쌓이면 채워집니다.</div>` : ""}
    ${sec("💑 베스트 커플", rankings.best_couple)}
    ${sec("💘 인기 많은 남자", rankings.popular_m)}
    ${sec("💘 인기 많은 여자", rankings.popular_f)}
    ${sec("💢 앙숙 매치", rankings.fighters)}
    <button class="closeb">닫기</button>`;
  boardEl.querySelector(".closeb").onclick = () => { boardEl.hidden = true; };
}
function toggleBoard() { if (boardEl.hidden) { renderBoard(); boardEl.hidden = false; } else boardEl.hidden = true; }

// ---------- 고백 허락 패널 ----------

const bubbleEl = document.getElementById("bubblebox");
let bubbleBusy = false, lastBubbles = [], knownBubbleCount = 0;
function renderBubbles(all) {
  lastBubbles = all || [];
  const bubbles = lastBubbles.map((b, i) => ({ ...b, _idx: i })).filter((b) => b.kind === "confess_request");
  if (!bubbles.length) { bubbleEl.hidden = true; return; }
  const b = bubbles[0];
  const more = bubbles.length > 1 ? ` (+${bubbles.length - 1}건 대기)` : "";
  bubbleEl.innerHTML = `<div class="title">💗 말풍선 도착!${more}</div>
    <div class="text">${escapeHtml(b.text || `${b.char}이(가) 할 말이 있어요`)}</div>
    <div class="btns">
      <button class="yes" ${bubbleBusy ? "disabled" : ""}>${bubbleBusy ? "두근두근..." : "💕 해!"}</button>
      <button class="no" ${bubbleBusy ? "disabled" : ""}>🙅 그만해</button></div>`;
  bubbleEl.querySelector(".yes").onclick = () => answerBubble(b._idx, b.char, true);
  bubbleEl.querySelector(".no").onclick = () => answerBubble(b._idx, b.char, false);
  bubbleEl.hidden = false;
}
async function answerBubble(index, charName, allow) {
  if (bubbleBusy) return;
  bubbleBusy = true; renderBubbles(lastBubbles);
  try { const out = await postJson("/api/bubble", { index, char: charName, answer: allow ? "allow" : "stop" }); if (out.error) toast("⚠️ " + out.error); }
  catch (err) { toast("⚠️ 서버 연결 실패"); }
  bubbleBusy = false; renderBubbles([]); poll();
}

// ---------- 서버 폴링 ----------

let cursor = 0, polling = false, firstPoll = true;
async function poll() {
  if (polling) return;
  polling = true;
  try {
    const res = await fetch(`/api/snapshot?since=${cursor}`);
    const snap = await res.json();
    cursor = snap.seq;
    locNames = snap.locations;
    hudEl.firstChild.textContent = `🏘 ${snap.village} · Day ${snap.day} · ${snap.clock}`;
    hudSub.textContent = `엔진: ${snap.provider}${anyModelLoaded ? "+glb" : ""}` +
      (snap.realtime ? " · ⏰ 리얼타임" : "") + (snap.asleep ? " · 🌙 자는 시간" : "") +
      (autoFollow ? ` · 🎯 ${autoFollow.data.name} 따라가는 중` : "");
    foods = snap.foods || [];
    photos = snap.photos || []; dishes = snap.dishes || [];
    const albumJson = JSON.stringify([photos.length, dishes.length]);
    if (!albumEl.hidden && albumJson !== lastAlbumJson) renderAlbum();
    lastAlbumJson = albumJson;
    rankings = snap.rankings || rankings;
    const rankJson = JSON.stringify(snap.rankings || null);
    if (!boardEl.hidden && rankJson !== lastRankJson) renderBoard();
    lastRankJson = rankJson;
    for (const c of snap.characters) upsertChar(c);
    if (cardCharId && !cardEl.hidden) { const ce = entries.get(cardCharId); if (ce) renderCardStats(ce.data); }
    let fresh = snap.events;
    if (firstPoll) { firstPoll = false; for (const ev of fresh.slice(0, -1).slice(-10)) logEvent(ev); fresh = fresh.slice(-1); }
    for (const ev of fresh) acceptEvent(ev);
    const confess = (snap.bubbles || []).filter((b) => b.kind === "confess_request");
    if (confess.length > knownBubbleCount) toast(`💗 ${confess[confess.length - 1].char}의 말풍선이 도착했어요!`);
    knownBubbleCount = confess.length;
    if (!bubbleBusy) renderBubbles(snap.bubbles);
    const hungry = new Set((snap.bubbles || []).filter((b) => b.kind === "hungry").map((b) => b.char));
    for (const e of entries.values()) if (hungry.has(e.data.name) && !e.bubble) showBubble(e, "🍚 배고파요...", { grey: true, dur: 2300 });
    updateSky(snap.minutes);
    for (const key of Object.keys(ANCHORS)) {
      const a = ANCHORS[key];
      if (a.label && !a.named && locNames[key] && key !== "balcony") { a.label.dispose(); a.label = makeLocLabel(locNames[key]); a.label.position.set(a.x, a.labelY, a.z); a.named = true; }
    }
  } catch (err) { hudEl.firstChild.textContent = "🏘 서버 연결 대기 중..."; }
  polling = false;
}

// ---------- 하늘 색 (시간대) ----------

const skyDay = BABYLON.Color3.FromHexString("#a9d7ee");
const skySunset = BABYLON.Color3.FromHexString("#f2bf8f");
const skyDusk = BABYLON.Color3.FromHexString("#52608f");
let lastMinutes = 600;
function lerpC(a, b, t) { return BABYLON.Color3.Lerp(a, b, Math.max(0, Math.min(1, t))); }
function updateSky(minutes) {
  lastMinutes = minutes;
  const h = minutes / 60;
  let c;
  if (view === "interior") c = BABYLON.Color3.FromHexString("#f4e8d2");
  else if (h < 5) c = skyDusk.clone();
  else if (h < 7) c = lerpC(skyDusk, skyDay, (h - 5) / 2);
  else if (h <= 16) c = skyDay.clone();
  else if (h <= 19) c = lerpC(skyDay, skySunset, (h - 16) / 3);
  else c = lerpC(skySunset, skyDusk, (h - 19) / 3.5);
  scene.clearColor = new BABYLON.Color4(c.r, c.g, c.b, 1);
  scene.fogColor = c;
  const dim = view === "interior" ? 0.95 : h < 6 ? 0.5 : h > 17 ? Math.max(0.55, 1 - (h - 17) * 0.09) : 1;
  sun.intensity = 1.5 * dim;
}

// ---------- 카메라 조작 (회전/패닝/줌/따라가기) ----------

let autoFollow = null;
const FOLLOW_ENGAGE = 2.2, FOLLOW_RELEASE = 3.6;
const HOME_TARGET = new BABYLON.Vector3(0, 0.6, 0);
const freeTarget = HOME_TARGET.clone();
let camEngaged = false;

const reticle = BABYLON.MeshBuilder.CreateTorus("reticle", { diameter: 2.4, thickness: 0.16, tessellation: 36 }, scene);
const reticleMat = new BABYLON.StandardMaterial("retm", scene);
reticleMat.emissiveColor = new BABYLON.Color3(1, 1, 1);
reticleMat.disableLighting = true; reticleMat.alpha = 0.4;
reticle.material = reticleMat; reticle.isPickable = false; reticle.position.y = 0.12;

function panCamera(dx, dy) {
  const s = camRadius * 0.0016;
  const fx = -Math.sin(camTheta), fz = -Math.cos(camTheta);
  const rx = Math.cos(camTheta), rz = -Math.sin(camTheta);
  freeTarget.x -= (rx * dx + fx * dy) * s;
  freeTarget.z -= (rz * dx + fz * dy) * s;
  const cx = view === "interior" ? INTERIOR_X : 0;
  const lim = view === "interior" ? 12 : 26;
  const offx = freeTarget.x - cx;
  const len = Math.hypot(offx, freeTarget.z);
  if (len > lim) { freeTarget.x = cx + offx * lim / len; freeTarget.z *= lim / len; }
}

const pointers = new Map();
let lastPinch = 0, downPos = null, lastCx = 0, lastCy = 0;
function rectXY(e) { const r = canvas.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; }

canvas.addEventListener("contextmenu", (e) => e.preventDefault());
canvas.addEventListener("dblclick", () => {
  if (view === "interior") { setView("village"); return; }
  autoFollow = null; freeTarget.copyFrom(HOME_TARGET);
});
canvas.addEventListener("pointerdown", (e) => {
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY, btn: e.button });
  downPos = { x: e.clientX, y: e.clientY, btn: e.button };
  canvas.setPointerCapture(e.pointerId);
  if (pointers.size === 2) { const p = [...pointers.values()]; lastCx = (p[0].x + p[1].x) / 2; lastCy = (p[0].y + p[1].y) / 2; }
});
canvas.addEventListener("pointermove", (e) => {
  if (!pointers.has(e.pointerId)) return;
  camEngaged = true;
  const prev = pointers.get(e.pointerId);
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
function endPointer(e) {
  pointers.delete(e.pointerId);
  if (pointers.size < 2) lastPinch = 0;
  if (downPos && downPos.btn === 0 && Math.hypot(e.clientX - downPos.x, e.clientY - downPos.y) < 6) {
    const p = rectXY(e); pickAt(p.x, p.y);
  }
  downPos = null;
}
canvas.addEventListener("pointerup", endPointer);
canvas.addEventListener("pointercancel", endPointer);
canvas.addEventListener("wheel", (e) => { e.preventDefault(); camEngaged = true; camRadius = Math.min(55, Math.max(10, camRadius * (1 + e.deltaY * 0.001))); }, { passive: false });
window.addEventListener("keydown", (e) => {
  const step = 46; let moved = true;
  if (e.key === "ArrowRight" || e.key === "d") panCamera(-step, 0);
  else if (e.key === "ArrowLeft" || e.key === "a") panCamera(step, 0);
  else if (e.key === "ArrowUp" || e.key === "w") panCamera(0, -step);
  else if (e.key === "ArrowDown" || e.key === "s") panCamera(0, step);
  else if (e.key === "Escape") { if (cardCharId) closeCard(); else autoFollow = null; moved = false; }
  else moved = false;
  if (moved) camEngaged = true;
});

function pickAt(x, y) {
  const pick = scene.pick(x, y, (m) => m.isPickable && !!m.metadata);
  if (pick && pick.hit && pick.pickedMesh && pick.pickedMesh.metadata) {
    const md = pick.pickedMesh.metadata;
    if (md.house) { setView("interior"); return; }
    if (md.board) { toggleBoard(); return; }
    if (md.charId != null) { const e = entries.get(md.charId); if (e) { showCard(e.data); focusOn(e); return; } }
  }
  closeCard(); boardEl.hidden = true;
}
function closeCard() { cardEl.hidden = true; cardCharId = null; }
function focusOn(e) {
  autoFollow = null;
  e.target = e.root.position.clone();
  freeTarget.set(e.root.position.x, 1.0, e.root.position.z);
  camRadius = Math.min(camRadius, 15);
}

// ---------- 공간 전환 (마을 ↔ 실내) ----------

let view = "village";
const fadeEl = document.getElementById("fade");
const exitBtn = document.getElementById("exitbtn");
exitBtn.onclick = () => setView("village");
function setView(v) {
  if (view === v) return;
  view = v; fadeEl.style.opacity = "1";
  setTimeout(() => {
    autoFollow = null; cardEl.hidden = true; cardCharId = null;
    if (v === "interior") { freeTarget.set(INTERIOR_X, 0.8, 0.5); camRadius = 14; camPhi = 1.0; }
    else { freeTarget.copyFrom(HOME_TARGET); camRadius = 27; }
    camTarget.copyFrom(freeTarget);
    updateSky(lastMinutes);
    exitBtn.hidden = v !== "interior";
    setTimeout(() => { fadeEl.style.opacity = "0"; }, 80);
  }, 260);
}

function inFollowView(e) { return (view === "interior") === (e.root.position.x > INTERIOR_X / 2); }
function updateAutoFollow(t) {
  const inspecting = cardCharId != null && !cardEl.hidden;
  reticle.setEnabled(camEngaged && !inspecting && view === "village");
  if (inspecting || !camEngaged) { autoFollow = null; }
  else {
    if (autoFollow) {
      const cp = autoFollow.root.position;
      freeTarget.x += cp.x - autoFollow.px; freeTarget.z += cp.z - autoFollow.pz;
      const d = Math.hypot(cp.x - freeTarget.x, cp.z - freeTarget.z);
      if (d > FOLLOW_RELEASE || !inFollowView(autoFollow)) autoFollow = null;
    }
    if (!autoFollow) {
      let best = null, bd = Infinity;
      for (const e of entries.values()) {
        if (!inFollowView(e)) continue;
        const d = Math.hypot(e.root.position.x - freeTarget.x, e.root.position.z - freeTarget.z);
        if (d < bd) { bd = d; best = e; }
      }
      if (best && bd < FOLLOW_ENGAGE) autoFollow = best;
    }
    reticle.position.set(freeTarget.x, 0.12, freeTarget.z);
    const locked = !!autoFollow;
    reticleMat.emissiveColor = locked ? BABYLON.Color3.FromHexString("#ffd36b") : new BABYLON.Color3(1, 1, 1);
    reticleMat.alpha = locked ? 0.85 : 0.4;
    reticle.scaling.setAll(locked ? 1 + Math.sin(t * 5) * 0.08 : 1);
  }
  for (const e of entries.values()) { e.px = e.root.position.x; e.pz = e.root.position.z; }
}

// ---------- 메인 루프 ----------

function angleDelta(target, current) { return Math.atan2(Math.sin(target - current), Math.cos(target - current)); }
const tmp = new BABYLON.Vector3();
let prevNow = performance.now();

engine.runRenderLoop(() => {
  const now = performance.now();
  const dt = Math.min(0.05, (now - prevNow) / 1000); prevNow = now;
  const t = now / 1000;

  stepPlayback(now);

  for (const e of entries.values()) {
    tmp.copyFrom(e.target).subtractInPlace(e.root.position); tmp.y = 0;
    const dist = tmp.length();
    const selected = cardCharId === e.data.id && !cardEl.hidden;
    if (!selected && e.pendingLoc) moveEntryTo(e, e.pendingLoc);
    if (dist > 0.08) {
      const speed = dist > 8 ? 4.2 : 1.7;
      tmp.normalize().scaleInPlace(Math.min(dist, speed * dt));
      e.root.position.addInPlace(tmp);
      e.heading = Math.atan2(tmp.x, tmp.z);
      e.root.rotation.y += angleDelta(e.heading, e.root.rotation.y) * 0.2;
      e.root.position.y = Math.abs(Math.sin(t * 9 + e.data.id)) * 0.07;
    } else {
      e.root.position.y *= 0.8;
      if (selected) {
        const toCam = Math.atan2(camera.position.x - e.root.position.x, camera.position.z - e.root.position.z);
        e.root.rotation.y += angleDelta(toCam, e.root.rotation.y) * 0.12;
        e.wanderAt = now + 2500;
      } else if (now > e.wanderAt) {
        e.target = anchorPoint(e.data.location);
        e.wanderAt = now + 4000 + Math.random() * 7000;
      }
    }
    if (e.bubble && now > e.bubbleUntil) { e.bubble.dispose(); e.bubble = null; }
  }

  for (const c of clouds) { c.position.x += dt * 0.25; if (c.position.x > 38) c.position.x = -76; }
  if (fountainWater) fountainWater.position.y = 0.32 + Math.sin(t * 2.2) * 0.03;

  updateAutoFollow(t);
  BABYLON.Vector3.LerpToRef(camTarget, freeTarget, 1 - Math.pow(0.002, dt), camTarget);
  updateCamera();

  scene.render();
});

window.addEventListener("resize", () => engine.resize());

// 콘솔/검증용 핸들
window.__poc = {
  followByName(name) { const e = charByName(name); if (e) { camEngaged = true; freeTarget.set(e.root.position.x, 1.0, e.root.position.z); camRadius = Math.min(camRadius, 14); } },
  inspectByName(name) { const e = charByName(name); if (e) { showCard(e.data); focusOn(e); } },
  isFollowing(name) { return !!(autoFollow && autoFollow.data.name === name); },
  view() { return view; },
  modelLoaded() { return anyModelLoaded; },
  charCount() { return entries.size; },
  enterHouse() { setView("interior"); },
};

// ---------- 부트스트랩 ----------

buildVillage();
buildInterior();
loadVillagerModels().then(() => { poll(); setInterval(poll, 1500); });
