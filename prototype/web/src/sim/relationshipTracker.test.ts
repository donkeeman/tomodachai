/**
 * relationshipTracker.test.ts
 * RelationshipTracker 통합 테스트 — 골든 덤프 아님, 시나리오 기반.
 * 기대값은 Python relationship.py 규칙으로 손계산.
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  RelationshipTracker,
  detectTriangles,
  applyJealousy,
} from "./relationshipTracker";

// ---------------------------------------------------------------------------
// 1. 비대칭 키 — (a,b) ≠ (b,a)
// ---------------------------------------------------------------------------
describe("asymmetric keys", () => {
  it("A→B와 B→A는 독립된 슬롯", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: 50 });
    // A→B=50, B→A는 아직 없음 → get하면 default(0)
    expect(t.get(1, 2).friendship).toBe(50);
    expect(t.get(2, 1).friendship).toBe(0);
  });

  it("update는 지정 방향만 변경", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: 30 });
    t.update(2, 1, { friendship: -20 });
    expect(t.get(1, 2).friendship).toBe(30);
    expect(t.get(2, 1).friendship).toBe(-20);
  });
});

// ---------------------------------------------------------------------------
// 2. update + clamp
// ---------------------------------------------------------------------------
describe("update clamping", () => {
  it("우정 +200 → 100 (상한 클램프)", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: 200 });
    // 0+200=200, clamp [-100,100] → 100
    expect(t.get(1, 2).friendship).toBe(100);
  });

  it("우정 -200 → -100 (하한 클램프)", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: -200 });
    // 0-200=-200, clamp → -100
    expect(t.get(1, 2).friendship).toBe(-100);
  });

  it("로맨스 -50 → 0 (0 미만 불가)", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { romance: -50 });
    // 0-50=-50, clamp [0,100] → 0
    expect(t.get(1, 2).romance).toBe(0);
  });

  it("누적 update: 50+60=110 → clamp 100", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: 50 });
    t.update(1, 2, { friendship: 60 });
    // 50+60=110, clamp → 100
    expect(t.get(1, 2).friendship).toBe(100);
  });
});

// ---------------------------------------------------------------------------
// 3. setLover / clearLover 상호성
// ---------------------------------------------------------------------------
describe("setLover / clearLover", () => {
  it("setLover(A,B): slots[A].lover=B, slots[B].lover=A", () => {
    const t = new RelationshipTracker();
    t.setLover(1, 2);
    expect(t.getSlots(1).lover).toBe(2);
    expect(t.getSlots(2).lover).toBe(1);
  });

  it("clearLover(A,B): 서로 가리킬 때 양쪽 해제", () => {
    const t = new RelationshipTracker();
    t.setLover(1, 2);
    t.clearLover(1, 2);
    expect(t.getSlots(1).lover).toBeNull();
    expect(t.getSlots(2).lover).toBeNull();
  });

  it("clearLover guard: A가 B를, B가 다른 사람(3)을 가리키면 A만 해제", () => {
    const t = new RelationshipTracker();
    // 수동으로 불일치 상태 설정
    t.setLover(1, 2);           // slots[1].lover=2, slots[2].lover=1
    t.setLover(2, 3);           // slots[2].lover=3, slots[3].lover=2 (slots[1]은 2 그대로)
    // 이제 slots[1].lover=2, slots[2].lover=3
    t.clearLover(1, 2);
    // slots[1].lover==2 → null
    expect(t.getSlots(1).lover).toBeNull();
    // slots[2].lover==3 (≠1이므로) → 변경 없음
    expect(t.getSlots(2).lover).toBe(3);
  });

  it("clearLover(B,A) 순서 반대도 동일 동작", () => {
    const t = new RelationshipTracker();
    t.setLover(5, 6);
    t.clearLover(6, 5);
    expect(t.getSlots(5).lover).toBeNull();
    expect(t.getSlots(6).lover).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// 4. recomputeSlots
// ---------------------------------------------------------------------------
describe("recomputeSlots", () => {
  it("양방향 friendship≥70 → best_friend 선택", () => {
    // A→B=75, B→A=72 (양방향≥70) ⇒ slots[A].best_friend=B
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: 75 });
    t.update(2, 1, { friendship: 72 });
    t.recomputeSlots(1);
    expect(t.getSlots(1).best_friend).toBe(2);
  });

  it("비대칭: A→C=80, C→A=10 → C는 후보 아님", () => {
    // 비대칭: 한쪽만 70 이상이면 후보 제외
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: 75 });
    t.update(2, 1, { friendship: 72 }); // 후보O
    t.update(1, 3, { friendship: 80 });
    t.update(3, 1, { friendship: 10 }); // 비대칭 → 후보X
    t.recomputeSlots(1);
    expect(t.getSlots(1).best_friend).toBe(2);
  });

  it("최고값 single slot: A→B=75(양방향), A→C=82(양방향) → C 선택", () => {
    // 초기값 70.0, 초과(>)해야 교체 → 75>70 → B. 82>75 → C
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: 75 });
    t.update(2, 1, { friendship: 71 });
    t.update(1, 3, { friendship: 82 });
    t.update(3, 1, { friendship: 75 });
    t.recomputeSlots(1);
    expect(t.getSlots(1).best_friend).toBe(3);
  });

  it("양방향 friendship≤-50 → enemy 선택", () => {
    // A→B=-60, B→A=-55 (양방향≤-50) → enemy=B
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: -60 });
    t.update(2, 1, { friendship: -55 });
    t.recomputeSlots(1);
    expect(t.getSlots(1).enemy).toBe(2);
  });

  it("enemy single slot: 두 후보 중 더 낮은 값 선택", () => {
    // A→B=-60(양방향), A→C=-80(양방향) → C 선택 (초기-50.0, -60<-50→B, -80<-60→C)
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: -60 });
    t.update(2, 1, { friendship: -55 });
    t.update(1, 3, { friendship: -80 });
    t.update(3, 1, { friendship: -70 });
    t.recomputeSlots(1);
    expect(t.getSlots(1).enemy).toBe(3);
  });

  it("경계값: A→B=70, B→A=70 → best_friend 아님 (초과 아닌 같음)", () => {
    // Python: if rel_ab.friendship > best_friend_value → 초기값 70.0, 70>70 false → 선택 안 됨
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: 70 });
    t.update(2, 1, { friendship: 70 });
    t.recomputeSlots(1);
    // 70>70은 false이므로 best_friend_candidate=None
    expect(t.getSlots(1).best_friend).toBeNull();
  });

  it("경계값: A→B=-50, B→A=-50 → enemy 아님 (미만 아닌 같음)", () => {
    // Python: if rel_ab.friendship < enemy_value → 초기값 -50.0, -50<-50 false → 선택 안 됨
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: -50 });
    t.update(2, 1, { friendship: -50 });
    t.recomputeSlots(1);
    expect(t.getSlots(1).enemy).toBeNull();
  });

  it("recomputeSlots는 lover 슬롯을 건드리지 않음", () => {
    const t = new RelationshipTracker();
    t.setLover(1, 2);
    t.update(1, 3, { friendship: 80 });
    t.update(3, 1, { friendship: 80 });
    t.recomputeSlots(1);
    // best_friend 업데이트됨
    expect(t.getSlots(1).best_friend).toBe(3);
    // lover는 그대로
    expect(t.getSlots(1).lover).toBe(2);
  });
});

// ---------------------------------------------------------------------------
// 5. getFights / resolveFight
// ---------------------------------------------------------------------------
describe("getFights / resolveFight", () => {
  it("getFights는 미해결만 반환", () => {
    const t = new RelationshipTracker();
    t.addFight({ participants: [1, 2], cause: "argument", resolved: false, witnessed_by_player: false });
    t.addFight({ participants: [3, 4], cause: "jealousy", resolved: true, witnessed_by_player: false });
    const fights = t.getFights();
    expect(fights.length).toBe(1);
    expect(fights[0].participants).toEqual([1, 2]);
  });

  it("resolveFight: set 비교 — (1,2)와 (2,1)은 동일", () => {
    const t = new RelationshipTracker();
    t.addFight({ participants: [1, 2], cause: "test", resolved: false, witnessed_by_player: false });
    // 순서 반대로 resolve
    const result = t.resolveFight([2, 1]);
    expect(result).toBe(true);
    expect(t.getFights().length).toBe(0); // 해결됨 → getFights에서 제외
  });

  it("resolveFight: 존재하지 않는 pair → false", () => {
    const t = new RelationshipTracker();
    t.addFight({ participants: [1, 2], cause: "test", resolved: false, witnessed_by_player: false });
    expect(t.resolveFight([3, 4])).toBe(false);
  });

  it("resolveFight: 첫 번째 미해결만 resolve", () => {
    const t = new RelationshipTracker();
    t.addFight({ participants: [1, 2], cause: "first", resolved: false, witnessed_by_player: false });
    t.addFight({ participants: [1, 2], cause: "second", resolved: false, witnessed_by_player: false });
    t.resolveFight([1, 2]);
    const remaining = t.getFights();
    // 두 번째 싸움은 여전히 미해결
    expect(remaining.length).toBe(1);
    expect(remaining[0].cause).toBe("second");
  });

  it("이미 해결된 fight는 resolveFight에서 스킵", () => {
    const t = new RelationshipTracker();
    t.addFight({ participants: [1, 2], cause: "done", resolved: true, witnessed_by_player: false });
    t.addFight({ participants: [1, 2], cause: "new", resolved: false, witnessed_by_player: false });
    const result = t.resolveFight([1, 2]);
    expect(result).toBe(true);
    // "done"은 이미 resolved라 스킵, "new"가 resolve됨
    expect(t.getFights().length).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// 6. getRomanticInterests / getFriends / getRivals
// ---------------------------------------------------------------------------
describe("getRomanticInterests", () => {
  it("threshold 20 기준 필터 + romance 내림차순 정렬", () => {
    const t = new RelationshipTracker();
    // 1→2: romance=50, 1→3: romance=30, 1→4: romance=10 (미만)
    t.update(1, 2, { romance: 50 });
    t.update(1, 3, { romance: 30 });
    t.update(1, 4, { romance: 10 });
    t.update(2, 1, { romance: 40 }); // 방향 반대: 제외
    const interests = t.getRomanticInterests(1);
    // threshold=20: 50, 30은 포함, 10은 제외
    expect(interests).toEqual([[2, 50], [3, 30]]);
  });

  it("커스텀 threshold 적용", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { romance: 25 });
    t.update(1, 3, { romance: 35 });
    const interests = t.getRomanticInterests(1, 30);
    // ≥30: 35만
    expect(interests).toEqual([[3, 35]]);
  });
});

describe("getFriends", () => {
  it("threshold 50 기준 필터 + friendship 내림차순 정렬", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: 80 });
    t.update(1, 3, { friendship: 55 });
    t.update(1, 4, { friendship: 40 }); // 미만
    const friends = t.getFriends(1);
    expect(friends).toEqual([[2, 80], [3, 55]]);
  });
});

describe("getRivals", () => {
  it("threshold -50 기준 필터 + friendship 오름차순 정렬", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: -80 });
    t.update(1, 3, { friendship: -60 });
    t.update(1, 4, { friendship: -30 }); // 미만 절대값 (> -50)
    const rivals = t.getRivals(1);
    // ≤-50: -80, -60. asc 정렬 → -80, -60
    expect(rivals).toEqual([[2, -80], [3, -60]]);
  });
});

// ---------------------------------------------------------------------------
// 7. applyDailyDecay
// ---------------------------------------------------------------------------
describe("applyDailyDecay", () => {
  it("모든 관계에 자연 감소 적용", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: 10, romance: 5 });
    t.update(3, 4, { friendship: -10 });
    t.applyDailyDecay();
    // 1→2: friendship=max(0, 10-0.75)=9.25, romance=max(0, 5-0.5)=4.5
    expect(t.get(1, 2).friendship).toBeCloseTo(9.25);
    expect(t.get(1, 2).romance).toBeCloseTo(4.5);
    // 3→4: friendship<0, min(0, -10+0.75)=-9.25
    expect(t.get(3, 4).friendship).toBeCloseTo(-9.25);
  });
});

// ---------------------------------------------------------------------------
// 8. ExLoverTag
// ---------------------------------------------------------------------------
describe("ExLoverTag", () => {
  it("addExLoverTag → getExLoverTags", () => {
    const t = new RelationshipTracker();
    t.addExLoverTag(1, 2, "fight", 5);
    const tags = t.getExLoverTags(1);
    expect(tags.length).toBe(1);
    expect(tags[0]).toEqual({ target: 2, reason: "fight", day: 5 });
  });

  it("removeExLoverTag: target 일치 항목만 삭제", () => {
    const t = new RelationshipTracker();
    t.addExLoverTag(1, 2, "boredom", 3);
    t.addExLoverTag(1, 3, "mutual", 4);
    t.removeExLoverTag(1, 2);
    const tags = t.getExLoverTags(1);
    expect(tags.length).toBe(1);
    expect(tags[0].target).toBe(3);
  });

  it("없는 캐릭터 getExLoverTags → 빈 배열", () => {
    const t = new RelationshipTracker();
    expect(t.getExLoverTags(99)).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// 9. allPairs
// ---------------------------------------------------------------------------
describe("allPairs", () => {
  it("존재하는 모든 쌍 반환", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: 10 });
    t.update(2, 1, { friendship: 20 });
    const pairs = t.allPairs();
    expect(pairs.length).toBe(2);
    // 키 존재 확인
    const keys = pairs.map(([a, b]) => `${a},${b}`);
    expect(keys).toContain("1,2");
    expect(keys).toContain("2,1");
  });
});

// ---------------------------------------------------------------------------
// 10. detectTriangles
// ---------------------------------------------------------------------------
describe("detectTriangles", () => {
  it("삼각관계 감지: A→B romance≥30, B→C friendship≥30 → triangle(jealous=A, target=B, rival=C)", () => {
    const t = new RelationshipTracker();
    // A=1, B=2, C=3
    t.update(1, 2, { romance: 50 }); // 1→2 romance=50 ≥30
    t.update(2, 3, { friendship: 40 }); // 2→3 friendship=40 ≥30
    const triangles = detectTriangles(t);
    expect(triangles.length).toBe(1);
    expect(triangles[0]).toEqual({
      jealous: 1,
      target: 2,
      rival: 3,
      romance_level: 50,
    });
  });

  it("romance 미달 시 삼각관계 없음", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { romance: 20 }); // <30
    t.update(2, 3, { friendship: 40 });
    expect(detectTriangles(t).length).toBe(0);
  });

  it("friendship 미달 시 삼각관계 없음", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { romance: 50 });
    t.update(2, 3, { friendship: 20 }); // <30
    expect(detectTriangles(t).length).toBe(0);
  });

  it("커스텀 threshold 적용", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { romance: 25 }); // <30 기본이지만 ≥20
    t.update(2, 3, { friendship: 25 }); // <30 기본이지만 ≥20
    expect(detectTriangles(t, 30, 30).length).toBe(0);
    expect(detectTriangles(t, 20, 20).length).toBe(1);
  });

  it("여러 삼각관계 감지", () => {
    const t = new RelationshipTracker();
    // 1→2 romance=50, 2→3 friendship=40 → (jealous=1,target=2,rival=3)
    // 1→2 romance=50, 2→4 friendship=35 → (jealous=1,target=2,rival=4)
    t.update(1, 2, { romance: 50 });
    t.update(2, 3, { friendship: 40 });
    t.update(2, 4, { friendship: 35 });
    const triangles = detectTriangles(t);
    expect(triangles.length).toBe(2);
    const rivals = triangles.map((tri) => tri.rival).sort();
    expect(rivals).toEqual([3, 4]);
  });
});

// ---------------------------------------------------------------------------
// 11. applyJealousy
// ---------------------------------------------------------------------------
describe("applyJealousy", () => {
  it("delta = -(romance_level * 0.3 * 0.1), update(jealous, rival, {friendship: delta})", () => {
    const t = new RelationshipTracker();
    // romance_level=50 → delta = -(50 * 0.3 * 0.1) = -1.5
    const triangles = [{ jealous: 1, target: 2, rival: 3, romance_level: 50 }];
    applyJealousy(t, triangles);
    // 1→3 friendship: 0 + (-1.5) = -1.5
    expect(t.get(1, 3).friendship).toBeCloseTo(-1.5);
  });

  it("커스텀 rate 적용: rate=0.5, romance=40 → delta=-2.0", () => {
    const t = new RelationshipTracker();
    const triangles = [{ jealous: 1, target: 2, rival: 3, romance_level: 40 }];
    // delta = -(40 * 0.5 * 0.1) = -2.0
    applyJealousy(t, triangles, 0.5);
    expect(t.get(1, 3).friendship).toBeCloseTo(-2.0);
  });

  it("누적: 여러 삼각관계 적용 시 friendship 감소 누적", () => {
    const t = new RelationshipTracker();
    // 두 삼각: 같은 jealous=1, rival=3, romance_level=50 → 각 delta=-1.5, 합계=-3.0
    const triangles = [
      { jealous: 1, target: 2, rival: 3, romance_level: 50 },
      { jealous: 1, target: 4, rival: 3, romance_level: 50 },
    ];
    applyJealousy(t, triangles);
    expect(t.get(1, 3).friendship).toBeCloseTo(-3.0);
  });

  it("빈 삼각관계 → 아무것도 변경 안 함", () => {
    const t = new RelationshipTracker();
    t.update(1, 2, { friendship: 50 });
    applyJealousy(t, []);
    expect(t.get(1, 2).friendship).toBe(50);
  });
});
