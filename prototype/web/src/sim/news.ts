/**
 * news.ts
 * Python news.py (NewsArticle + NewsManager + _build_event_summary) 포팅.
 * 오라클: src/tomodachai/news.py
 *
 * 결정론(이벤트 우선순위 선택 + 요약 조립)은 골든으로 1:1 검증.
 * LLM 호출 자체는 주입 LlmClient(stub)로 구조만 검증.
 */
import type { SocialEvent } from "./memory";
import type { Character } from "./character";
import type { LlmClient } from "../llm";
import { characterName } from "./characterAccessors";

// ---------------------------------------------------------------------------
// NewsArticle
// ---------------------------------------------------------------------------

export interface NewsArticle {
  id: number;
  day: number;
  newsType: "real" | "absurd";
  headline: string;
  body: string;
}

// ---------------------------------------------------------------------------
// 흥미로운 이벤트 우선순위 (news.py _PRIORITY 39-50, 1:1)
// ---------------------------------------------------------------------------

const _PRIORITY: Record<string, number> = {
  marriage: 10,
  breakup: 9,
  confession: 8,
  fight: 7,
  reconciliation: 6,
  birthday: 5,
  travel: 4,
  nickname: 3,
  donation: 2,
  conversation: 1,
};

function score(e: SocialEvent): number {
  return _PRIORITY[e.type] ?? 0;
}

// ---------------------------------------------------------------------------
// NewsManager
// ---------------------------------------------------------------------------

export class NewsManager {
  private articles: NewsArticle[] = [];
  private nextId = 1;

  /** 당일 이벤트 중 가장 흥미로운 것을 골라 뉴스 형식으로 작성 (real). */
  async generateRealNews(
    day: number,
    events: SocialEvent[],
    llm: LlmClient,
    characters: Character[],
  ): Promise<NewsArticle> {
    let eventSummary: string;
    if (events.length) {
      // Python max(events, key=score): 동점 시 첫 항목 유지(안정).
      // 엄격히 더 클 때만 교체하여 첫 최댓값을 보존.
      let highlight = events[0];
      let best = score(highlight);
      for (let i = 1; i < events.length; i++) {
        const s = score(events[i]);
        if (s > best) {
          highlight = events[i];
          best = s;
        }
      }
      eventSummary = buildEventSummary(highlight, characters);
    } else {
      eventSummary = "마을에 특별한 일이 없었습니다.";
    }

    const messages = [
      {
        role: "system" as const,
        content:
          "당신은 아늑한 마을의 뉴스 앵커입니다. " +
          "정중하고 신뢰감 있는 해요체로 짧은 뉴스를 전달해요. " +
          "2~3문장으로 간결하게 작성하세요. " +
          "헤드라인과 본문을 JSON 형식으로 반환하세요: " +
          '{"headline": "...", "body": "..."}',
      },
      {
        role: "user" as const,
        content:
          `오늘(${day}일차) 마을에서 일어난 일을 뉴스 형식으로 전달해주세요.\n\n` +
          `이벤트 요약: ${eventSummary}\n\n` +
          "뉴스 앵커 말투로, 속보 느낌으로 극적으로 전달해주세요. " +
          '예시: "속보! 주민 김민수 씨와 이지은 씨가..." ' +
          "해요체 사용.",
      },
    ];

    const raw = await llm.chatJson(messages, { maxTokens: 256 });
    const article: NewsArticle = {
      id: this.nextId,
      day,
      newsType: "real",
      headline: (raw.headline as string | undefined) ?? "오늘의 마을 소식",
      body: (raw.body as string | undefined) ?? eventSummary,
    };
    this.articles.push(article);
    this.nextId += 1;
    return article;
  }

  /** 완전히 엉뚱한 병맛 뉴스를 LLM으로 자유 생성 (absurd). */
  async generateAbsurdNews(day: number, llm: LlmClient): Promise<NewsArticle> {
    const messages = [
      {
        role: "system" as const,
        content:
          "당신은 마을의 뉴스 앵커입니다. " +
          "지금은 완전히 황당하고 말이 안 되는 병맛 뉴스를 전달할 시간이에요. " +
          "현실과 전혀 관계없는 우스꽝스러운 내용으로, 해요체로 작성하세요. " +
          "2~3문장으로 간결하게. " +
          '{"headline": "...", "body": "..."} 형식으로 반환하세요.',
      },
      {
        role: "user" as const,
        content:
          "황당하고 웃긴 병맛 뉴스 하나 만들어주세요. " +
          "마을이나 캐릭터와 완전히 무관한 엉뚱한 내용이어야 해요. " +
          '예시: "긴급! 공원 분수대에서 라면 맛 물이..." ' +
          "해요체, 속보 느낌으로.",
      },
    ];

    const raw = await llm.chatJson(messages, { maxTokens: 256 });
    const article: NewsArticle = {
      id: this.nextId,
      day,
      newsType: "absurd",
      headline: (raw.headline as string | undefined) ?? "긴급 속보",
      body: (raw.body as string | undefined) ?? "오늘도 마을은 평화롭습니다.",
    };
    this.articles.push(article);
    this.nextId += 1;
    return article;
  }

  // -------------------------------------------------------------------------
  // Queries
  // -------------------------------------------------------------------------

  /** 특정 날의 뉴스 목록 반환. */
  getTodayNews(day: number): NewsArticle[] {
    return this.articles.filter((a) => a.day === day);
  }

  /** 전체 뉴스 목록 반환 (복사본). */
  getAllNews(): NewsArticle[] {
    return [...this.articles];
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** SocialEvent를 사람이 읽기 쉬운 요약 문자열로 변환 (news.py _build_event_summary 1:1). */
export function buildEventSummary(
  event: SocialEvent,
  characters: Character[],
): string {
  const idToName = new Map<string, string>();
  for (const c of characters) {
    idToName.set(String(c.id), characterName(c));
  }

  const participantNames = event.participants.map(
    (p) => idToName.get(String(p)) ?? String(p),
  );
  const namesStr = participantNames.length
    ? participantNames.join("과(와) ")
    : "주민";

  const parts: string[] = [namesStr, event.type];
  if (event.location) parts.push(`장소: ${event.location}`);
  if (event.reason) parts.push(`사유: ${event.reason}`);
  if (event.result) parts.push(`결과: ${event.result}`);
  return parts.join(" — ");
}
