/**
 * conversation.ts
 * Python src/tomodachai/conversation.py 미러.
 * 이 파일은 결정론 부분만: 타입 + 헬퍼 + SYSTEM_PROMPT + buildConversationPrompt.
 * ConversationEngine(LLM seam)은 별도 태스크.
 * src/sim/은 프레임워크 무의존 — cross-module 타입은 import type만.
 */
import type { Character } from "./character";
import type { SocialEvent } from "./memory";
import type { PersonalityType } from "./personalityType";
import type { Relationship } from "./relationship";
import {
  characterName,
  characterSpeechHabits,
  characterBackstory,
} from "./characterAccessors";
import { getStatusText, getFriendshipText } from "./relationship";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DialogueLine {
  speaker: string;
  text: string;
}

export interface ConversationResult {
  dialogue: DialogueLine[];
  deltas: Record<string, Record<string, number>>;
  summary: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** SocialEvent를 LLM 프롬프트용 한 줄로 포맷. Python _format_memory 1:1. */
export function formatMemory(m: SocialEvent): string {
  const parts: string[] = [`(Day ${m.day})`];
  const typeLabels: Record<string, string> = {
    conversation: "대화",
    fight: "싸움",
    reconciliation: "화해",
    confession: "고백",
    breakup: "이별",
    nickname: "별명 지음",
    donation: "모금",
    birthday: "생일",
    travel: "여행",
    dream: "꿈",
    cheating: "바람",
    catchup: "일상",
  };
  parts.push(typeLabels[m.type] ?? m.type);
  if (m.location) parts.push(`@ ${m.location}`);
  if (m.reason) parts.push(`(사유: ${m.reason})`);
  if (m.result) parts.push(`→ ${m.result}`);
  return "- " + parts.join(" ");
}

/** 말버릇 dict → 한 줄 텍스트. 빈 입력/매칭 없음 → "없음". Python _format_speech_habits 1:1. */
export function formatSpeechHabits(habits: Record<string, string>): string {
  if (Object.keys(habits).length === 0) return "없음";
  const labels: [string, string][] = [
    ["normal", "일반"],
    ["happy", "기쁠 때"],
    ["angry", "화날 때"],
    ["sad", "슬플 때"],
    ["worried", "걱정할 때"],
  ];
  const parts: string[] = [];
  for (const [key, label] of labels) {
    if (key in habits) parts.push(`${label}: "${habits[key]}"`);
  }
  return parts.length > 0 ? parts.join(" / ") : "없음";
}

// ---------------------------------------------------------------------------
// System prompt
// ---------------------------------------------------------------------------

export const SYSTEM_PROMPT =
  "당신은 작은 마을의 주민들 간의 대화를 시뮬레이션하는 AI입니다. 모든 캐릭터는 20~30대 성인입니다. 이름이나 말투에 관계없이 절대로 노인, 어린이, 청소년으로 설정하지 마세요. 반드시 지정된 JSON 형식으로만 응답하세요.";

// ---------------------------------------------------------------------------
// Prompt builder
// ---------------------------------------------------------------------------

/** Python build_conversation_prompt 1:1. */
export function buildConversationPrompt(
  charA: Character,
  charB: Character,
  personalityA: PersonalityType,
  personalityB: PersonalityType,
  relAb: Relationship,
  relBa: Relationship,
  memories: SocialEvent[],
  location: string,
  timeOfDay: string,
): string {
  let memoryText = "없음";
  if (memories.length > 0) {
    memoryText = memories.map(formatMemory).join("\n");
  }

  const habitsA = formatSpeechHabits(characterSpeechHabits(charA));
  const habitsB = formatSpeechHabits(characterSpeechHabits(charB));

  const nameA = characterName(charA);
  const nameB = characterName(charB);

  return `## 캐릭터 1: ${nameA}
성격 유형: ${personalityA.name} (${personalityA.group})
성격: ${personalityA.behavior_guide.trim()}
말버릇: ${habitsA}
배경: ${characterBackstory(charA)}

## 캐릭터 2: ${nameB}
성격 유형: ${personalityB.name} (${personalityB.group})
성격: ${personalityB.behavior_guide.trim()}
말버릇: ${habitsB}
배경: ${characterBackstory(charB)}

## 두 사람의 관계
${nameA} → ${nameB}: ${getStatusText(relAb.stage)} (${getFriendshipText(relAb.friendship)})
${nameB} → ${nameA}: ${getStatusText(relBa.stage)} (${getFriendshipText(relBa.friendship)})

## 최근 기억
${memoryText}

## 상황
장소: ${location}
시간대: ${timeOfDay}

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
{
  "dialogue": [
    {"speaker": "${nameA}", "text": "대사"},
    {"speaker": "${nameB}", "text": "대사"}
  ],
  "deltas": {
    "${nameA}": {"friendship": 0, "romance": 0, "tension": 0},
    "${nameB}": {"friendship": 0, "romance": 0, "tension": 0}
  },
  "summary": "이 대화에서 일어난 일 한 줄 요약"
}

delta 범위: friendship(-10~+10), romance(-5~+5), tension(-10~+10)`;
}
