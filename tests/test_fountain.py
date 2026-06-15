"""분수대 이벤트 시스템 테스트 — 모금/랩배틀/끝말잇기."""

from __future__ import annotations

import pytest

from tomodachai.fountain import (
    DonationResult,
    FountainManager,
    RapBattleResult,
    WordChainResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeChar:
    def __init__(self, id_, name, personality_code="outgoing_dynamo"):
        self.id = id_
        self.name = name
        self.personality_code = personality_code


class _FakeGameState:
    """add_money만 흉내내는 가벼운 게임 상태."""

    def __init__(self, money=0):
        self.money = money

    def add_money(self, amount):
        self.money += amount


class _MockLLM:
    """LLMClient를 대신하는 목 객체 (test_news 스타일)."""

    def __init__(self, response: dict):
        self._response = response
        self.call_count = 0
        self.last_messages: list[dict] = []

    def chat_json(self, messages: list[dict], **kwargs) -> dict:
        self.call_count += 1
        self.last_messages = messages
        return self._response


# ---------------------------------------------------------------------------
# 모금 (donation)
# ---------------------------------------------------------------------------


def test_donation_amount_scales_with_character_count():
    mgr = FountainManager()
    gs = _FakeGameState()

    result = mgr.run_donation(day=1, character_count=4, game_state=gs)

    assert isinstance(result, DonationResult)
    assert result.character_count == 4
    # 캐릭터 수에 비례 — 1명일 때보다 많아야 한다
    one = FountainManager().run_donation(day=1, character_count=1, game_state=_FakeGameState())
    assert result.amount > one.amount


def test_donation_adds_money_to_game_state():
    mgr = FountainManager()
    gs = _FakeGameState(money=500)

    result = mgr.run_donation(day=1, character_count=3, game_state=gs)

    assert gs.money == 500 + result.amount


def test_donation_only_once_per_day():
    mgr = FountainManager()
    gs = _FakeGameState()

    first = mgr.run_donation(day=1, character_count=3, game_state=gs)
    second = mgr.run_donation(day=1, character_count=3, game_state=gs)

    assert first is not None
    assert second is None  # 같은 날 두 번째 모금은 없음
    assert gs.money == first.amount  # 돈도 한 번만 추가


def test_donation_resets_next_day():
    mgr = FountainManager()
    gs = _FakeGameState()

    mgr.run_donation(day=1, character_count=3, game_state=gs)
    second = mgr.run_donation(day=2, character_count=3, game_state=gs)

    assert second is not None  # 다음 날은 다시 가능


def test_donation_zero_characters():
    """캐릭터가 없으면 모금액은 0이어도 실행은 된다."""
    mgr = FountainManager()
    gs = _FakeGameState()

    result = mgr.run_donation(day=1, character_count=0, game_state=gs)

    assert result.amount == 0
    assert result.character_count == 0


def test_has_donated_today_flag():
    mgr = FountainManager()
    gs = _FakeGameState()

    assert mgr.has_donated(day=1) is False
    mgr.run_donation(day=1, character_count=2, game_state=gs)
    assert mgr.has_donated(day=1) is True
    assert mgr.has_donated(day=2) is False


# ---------------------------------------------------------------------------
# 랩배틀 (rap battle)
# ---------------------------------------------------------------------------


def test_rap_battle_returns_result_with_verses():
    mgr = FountainManager()
    llm = _MockLLM(
        {
            "verses": [
                {"name": "민수", "line": "내 라임은 폭발해 너는 그냥 조용해"},
                {"name": "지은", "line": "조용한 게 클래스지 넌 그냥 시끄러워"},
            ],
            "winner": "지은",
        }
    )
    a = _FakeChar(1, "민수")
    b = _FakeChar(2, "지은")

    result = mgr.generate_rap_battle(a, b, llm)

    assert isinstance(result, RapBattleResult)
    assert result.participants == ["민수", "지은"]
    assert len(result.verses) == 2
    assert result.winner == "지은"
    assert llm.call_count == 1


def test_rap_battle_prompt_includes_both_names():
    mgr = FountainManager()
    captured: list[list[dict]] = []

    class CaptureLLM:
        def chat_json(self, messages, **kwargs):
            captured.append(messages)
            return {"verses": [], "winner": "민수"}

    a = _FakeChar(1, "민수")
    b = _FakeChar(2, "지은")
    mgr.generate_rap_battle(a, b, CaptureLLM())

    all_content = " ".join(m["content"] for m in captured[0])
    assert "민수" in all_content
    assert "지은" in all_content


def test_rap_battle_winner_falls_back_to_participant():
    """LLM이 엉뚱한 승자를 반환하면 참가자 중 하나로 보정."""
    mgr = FountainManager()
    llm = _MockLLM({"verses": [], "winner": "존재하지않는사람"})
    a = _FakeChar(1, "민수")
    b = _FakeChar(2, "지은")

    result = mgr.generate_rap_battle(a, b, llm)

    assert result.winner in ("민수", "지은")


# ---------------------------------------------------------------------------
# 끝말잇기 (word chain)
# ---------------------------------------------------------------------------


def test_word_chain_returns_result():
    mgr = FountainManager()
    llm = _MockLLM(
        {
            "rounds": [
                {"name": "민수", "word": "사과"},
                {"name": "지은", "word": "과자"},
                {"name": "민수", "word": "자전거"},
            ],
            "eliminated": "지은",
            "winner": "민수",
        }
    )
    chars = [_FakeChar(1, "민수"), _FakeChar(2, "지은")]
    item_pool = ["사과", "과자", "자전거", "거울"]

    result = mgr.generate_word_chain(chars, item_pool, llm)

    assert isinstance(result, WordChainResult)
    assert result.winner == "민수"
    assert result.eliminated == "지은"
    assert len(result.rounds) == 3


def test_word_chain_prompt_includes_item_pool():
    mgr = FountainManager()
    captured: list[list[dict]] = []

    class CaptureLLM:
        def chat_json(self, messages, **kwargs):
            captured.append(messages)
            return {"rounds": [], "eliminated": None, "winner": "민수"}

    chars = [_FakeChar(1, "민수"), _FakeChar(2, "지은")]
    item_pool = ["사과", "바나나"]
    mgr.generate_word_chain(chars, item_pool, llm=CaptureLLM())

    all_content = " ".join(m["content"] for m in captured[0])
    assert "사과" in all_content
    assert "바나나" in all_content


def test_word_chain_needs_at_least_two_players():
    mgr = FountainManager()
    llm = _MockLLM({"rounds": [], "eliminated": None, "winner": "민수"})
    chars = [_FakeChar(1, "민수")]

    with pytest.raises(ValueError):
        mgr.generate_word_chain(chars, ["사과"], llm)


def test_word_chain_empty_pool_raises():
    mgr = FountainManager()
    llm = _MockLLM({"rounds": [], "eliminated": None, "winner": "민수"})
    chars = [_FakeChar(1, "민수"), _FakeChar(2, "지은")]

    with pytest.raises(ValueError):
        mgr.generate_word_chain(chars, [], llm)


# ---------------------------------------------------------------------------
# GameState wiring
# ---------------------------------------------------------------------------


def test_game_state_has_fountain_manager():
    from tomodachai.game_state import GameState

    gs = GameState()
    assert isinstance(gs.fountain, FountainManager)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_fountain():
    """분수대 API 테스트용 TestClient (캐릭터 2명 포함)."""
    from fastapi.testclient import TestClient

    from tomodachai.api.routes import set_game_state
    from tomodachai.character import (
        Character,
        CharacterState,
        Customizable,
        Profile,
        SpeechHabits,
    )
    from tomodachai.config import AppConfig, LLMConfig, LocationConfig, SimulationConfig
    from tomodachai.game_state import GameState
    from tomodachai.server import create_app

    cfg = AppConfig(
        llm=LLMConfig(provider="litellm", model="ollama/gemma3", temperature=0.8),
        simulation=SimulationConfig(),
        locations=[LocationConfig(id="fountain", name="분수대")],
    )
    gs = GameState(config=cfg)
    for cid, name, code in [(1, "민수", "outgoing_dynamo"), (2, "지은", "easygoing_dreamer")]:
        gs.add_character(
            Character(
                id=cid,
                personality_code=code,
                profile=Profile(name=name, birthday="03-15", blood_type="B", gender="남성"),
                state=CharacterState(),
                customizable=Customizable(speech_habits=SpeechHabits(normal="~")),
            )
        )
    application = create_app()
    set_game_state(gs)
    return TestClient(application)


def test_api_donation_runs(client_with_fountain):
    resp = client_with_fountain.post("/api/fountain/donation")
    assert resp.status_code == 201
    data = resp.json()
    assert data["character_count"] == 2
    assert data["amount"] > 0


def test_api_donation_twice_same_day_conflicts(client_with_fountain):
    first = client_with_fountain.post("/api/fountain/donation")
    assert first.status_code == 201
    second = client_with_fountain.post("/api/fountain/donation")
    assert second.status_code == 409  # 이미 오늘 모금함


def test_api_donation_status(client_with_fountain):
    before = client_with_fountain.get("/api/fountain/donation/status")
    assert before.status_code == 200
    assert before.json()["donated"] is False

    client_with_fountain.post("/api/fountain/donation")

    after = client_with_fountain.get("/api/fountain/donation/status")
    assert after.json()["donated"] is True


def test_api_rap_battle(client_with_fountain, monkeypatch):
    from tomodachai.api import routes as routes_module
    from tomodachai.fountain import RapBattleResult, RapVerse

    def fake_rap(char_a, char_b, llm):
        return RapBattleResult(
            participants=[char_a.name, char_b.name],
            verses=[RapVerse(name=char_a.name, line="라임")],
            winner=char_b.name,
        )

    monkeypatch.setattr(routes_module._game.fountain, "generate_rap_battle", fake_rap)
    resp = client_with_fountain.post("/api/fountain/rap-battle", json={"char_ids": [1, 2]})
    assert resp.status_code == 201
    data = resp.json()
    assert data["participants"] == ["민수", "지은"]
    assert data["winner"] == "지은"


def test_api_rap_battle_unknown_char(client_with_fountain):
    resp = client_with_fountain.post("/api/fountain/rap-battle", json={"char_ids": [1, 999]})
    assert resp.status_code == 404


def test_api_word_chain(client_with_fountain, monkeypatch):
    from tomodachai.api import routes as routes_module
    from tomodachai.fountain import WordChainResult, WordChainRound

    def fake_chain(characters, item_pool, llm):
        return WordChainResult(
            participants=[c.name for c in characters],
            rounds=[WordChainRound(name=characters[0].name, word="사과")],
            eliminated=characters[1].name,
            winner=characters[0].name,
        )

    monkeypatch.setattr(routes_module._game.fountain, "generate_word_chain", fake_chain)
    resp = client_with_fountain.post(
        "/api/fountain/word-chain",
        json={"char_ids": [1, 2], "item_pool": ["사과", "과자"]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["winner"] == "민수"
    assert data["eliminated"] == "지은"


def test_api_word_chain_empty_pool(client_with_fountain):
    resp = client_with_fountain.post(
        "/api/fountain/word-chain",
        json={"char_ids": [1, 2], "item_pool": []},
    )
    assert resp.status_code == 400
