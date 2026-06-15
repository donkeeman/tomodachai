"""분수대 이벤트 시스템 — 모금/랩배틀/끝말잇기.

기획서 03-space-and-events.md §5 "분수대 (확정)" 참조.

- 모금: 하루 1회 필수. 캐릭터 수에 비례한 금액을 플레이어 자금에 추가.
- 랩배틀: 캐릭터 2명이 번갈아 디스. LLM이 성격 기반으로 라임 생성 (관찰형).
- 끝말잇기: 게임 내 아이템 풀에서 LLM이 단어 선택. 못 찾으면 탈락 (관찰형).

아침 장터는 상점 시스템(shop.py)에서 처리한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from tomodachai.llm import LLMClient

# 캐릭터 1명당 모금액 (원). 캐릭터 수에 비례.
_DONATION_PER_CHARACTER = 100


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class DonationResult(BaseModel):
    day: int
    character_count: int
    amount: int


class RapVerse(BaseModel):
    name: str
    line: str


class RapBattleResult(BaseModel):
    participants: list[str]
    verses: list[RapVerse]
    winner: str


class WordChainRound(BaseModel):
    name: str
    word: str


class WordChainResult(BaseModel):
    participants: list[str]
    rounds: list[WordChainRound]
    eliminated: str | None
    winner: str


# ---------------------------------------------------------------------------
# FountainManager
# ---------------------------------------------------------------------------


class FountainManager:
    """분수대 이벤트 상태를 관리한다 (세션 한정).

    모금의 '하루 1회' 제약만 상태로 추적한다. 랩배틀/끝말잇기는 무상태 생성기.
    """

    def __init__(self) -> None:
        self._last_donation_day: int | None = None

    # ------------------------------------------------------------------
    # 모금 (donation)
    # ------------------------------------------------------------------

    def has_donated(self, day: int) -> bool:
        """*day*에 이미 모금이 진행됐는지 여부."""
        return self._last_donation_day == day

    def run_donation(self, day: int, character_count: int, game_state) -> DonationResult | None:
        """하루 1회 모금을 진행한다.

        Args:
            day:             현재 게임 일차.
            character_count: 마을 캐릭터 수 (모금액 비례 기준).
            game_state:      ``add_money(int)``를 가진 게임 상태.

        Returns:
            진행 시 :class:`DonationResult`, 같은 날 이미 했다면 ``None``.
        """
        if self.has_donated(day):
            return None

        amount = max(0, character_count) * _DONATION_PER_CHARACTER
        if amount:
            game_state.add_money(amount)

        self._last_donation_day = day
        return DonationResult(
            day=day,
            character_count=character_count,
            amount=amount,
        )

    # ------------------------------------------------------------------
    # 랩배틀 (rap battle)
    # ------------------------------------------------------------------

    def generate_rap_battle(self, char_a, char_b, llm: LLMClient) -> RapBattleResult:
        """캐릭터 2명의 랩배틀을 LLM으로 생성한다 (관찰형)."""
        names = [char_a.name, char_b.name]
        messages = [
            {
                "role": "system",
                "content": (
                    "당신은 마을 분수대 랩배틀의 진행자 겸 라임 작가입니다. "
                    "두 캐릭터가 번갈아 가며 서로를 디스하는 랩 가사를 씁니다. "
                    "디스는 과격하지 않고 유쾌한 병맛 톤으로, 각 캐릭터의 성격을 반영하세요. "
                    "총 4줄(각자 2줄씩) 정도, 마지막에 승자를 한 명 정하세요. "
                    "JSON 형식으로 반환: "
                    '{"verses": [{"name": "...", "line": "..."}], "winner": "..."}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"'{char_a.name}'({char_a.personality_code})와(과) "
                    f"'{char_b.name}'({char_b.personality_code})의 랩배틀을 만들어주세요. "
                    "번갈아 가며 디스하는 라임으로요. 승자도 정해주세요."
                ),
            },
        ]

        raw = llm.chat_json(messages, max_tokens=512)

        verses = [
            RapVerse(name=str(v.get("name", "")), line=str(v.get("line", "")))
            for v in raw.get("verses", [])
            if isinstance(v, dict)
        ]

        winner = raw.get("winner")
        if winner not in names:
            winner = names[0]

        return RapBattleResult(participants=names, verses=verses, winner=winner)

    # ------------------------------------------------------------------
    # 끝말잇기 (word chain)
    # ------------------------------------------------------------------

    def generate_word_chain(
        self, characters: list, item_pool: list[str], llm: LLMClient
    ) -> WordChainResult:
        """아이템 풀에서 단어를 골라 끝말잇기를 진행한다 (관찰형).

        Raises:
            ValueError: 참가자가 2명 미만이거나 아이템 풀이 비었을 때.
        """
        if len(characters) < 2:
            raise ValueError("끝말잇기는 최소 2명이 필요합니다.")
        if not item_pool:
            raise ValueError("끝말잇기 아이템 풀이 비어 있습니다.")

        names = [c.name for c in characters]
        messages = [
            {
                "role": "system",
                "content": (
                    "당신은 마을 분수대 끝말잇기 게임의 진행자입니다. "
                    "캐릭터들이 번갈아 주어진 단어 풀에서 끝말잇기 규칙에 맞는 단어를 고릅니다. "
                    "이어갈 단어를 못 찾는 캐릭터가 탈락하고, 마지막에 남은 캐릭터가 승자입니다. "
                    "JSON 형식으로 반환: "
                    '{"rounds": [{"name": "...", "word": "..."}], '
                    '"eliminated": "...", "winner": "..."}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"참가자: {', '.join(names)}\n"
                    f"사용 가능한 단어 풀: {', '.join(item_pool)}\n\n"
                    "끝말잇기 게임을 진행해주세요. 풀 안의 단어만 사용하세요."
                ),
            },
        ]

        raw = llm.chat_json(messages, max_tokens=512)

        rounds = [
            WordChainRound(name=str(r.get("name", "")), word=str(r.get("word", "")))
            for r in raw.get("rounds", [])
            if isinstance(r, dict)
        ]

        winner = raw.get("winner")
        if winner not in names:
            winner = names[0]

        eliminated = raw.get("eliminated")
        if eliminated is not None and eliminated not in names:
            eliminated = None

        return WordChainResult(
            participants=names,
            rounds=rounds,
            eliminated=eliminated,
            winner=winner,
        )
