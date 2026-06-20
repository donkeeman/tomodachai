/**
 * memory.test.ts
 * MemoryStore 통합 테스트 — Python memory.py 기반 손계산 기대값.
 * 골든 덤프 없음; 시나리오로 검증.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { MemoryStore, defaultSocialEvent } from "./memory";
import type { SocialEvent } from "./memory";

// ---------------------------------------------------------------------------
// 헬퍼
// ---------------------------------------------------------------------------
function makeEvent(partial: Partial<SocialEvent>): SocialEvent {
  return defaultSocialEvent(partial);
}

// ---------------------------------------------------------------------------
// 1. defaultSocialEvent — null 기본값
// ---------------------------------------------------------------------------
describe("defaultSocialEvent", () => {
  it("필수 필드만 지정하면 나머지 null", () => {
    const e = defaultSocialEvent({ id: 1, type: "chat", participants: [1, 2], day: 1 });
    expect(e.time).toBeNull();
    expect(e.location).toBeNull();
    expect(e.reason).toBeNull();
    expect(e.result).toBeNull();
  });

  it("선택 필드 지정 가능", () => {
    const e = defaultSocialEvent({
      id: 1, type: "chat", participants: [1, 2], day: 1,
      time: "morning", location: "park", reason: "lonely", result: "happy",
    });
    expect(e.time).toBe("morning");
    expect(e.location).toBe("park");
    expect(e.reason).toBe("lonely");
    expect(e.result).toBe("happy");
  });
});

// ---------------------------------------------------------------------------
// 2. addEvent — id 자동 부여 (id===0)
// ---------------------------------------------------------------------------
describe("addEvent — id auto-assign", () => {
  it("id=0으로 3개 추가 → 1, 2, 3 순서로 부여", () => {
    const store = new MemoryStore();
    store.addEvent(makeEvent({ id: 0, type: "chat", participants: [1, 2], day: 1 }));
    store.addEvent(makeEvent({ id: 0, type: "gift", participants: [2, 3], day: 2 }));
    store.addEvent(makeEvent({ id: 0, type: "fight", participants: [1, 3], day: 3 }));

    // getEventsFor(1) → day desc → [day3/fight, day1/chat]
    const ev1 = store.getEventsFor(1);
    expect(ev1).toHaveLength(2);
    // id 확인: day3은 3번째 추가 → id=3, day1은 1번째 → id=1
    expect(ev1[0].id).toBe(3); // day=3
    expect(ev1[1].id).toBe(1); // day=1

    // getEventsFor(2) → day desc → [day2/gift, day1/chat]
    const ev2 = store.getEventsFor(2);
    expect(ev2).toHaveLength(2);
    expect(ev2[0].id).toBe(2); // day=2
    expect(ev2[1].id).toBe(1); // day=1
  });

  it("추가된 이벤트의 id가 0이 아님 (불변성 확인)", () => {
    const store = new MemoryStore();
    store.addEvent(makeEvent({ id: 0, type: "chat", participants: [1], day: 1 }));
    const events = store.getEventsFor(1);
    expect(events[0].id).not.toBe(0);
    expect(events[0].id).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// 3. addEvent — 명시적 id가 _nextId 갱신
// ---------------------------------------------------------------------------
describe("addEvent — explicit id bumps _nextId", () => {
  it("id=10 명시 추가 후 id=0 추가 → 11 부여", () => {
    const store = new MemoryStore();
    // _nextId=1에서 시작
    store.addEvent(makeEvent({ id: 10, type: "party", participants: [1, 2], day: 5 }));
    // _nextId = max(1, 10) + 1 = 11
    store.addEvent(makeEvent({ id: 0, type: "chat", participants: [1, 2], day: 6 }));
    // id=0이므로 _nextId(=11) 부여 → 저장 id=11
    // _nextId = max(11, 11) + 1 = 12

    const events = store.getEventsFor(1);
    // day desc → [day6/id=11, day5/id=10]
    expect(events).toHaveLength(2);
    expect(events[0].id).toBe(11); // day=6
    expect(events[1].id).toBe(10); // day=5
  });

  it("id=0 먼저, id=5 명시, id=0 다시 → 1, 5, 6 순서", () => {
    const store = new MemoryStore();
    store.addEvent(makeEvent({ id: 0, type: "a", participants: [1], day: 1 }));
    // _nextId=1 → id=1 부여; _nextId = max(1,1)+1 = 2
    store.addEvent(makeEvent({ id: 5, type: "b", participants: [1], day: 2 }));
    // _nextId = max(2,5)+1 = 6
    store.addEvent(makeEvent({ id: 0, type: "c", participants: [1], day: 3 }));
    // id=0 → _nextId=6 부여; _nextId = max(6,6)+1 = 7

    const events = store.getEventsFor(1);
    // day desc → [day3/id=6, day2/id=5, day1/id=1]
    expect(events).toHaveLength(3);
    expect(events[0].id).toBe(6);
    expect(events[1].id).toBe(5);
    expect(events[2].id).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// 4. getEventsFor — 필터, day desc 정렬, limit
// ---------------------------------------------------------------------------
describe("getEventsFor", () => {
  let store: MemoryStore;

  beforeEach(() => {
    store = new MemoryStore();
    // char 1,2 포함 이벤트: day 1, 3, 5
    store.addEvent(makeEvent({ id: 0, type: "chat", participants: [1, 2], day: 1 }));
    store.addEvent(makeEvent({ id: 0, type: "lunch", participants: [2, 3], day: 2 }));
    store.addEvent(makeEvent({ id: 0, type: "walk", participants: [1, 2, 3], day: 3 }));
    store.addEvent(makeEvent({ id: 0, type: "game", participants: [3, 4], day: 4 }));
    store.addEvent(makeEvent({ id: 0, type: "party", participants: [1, 2], day: 5 }));
  });

  it("char=1은 day 1, 3, 5 이벤트만 반환", () => {
    const events = store.getEventsFor(1);
    expect(events.map(e => e.day)).toEqual([5, 3, 1]); // day desc
  });

  it("char=2는 day 1, 2, 3, 5 이벤트 반환", () => {
    const events = store.getEventsFor(2);
    expect(events.map(e => e.day)).toEqual([5, 3, 2, 1]); // day desc
  });

  it("char=4는 day 4만 반환", () => {
    const events = store.getEventsFor(4);
    expect(events).toHaveLength(1);
    expect(events[0].day).toBe(4);
  });

  it("char=99는 빈 배열", () => {
    expect(store.getEventsFor(99)).toEqual([]);
  });

  it("limit=2이면 최신 2개만 반환", () => {
    const events = store.getEventsFor(2, 2);
    expect(events).toHaveLength(2);
    expect(events.map(e => e.day)).toEqual([5, 3]);
  });

  it("limit 기본값 10 — 이벤트 3개면 3개 전부", () => {
    const events = store.getEventsFor(1);
    expect(events).toHaveLength(3);
  });

  it("limit=1이면 가장 최신 1개", () => {
    const events = store.getEventsFor(1, 1);
    expect(events).toHaveLength(1);
    expect(events[0].day).toBe(5);
  });
});

// ---------------------------------------------------------------------------
// 5. getEventsBetween — 양자 모두 포함 필터, day desc, limit
// ---------------------------------------------------------------------------
describe("getEventsBetween", () => {
  let store: MemoryStore;

  beforeEach(() => {
    store = new MemoryStore();
    // 1&2 공유: day 1, 3, 5, 7, 9, 11
    store.addEvent(makeEvent({ id: 0, type: "chat",  participants: [1, 2],    day: 1  }));
    store.addEvent(makeEvent({ id: 0, type: "lunch", participants: [2, 3],    day: 2  }));
    store.addEvent(makeEvent({ id: 0, type: "walk",  participants: [1, 2, 3], day: 3  }));
    store.addEvent(makeEvent({ id: 0, type: "game",  participants: [1, 3],    day: 4  }));
    store.addEvent(makeEvent({ id: 0, type: "party", participants: [1, 2],    day: 5  }));
    store.addEvent(makeEvent({ id: 0, type: "movie", participants: [2, 4],    day: 6  }));
    store.addEvent(makeEvent({ id: 0, type: "date",  participants: [1, 2],    day: 7  }));
    store.addEvent(makeEvent({ id: 0, type: "fight", participants: [1, 2, 3], day: 9  }));
    store.addEvent(makeEvent({ id: 0, type: "cafe",  participants: [1, 2],    day: 11 }));
  });

  it("1&2 사이 이벤트: day desc, 기본 limit=5 → 최신 5개", () => {
    const events = store.getEventsBetween(1, 2);
    // 1&2 공유: day 1, 3, 5, 7, 9, 11 → day desc → 11,9,7,5,3 (limit 5)
    expect(events.map(e => e.day)).toEqual([11, 9, 7, 5, 3]);
  });

  it("인자 순서 무관 (a=2, b=1도 동일)", () => {
    const ev12 = store.getEventsBetween(1, 2);
    const ev21 = store.getEventsBetween(2, 1);
    expect(ev12.map(e => e.id)).toEqual(ev21.map(e => e.id));
  });

  it("limit=2이면 최신 2개", () => {
    const events = store.getEventsBetween(1, 2, 2);
    expect(events.map(e => e.day)).toEqual([11, 9]);
  });

  it("2&3 사이: day desc → [9, 3, 2] (limit=5 이내)", () => {
    const events = store.getEventsBetween(2, 3);
    expect(events.map(e => e.day)).toEqual([9, 3, 2]);
  });

  it("1&4 사이: 공유 이벤트 없음 → 빈 배열", () => {
    expect(store.getEventsBetween(1, 4)).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// 6. day 동일할 때 삽입 순서(stable sort) 유지
// ---------------------------------------------------------------------------
describe("stable sort on same day", () => {
  it("같은 day이면 삽입 순서 유지", () => {
    const store = new MemoryStore();
    store.addEvent(makeEvent({ id: 0, type: "first",  participants: [1], day: 5 }));
    store.addEvent(makeEvent({ id: 0, type: "second", participants: [1], day: 5 }));
    store.addEvent(makeEvent({ id: 0, type: "third",  participants: [1], day: 5 }));

    const events = store.getEventsFor(1);
    // 모두 day=5 → 삽입 순서 유지: first(id=1), second(id=2), third(id=3)
    expect(events.map(e => e.type)).toEqual(["first", "second", "third"]);
  });
});
