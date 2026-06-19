import type { Snapshot } from "./types";

// 상대경로 — dev: Vite(1420) 프록시가 /api 를 백엔드로 전달(vite.config.ts), prod: 정적 서버가 동일 출처로 서빙.
// (절대 URL 로 두면 Vite 프록시를 우회해 포트/CORS 가 어긋남)
const BASE = "/api";

export async function getSnapshot(since: number): Promise<Snapshot> {
  const res = await fetch(`${BASE}/snapshot?since=${since}`);
  return res.json();
}

async function post(url: string, body: unknown): Promise<any> {
  const res = await fetch(`${BASE}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export const feed = (char_id: number, food_id: number) => post("/feed", { char_id, food_id });
export const give = (char_id: number, tool: string) => post("/give", { char_id, tool });
export const answerBubble = (index: number, char: string, allow: boolean) =>
  post("/bubble", { index, char, answer: allow ? "allow" : "stop" });
export const saveGame = () => post("/save", {});
export const resetGame = () => post("/reset", {});

// 캐릭터 생성 — 백엔드가 /api/characters 를 구현하면 영속/시뮬 참여. appearance 는 전방호환(현재 미저장).
export interface CreatePayload {
  id: number;
  name: string;
  gender: string;
  personality_code: string;
  speech_habits: Record<string, string>;
  favorite_color: string;
  birthday?: string;
  blood_type?: string;
  appearance?: unknown;
  location?: string;
}
export const createCharacter = (p: CreatePayload) => post("/characters", p);
