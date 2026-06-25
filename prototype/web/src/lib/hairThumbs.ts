// 헤어스타일 썸네일 생성 — 오프스크린 Babylon 씬에서 각 스타일을 1회 렌더해 PNG dataURL로 캐시.
// 생성 UI 의 머리 스타일 버튼이 텍스트가 아니라 실제 머리 실루엣을 보여주도록(기획 §1 외모 확장).
// 색상이 아니라 "형태"를 안내하므로 중립 머리색으로 렌더(색은 바로 위 색 스와치에서 별도 선택).
import { Engine } from "@babylonjs/core/Engines/engine";
import { Scene } from "@babylonjs/core/scene";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { ArcRotateCamera } from "@babylonjs/core/Cameras/arcRotateCamera";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { CreateScreenshotAsync } from "@babylonjs/core/Misc/screenshotTools";

import { buildAvatar } from "./figures";
import { HAIR_STYLES, type HairStyle, type AvatarLook } from "./appearance";

// 형태만 보이도록 한 중립 룩(머리색·피부톤 고정).
const NEUTRAL: Omit<AvatarLook, "hairStyle"> = {
  gender: "F",
  skin: "#ffe0bd",
  hairColor: "#6d4c41",
  bodyColor: "#cfd3d8",
  eyeColor: "#3a2b22",
};

let cache: Promise<Record<HairStyle, string>> | null = null;

// 4종 헤어 썸네일을 한 번에 생성(이후 캐시 재사용). dataURL(PNG, 투명 배경) 맵 반환.
export function getHairThumbs(size = 96): Promise<Record<HairStyle, string>> {
  if (cache) return cache;
  cache = (async () => {
    const canvas = document.createElement("canvas");
    const engine = new Engine(canvas, true, { preserveDrawingBuffer: true });
    const scene = new Scene(engine);
    scene.clearColor = new Color4(0, 0, 0, 0); // 투명 — 버튼 배경에 자연스럽게

    // 머리를 살짝 옆에서 클로즈업(뒤로 밀린 머리 볼륨이 보이도록 alpha 를 정면에서 약간 틀기).
    const cam = new ArcRotateCamera("htcam", Math.PI / 2 + 0.5, 1.2, 2.1, new Vector3(0, 1.62, 0), scene);
    cam.fov = 0.6;
    const hemi = new HemisphericLight("hth", new Vector3(0.3, 1, 0.3), scene);
    hemi.intensity = 1.0;
    hemi.diffuse = Color3.FromHexString("#ffffff");

    const out = {} as Record<HairStyle, string>;
    for (const h of HAIR_STYLES) {
      const handle = buildAvatar(scene, { ...NEUTRAL, hairStyle: h.id });
      out[h.id] = await CreateScreenshotAsync(engine, cam, { width: size, height: size });
      handle.root.dispose();
    }

    scene.dispose();
    engine.dispose();
    return out;
  })();
  return cache;
}
