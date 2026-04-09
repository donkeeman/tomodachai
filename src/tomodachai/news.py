"""뉴스 시스템 — 일일 뉴스 브리핑 생성."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from tomodachai.llm import LLMClient
from tomodachai.memory import SocialEvent


class NewsArticle(BaseModel):
    id: int
    day: int
    news_type: Literal["real", "absurd"]
    headline: str
    body: str


class NewsManager:
    def __init__(self) -> None:
        self._articles: list[NewsArticle] = []
        self._next_id: int = 1

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate_real_news(
        self,
        day: int,
        events: list[SocialEvent],
        llm: LLMClient,
        characters: list,
    ) -> NewsArticle:
        """당일 이벤트 중 가장 흥미로운 것을 골라 뉴스 형식으로 작성."""
        # 흥미로운 이벤트 우선순위: 큰 사건(이별/고백/결혼/싸움) > 일반
        _PRIORITY: dict[str, int] = {
            "marriage": 10,
            "breakup": 9,
            "confession": 8,
            "fight": 7,
            "reconciliation": 6,
            "birthday": 5,
            "travel": 4,
            "nickname": 3,
            "donation": 2,
            "conversation": 1,
        }

        def score(e: SocialEvent) -> int:
            return _PRIORITY.get(e.type, 0)

        if events:
            highlight = max(events, key=score)
            event_summary = _build_event_summary(highlight, characters)
        else:
            event_summary = "마을에 특별한 일이 없었습니다."

        messages = [
            {
                "role": "system",
                "content": (
                    "당신은 아늑한 마을의 뉴스 앵커입니다. "
                    "정중하고 신뢰감 있는 해요체로 짧은 뉴스를 전달해요. "
                    "2~3문장으로 간결하게 작성하세요. "
                    "헤드라인과 본문을 JSON 형식으로 반환하세요: "
                    '{"headline": "...", "body": "..."}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"오늘({day}일차) 마을에서 일어난 일을 뉴스 형식으로 전달해주세요.\n\n"
                    f"이벤트 요약: {event_summary}\n\n"
                    "뉴스 앵커 말투로, 속보 느낌으로 극적으로 전달해주세요. "
                    '예시: "속보! 주민 김민수 씨와 이지은 씨가..." '
                    "해요체 사용."
                ),
            },
        ]

        raw = llm.chat_json(messages, max_tokens=256)
        article = NewsArticle(
            id=self._next_id,
            day=day,
            news_type="real",
            headline=raw.get("headline", "오늘의 마을 소식"),
            body=raw.get("body", event_summary),
        )
        self._articles.append(article)
        self._next_id += 1
        return article

    def generate_absurd_news(
        self,
        day: int,
        llm: LLMClient,
    ) -> NewsArticle:
        """완전히 엉뚱한 병맛 뉴스를 LLM으로 자유 생성."""
        messages = [
            {
                "role": "system",
                "content": (
                    "당신은 마을의 뉴스 앵커입니다. "
                    "지금은 완전히 황당하고 말이 안 되는 병맛 뉴스를 전달할 시간이에요. "
                    "현실과 전혀 관계없는 우스꽝스러운 내용으로, 해요체로 작성하세요. "
                    "2~3문장으로 간결하게. "
                    '{"headline": "...", "body": "..."} 형식으로 반환하세요.'
                ),
            },
            {
                "role": "user",
                "content": (
                    "황당하고 웃긴 병맛 뉴스 하나 만들어주세요. "
                    "마을이나 캐릭터와 완전히 무관한 엉뚱한 내용이어야 해요. "
                    '예시: "긴급! 공원 분수대에서 라면 맛 물이..." '
                    "해요체, 속보 느낌으로."
                ),
            },
        ]

        raw = llm.chat_json(messages, max_tokens=256)
        article = NewsArticle(
            id=self._next_id,
            day=day,
            news_type="absurd",
            headline=raw.get("headline", "긴급 속보"),
            body=raw.get("body", "오늘도 마을은 평화롭습니다."),
        )
        self._articles.append(article)
        self._next_id += 1
        return article

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_today_news(self, day: int) -> list[NewsArticle]:
        """특정 날의 뉴스 목록 반환."""
        return [a for a in self._articles if a.day == day]

    def get_all_news(self) -> list[NewsArticle]:
        """전체 뉴스 목록 반환."""
        return list(self._articles)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _build_event_summary(event: SocialEvent, characters: list) -> str:
    """SocialEvent를 사람이 읽기 쉬운 요약 문자열로 변환."""
    id_to_name: dict[str, str] = {str(c.id): c.name for c in characters}

    participant_names = [
        id_to_name.get(str(p), str(p)) for p in event.participants
    ]
    names_str = "과(와) ".join(participant_names) if participant_names else "주민"

    parts = [f"{names_str}", event.type]
    if event.location:
        parts.append(f"장소: {event.location}")
    if event.reason:
        parts.append(f"사유: {event.reason}")
    if event.result:
        parts.append(f"결과: {event.result}")
    return " — ".join(parts)
