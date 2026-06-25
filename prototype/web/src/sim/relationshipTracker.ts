/**
 * relationshipTracker.ts
 * Python tomodachai/relationship.py의 RelationshipTracker 클래스 및
 * detectTriangles / applyJealousy 헬퍼를 TypeScript로 포팅.
 *
 * 외부 의존 없음 (Babylon/Svelte/Tauri 임포트 금지).
 */

import {
  type Relationship,
  type BreakupReason,
  defaultRelationship,
  applyDeltas,
  applyNaturalDecay,
} from "./relationship";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RelationshipSlots {
  best_friend: number | null;
  lover: number | null;
  enemy: number | null;
}

export interface Fight {
  participants: [number, number];
  cause: string;
  resolved: boolean;
  witnessed_by_player: boolean;
}

export interface ExLoverTag {
  target: number;
  reason: BreakupReason;
  day: number;
}

export interface Triangle {
  jealous: number;
  target: number;
  rival: number;
  romance_level: number;
}

// ---------------------------------------------------------------------------
// RelationshipTracker
// ---------------------------------------------------------------------------

function pairKey(a: number, b: number): string {
  return `${a},${b}`;
}

export class RelationshipTracker {
  private _relationships: Map<string, Relationship> = new Map();
  private _fights: Fight[] = [];
  private _slots: Map<number, RelationshipSlots> = new Map();
  private _exLoverTags: Map<number, ExLoverTag[]> = new Map();

  // ------------------------------------------------------------------
  // Core get/update
  // ------------------------------------------------------------------

  /**
   * (a,b) 방향의 Relationship 반환. 없으면 default 생성 후 저장.
   * 키는 순서 있음: (a,b) ≠ (b,a).
   */
  get(a: number, b: number): Relationship {
    const key = pairKey(a, b);
    if (!this._relationships.has(key)) {
      this._relationships.set(key, defaultRelationship());
    }
    return this._relationships.get(key)!;
  }

  /**
   * (a,b) 방향의 Relationship에 델타 적용 후 저장.
   */
  update(a: number, b: number, deltas: Record<string, number>): void {
    const rel = this.get(a, b);
    this._relationships.set(pairKey(a, b), applyDeltas(rel, deltas));
  }

  /**
   * 모든 (a, b, relationship) 트리플 반환.
   */
  allPairs(): [number, number, Relationship][] {
    const result: [number, number, Relationship][] = [];
    for (const [key, rel] of this._relationships) {
      const [a, b] = key.split(",").map(Number);
      result.push([a, b, rel]);
    }
    return result;
  }

  // ------------------------------------------------------------------
  // Natural decay (daily tick)
  // ------------------------------------------------------------------

  /**
   * 모든 관계에 자연 감소 적용.
   */
  applyDailyDecay(decayFriendship = 0.75, decayRomance = 0.5): void {
    for (const [key, rel] of this._relationships) {
      this._relationships.set(key, applyNaturalDecay(rel, decayFriendship, decayRomance));
    }
  }

  // ------------------------------------------------------------------
  // Slots management
  // ------------------------------------------------------------------

  getSlots(charId: number): RelationshipSlots {
    if (!this._slots.has(charId)) {
      this._slots.set(charId, { best_friend: null, lover: null, enemy: null });
    }
    return this._slots.get(charId)!;
  }

  /**
   * setLover(a, b): slots[a].lover=b, slots[b].lover=a (양방향 상호 설정)
   */
  setLover(a: number, b: number): void {
    this.getSlots(a).lover = b;
    this.getSlots(b).lover = a;
  }

  /**
   * clearLover(a, b): 서로 가리킬 때만 해제.
   * slots[a].lover==b → null, slots[b].lover==a → null (각자 독립 확인).
   */
  clearLover(a: number, b: number): void {
    const slotsA = this.getSlots(a);
    const slotsB = this.getSlots(b);
    if (slotsA.lover === b) {
      slotsA.lover = null;
    }
    if (slotsB.lover === a) {
      slotsB.lover = null;
    }
  }

  /**
   * recomputeSlots(id): best_friend와 enemy 슬롯 재계산.
   * lover 슬롯은 건드리지 않음.
   *
   * best_friend: 양방향 friendship≥70 중 id→other가 가장 높은 1명
   *              (초기 비교값 70.0, 반드시 초과해야 교체)
   * enemy: 양방향 friendship≤-50 중 id→other가 가장 낮은 1명
   *        (초기 비교값 -50.0, 반드시 미만이어야 교체)
   */
  recomputeSlots(charId: number): void {
    const slots = this.getSlots(charId);

    let bestFriendCandidate: number | null = null;
    let bestFriendValue = 70.0; // 초기값: 이 값을 초과(>)해야 교체

    let enemyCandidate: number | null = null;
    let enemyValue = -50.0; // 초기값: 이 값보다 작아야(<) 교체

    // charId가 출발점인 관계들에서 other 수집
    const allOthers = new Set<number>();
    for (const key of this._relationships.keys()) {
      const [a, b] = key.split(",").map(Number);
      if (a === charId) {
        allOthers.add(b);
      }
    }

    for (const other of allOthers) {
      const relAB = this.get(charId, other);
      const relBA = this.get(other, charId);

      // best_friend: 양방향 ≥70, id→other 최대값
      if (relAB.friendship >= 70.0 && relBA.friendship >= 70.0) {
        if (relAB.friendship > bestFriendValue) {
          bestFriendValue = relAB.friendship;
          bestFriendCandidate = other;
        }
      }

      // enemy: 양방향 ≤-50, id→other 최솟값
      if (relAB.friendship <= -50.0 && relBA.friendship <= -50.0) {
        if (relAB.friendship < enemyValue) {
          enemyValue = relAB.friendship;
          enemyCandidate = other;
        }
      }
    }

    slots.best_friend = bestFriendCandidate;
    slots.enemy = enemyCandidate;
    // lover 슬롯은 건드리지 않음
  }

  // ------------------------------------------------------------------
  // Ex-lover tags
  // ------------------------------------------------------------------

  addExLoverTag(charId: number, target: number, reason: BreakupReason, day: number): void {
    if (!this._exLoverTags.has(charId)) {
      this._exLoverTags.set(charId, []);
    }
    this._exLoverTags.get(charId)!.push({ target, reason, day });
  }

  getExLoverTags(charId: number): ExLoverTag[] {
    return [...(this._exLoverTags.get(charId) ?? [])];
  }

  removeExLoverTag(charId: number, target: number): void {
    const tags = this._exLoverTags.get(charId) ?? [];
    this._exLoverTags.set(charId, tags.filter((t) => t.target !== target));
  }

  // ------------------------------------------------------------------
  // Fight management
  // ------------------------------------------------------------------

  addFight(fight: Fight): void {
    this._fights.push(fight);
  }

  /** 미해결 싸움만 반환. */
  getFights(): Fight[] {
    return this._fights.filter((f) => !f.resolved);
  }

  /**
   * participants 집합과 일치하는 첫 번째 미해결 싸움을 해결.
   * set 비교: (1,2)와 (2,1)은 동일.
   * 해결 성공 시 true, 없으면 false.
   */
  resolveFight(participants: [number, number]): boolean {
    const key = new Set(participants);
    for (const fight of this._fights) {
      if (!fight.resolved && setsEqual(new Set(fight.participants), key)) {
        fight.resolved = true;
        return true;
      }
    }
    return false;
  }

  // ------------------------------------------------------------------
  // Query helpers
  // ------------------------------------------------------------------

  /**
   * charId→b 관계 중 romance≥threshold인 (b, romance) 목록, romance 내림차순.
   */
  getRomanticInterests(charId: number, threshold = 20.0): [number, number][] {
    const results: [number, number][] = [];
    for (const [key, rel] of this._relationships) {
      const [a, b] = key.split(",").map(Number);
      if (a === charId && rel.romance >= threshold) {
        results.push([b, rel.romance]);
      }
    }
    return results.sort((x, y) => y[1] - x[1]);
  }

  /**
   * charId→b 관계 중 friendship≥threshold인 (b, friendship) 목록, friendship 내림차순.
   */
  getFriends(charId: number, threshold = 50.0): [number, number][] {
    const results: [number, number][] = [];
    for (const [key, rel] of this._relationships) {
      const [a, b] = key.split(",").map(Number);
      if (a === charId && rel.friendship >= threshold) {
        results.push([b, rel.friendship]);
      }
    }
    return results.sort((x, y) => y[1] - x[1]);
  }

  /**
   * charId→b 관계 중 friendship≤threshold인 (b, friendship) 목록, friendship 오름차순.
   */
  getRivals(charId: number, threshold = -50.0): [number, number][] {
    const results: [number, number][] = [];
    for (const [key, rel] of this._relationships) {
      const [a, b] = key.split(",").map(Number);
      if (a === charId && rel.friendship <= threshold) {
        results.push([b, rel.friendship]);
      }
    }
    return results.sort((x, y) => x[1] - y[1]);
  }

  // ------------------------------------------------------------------
  // Serialization accessors (additive, 비파괴) — save.py가 내부 저장 전체를 읽음.
  // getFights()는 미해결만 반환하므로 직렬화엔 allFightsRaw()를 써야 한다.
  // ------------------------------------------------------------------

  /** 모든 (charId, slots) 쌍을 삽입 순서대로. Python tracker._slots.items() 미러. */
  allSlots(): [number, RelationshipSlots][] {
    return [...this._slots.entries()];
  }

  /** 모든 (charId, tags[]) 쌍을 삽입 순서대로. Python tracker._ex_lover_tags.items() 미러. */
  allExLoverTags(): [number, ExLoverTag[]][] {
    return [...this._exLoverTags.entries()];
  }

  /** 해결 여부 무관 전체 싸움 목록(복사본). Python tracker._fights 미러. */
  allFightsRaw(): Fight[] {
    return [...this._fights];
  }
}

// ---------------------------------------------------------------------------
// Triangle detection & jealousy
// ---------------------------------------------------------------------------

/**
 * detectTriangles: 결정론적 삼각관계 감지.
 *
 * for a in all_chars:
 *   for b in all_chars (b≠a):
 *     if rel(a,b).romance >= romanceTh:
 *       for c in all_chars (c≠a, c≠b):
 *         if rel(b,c).friendship >= friendshipTh:
 *           → Triangle(jealous=a, target=b, rival=c, romance_level=rel(a,b).romance)
 */
export function detectTriangles(
  tracker: RelationshipTracker,
  romanceTh = 30.0,
  friendshipTh = 30.0,
): Triangle[] {
  const triangles: Triangle[] = [];

  // 모든 캐릭터 ID 수집
  const allChars = new Set<number>();
  for (const [a, b] of tracker.allPairs()) {
    allChars.add(a);
    allChars.add(b);
  }

  for (const a of allChars) {
    for (const b of allChars) {
      if (a === b) continue;
      const relAB = tracker.get(a, b);
      if (relAB.romance < romanceTh) continue;
      for (const c of allChars) {
        if (c === a || c === b) continue;
        const relBC = tracker.get(b, c);
        if (relBC.friendship >= friendshipTh) {
          triangles.push({
            jealous: a,
            target: b,
            rival: c,
            romance_level: relAB.romance,
          });
        }
      }
    }
  }

  return triangles;
}

/**
 * applyJealousy: 삼각관계별 질투 효과 적용.
 * delta = -(romance_level * rate * 0.1)
 * tracker.update(jealous, rival, {friendship: delta})
 */
export function applyJealousy(
  tracker: RelationshipTracker,
  triangles: Triangle[],
  jealousyRate = 0.3,
): void {
  for (const tri of triangles) {
    const friendshipDelta = -(tri.romance_level * jealousyRate * 0.1);
    tracker.update(tri.jealous, tri.rival, { friendship: friendshipDelta });
  }
}

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

function setsEqual(a: Set<number>, b: Set<number>): boolean {
  if (a.size !== b.size) return false;
  for (const v of a) {
    if (!b.has(v)) return false;
  }
  return true;
}
