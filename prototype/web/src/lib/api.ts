import type { Snapshot } from "./types";
import * as sim from "../sim";

export async function getSnapshot(since: number): Promise<Snapshot> {
  return sim.getSnapshot(since);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const wrap = (p: Promise<Record<string, unknown>>): Promise<any> => p;

export const feed = (char_id: number, food_id: number) => wrap(sim.feed());
export const give = (char_id: number, tool: string) => wrap(sim.give());
export const answerBubble = (index: number, char: string, allow: boolean) => wrap(sim.answerBubble());
export const saveGame = () => wrap(sim.save());
export const resetGame = () => wrap(sim.reset());
