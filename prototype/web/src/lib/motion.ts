// 아바타 절차적 모션 시스템 — 스켈레톤 없이 transform(위치/회전)으로 동작을 표현.
// 핸들(root=전신, head=목 위 피벗)의 "로컬" 변형만 건드리므로, 마을의 월드 이동/방향과 자연스럽게 합성된다.
// 기획 §7(걷기/먹기/대기 모션)의 클라이언트 구현. 백엔드 무관.
import type { AvatarHandle } from "./figures";

export type MotionKind = "idle" | "walk" | "eat" | "celebrate";

export type WalkStyle = "waddle" | "brisk" | "slow"; // 뒤뚱 / 씩씩 / 느릿
export type IdleStyle = "calm" | "bouncy" | "looky" | "doze"; // 반듯 / 까불 / 두리번 / 졸기
export type EatStyle = "gobble" | "savor"; // 허겁지겁 / 천천히 음미

export interface MotionOpts {
  seed?: number;       // 캐릭터별 위상 차(여럿이 동시에 똑같이 움직이지 않도록)
  walk?: WalkStyle;
  idle?: IdleStyle;
  eat?: EatStyle;
}

const TAU = Math.PI * 2;

export class MotionController {
  private root: AvatarHandle["root"];
  private head: AvatarHandle["head"];
  private seed: number;
  private kind: MotionKind = "idle";
  private opts: Required<Pick<MotionOpts, "walk" | "idle" | "eat">>;
  private startMs = 0;        // 현재 동작 시작 시각
  private celebrateUntil = 0; // celebrate 종료 시각(이후 idle 복귀)

  constructor(handle: AvatarHandle, opts: MotionOpts = {}) {
    this.root = handle.root;
    this.head = handle.head;
    this.seed = opts.seed ?? 0;
    this.opts = {
      walk: opts.walk ?? "brisk",
      idle: opts.idle ?? "calm",
      eat: opts.eat ?? "savor",
    };
  }

  /** 동작 전환(같은 동작이면 무시). celebrate 는 일정 시간 후 자동으로 idle 복귀. */
  set(kind: MotionKind, now = performance.now()): void {
    if (kind === this.kind) return;
    this.kind = kind;
    this.startMs = now;
    if (kind === "celebrate") this.celebrateUntil = now + 2600;
  }

  /** 매 프레임 호출 — 현재 동작에 맞춰 로컬 변형을 기록. */
  update(now = performance.now()): void {
    if (this.kind === "celebrate" && now > this.celebrateUntil) this.set("idle", now);
    const t = (now / 1000) + this.seed;
    switch (this.kind) {
      case "walk": this.walk(t); break;
      case "eat": this.eat(t); break;
      case "celebrate": this.celebrate(t); break;
      default: this.idle(t); break;
    }
  }

  /** 변형 초기화(정지 자세). */
  reset(): void {
    this.root.position.y = 0;
    this.root.rotation.x = 0; this.root.rotation.z = 0;
    this.head.rotation.x = 0; this.head.rotation.y = 0;
  }

  private idle(t: number): void {
    this.head.rotation.x = 0; this.head.rotation.y = 0;
    this.root.rotation.x = 0; this.root.rotation.z = 0;
    switch (this.opts.idle) {
      case "bouncy": // 까불까불 — 가볍게 콩콩
        this.root.position.y = Math.abs(Math.sin(t * 4)) * 0.05;
        break;
      case "looky": // 두리번 — 머리를 좌우로
        this.root.position.y = Math.sin(t * 1.5) * 0.012;
        this.head.rotation.y = Math.sin(t * 0.7) * 0.5;
        break;
      case "doze": // 졸기 — 고개를 떨구며 꾸벅
        this.root.position.y = Math.sin(t * 1.1) * 0.01;
        this.head.rotation.x = 0.22 + Math.sin(t * 1.1) * 0.1;
        break;
      default: // calm 반듯 — 숨쉬듯 미세한 보브
        this.root.position.y = Math.sin(t * 1.6) * 0.015;
        break;
    }
  }

  private walk(t: number): void {
    // 스타일별 진폭/주기 — 걸음 보브 + 좌우 흔들 + 앞 기울임.
    let freq = 9, hop = 0.07, sway = 0.06, lean = 0.05;
    if (this.opts.walk === "waddle") { freq = 7; hop = 0.05; sway = 0.16; lean = 0.03; }
    else if (this.opts.walk === "slow") { freq = 5.5; hop = 0.04; sway = 0.05; lean = 0.02; }
    const p = t * freq;
    this.root.position.y = Math.abs(Math.sin(p)) * hop;
    this.root.rotation.z = Math.sin(p) * sway;
    this.root.rotation.x = lean;
    this.head.rotation.x = 0; this.head.rotation.y = 0;
  }

  private eat(t: number): void {
    // 고개를 끄덕이며 먹는 동작.
    const fast = this.opts.eat === "gobble";
    const p = t * (fast ? 8 : 3.5);
    const amp = fast ? 0.32 : 0.18;
    this.head.rotation.x = (0.5 + 0.5 * Math.sin(p)) * amp;
    this.root.position.y = Math.abs(Math.sin(p)) * (fast ? 0.03 : 0.012);
    this.root.rotation.x = 0; this.root.rotation.z = 0;
  }

  private celebrate(t: number): void {
    // 신나게 콩콩 뛰며 살짝 흔들(완성 리빌 등).
    this.root.position.y = Math.abs(Math.sin(t * 7)) * 0.28;
    this.root.rotation.y = Math.sin(t * 9) * 0.18;
    this.root.rotation.x = 0; this.root.rotation.z = 0;
    this.head.rotation.x = 0; this.head.rotation.y = 0;
  }
}

// 캐릭터별 위상차(seed) — 같은 스타일이라도 동시에 똑같이 움직이지 않도록.
function seedForId(id: number): number {
  return (Math.abs(id) % 16) * (TAU / 16);
}

// 캐릭터 id 로 대기/걷기 스타일을 결정(성격 정보가 없는 시드/기존 캐릭터용 폴백).
const IDLE_STYLES: IdleStyle[] = ["calm", "bouncy", "looky", "doze"];
const WALK_STYLES: WalkStyle[] = ["brisk", "waddle", "slow"];
export function styleForId(id: number): MotionOpts {
  const i = Math.abs(id);
  return {
    seed: seedForId(id),
    idle: IDLE_STYLES[i % IDLE_STYLES.length],
    walk: WALK_STYLES[i % WALK_STYLES.length],
  };
}

// 성격 16유형(personality.ts 코드) → 움직임 스타일.
// 계통(안정/신중/주도/사교)이 걸음 속도를, 세부 유형이 대기 동작 결을 좌우.
const PERSONALITY_MOTION: Record<string, { idle: IdleStyle; walk: WalkStyle }> = {
  easygoing_softie: { idle: "calm", walk: "slow" },
  easygoing_optimist: { idle: "bouncy", walk: "slow" },
  easygoing_carer: { idle: "looky", walk: "slow" },
  easygoing_dreamer: { idle: "doze", walk: "slow" },
  independent_dogooder: { idle: "calm", walk: "brisk" },
  independent_perfectionist: { idle: "calm", walk: "brisk" },
  independent_introvert: { idle: "doze", walk: "slow" },
  independent_thinker: { idle: "looky", walk: "slow" },
  confident_busybee: { idle: "bouncy", walk: "brisk" },
  confident_gogetter: { idle: "calm", walk: "brisk" },
  confident_freespirit: { idle: "looky", walk: "brisk" },
  confident_brainiac: { idle: "calm", walk: "brisk" },
  outgoing_charmer: { idle: "bouncy", walk: "waddle" },
  outgoing_dynamo: { idle: "bouncy", walk: "brisk" },
  outgoing_buddy: { idle: "looky", walk: "waddle" },
  outgoing_extrovert: { idle: "bouncy", walk: "brisk" },
};

// 성격 코드로 모션 스타일을 결정. 미등록 코드는 id 기반 폴백.
export function styleForPersonality(code: string, id = 0): MotionOpts {
  const m = PERSONALITY_MOTION[code];
  if (!m) return styleForId(id);
  return { seed: seedForId(id), idle: m.idle, walk: m.walk };
}
