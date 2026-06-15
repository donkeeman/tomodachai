"""뉴스 시스템 테스트."""

from __future__ import annotations

import pytest

from tomodachai.memory import SocialEvent
from tomodachai.news import NewsArticle, NewsManager, _build_event_summary

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_event(
    day: int = 1,
    participants: list[int] | None = None,
    type: str = "conversation",
    location: str | None = None,
    reason: str | None = None,
    result: str | None = None,
    id: int = 0,
) -> SocialEvent:
    return SocialEvent(
        id=id,
        type=type,
        participants=participants or [1, 2],
        day=day,
        location=location,
        reason=reason,
        result=result,
    )


class _FakeChar:
    def __init__(self, id_, name):
        self.id = id_
        self.name = name


class _MockLLM:
    """LLMClient를 대신하는 목 객체."""

    def __init__(self, response: dict):
        self._response = response
        self.call_count = 0
        self.last_messages: list[dict] = []

    def chat_json(self, messages: list[dict], **kwargs) -> dict:
        self.call_count += 1
        self.last_messages = messages
        return self._response


# ---------------------------------------------------------------------------
# NewsArticle model
# ---------------------------------------------------------------------------

def test_news_article_model():
    a = NewsArticle(id=1, day=3, news_type="real", headline="속보!", body="내용입니다.")
    assert a.id == 1
    assert a.news_type == "real"
    assert a.headline == "속보!"


def test_news_article_absurd_type():
    a = NewsArticle(id=2, day=1, news_type="absurd", headline="긴급!", body="병맛 내용.")
    assert a.news_type == "absurd"


# ---------------------------------------------------------------------------
# NewsManager — generate_real_news
# ---------------------------------------------------------------------------

def test_generate_real_news_returns_article():
    manager = NewsManager()
    llm = _MockLLM({
        "headline": "속보! 민수와 지은이 만났다",
        "body": "오늘 마을에서 대화가 있었어요.",
    })
    events = [_make_event()]
    characters = [_FakeChar(1, "민수"), _FakeChar(2, "지은")]

    article = manager.generate_real_news(day=1, events=events, llm=llm, characters=characters)

    assert isinstance(article, NewsArticle)
    assert article.news_type == "real"
    assert article.day == 1
    assert article.headline == "속보! 민수와 지은이 만났다"
    assert article.body == "오늘 마을에서 대화가 있었어요."
    assert llm.call_count == 1


def test_generate_real_news_picks_highest_impact():
    """emotional_impact 절댓값 합이 가장 큰 이벤트가 선택되는지 확인."""
    manager = NewsManager()
    captured_prompts: list[str] = []

    class CaptureLLM:
        def chat_json(self, messages, **kwargs):
            # user 메시지에서 어떤 이벤트가 쓰였는지 확인
            captured_prompts.append(messages[-1]["content"])
            return {"headline": "h", "body": "b"}

    # 우선순위: marriage(10) > breakup(9) > confession(8) > fight(7) > conversation(1)
    low_event = _make_event(day=1, type="conversation", location="공원")
    high_event = _make_event(day=2, type="confession", result="rejected")
    events = [low_event, high_event]
    characters = [_FakeChar(1, "민수"), _FakeChar(2, "지은")]

    manager.generate_real_news(day=1, events=events, llm=CaptureLLM(), characters=characters)

    # 프롬프트에 우선순위 높은 이벤트(confession)이 포함되어야 함
    assert "confession" in captured_prompts[0]


def test_generate_real_news_no_events():
    """이벤트가 없어도 뉴스 생성이 실패하지 않는다."""
    manager = NewsManager()
    llm = _MockLLM({"headline": "특별 뉴스 없음", "body": "오늘은 조용했어요."})
    characters = [_FakeChar(1, "민수")]

    article = manager.generate_real_news(day=5, events=[], llm=llm, characters=characters)

    assert article.news_type == "real"
    assert article.day == 5


def test_generate_real_news_increments_id():
    manager = NewsManager()
    llm = _MockLLM({"headline": "h", "body": "b"})
    characters = [_FakeChar(1, "민수")]

    a1 = manager.generate_real_news(day=1, events=[], llm=llm, characters=characters)
    a2 = manager.generate_real_news(day=2, events=[], llm=llm, characters=characters)

    assert a1.id == 1
    assert a2.id == 2


# ---------------------------------------------------------------------------
# NewsManager — generate_absurd_news
# ---------------------------------------------------------------------------

def test_generate_absurd_news_returns_article():
    manager = NewsManager()
    llm = _MockLLM({
        "headline": "긴급! 공원 분수에서 라면 맛 물이",
        "body": "오늘 오후 공원 분수에서 라면 맛이 나는 물이 나왔다고 해요.",
    })

    article = manager.generate_absurd_news(day=3, llm=llm)

    assert isinstance(article, NewsArticle)
    assert article.news_type == "absurd"
    assert article.day == 3
    assert "라면" in article.headline
    assert llm.call_count == 1


def test_generate_absurd_news_prompt_has_no_event_context():
    """병맛 뉴스 프롬프트에는 실제 이벤트 컨텍스트가 없어야 한다."""
    captured: list[list[dict]] = []

    class CaptureLLM:
        def chat_json(self, messages, **kwargs):
            captured.append(messages)
            return {"headline": "h", "body": "b"}

    manager = NewsManager()
    manager.generate_absurd_news(day=1, llm=CaptureLLM())

    # 이벤트 요약 문구가 프롬프트에 없어야 함
    all_content = " ".join(m["content"] for m in captured[0])
    assert "이벤트 요약" not in all_content


def test_absurd_and_real_ids_are_sequential():
    manager = NewsManager()
    llm = _MockLLM({"headline": "h", "body": "b"})
    characters = [_FakeChar(1, "민수")]

    a_real = manager.generate_real_news(day=1, events=[], llm=llm, characters=characters)
    a_absurd = manager.generate_absurd_news(day=1, llm=llm)

    assert a_real.id == 1
    assert a_absurd.id == 2


# ---------------------------------------------------------------------------
# NewsManager — get_today_news / get_all_news
# ---------------------------------------------------------------------------

def test_get_today_news_filters_by_day():
    manager = NewsManager()
    llm = _MockLLM({"headline": "h", "body": "b"})
    characters = [_FakeChar(1, "민수")]

    manager.generate_real_news(day=1, events=[], llm=llm, characters=characters)
    manager.generate_real_news(day=2, events=[], llm=llm, characters=characters)
    manager.generate_absurd_news(day=1, llm=llm)

    day1 = manager.get_today_news(1)
    day2 = manager.get_today_news(2)
    day3 = manager.get_today_news(3)

    assert len(day1) == 2  # real + absurd on day 1
    assert len(day2) == 1
    assert len(day3) == 0


def test_get_all_news_returns_everything():
    manager = NewsManager()
    llm = _MockLLM({"headline": "h", "body": "b"})
    characters = [_FakeChar(1, "민수")]

    manager.generate_real_news(day=1, events=[], llm=llm, characters=characters)
    manager.generate_absurd_news(day=1, llm=llm)
    manager.generate_absurd_news(day=2, llm=llm)

    all_news = manager.get_all_news()
    assert len(all_news) == 3


def test_get_today_news_returns_copy():
    """반환된 리스트 수정이 내부 상태에 영향을 주지 않아야 한다."""
    manager = NewsManager()
    llm = _MockLLM({"headline": "h", "body": "b"})
    characters = [_FakeChar(1, "민수")]

    manager.generate_real_news(day=1, events=[], llm=llm, characters=characters)
    result = manager.get_today_news(1)
    result.clear()

    assert len(manager.get_today_news(1)) == 1


# ---------------------------------------------------------------------------
# LLM fallback — missing keys in response
# ---------------------------------------------------------------------------

def test_real_news_fallback_on_missing_keys():
    """LLM이 headline/body 키 중 하나만 반환해도 기본값으로 처리."""
    manager = NewsManager()
    llm = _MockLLM({"headline": "헤드라인만 있음"})  # body 없음
    characters = [_FakeChar(1, "민수")]

    article = manager.generate_real_news(day=1, events=[], llm=llm, characters=characters)
    assert article.headline == "헤드라인만 있음"
    assert article.body  # 기본값이 있어야 함


def test_absurd_news_fallback_on_missing_keys():
    manager = NewsManager()
    llm = _MockLLM({})  # headline, body 둘 다 없음

    article = manager.generate_absurd_news(day=1, llm=llm)
    assert article.headline  # 기본값이 있어야 함
    assert article.body


# ---------------------------------------------------------------------------
# _build_event_summary helper
# ---------------------------------------------------------------------------

def test_build_event_summary_with_characters():
    event = _make_event(participants=[1, 2], type="conversation", location="공원")
    characters = [_FakeChar(1, "민수"), _FakeChar(2, "지은")]

    summary = _build_event_summary(event, characters)

    assert "민수" in summary
    assert "지은" in summary
    assert "conversation" in summary


def test_build_event_summary_unknown_character():
    """characters 목록에 없는 ID는 ID 문자열로 표시."""
    event = _make_event(participants=[99, 100])
    summary = _build_event_summary(event, [])

    assert "99" in summary
    assert "100" in summary


# ---------------------------------------------------------------------------
# API endpoint tests (integration with mock LLM)
# ---------------------------------------------------------------------------

def test_api_get_news_empty(client_with_news):
    """뉴스가 없을 때 빈 리스트를 반환한다."""
    resp = client_with_news.get("/api/news?day=99")
    assert resp.status_code == 200
    assert resp.json() == []


def test_api_get_news_default_day(client_with_news):
    """day 파라미터 없이 조회하면 현재 day_count 기준."""
    resp = client_with_news.get("/api/news")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_api_generate_real_news(client_with_news, monkeypatch):
    """POST /api/news/generate → real 뉴스 생성."""
    from tomodachai.api import routes as routes_module

    def fake_generate_real(day, events, llm, characters):
        from tomodachai.news import NewsArticle
        return NewsArticle(id=1, day=day, news_type="real", headline="속보!", body="내용.")

    monkeypatch.setattr(
        routes_module._game.news,  # type: ignore[union-attr]
        "generate_real_news",
        fake_generate_real,
    )
    resp = client_with_news.post("/api/news/generate", json={"news_type": "real"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["news_type"] == "real"
    assert data["headline"] == "속보!"


def test_api_generate_absurd_news(client_with_news, monkeypatch):
    """POST /api/news/generate?news_type=absurd → 병맛 뉴스 생성."""
    from tomodachai.api import routes as routes_module

    def fake_generate_absurd(day, llm):
        from tomodachai.news import NewsArticle
        return NewsArticle(id=2, day=day, news_type="absurd", headline="긴급!", body="병맛.")

    monkeypatch.setattr(
        routes_module._game.news,  # type: ignore[union-attr]
        "generate_absurd_news",
        fake_generate_absurd,
    )
    resp = client_with_news.post("/api/news/generate", json={"news_type": "absurd"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["news_type"] == "absurd"
    assert data["headline"] == "긴급!"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client_with_news():
    """뉴스 API 테스트용 TestClient."""
    from fastapi.testclient import TestClient

    from tomodachai.api.routes import set_game_state
    from tomodachai.config import AppConfig, LLMConfig, LocationConfig, SimulationConfig
    from tomodachai.game_state import GameState
    from tomodachai.server import create_app

    cfg = AppConfig(
        llm=LLMConfig(provider="litellm", model="ollama/gemma3", temperature=0.8),
        simulation=SimulationConfig(),
        locations=[LocationConfig(id="park", name="공원")],
    )
    gs = GameState(config=cfg)
    application = create_app()
    set_game_state(gs)
    return TestClient(application)
