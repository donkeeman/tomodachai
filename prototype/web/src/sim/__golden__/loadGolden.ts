// 골든 픽스처 JSON을 읽어 케이스 배열로 반환. Python dump_golden.py가 생성.
export interface GoldenCase<I = unknown, E = unknown> {
  input: I;
  expected?: E;
  throws?: true;
}

import parseJsonCases from "./parse_json.json";

const REGISTRY: Record<string, GoldenCase[]> = {
  parse_json: parseJsonCases as GoldenCase[],
};

export function loadGolden<I = unknown, E = unknown>(name: string): GoldenCase<I, E>[] {
  const cases = REGISTRY[name];
  if (!cases) throw new Error(`unknown golden fixture: ${name}`);
  return cases as GoldenCase<I, E>[];
}
