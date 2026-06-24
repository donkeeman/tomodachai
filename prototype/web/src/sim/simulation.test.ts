import { describe, it, expect } from "vitest";
import { defaultCharacter, type Character } from "./character";
import { makeDefaultConfig, type LocationConfig } from "./config";
import type { SimRng } from "./rng";
import { assignLocations, Simulation, type SimEvent, type CatchupEvent } from "./simulation";
import { loadPersonalities } from "./personalityType";
import type { Msg, LlmClient, ChatOpts } from "../llm";

// ────────────────────────────────────────────────────────────────────────────
// 고정 raw dict를 반환하는 stub LlmClient (대화 내용 비결정 → 검증 안 함).
// ────────────────────────────────────────────────────────────────────────────
class StubLlm implements LlmClient {
  received: Msg[] | null = null;
  constructor(private readonly raw: Record<string, unknown>) {}
  async chatJson(messages: Msg[], _opts?: ChatOpts): Promise<Record<string, unknown>> {
    this.received = messages;
    return this.raw;
  }
}

// random()을 큐에서 순서대로 반환하는 통제형 rng. consumed로 소비 개수 검증.
class ScriptedRng implements SimRng {
  private i = 0;
  constructor(private readonly randoms: number[] = []) {}
  random(): number {
    const v = this.randoms[this.i] ?? 0;
    this.i += 1;
    return v;
  }
  get consumed(): number {
    return this.i;
  }
  shuffle(): void {}
  choice<T>(arr: readonly T[]): T {
    return arr[0];
  }
  sample<T>(arr: readonly T[], k: number): T[] {
    return arr.slice(0, k);
  }
  uniform(a: number): number {
    return a;
  }
}

function makeSim(
  characters: Character[],
  rng: SimRng,
  raw: Record<string, unknown> = { dialogue: [], deltas: {}, summary: "" },
): Simulation {
  return new Simulation(makeDefaultConfig(), characters, new StubLlm(raw), loadPersonalities(), rng);
}

// ────────────────────────────────────────────────────────────────────────────
// 통제형 stub SimRng — shuffle을 주입해 배정을 결정론으로 만든다.
// 기본 shuffle은 항등(순서 유지)이라 배정 결과를 손으로 예측할 수 있다.
// ────────────────────────────────────────────────────────────────────────────
class StubRng implements SimRng {
  shuffleLengths: number[] = [];
  private readonly shuffleFn: (arr: unknown[]) => void;
  constructor(shuffleFn?: (arr: unknown[]) => void) {
    this.shuffleFn = shuffleFn ?? (() => {});
  }
  random(): number {
    return 0;
  }
  shuffle<T>(arr: T[]): void {
    this.shuffleLengths.push(arr.length);
    this.shuffleFn(arr as unknown[]);
  }
  choice<T>(arr: readonly T[]): T {
    return arr[0];
  }
  sample<T>(arr: readonly T[], k: number): T[] {
    return arr.slice(0, k);
  }
  uniform(a: number): number {
    return a;
  }
}

function chars(...names: string[]): Character[] {
  return names.map((n, i) => defaultCharacter(i + 1, n));
}

function loc(name: string, capacity: number): LocationConfig {
  return { name, capacity };
}

describe("assignLocations (simulation.py 1:1, 주입 rng seam)", () => {
  it("(a) 항등 shuffle: capacity 순서대로 채움", () => {
    const cs = chars("아리", "보리", "초리"); // c1,c2,c3
    const locs = [loc("공원", 2), loc("카페", 1)];
    const res = assignLocations(cs, locs, new StubRng());

    expect(res.get("공원")!.map((c) => c.profile.name)).toEqual(["아리", "보리"]);
    expect(res.get("카페")!.map((c) => c.profile.name)).toEqual(["초리"]);
  });

  it("(b) 모든 장소가 차면 그 캐릭터는 미배정 (break 없이 종료)", () => {
    const cs = chars("아리", "보리");
    const locs = [loc("공원", 1)];
    const res = assignLocations(cs, locs, new StubRng());

    expect(res.get("공원")!.map((c) => c.profile.name)).toEqual(["아리"]);
    const total = [...res.values()].reduce((n, arr) => n + arr.length, 0);
    expect(total).toBe(1); // 보리는 드롭
  });

  it("(c) 캐릭터 0명: 모든 장소 키 존재 + 빈 배열, Map 삽입 순서 유지", () => {
    const locs = [loc("공원", 5), loc("편의점", 3), loc("카페", 4)];
    const res = assignLocations([], locs, new StubRng());

    expect([...res.keys()]).toEqual(["공원", "편의점", "카페"]);
    expect([...res.values()].every((arr) => arr.length === 0)).toBe(true);
  });

  it("(d) shuffle 호출: 캐릭터 1회 + 캐릭터마다 available 1회", () => {
    const cs = chars("아리", "보리", "초리"); // 3명
    const locs = [loc("공원", 5), loc("카페", 5)]; // 2장소
    const rng = new StubRng();
    assignLocations(cs, locs, rng);

    // 첫 호출=캐릭터 배열(len 3), 이후 3회=available(len 2)씩
    expect(rng.shuffleLengths).toEqual([3, 2, 2, 2]);
  });

  it("(e) rng가 실제 순서를 좌우: 캐릭터 역순 shuffle → 배정 순서 반전", () => {
    const cs = chars("아리", "보리", "초리");
    const locs = [loc("공원", 1), loc("카페", 1), loc("도서관", 1)];
    // 캐릭터 배열만 역순으로(available은 문자열이라 그대로) — 원소 타입으로 구분
    const rng = new StubRng((arr) => {
      if (arr.length > 0 && typeof arr[0] !== "string") arr.reverse();
    });
    const res = assignLocations(cs, locs, rng);

    // 역순(초리,보리,아리)이 공원/카페/도서관 순서로 배정
    expect(res.get("공원")!.map((c) => c.profile.name)).toEqual(["초리"]);
    expect(res.get("카페")!.map((c) => c.profile.name)).toEqual(["보리"]);
    expect(res.get("도서관")!.map((c) => c.profile.name)).toEqual(["아리"]);
  });

  it("(f) 입력 characters 배열은 변형하지 않음 (복사본 shuffle)", () => {
    const cs = chars("아리", "보리", "초리");
    const snapshot = cs.map((c) => c.profile.name);
    const rng = new StubRng((arr) => arr.reverse());
    assignLocations(cs, [loc("공원", 5)], rng);
    expect(cs.map((c) => c.profile.name)).toEqual(snapshot);
  });
});

describe("Simulation._runConversation (simulation.py 1:1, LLM seam)", () => {
  it("deltas를 이름→방향으로 적용 + conversation 메모리 이벤트 추가", async () => {
    const a = defaultCharacter(1, "아리");
    const b = defaultCharacter(2, "보리");
    const raw = {
      dialogue: [{ speaker: "아리", text: "안녕" }],
      deltas: { 아리: { friendship: 7 }, 보리: { friendship: 3 } },
      summary: "둘이 인사함",
    };
    const sim = makeSim([a, b], new ScriptedRng(), raw);

    const result = await sim._runConversation(a, b, "공원", "오후");

    expect(result.summary).toBe("둘이 인사함");
    // 아리→보리 방향 friendship +7, 보리→아리 방향 +3
    expect(sim.relationships.get(1, 2).friendship).toBe(7);
    expect(sim.relationships.get(2, 1).friendship).toBe(3);
    // conversation 이벤트: participants/day/location
    const ev = sim.memory.getEventsBetween(1, 2);
    expect(ev.length).toBe(1);
    expect(ev[0].type).toBe("conversation");
    expect(ev[0].location).toBe("공원");
    expect(ev[0].day).toBe(0);
    expect(ev[0].participants).toEqual([1, 2]);
  });

  it("이름이 어느 쪽과도 안 맞으면 그 deltas는 무시", async () => {
    const a = defaultCharacter(1, "아리");
    const b = defaultCharacter(2, "보리");
    const raw = { dialogue: [], deltas: { 엉뚱: { friendship: 99 } }, summary: "" };
    const sim = makeSim([a, b], new ScriptedRng(), raw);
    await sim._runConversation(a, b, "공원", "오후");
    expect(sim.relationships.get(1, 2).friendship).toBe(0);
    expect(sim.relationships.get(2, 1).friendship).toBe(0);
  });
});

describe("Simulation._triggerFight (simulation.py 1:1)", () => {
  it("Fight 추가 + 양방 friendship-5 + satisfaction-10 + 메모리 + 요약/원인", () => {
    const a = defaultCharacter(1, "아리");
    const b = defaultCharacter(2, "보리");
    const sim = makeSim([a, b], new ScriptedRng());

    const ev = sim._triggerFight(1, 2, -42)!;

    expect(ev.type).toBe("fight");
    expect(ev.participants).toEqual(["아리", "보리"]);
    expect(ev.summary).toBe("아리와(과) 보리의 긴장이 폭발하여 싸움이 벌어졌다!");
    // friendship -5 양방
    expect(sim.relationships.get(1, 2).friendship).toBe(-5);
    expect(sim.relationships.get(2, 1).friendship).toBe(-5);
    // 미해결 싸움 등록 + cause :.0f
    const fights = sim.relationships.getFights();
    expect(fights.length).toBe(1);
    expect(fights[0].cause).toBe("우정 -42 — 사이가 나쁨");
    expect(fights[0].resolved).toBe(false);
    // satisfaction 50→40
    expect(a.state.satisfaction).toBe(40);
    expect(b.state.satisfaction).toBe(40);
    // 메모리 fight 이벤트
    const mem = sim.memory.getEventsBetween(1, 2);
    expect(mem[0].type).toBe("fight");
  });

  it("이미 싸우는 쌍이면 null (순서 무관)", () => {
    const a = defaultCharacter(1, "아리");
    const b = defaultCharacter(2, "보리");
    const sim = makeSim([a, b], new ScriptedRng());
    sim._triggerFight(1, 2, -40);
    // 역순으로 호출해도 동일 쌍 인식
    const second = sim._triggerFight(2, 1, -40);
    expect(second).toBeNull();
    expect(sim.relationships.getFights().length).toBe(1);
  });

  it("cause :.0f banker's rounding (.5 → 짝수)", () => {
    const sim = makeSim([defaultCharacter(1, "아리"), defaultCharacter(2, "보리")], new ScriptedRng());
    const ev = sim._triggerFight(1, 2, -30.5)!; // -30.5 → -30 (짝수)
    expect(ev).not.toBeNull();
    expect(sim.relationships.getFights()[0].cause).toBe("우정 -30 — 사이가 나쁨");
  });
});

describe("Simulation._triggerConfession (simulation.py 1:1, rng seam)", () => {
  function setupFriendPair(): Simulation {
    const a = defaultCharacter(1, "아리");
    const b = defaultCharacter(2, "보리");
    const sim = makeSim([a, b], new ScriptedRng([0])); // 사용 시 random() 주입
    // 저장된 rel 참조를 직접 세팅: friend 단계 + romance 60
    for (const [x, y] of [[1, 2], [2, 1]] as const) {
      const rel = sim.relationships.get(x, y);
      rel.friendship = 40;
      rel.romance = 60;
      rel.stage = "friend";
    }
    return sim;
  }

  it("성공(random<0.5): 양쪽 LOVER 전환 + 요약 + 메모리 accepted", () => {
    const sim = makeSim(
      [defaultCharacter(1, "아리"), defaultCharacter(2, "보리")],
      new ScriptedRng([0.2]), // <0.5 성공
    );
    for (const [x, y] of [[1, 2], [2, 1]] as const) {
      const rel = sim.relationships.get(x, y);
      rel.friendship = 40;
      rel.romance = 60;
      rel.stage = "friend";
    }

    const ev = sim._triggerConfession(1, 2);
    expect(ev.type).toBe("confession_success");
    expect(ev.summary).toBe("아리가 보리에게 고백하여 연인이 되었다!");
    expect(sim.relationships.get(1, 2).stage).toBe("lover");
    expect(sim.relationships.get(2, 1).stage).toBe("lover");
    const mem = sim.memory.getEventsBetween(1, 2);
    expect(mem[0].type).toBe("confession");
    expect(mem[0].result).toBe("accepted");
  });

  it("실패(random>=0.5): friendship-5/romance-10 + 요약 + 메모리 rejected", () => {
    const sim = makeSim(
      [defaultCharacter(1, "아리"), defaultCharacter(2, "보리")],
      new ScriptedRng([0.7]), // >=0.5 실패
    );
    for (const [x, y] of [[1, 2], [2, 1]] as const) {
      const rel = sim.relationships.get(x, y);
      rel.friendship = 40;
      rel.romance = 60;
      rel.stage = "friend";
    }

    const ev = sim._triggerConfession(1, 2);
    expect(ev.type).toBe("confession_fail");
    expect(ev.summary).toBe("아리가 보리에게 고백했지만 거절당했다.");
    // a→b 방향만 델타 적용
    expect(sim.relationships.get(1, 2).friendship).toBe(35);
    expect(sim.relationships.get(1, 2).romance).toBe(50);
    const mem = sim.memory.getEventsBetween(1, 2);
    expect(mem[0].result).toBe("rejected");
  });

  // setupFriendPair 사용 안 함 경고 방지용 참조 — 헬퍼 의도 보존
  it("setupFriendPair 헬퍼: friend/romance60 세팅 확인", () => {
    const sim = setupFriendPair();
    expect(sim.relationships.get(1, 2).stage).toBe("friend");
    expect(sim.relationships.get(1, 2).romance).toBe(60);
  });
});

describe("Simulation._updateNeeds / _checkStageTransitions / _name", () => {
  it("_updateNeeds: hunger +5(max100), satisfaction -1(min0)", () => {
    const a = defaultCharacter(1, "아리"); // hunger 0, satisfaction 50
    const b = defaultCharacter(2, "보리");
    a.state.hunger = 98;
    b.state.satisfaction = 0;
    const sim = makeSim([a, b], new ScriptedRng());
    sim._updateNeeds();
    expect(a.state.hunger).toBe(100); // 98+5=103 → clamp 100
    expect(a.state.satisfaction).toBe(49); // 50-1
    expect(b.state.hunger).toBe(5);
    expect(b.state.satisfaction).toBe(0); // 0-1 → clamp 0
  });

  it("_checkStageTransitions: friendship 기반(allowRomantic=false)", () => {
    const sim = makeSim([defaultCharacter(1, "아리"), defaultCharacter(2, "보리")], new ScriptedRng());
    const rel = sim.relationships.get(1, 2);
    rel.friendship = 45; // friendshipStage(45)="friend"
    sim._checkStageTransitions();
    expect(sim.relationships.get(1, 2).stage).toBe("friend");
  });

  it("_name: 알려진 id→이름, 미지 id→String(id)", () => {
    const sim = makeSim([defaultCharacter(1, "아리")], new ScriptedRng());
    expect(sim._name(1)).toBe("아리");
    expect(sim._name(999)).toBe("999");
  });
});

describe("Simulation._checkTriggeredEventsForPair (rng 소비 순서)", () => {
  it("fight 게이트: friendship<=-30 → random 소비 후 stage 체크 → fight", () => {
    const sim = makeSim(
      [defaultCharacter(1, "아리"), defaultCharacter(2, "보리")],
      new ScriptedRng([0.1]), // <0.3 fight
    );
    const rel = sim.relationships.get(1, 2);
    rel.friendship = -40;
    rel.stage = "friend"; // !=stranger
    const events = sim._checkTriggeredEventsForPair(1, 2);
    expect(events.length).toBe(1);
    expect(events[0].type).toBe("fight");
  });

  it("단락 평가: friendship>임계면 fight random 미소비", () => {
    const rng = new ScriptedRng([0.1, 0.1]);
    const sim = makeSim([defaultCharacter(1, "아리"), defaultCharacter(2, "보리")], rng);
    const rel = sim.relationships.get(1, 2);
    rel.friendship = 10; // > -30 → fight 조건 첫 항에서 단락, random 미소비
    rel.romance = 0; // < 60 → confession도 첫 항 단락
    sim._checkTriggeredEventsForPair(1, 2);
    expect(rng.consumed).toBe(0); // 둘 다 random 도달 전 단락
  });

  it("confession 게이트: romance>=60 & stage friend & random<0.2 → confession", () => {
    const sim = makeSim(
      [defaultCharacter(1, "아리"), defaultCharacter(2, "보리")],
      new ScriptedRng([0.1]), // confession random<0.2 (friendship>임계라 fight random 미소비)
    );
    const rel = sim.relationships.get(1, 2);
    rel.friendship = 50; // > -30, fight 단락
    rel.romance = 60;
    rel.stage = "friend";
    const events = sim._checkTriggeredEventsForPair(1, 2);
    expect(events.length).toBe(1);
    expect(events[0].type).toBe("confession_success");
  });

  it("stage=stranger: friendship<=임계라 random은 소비되나 stage 탈락 → fight 없음", () => {
    const rng = new ScriptedRng([0.1]);
    const sim = makeSim([defaultCharacter(1, "아리"), defaultCharacter(2, "보리")], rng);
    const rel = sim.relationships.get(1, 2);
    rel.friendship = -40; // <= -30 → random 소비
    rel.stage = "stranger"; // stage 체크에서 탈락
    rel.romance = 0; // confession 첫 항 단락
    const events = sim._checkTriggeredEventsForPair(1, 2);
    expect(events).toEqual([]);
    expect(rng.consumed).toBe(1); // fight random은 소비됨(순서 충실)
  });
});

describe("Simulation._checkTriggeredEvents (전체 쌍)", () => {
  it("allPairs 순회하며 fight 트리거", () => {
    const sim = makeSim(
      [defaultCharacter(1, "아리"), defaultCharacter(2, "보리")],
      new ScriptedRng([0.1]),
    );
    const rel = sim.relationships.get(1, 2); // 쌍 생성
    rel.friendship = -40;
    rel.stage = "friend";
    const events = sim._checkTriggeredEvents();
    expect(events.length).toBe(1);
    expect(events[0].type).toBe("fight");
  });
});

describe("Simulation.step (simulation.py 1:1, RNG/LLM seam)", () => {
  it("캐릭터 2명 미만이면 []", async () => {
    const sim = makeSim([defaultCharacter(1, "아리")], new ScriptedRng());
    expect(await sim.step("낮")).toEqual([]);
  });

  it("기본: conversation 이벤트 1개 + 트리거 없음 + step_count++ + needs 갱신", async () => {
    const a = defaultCharacter(1, "아리");
    const b = defaultCharacter(2, "보리");
    const sim = makeSim([a, b], new ScriptedRng());

    const events = await sim.step("낮");

    expect(events.length).toBe(1);
    expect(events[0].type).toBe("conversation");
    // 기본 장소 = config.locations[0] = 공원 (stub choice→arr[0])
    expect((events[0] as Extract<SimEvent, { type: "conversation" }>).location).toBe("공원");
    expect((events[0] as Extract<SimEvent, { type: "conversation" }>).participants).toEqual([
      "아리",
      "보리",
    ]);
    expect(sim.stepCount).toBe(1);
    // _updateNeeds: hunger 0→5, satisfaction 50→49
    expect(a.state.hunger).toBe(5);
    expect(a.state.satisfaction).toBe(49);
  });

  it("timeOfDay가 대화 프롬프트로 전파됨 (시간대: 낮)", async () => {
    const a = defaultCharacter(1, "아리");
    const b = defaultCharacter(2, "보리");
    const llm = new StubLlm({ dialogue: [], deltas: {}, summary: "" });
    const sim = new Simulation(makeDefaultConfig(), [a, b], llm, loadPersonalities(), new ScriptedRng());
    await sim.step("낮");
    expect(llm.received![1].content).toContain("시간대: 낮");
  });

  it("config.locations 비어있으면 '공동주택'", async () => {
    const cfg = makeDefaultConfig();
    cfg.locations = [];
    const a = defaultCharacter(1, "아리");
    const b = defaultCharacter(2, "보리");
    const sim = new Simulation(
      cfg,
      [a, b],
      new StubLlm({ dialogue: [], deltas: {}, summary: "" }),
      loadPersonalities(),
      new ScriptedRng(),
    );
    const events = await sim.step("낮");
    expect((events[0] as Extract<SimEvent, { type: "conversation" }>).location).toBe("공동주택");
  });

  it("트리거 발생: fight도 events에 포함 (conversation 다음)", async () => {
    const a = defaultCharacter(1, "아리");
    const b = defaultCharacter(2, "보리");
    const sim = makeSim([a, b], new ScriptedRng([0.1])); // fight random<0.3
    const rel = sim.relationships.get(1, 2);
    rel.friendship = -40;
    rel.stage = "friend";

    const events = await sim.step("낮");
    expect(events.length).toBe(2);
    expect(events[0].type).toBe("conversation");
    expect(events[1].type).toBe("fight");
  });
});

// catchup용 rng: uniform을 큐에서 반환, choice는 첫 원소.
class CatchupRng implements SimRng {
  private ui = 0;
  constructor(private readonly uniforms: number[]) {}
  random(): number {
    return 0;
  }
  shuffle(): void {}
  choice<T>(arr: readonly T[]): T {
    return arr[0];
  }
  sample<T>(arr: readonly T[], k: number): T[] {
    return arr.slice(0, k);
  }
  uniform(): number {
    const v = this.uniforms[this.ui] ?? 0;
    this.ui += 1;
    return v;
  }
}

describe("Simulation.generateCatchupEvents (simulation.py 1:1, RNG seam)", () => {
  it("offline 0시간(count 0) → []", () => {
    const sim = makeSim([defaultCharacter(1, "아리"), defaultCharacter(2, "보리")], new CatchupRng([]));
    expect(sim.generateCatchupEvents(0)).toEqual([]);
  });

  it("캐릭터 2명 미만 → []", () => {
    const sim = makeSim([defaultCharacter(1, "아리")], new CatchupRng([]));
    expect(sim.generateCatchupEvents(24)).toEqual([]);
  });

  it("count=1(offline 2.4h): 비대칭 델타(0.8/0.6) + round1 + 요약 + 메모리", () => {
    const a = defaultCharacter(1, "아리");
    const b = defaultCharacter(2, "보리");
    const sim = makeSim([a, b], new CatchupRng([5.0, 2.0])); // fDelta=5, rDelta=2

    const events = sim.generateCatchupEvents(2.4);

    expect(events.length).toBe(1);
    const ev = events[0] as CatchupEvent;
    expect(ev.type).toBe("catchup");
    expect(ev.participants).toEqual(["아리", "보리"]);
    expect(ev.summary).toBe("아리와(과) 보리이(가) 어울렸다.");
    expect(ev.deltas).toEqual({
      아리: { friendship: 5, romance: 2 },
      보리: { friendship: 4, romance: 1.2 }, // 5*0.8=4, 2*0.6=1.2
    });
    // 실제 트래커 반영 (비대칭)
    expect(sim.relationships.get(1, 2).friendship).toBe(5);
    expect(sim.relationships.get(1, 2).romance).toBe(2);
    expect(sim.relationships.get(2, 1).friendship).toBe(4);
    expect(sim.relationships.get(2, 1).romance).toBeCloseTo(1.2, 10);
    expect(sim.stepCount).toBe(1);
    expect(sim.memory.getEventsBetween(1, 2)[0].type).toBe("catchup");
  });

  it("count=2(offline 9.6h): 누적 + step_count=2 + 메모리 2건", () => {
    const a = defaultCharacter(1, "아리");
    const b = defaultCharacter(2, "보리");
    // iter1 f=5,r=2 / iter2 f=3,r=1
    const sim = makeSim([a, b], new CatchupRng([5.0, 2.0, 3.0, 1.0]));

    const events = sim.generateCatchupEvents(9.6);

    expect(events.length).toBe(2);
    expect(sim.stepCount).toBe(2);
    expect(sim.memory.getEventsBetween(1, 2).length).toBe(2);
    // 누적: a→b friendship 5+3=8, romance 2+1=3
    expect(sim.relationships.get(1, 2).friendship).toBe(8);
    expect(sim.relationships.get(1, 2).romance).toBe(3);
    // 두 번째 이벤트 델타
    expect((events[1] as CatchupEvent).deltas).toEqual({
      아리: { friendship: 3, romance: 1 },
      보리: { friendship: 2.4, romance: 0.6 }, // 3*0.8=2.4, 1*0.6=0.6
    });
  });
});
