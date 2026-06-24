// Python src/tomodachai/simulation.py 미러.
//
// 결정론(상수/델타 산술/요약 문자열/임계 비교/clamp)은 1:1 충실 포팅.
// 확률(shuffle/choice/sample/random/uniform)은 주입형 SimRng seam — 비트일치
// 안 함, 구조/후처리만 검증. LLM 호출은 ConversationEngine(주입 LlmClient) seam.

import type { Character } from "./character";
import type { LocationConfig } from "./config";
import type { SimRng } from "./rng";

// 오프라인 catch-up: 큰 이벤트는 생성 금지
export const BIG_EVENT_TYPES: ReadonlySet<string> = new Set([
  "confession_success",
  "confession_fail",
  "marriage",
  "breakup",
]);

// catch-up 1회 이벤트 수치 변화 폭 (작게 유지)
export const CATCHUP_FRIENDSHIP_DELTA_RANGE: readonly [number, number] = [-3.0, 5.0];
export const CATCHUP_ROMANCE_DELTA_RANGE: readonly [number, number] = [-1.0, 3.0];

// 자동 트리거 임계값
export const FIGHT_FRIENDSHIP_THRESHOLD = -30.0; // friendship 이하면 싸움 가능
export const FIGHT_CHANCE = 0.3;
export const CONFESSION_ROMANCE_THRESHOLD = 60.0;
export const CONFESSION_CHANCE = 0.2;
export const HUNGER_PER_TICK = 5.0;
export const SATISFACTION_DECAY = 1.0;

/**
 * 캐릭터를 장소에 배정. Python assign_locations 미러 (seed 인자 → 주입 rng).
 *
 * rng.shuffle로 캐릭터 순서를 섞고, 각 캐릭터마다 available 장소 순서를 다시
 * 섞은 뒤 capacity 미만인 첫 장소에 배정한다. 모든 장소가 차면 그 캐릭터는
 * 배정되지 않는다 (Python과 동일: break 없이 루프 종료).
 *
 * 반환 Map은 locations 삽입 순서를 보존한다 (Python dict 순서 = 삽입 순서).
 */
export function assignLocations(
  characters: readonly Character[],
  locations: readonly LocationConfig[],
  rng: SimRng,
): Map<string, Character[]> {
  const assignments = new Map<string, Character[]>();
  const capacityMap = new Map<string, number>();
  for (const loc of locations) {
    assignments.set(loc.name, []);
    capacityMap.set(loc.name, loc.capacity);
  }

  const shuffled = [...characters];
  rng.shuffle(shuffled);

  const available = locations.map((loc) => loc.name);
  for (const char of shuffled) {
    rng.shuffle(available);
    for (const locName of available) {
      if (assignments.get(locName)!.length < capacityMap.get(locName)!) {
        assignments.get(locName)!.push(char);
        break;
      }
    }
  }

  return assignments;
}
