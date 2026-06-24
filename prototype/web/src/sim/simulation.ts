// Python src/tomodachai/simulation.py 미러.
//
// 결정론(상수/델타 산술/요약 문자열/임계 비교/clamp)은 1:1 충실 포팅.
// 확률(shuffle/choice/sample/random/uniform)은 주입형 SimRng seam — 비트일치
// 안 함, 구조/후처리만 검증. LLM 호출은 ConversationEngine(주입 LlmClient) seam.

import type { Character } from "./character";
import type { AppConfig, LocationConfig } from "./config";
import type { SimRng } from "./rng";
import type { LlmClient } from "../llm";
import type { PersonalityType } from "./personalityType";
import { ConversationEngine } from "./conversation";
import type { ConversationResult } from "./conversation";
import { computeStage } from "./relationship";
import type { Relationship } from "./relationship";
import {
  RelationshipTracker,
  detectTriangles,
  applyJealousy,
} from "./relationshipTracker";
import type { Fight } from "./relationshipTracker";
import { MemoryStore, defaultSocialEvent } from "./memory";

// 오프라인 catch-up: 큰 이벤트는 생성 금지
export const BIG_EVENT_TYPES: ReadonlySet<string> = new Set([
  "confession_success",
  "confession_fail",
  "marriage",
  "breakup",
]);

// catch-up 1회 이벤트 수치 변화 폭 (작게 유지)
export const CATCHUP_FRIENDSHIP_DELTA_RANGE: readonly [number, number] = [-3.0, 5.0];
export const CATCHUP_ROMANCE_DELTA_RANGE: readonly [number, number] = [-1.0, 3.0];

// 자동 트리거 임계값
export const FIGHT_FRIENDSHIP_THRESHOLD = -30.0; // friendship 이하면 싸움 가능
export const FIGHT_CHANCE = 0.3;
export const CONFESSION_ROMANCE_THRESHOLD = 60.0;
export const CONFESSION_CHANCE = 0.2;
export const HUNGER_PER_TICK = 5.0;
export const SATISFACTION_DECAY = 1.0;

/**
 * 캐릭터를 장소에 배정. Python assign_locations 미러 (seed 인자 → 주입 rng).
 *
 * rng.shuffle로 캐릭터 순서를 섞고, 각 캐릭터마다 available 장소 순서를 다시
 * 섞은 뒤 capacity 미만인 첫 장소에 배정한다. 모든 장소가 차면 그 캐릭터는
 * 배정되지 않는다 (Python과 동일: break 없이 루프 종료).
 *
 * 반환 Map은 locations 삽입 순서를 보존한다 (Python dict 순서 = 삽입 순서).
 */
export function assignLocations(
  characters: readonly Character[],
  locations: readonly LocationConfig[],
  rng: SimRng,
): Map<string, Character[]> {
  const assignments = new Map<string, Character[]>();
  const capacityMap = new Map<string, number>();
  for (const loc of locations) {
    assignments.set(loc.name, []);
    capacityMap.set(loc.name, loc.capacity);
  }

  const shuffled = [...characters];
  rng.shuffle(shuffled);

  const available = locations.map((loc) => loc.name);
  for (const char of shuffled) {
    rng.shuffle(available);
    for (const locName of available) {
      if (assignments.get(locName)!.length < capacityMap.get(locName)!) {
        assignments.get(locName)!.push(char);
        break;
      }
    }
  }

  return assignments;
}

// ────────────────────────────────────────────────────────────────────────────
// 이벤트 dict 타입 (Python list[dict] 미러)
// ────────────────────────────────────────────────────────────────────────────

export interface ConversationEvent {
  type: "conversation";
  location: string;
  participants: [string, string];
  result: ConversationResult;
}

export interface TriggeredEvent {
  type: "fight" | "confession_success" | "confession_fail";
  participants: [string, string];
  summary: string;
}

export interface CatchupEvent {
  type: "catchup";
  participants: [string, string];
  summary: string;
  deltas: Record<string, { friendship: number; romance: number }>;
}

export type SimEvent = ConversationEvent | TriggeredEvent | CatchupEvent;

// ────────────────────────────────────────────────────────────────────────────
// 헬퍼
// ────────────────────────────────────────────────────────────────────────────

/**
 * Python Relationship.check_stage_transition 미러: stage를 in-place 재평가.
 * computeStage(friendship, romance, currentStage, allowRomantic) 결과가 다르면
 * stage를 갱신하고 true 반환. allPairs()/get()이 돌려주는 저장된 참조를 직접
 * 변형하므로 트래커에 반영된다 (update()는 새 객체로 교체하므로 여기선 안 씀).
 */
export function applyStageTransition(rel: Relationship, allowRomantic: boolean): boolean {
  const newStage = computeStage(rel.friendship, rel.romance, rel.stage, allowRomantic);
  if (newStage !== rel.stage) {
    rel.stage = newStage;
    return true;
  }
  return false;
}

/** Python f"{x:.0f}" 미러 — 소수점 0자리, 반올림 half-to-even(banker's). */
function fmt0(x: number): string {
  const floor = Math.floor(x);
  const frac = x - floor;
  if (frac !== 0.5) return String(Math.round(x));
  return String(floor % 2 === 0 ? floor : floor + 1);
}

/** Python set(participants) == {a, b} 미러 (순서 무관 쌍 비교). */
function sameUnorderedPair(p: readonly [number, number], a: number, b: number): boolean {
  return (p[0] === a && p[1] === b) || (p[0] === b && p[1] === a);
}

// ────────────────────────────────────────────────────────────────────────────
// Simulation
// ────────────────────────────────────────────────────────────────────────────

export class Simulation {
  readonly conversationEngine: ConversationEngine;
  readonly relationships: RelationshipTracker;
  readonly memory: MemoryStore;
  private readonly config: AppConfig;
  private readonly characters: Character[];
  private readonly rng: SimRng;
  private readonly _charMap: Map<number, Character>;
  private _stepCount = 0;

  constructor(
    config: AppConfig,
    characters: Character[],
    llm: LlmClient,
    personalities: Record<string, PersonalityType>,
    rng: SimRng,
  ) {
    this.config = config;
    this.characters = characters;
    this.conversationEngine = new ConversationEngine(llm, personalities);
    this.relationships = new RelationshipTracker();
    this.memory = new MemoryStore();
    this.rng = rng;
    this._charMap = new Map(characters.map((c) => [Number(c.id), c]));
  }

  /** Python self._step_count 노출 (테스트/저장용). */
  get stepCount(): number {
    return this._stepCount;
  }

  // 주의: 아래 _접두 메서드들은 Python의 "비공개" 메서드 미러. Python처럼
  // 외부에서 호출 가능(오라클 충실도 단위 테스트용). step()/generateCatchupEvents()는 T4.

  async _runConversation(
    charA: Character,
    charB: Character,
    location: string,
    timeOfDay: string,
  ): Promise<ConversationResult> {
    const aId = Number(charA.id);
    const bId = Number(charB.id);
    const relAb = this.relationships.get(aId, bId);
    const relBa = this.relationships.get(bId, aId);
    const memories = this.memory.getEventsBetween(aId, bId);

    const result = await this.conversationEngine.generate(
      charA,
      charB,
      relAb,
      relBa,
      memories,
      location,
      timeOfDay,
    );

    for (const [name, deltas] of Object.entries(result.deltas)) {
      if (name === charA.profile.name) {
        this.relationships.update(aId, bId, deltas);
      } else if (name === charB.profile.name) {
        this.relationships.update(bId, aId, deltas);
      }
    }

    this.memory.addEvent(
      defaultSocialEvent({
        id: 0,
        type: "conversation",
        participants: [aId, bId],
        day: this._stepCount,
        location,
      }),
    );

    return result;
  }

  _checkTriggeredEvents(): TriggeredEvent[] {
    const events: TriggeredEvent[] = [];
    for (const [aId, bId, rel] of this.relationships.allPairs()) {
      if (
        rel.friendship <= FIGHT_FRIENDSHIP_THRESHOLD &&
        this.rng.random() < FIGHT_CHANCE &&
        rel.stage !== "stranger"
      ) {
        const fight = this._triggerFight(aId, bId, rel.friendship);
        if (fight) events.push(fight);
      }
      if (
        rel.romance >= CONFESSION_ROMANCE_THRESHOLD &&
        (rel.stage === "friend" || rel.stage === "best_friend") &&
        this.rng.random() < CONFESSION_CHANCE
      ) {
        const confession = this._triggerConfession(aId, bId);
        if (confession) events.push(confession);
      }
    }
    return events;
  }

  _triggerFight(aId: number, bId: number, friendship: number): TriggeredEvent | null {
    // 이미 싸우는 중이면 새로 만들지 않음
    for (const f of this.relationships.getFights()) {
      if (sameUnorderedPair(f.participants, aId, bId)) return null;
    }

    const fight: Fight = {
      participants: [aId, bId],
      cause: `우정 ${fmt0(friendship)} — 사이가 나쁨`,
      resolved: false,
      witnessed_by_player: false,
    };
    this.relationships.addFight(fight);

    this.relationships.update(aId, bId, { friendship: -5 });
    this.relationships.update(bId, aId, { friendship: -5 });

    this.memory.addEvent(
      defaultSocialEvent({
        id: 0,
        type: "fight",
        participants: [aId, bId],
        day: this._stepCount,
      }),
    );

    // 만족도 하락
    for (const cid of [aId, bId]) {
      const c = this._charMap.get(cid);
      if (c) c.state.satisfaction = Math.max(0.0, c.state.satisfaction - 10.0);
    }

    const aName = this._name(aId);
    const bName = this._name(bId);
    return {
      type: "fight",
      participants: [aName, bName],
      summary: `${aName}와(과) ${bName}의 긴장이 폭발하여 싸움이 벌어졌다!`,
    };
  }

  _triggerConfession(aId: number, bId: number): TriggeredEvent {
    const relAb = this.relationships.get(aId, bId);
    const relBa = this.relationships.get(bId, aId);

    // 기획서 §3-3: 상대 수치 미참조 랜덤
    const success = this.rng.random() < 0.5;

    let eventType: TriggeredEvent["type"];
    let summary: string;
    if (success) {
      // 양쪽 LOVER 전환
      applyStageTransition(relAb, true);
      applyStageTransition(relBa, true);
      eventType = "confession_success";
      summary = `${this._name(aId)}가 ${this._name(bId)}에게 고백하여 연인이 되었다!`;
    } else {
      // 거절: friendship/romance 하락
      this.relationships.update(aId, bId, { friendship: -5, romance: -10 });
      eventType = "confession_fail";
      summary = `${this._name(aId)}가 ${this._name(bId)}에게 고백했지만 거절당했다.`;
    }

    this.memory.addEvent(
      defaultSocialEvent({
        id: 0,
        type: "confession",
        participants: [aId, bId],
        day: this._stepCount,
        result: success ? "accepted" : "rejected",
      }),
    );

    return {
      type: eventType,
      participants: [this._name(aId), this._name(bId)],
      summary,
    };
  }

  _checkStageTransitions(): void {
    for (const [, , rel] of this.relationships.allPairs()) {
      applyStageTransition(rel, false);
    }
  }

  _updateNeeds(): void {
    for (const char of this.characters) {
      char.state.hunger = Math.min(100.0, char.state.hunger + HUNGER_PER_TICK);
      char.state.satisfaction = Math.max(0.0, char.state.satisfaction - SATISFACTION_DECAY);
    }
  }

  _name(charId: number): string {
    const c = this._charMap.get(charId);
    return c ? c.profile.name : String(charId);
  }

  _checkTriggeredEventsForPair(aId: number, bId: number): TriggeredEvent[] {
    const events: TriggeredEvent[] = [];
    const rel = this.relationships.get(aId, bId);

    if (
      rel.friendship <= FIGHT_FRIENDSHIP_THRESHOLD &&
      this.rng.random() < FIGHT_CHANCE &&
      rel.stage !== "stranger"
    ) {
      const fight = this._triggerFight(aId, bId, rel.friendship);
      if (fight) events.push(fight);
    }

    if (
      rel.romance >= CONFESSION_ROMANCE_THRESHOLD &&
      (rel.stage === "friend" || rel.stage === "best_friend") &&
      this.rng.random() < CONFESSION_CHANCE
    ) {
      const confession = this._triggerConfession(aId, bId);
      if (confession) events.push(confession);
    }

    return events;
  }

  async _forceEncounter(
    charA: Character,
    charB: Character,
    location: string,
  ): Promise<ConversationResult> {
    return this._runConversation(charA, charB, location, "오후");
  }
}
