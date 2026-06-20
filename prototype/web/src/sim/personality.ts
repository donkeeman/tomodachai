// Python src/tomodachai/personality.py 미러 (결정론 성격코드 판정).
import type { Personality } from "./character";

const GROUP_THRESHOLDS: readonly [number, string][] = [
  [0.25, "easygoing"],
  [0.5, "independent"],
  [0.75, "confident"],
  [1.01, "outgoing"],
];

const TYPE_SUFFIXES: readonly [number, number][] = [
  [0.25, 1],
  [0.5, 2],
  [0.75, 3],
  [1.01, 4],
];

const GROUP_TYPE_CODES: Record<string, string> = {
  "easygoing,1": "easygoing_softie",
  "easygoing,2": "easygoing_optimist",
  "easygoing,3": "easygoing_carer",
  "easygoing,4": "easygoing_dreamer",
  "independent,1": "independent_dogooder",
  "independent,2": "independent_perfectionist",
  "independent,3": "independent_introvert",
  "independent,4": "independent_thinker",
  "confident,1": "confident_busybee",
  "confident,2": "confident_gogetter",
  "confident,3": "confident_freespirit",
  "confident,4": "confident_brainiac",
  "outgoing,1": "outgoing_charmer",
  "outgoing,2": "outgoing_dynamo",
  "outgoing,3": "outgoing_buddy",
  "outgoing,4": "outgoing_extrovert",
};

/** 4슬라이더(0~1) → 16 성격코드. Python determine_personality 1:1. */
export function determinePersonality(s: {
  movement: number;
  speech: number;
  expressiveness: number;
  attitude: number;
}): string {
  const msAvg = (s.movement + s.speech) / 2.0;
  const eaAvg = (s.expressiveness + s.attitude) / 2.0;
  const group = GROUP_THRESHOLDS.find(([t]) => msAvg < t)![1];
  const typeIdx = TYPE_SUFFIXES.find(([t]) => eaAvg < t)![1];
  return GROUP_TYPE_CODES[`${group},${typeIdx}`];
}

/** Personality(0~10 int) → 코드. Python Character.personality_code 1:1 (/10 후 determine). */
export function personalityCode(p: Personality): string {
  return determinePersonality({
    movement: p.movement / 10.0,
    speech: p.speech / 10.0,
    expressiveness: p.expressiveness / 10.0,
    attitude: p.attitude / 10.0,
  });
}
