from __future__ import annotations

from pydantic import BaseModel

from tomodachai.character import Character
from tomodachai.llm import LLMClient
from tomodachai.memory import SocialEvent
from tomodachai.personality import PersonalityType
from tomodachai.relationship import Relationship


class DialogueLine(BaseModel):
    speaker: str
    text: str


class ConversationResult(BaseModel):
    dialogue: list[DialogueLine]
    deltas: dict[str, dict[str, float]]
    summary: str


_SYSTEM_PROMPT = "당신은 작은 마을의 주민들 간의 대화를 시뮬레이션하는 AI입니다. 모든 캐릭터는 20~30대 성인입니다. 이름이나 말투에 관계없이 절대로 노인, 어린이, 청소년으로 설정하지 마세요. 반드시 지정된 JSON 형식으로만 응답하세요."


def build_conversation_prompt(
    char_a: Character,
    char_b: Character,
    personality_a: PersonalityType,
    personality_b: PersonalityType,
    rel_ab: Relationship,
    rel_ba: Relationship,
    memories: list[SocialEvent],
    location: str,
    time_of_day: str,
) -> str:
    memory_text = "없음"
    if memories:
        memory_text = "\n".join(
            f"- (틱 {m.tick}) {m.summary}" for m in memories
        )

    return f"""## 캐릭터 1: {char_a.name}
성격 유형: {personality_a.name}
성격: {personality_a.behavior_guide.strip()}
말버릇: "{char_a.speech_habit}" (문맥에 맞게 자연스럽게 섞어 사용)
배경: {char_a.backstory}

## 캐릭터 2: {char_b.name}
성격 유형: {personality_b.name}
성격: {personality_b.behavior_guide.strip()}
말버릇: "{char_b.speech_habit}" (문맥에 맞게 자연스럽게 섞어 사용)
배경: {char_b.backstory}

## 두 사람의 관계
{char_a.name} → {char_b.name}: 우정 {rel_ab.friendship:.0f}, 로맨스 {rel_ab.romance:.0f}, 긴장 {rel_ab.tension:.0f}
{char_b.name} → {char_a.name}: 우정 {rel_ba.friendship:.0f}, 로맨스 {rel_ba.romance:.0f}, 긴장 {rel_ba.tension:.0f}

## 최근 기억
{memory_text}

## 상황
장소: {location}
시간대: {time_of_day}

## 지시사항
모든 캐릭터는 20~30대 성인입니다. 이름에 관계없이 절대 노인이나 미성년자로 묘사하지 마세요.
말투 규칙 (매우 중요):
- 모든 캐릭터는 항상 존댓말(해요체)을 사용합니다. 친밀도와 관계없이 절대 반말하지 마세요.
- 닌텐도 게임 한국어 번역체 특유의 살짝 어색하고 정중한 말투를 사용하세요.
- 예시: "저는 오늘 기분이 정말 좋아요!", "혹시 같이 가실래요?", "그건 정말 멋진 생각이에요!", "저도 그렇게 생각해요!"
- 감정 표현이 살짝 과하고 직접적이며, 문장이 깔끔하게 끝나는 느낌입니다.
- 줄임말(ㅋㅋ, ㅎㅎ)이나 인터넷 용어는 사용하지 마세요.
두 캐릭터 간의 대화를 3~8번 주고받는 형태로 생성하세요.
각 캐릭터는 성격대로 행동하고 말버릇을 자연스럽게 섞으세요.

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "dialogue": [
    {{"speaker": "{char_a.name}", "text": "대사"}},
    {{"speaker": "{char_b.name}", "text": "대사"}}
  ],
  "deltas": {{
    "{char_a.name}": {{"friendship": 0, "romance": 0, "tension": 0}},
    "{char_b.name}": {{"friendship": 0, "romance": 0, "tension": 0}}
  }},
  "summary": "이 대화에서 일어난 일 한 줄 요약"
}}

delta 범위: friendship(-10~+10), romance(-5~+5), tension(-10~+10)"""


class ConversationEngine:
    def __init__(
        self,
        llm: LLMClient,
        personalities: dict[str, PersonalityType],
    ):
        self._llm = llm
        self._personalities = personalities

    def generate(
        self,
        char_a: Character,
        char_b: Character,
        rel_ab: Relationship,
        rel_ba: Relationship,
        memories: list[SocialEvent],
        location: str,
        time_of_day: str = "오후",
    ) -> ConversationResult:
        personality_a = self._personalities[char_a.personality_code]
        personality_b = self._personalities[char_b.personality_code]

        prompt = build_conversation_prompt(
            char_a=char_a,
            char_b=char_b,
            personality_a=personality_a,
            personality_b=personality_b,
            rel_ab=rel_ab,
            rel_ba=rel_ba,
            memories=memories,
            location=location,
            time_of_day=time_of_day,
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        raw = self._llm.chat_json(messages)

        return ConversationResult(
            dialogue=[DialogueLine(**line) for line in raw["dialogue"]],
            deltas=raw["deltas"],
            summary=raw["summary"],
        )
