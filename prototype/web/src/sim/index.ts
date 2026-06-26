// Phase 0 스텁 sim: 빈 마을 + 도는 시계만. 실제 시뮬은 후속 Phase에서.
import type { Snapshot, Rankings } from "../lib/types";
import { GameClock } from "./clock";

const SLEEP_START_MIN = 23 * 60 - 5; // 22:55
const WAKE_MIN = 7 * 60; // 07:00

const EMPTY_RANKINGS: Rankings = { best_couple: [], popular_m: [], popular_f: [], fighters: [] };

export function getSnapshot(_since: number, nowFn?: () => Date): Snapshot {
  // 스텁: 호출마다 GameClock 생성(상태 없음). 폴링이 붙는 후속 Phase에서 재검토.
  const clock = new GameClock(false, nowFn);
  const now = clock.now();
  const hour = clock.getGameHour();
  const minute = now.getUTCMinutes();
  const minutes = hour * 60 + minute;
  const clockStr = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
  return {
    village: "우리 마을",
    provider: "ollama",
    day: 1,
    clock: clockStr,
    minutes,
    seq: 0,
    locations: {},
    foods: [],
    rankings: EMPTY_RANKINGS,
    asleep: minutes >= SLEEP_START_MIN || minutes < WAKE_MIN,
    realtime: true,
    photos: [],
    dishes: [],
    characters: [],
    events: [],
    bubbles: [],
  };
}

const noop = async (): Promise<Record<string, unknown>> => ({ message: "" });
export const feed = noop;
export const give = noop;
export const save = noop;
export const reset = noop;
export const answerBubble = noop;
