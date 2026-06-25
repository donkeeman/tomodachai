import { describe, it, expect } from "vitest";
import { defaultCharacter, type Character } from "./character";
import { defaultSocialEvent, type SocialEvent } from "./memory";
import { buildEventSummary, NewsManager } from "./news";
import { loadGolden } from "./__golden__/loadGolden";
import type { Msg, LlmClient, ChatOpts } from "../llm";

// ────────────────────────────────────────────────────────────────────────────
// 주입형 stub LlmClient — 받은 messages/opts를 기록하고 고정 raw dict 반환.
// LLM 응답 내용 자체는 비결정적이므로 검증하지 않는다 (구조/후처리만 검증).
// ────────────────────────────────────────────────────────────────────────────
class StubLlm implements LlmClient {
  received: Msg[] | null = null;
  receivedOpts: (ChatOpts & { retries?: number }) | undefined = undefined;
  constructor(private readonly raw: Record<string, unknown>) {}
  async chatJson(
    messages: Msg[],
    opts?: ChatOpts & { retries?: number },
  ): Promise<Record<string, unknown>> {
    this.received = messages;
    this.receivedOpts = opts;
    return this.raw;
  }
}

function makeChars(specs: { id: number; name: string }[]): Character[] {
  return specs.map((s) => defaultCharacter(s.id, s.name));
}

function toEvent(d: Record<string, unknown>): SocialEvent {
  return defaultSocialEvent({
    id: d.id as number,
    type: d.type as string,
    participants: d.participants as number[],
    day: d.day as number,
    time: (d.time as string | null) ?? null,
    location: (d.location as string | null) ?? null,
    reason: (d.reason as string | null) ?? null,
    result: (d.result as string | null) ?? null,
  });
}

// ────────────────────────────────────────────────────────────────────────────
// 골든: buildEventSummary + 우선순위 선택
// ────────────────────────────────────────────────────────────────────────────
interface SummaryInput {
  kind: "summary";
  event: Record<string, unknown>;
  characters: { id: number; name: string }[];
}
interface SelectionInput {
  kind: "selection";
  events: Record<string, unknown>[];
  characters: { id: number; name: string }[];
}

describe("buildEventSummary / 우선순위 선택 (골든)", () => {
  const cases = loadGolden<
    SummaryInput | SelectionInput,
    { summary?: string; highlight_index?: number; highlight_type?: string }
  >("event_summary");

  it("골든 케이스 6개가 로드된다", () => {
    expect(cases.length).toBe(6);
  });

  for (const [i, c] of cases.entries()) {
    if (c.input.kind === "summary") {
      it(`[${i}] buildEventSummary === expected`, () => {
        const input = c.input as SummaryInput;
        const event = toEvent(input.event);
        const chars = makeChars(input.characters);
        expect(buildEventSummary(event, chars)).toBe(c.expected!.summary);
      });
    } else {
      it(`[${i}] generateRealNews가 expected highlight를 선택 (요약이 프롬프트에 포함)`, async () => {
        const input = c.input as SelectionInput;
        const events = input.events.map(toEvent);
        const chars = makeChars(input.characters);

        // 기대 하이라이트의 요약 = buildEventSummary(events[highlight_index], chars)
        const expectedHighlight = events[c.expected!.highlight_index!];
        const expectedSummary = buildEventSummary(expectedHighlight, chars);
        expect(expectedSummary).toBe(c.expected!.summary);
        expect(expectedHighlight.type).toBe(c.expected!.highlight_type);

        const llm = new StubLlm({ headline: "H", body: "B" });
        const mgr = new NewsManager();
        await mgr.generateRealNews(1, events, llm, chars);

        const userMsg = llm.received![1].content;
        expect(userMsg).toContain(`이벤트 요약: ${expectedSummary}`);
      });
    }
  }
});

// ────────────────────────────────────────────────────────────────────────────
// NewsManager 통합 (stub llm)
// ────────────────────────────────────────────────────────────────────────────
describe("NewsManager.generateRealNews (LLM seam, 구조 검증)", () => {
  const chars = makeChars([
    { id: 1, name: "민수" },
    { id: 2, name: "지은" },
  ]);
  const events = [
    defaultSocialEvent({ id: 1, type: "marriage", participants: [1, 2], day: 1, location: "공원" }),
  ];

  it("raw 완전 → id 1, newsType real, headline/body가 raw에서", async () => {
    const llm = new StubLlm({ headline: "결혼 속보", body: "두 사람이 결혼했어요" });
    const mgr = new NewsManager();
    const article = await mgr.generateRealNews(5, events, llm, chars);

    expect(article.id).toBe(1);
    expect(article.day).toBe(5);
    expect(article.newsType).toBe("real");
    expect(article.headline).toBe("결혼 속보");
    expect(article.body).toBe("두 사람이 결혼했어요");

    const msgs = llm.received!;
    expect(msgs.length).toBe(2);
    expect(msgs[0].role).toBe("system");
    expect(msgs[1].role).toBe("user");
    expect(msgs[1].content).toContain("오늘(5일차)");
    expect(llm.receivedOpts?.maxTokens).toBe(256);
  });

  it("raw headline 누락 → 기본 '오늘의 마을 소식', body 누락 → eventSummary", async () => {
    const llm = new StubLlm({});
    const mgr = new NewsManager();
    const article = await mgr.generateRealNews(2, events, llm, chars);

    expect(article.headline).toBe("오늘의 마을 소식");
    expect(article.body).toBe(buildEventSummary(events[0], chars));
  });

  it("빈 events → 요약 '마을에 특별한 일이 없었습니다.' (프롬프트 + body 폴백)", async () => {
    const llm = new StubLlm({});
    const mgr = new NewsManager();
    const article = await mgr.generateRealNews(3, [], llm, chars);

    expect(llm.received![1].content).toContain(
      "이벤트 요약: 마을에 특별한 일이 없었습니다.",
    );
    expect(article.body).toBe("마을에 특별한 일이 없었습니다.");
  });
});

describe("NewsManager.generateAbsurdNews (LLM seam, 구조 검증)", () => {
  it("raw 완전 → newsType absurd, headline/body가 raw에서, maxTokens 256", async () => {
    const llm = new StubLlm({ headline: "라면 분수", body: "공원 분수에서 라면이" });
    const mgr = new NewsManager();
    const article = await mgr.generateAbsurdNews(7, llm);

    expect(article.id).toBe(1);
    expect(article.day).toBe(7);
    expect(article.newsType).toBe("absurd");
    expect(article.headline).toBe("라면 분수");
    expect(article.body).toBe("공원 분수에서 라면이");

    const msgs = llm.received!;
    expect(msgs.length).toBe(2);
    expect(llm.receivedOpts?.maxTokens).toBe(256);
  });

  it("raw 누락 → 기본 '긴급 속보' / '오늘도 마을은 평화롭습니다.'", async () => {
    const llm = new StubLlm({});
    const mgr = new NewsManager();
    const article = await mgr.generateAbsurdNews(1, llm);

    expect(article.headline).toBe("긴급 속보");
    expect(article.body).toBe("오늘도 마을은 평화롭습니다.");
  });
});

describe("NewsManager id 증가 + 조회", () => {
  const chars = makeChars([{ id: 1, name: "민수" }]);
  const events = [defaultSocialEvent({ id: 1, type: "conversation", participants: [1], day: 1 })];

  it("id가 1부터 순차 증가 (real → absurd)", async () => {
    const mgr = new NewsManager();
    const a1 = await mgr.generateRealNews(1, events, new StubLlm({}), chars);
    const a2 = await mgr.generateAbsurdNews(1, new StubLlm({}));
    expect(a1.id).toBe(1);
    expect(a2.id).toBe(2);
  });

  it("getTodayNews는 day로 필터, getAllNews는 전체", async () => {
    const mgr = new NewsManager();
    await mgr.generateRealNews(1, events, new StubLlm({}), chars);
    await mgr.generateAbsurdNews(2, new StubLlm({}));
    await mgr.generateRealNews(2, events, new StubLlm({}), chars);

    expect(mgr.getTodayNews(1).length).toBe(1);
    expect(mgr.getTodayNews(2).length).toBe(2);
    expect(mgr.getTodayNews(99).length).toBe(0);
    expect(mgr.getAllNews().length).toBe(3);
  });

  it("getAllNews는 복사본 — 반환 배열 변형이 내부 상태에 영향 없음", async () => {
    const mgr = new NewsManager();
    await mgr.generateAbsurdNews(1, new StubLlm({}));
    const all = mgr.getAllNews();
    all.pop();
    expect(mgr.getAllNews().length).toBe(1);
  });
});
