import type { Snapshot } from "./types";

const BASE = "http://127.0.0.1:8000/api";

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
