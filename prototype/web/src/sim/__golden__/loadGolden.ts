// 골든 픽스처 JSON을 읽어 케이스 배열로 반환. Python dump_golden.py가 생성.
import parseJsonCases from "./parse_json.json";
import periodCases from "./game_clock_period.json";
import newdayCases from "./game_clock_newday.json";
import catchupCases from "./game_clock_catchup.json";
import zodiacCases from "./zodiac.json";
import characterDefaultsCases from "./character_defaults.json";
import determinePersonalityCases from "./determine_personality.json";
import personalityCodeCases from "./personality_code.json";
import relFriendshipLabelsCases from "./rel_friendship_labels.json";
import relRomanceTextCases from "./rel_romance_text.json";
import relStatusTextCases from "./rel_status_text.json";
import relComputeStageCases from "./rel_compute_stage.json";
import relBreakupCases from "./rel_breakup.json";
import relApplyDeltasCases from "./rel_apply_deltas.json";
import relDecayCases from "./rel_decay.json";

export interface GoldenCase<I = unknown, E = unknown> {
  input: I;
  expected?: E;
  throws?: true;
}

const REGISTRY: Record<string, GoldenCase<unknown, unknown>[]> = {
  parse_json: parseJsonCases as GoldenCase[],
  game_clock_period: periodCases as GoldenCase[],
  game_clock_newday: newdayCases as GoldenCase[],
  game_clock_catchup: catchupCases as GoldenCase[],
  zodiac: zodiacCases as GoldenCase[],
  character_defaults: characterDefaultsCases as GoldenCase[],
  determine_personality: determinePersonalityCases as GoldenCase[],
  personality_code: personalityCodeCases as GoldenCase[],
  rel_friendship_labels: relFriendshipLabelsCases as GoldenCase[],
  rel_romance_text: relRomanceTextCases as GoldenCase[],
  rel_status_text: relStatusTextCases as GoldenCase[],
  rel_compute_stage: relComputeStageCases as GoldenCase[],
  rel_breakup: relBreakupCases as GoldenCase[],
  rel_apply_deltas: relApplyDeltasCases as GoldenCase[],
  rel_decay: relDecayCases as GoldenCase[],
};

export function loadGolden<I = unknown, E = unknown>(name: string): GoldenCase<I, E>[] {
  const cases = REGISTRY[name];
  if (!cases) throw new Error(`unknown golden fixture: ${name}`);
  return cases as GoldenCase<I, E>[];
}
