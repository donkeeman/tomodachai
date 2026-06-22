// Python src/tomodachai/character.py Character 하위 호환 프로퍼티 미러 (플랫 접근자).
import type { Character } from "./character";
import { personalityCode } from "./personality";

/** Python Character.name → profile.name. */
export function characterName(c: Character): string {
  return c.profile.name;
}

/** Python Character.personality_code → 성격 슬라이더(0~10)에서 런타임 계산. */
export function characterPersonalityCode(c: Character): string {
  return personalityCode(c.profile.personality);
}

/**
 * Python Character.speech_habits → SpeechHabits.as_dict().
 * 빈 문자열 제외, 필드 순서 normal/happy/angry/sad/worried 유지.
 */
export function characterSpeechHabits(c: Character): Record<string, string> {
  const h = c.customizable.speech_habits;
  const result: Record<string, string> = {};
  for (const key of ["normal", "happy", "angry", "sad", "worried"] as const) {
    const value = h[key];
    if (value) result[key] = value;
  }
  return result;
}

/** Python Character.backstory → 필드 제거됨, 항상 빈 문자열. */
export function characterBackstory(_c: Character): string {
  return "";
}
