import type { Snapshot } from "./types";

export async function getSnapshot(since: number): Promise<Snapshot> {
  const res = await fetch(`/api/snapshot?since=${since}`);
  return res.json();
}

async function post(url: string, body: unknown): Promise<any> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export const feed = (char_id: number, food_id: number) => post("/api/feed", { char_id, food_id });
export const give = (char_id: number, tool: string) => post("/api/give", { char_id, tool });
export const answerBubble = (index: number, char: string, allow: boolean) =>
  post("/api/bubble", { index, char, answer: allow ? "allow" : "stop" });
export const saveGame = () => post("/api/save", {});
export const resetGame = () => post("/api/reset", {});
