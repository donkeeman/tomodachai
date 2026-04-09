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


def _format_memory(m: SocialEvent) -> str:
    """SocialEvent를 LLM 프롬프트용 한 줄로 포맷."""
    parts = [f"(Day {m.day})"]
    type_labels = {
        "conversation": "대화",
        "fight": "싸움",
        "reconciliation": "화해",
        "confession": "고백",
        "breakup": "이별",
        "nickname": "별명 지음",
        "donation": "모금",
        "birthday": "생일",
        "travel": "여행",
        "dream": "꿈",
        "cheating": "바람",
        "catchup": "일상",
    }
    parts.append(type_labels.get(m.type, m.type))
    if m.location:
        parts.append(f"@ {m.location}")
    if m.reason:
        parts.append(f"(사유: {m.reason})")
    if m.result:
        parts.append(f"→ {m.result}")
    return "- " + " ".join(parts)


def _format_speech_habits(habits: dict[str, str]) -> str:
    if not habits:
        return "없음"
    parts = []
    labels = {"normal": "일반", "happy": "기쁠 때", "angry": "화날 때", "sad": "슬플 때", "worried": "걱정할 때"}
    for key, label in labels.items():
        if key in habits:
            parts.append(f'{label}: "{habits[key]}"')
    return " / ".join(parts) if parts else "없음"


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
        memory_text = "\n".join(_format_memory(m) for m in memories)

    habits_a = _format_speech_habits(char_a.speech_habits)
    habits_b = _format_speech_habits(char_b.speech_habits)

    return f"""## 캐릭터 1: {char_a.name}
성격 유형: {personality_a.name} ({personality_a.group})
성격: {personality_a.behavior_guide.strip()}
말버릇: {habits_a}
배경: {char_a.backstory}

## 캐릭터 2: {char_b.name}
성격 유형: {personality_b.name} ({personality_b.group})
성격: {personality_b.behavior_guide.strip()}
말버릇: {habits_b}
배경: {char_b.backstory}

## 두 사람의 관계
{char_a.name} → {char_b.name}: {rel_ab.get_status_text()} ({rel_ab.get_friendship_text()})
{char_b.name} → {char_a.name}: {rel_ba.get_status_text()} ({rel_ba.get_friendship_text()})

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
