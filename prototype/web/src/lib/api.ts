import type { Snapshot } from "./types";
import * as sim from "../sim";

export async function getSnapshot(since: number): Promise<Snapshot> {
  return sim.getSnapshot(since);
}

// 스텁 노옵. 소비자(Card/Toolbar)가 .error/.messages를 읽으므로 그 형태로 캐스팅. 실제 액션 응답은 후속 Phase에서 정의.
const wrap = (p: Promise<Record<string, unknown>>) =>
  p as Promise<{ error?: string; messages?: string[]; message: string; [k: string]: unknown }>;

export const feed = (char_id: number, food_id: number) => wrap(sim.feed());
export const give = (char_id: number, tool: string) => wrap(sim.give());
export const answerBubble = (index: number, char: string, allow: boolean) => wrap(sim.answerBubble());
export const saveGame = () => wrap(sim.save());
export const resetGame = () => wrap(sim.reset());

// 캐릭터 생성 — 인-프로세스 sim 코어가 영속/시뮬 참여를 맡음. appearance 는 전방호환(현재 미저장).
export interface CreatePayload {
  id: number;
  name: string;
  gender: string;
  personality_code: string;
  personality?: Record<string, number>; // 슬라이더 원본(movement/speech/expressiveness/attitude/overall, 0~10)
  speech_habits: Record<string, string>;
  favorite_color: string;
  birthday?: string;        // "MM-DD"
  blood_type?: string;
  voice?: { preset: string; pitch: number; speed: number }; // 0~10
  appearance?: unknown;
  location?: string;
}
export const createCharacter = (p: CreatePayload) => wrap(sim.createCharacter(p));
