// Python src/tomodachai/config.py 미러. 순수 TS, 기본값 팩토리만.
//
// 클라이언트엔 config.yaml 파일도 LLM_API_KEY env도 없으므로 load_config의
// 파일/env 병합부는 포팅 범위 밖이다. 기본값(AppConfig())만 1:1로 옮긴다.
// 골든: AppConfig().model_dump() == makeDefaultConfig() (snake_case 키 유지).

export interface LLMConfig {
  provider: string; // "litellm" | "claude-cli" | "codex-cli"
  model: string;
  api_key: string | null;
  api_base: string | null;
  temperature: number;
  max_tokens: number;
}

export interface SimulationConfig {
  ticks_per_day: number;
  max_characters: number;
}

export interface LocationConfig {
  name: string;
  capacity: number;
}

export interface AppConfig {
  llm: LLMConfig;
  simulation: SimulationConfig;
  locations: LocationConfig[];
}

export function makeDefaultLLMConfig(): LLMConfig {
  return {
    provider: "litellm",
    model: "claude-sonnet-4-20250514",
    api_key: null,
    api_base: null,
    temperature: 0.8,
    max_tokens: 1000,
  };
}

export function makeDefaultSimulationConfig(): SimulationConfig {
  return { ticks_per_day: 6, max_characters: 10 };
}

/** LocationConfig 생성 — Python LocationConfig(capacity: int = 4) 미러. */
export function makeLocationConfig(name: string, capacity = 4): LocationConfig {
  return { name, capacity };
}

/** AppConfig.locations 기본값 (config.py Field default_factory). */
export function makeDefaultLocations(): LocationConfig[] {
  return [
    { name: "공원", capacity: 5 },
    { name: "편의점", capacity: 3 },
    { name: "카페", capacity: 4 },
  ];
}

/** AppConfig() 기본값 — load_config가 파일/env 없을 때 반환하는 것과 동일. */
export function makeDefaultConfig(): AppConfig {
  return {
    llm: makeDefaultLLMConfig(),
    simulation: makeDefaultSimulationConfig(),
    locations: makeDefaultLocations(),
  };
}
