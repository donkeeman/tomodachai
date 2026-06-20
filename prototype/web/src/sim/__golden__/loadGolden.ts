// 골든 픽스처 JSON을 읽어 케이스 배열로 반환. Python dump_golden.py가 생성.
import parseJsonCases from "./parse_json.json";
import periodCases from "./game_clock_period.json";
import newdayCases from "./game_clock_newday.json";
import catchupCases from "./game_clock_catchup.json";

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
};

export function loadGolden<I = unknown, E = unknown>(name: string): GoldenCase<I, E>[] {
  const cases = REGISTRY[name];
  if (!cases) throw new Error(`unknown golden fixture: ${name}`);
  return cases as GoldenCase<I, E>[];
}
