// 성격 검사 — 5개 트레잇을 1~8 스케일로 고른다(친구모아풍). 백엔드(src/tomodachai)와 동일 매핑.
// movement+speech → 4계통, expressiveness+attitude → 4형. overall은 유형 판정 무관(병맛 톤만).

export type Axis = "movement" | "speech" | "expressiveness" | "attitude" | "overall";

// 1~8 스케일(검사 문항 느낌). 양 끝 라벨로 방향을 안내.
export interface TraitDef {
  axis: Axis;
  label: string;
  low: string;
  high: string;
  affectsType: boolean; // 유형 판정에 쓰이는 축인지
}

export const TRAITS: TraitDef[] = [
  { axis: "movement", label: "행동", low: "느긋함", high: "활발함", affectsType: true },
  { axis: "speech", label: "말투", low: "유순함", high: "직설적", affectsType: true },
  { axis: "expressiveness", label: "감정 표현", low: "냉정함", high: "감정적", affectsType: true },
  { axis: "attitude", label: "태도", low: "진지함", high: "여유로움", affectsType: true },
  { axis: "overall", label: "분위기", low: "특이함", high: "평범함", affectsType: false },
];

export const SCALE_MIN = 1;
export const SCALE_MAX = 8;

export type TraitValues = Record<Axis, number>; // 각 1~8

export const DEFAULT_TRAITS: TraitValues = {
  movement: 4, speech: 4, expressiveness: 4, attitude: 4, overall: 4,
};

// 1~8 → 0~1 정규화
function norm(v: number): number {
  return (v - SCALE_MIN) / (SCALE_MAX - SCALE_MIN);
}

// 1~8 → 백엔드 Personality(0~10 int) 변환
export function toBackendSliders(t: TraitValues): Record<Axis, number> {
  const conv = (v: number) => Math.round(norm(v) * 10);
  return {
    movement: conv(t.movement),
    speech: conv(t.speech),
    expressiveness: conv(t.expressiveness),
    attitude: conv(t.attitude),
    overall: conv(t.overall),
  };
}

const GROUP_THRESHOLDS: [number, string][] = [
  [0.25, "easygoing"],
  [0.5, "independent"],
  [0.75, "confident"],
  [1.01, "outgoing"],
];

const TYPE_SUFFIXES: [number, number][] = [
  [0.25, 1],
  [0.5, 2],
  [0.75, 3],
  [1.01, 4],
];

const GROUP_TYPE_CODES: Record<string, string> = {
  "easygoing:1": "easygoing_softie",
  "easygoing:2": "easygoing_optimist",
  "easygoing:3": "easygoing_carer",
  "easygoing:4": "easygoing_dreamer",
  "independent:1": "independent_dogooder",
  "independent:2": "independent_perfectionist",
  "independent:3": "independent_introvert",
  "independent:4": "independent_thinker",
  "confident:1": "confident_busybee",
  "confident:2": "confident_gogetter",
  "confident:3": "confident_freespirit",
  "confident:4": "confident_brainiac",
  "outgoing:1": "outgoing_charmer",
  "outgoing:2": "outgoing_dynamo",
  "outgoing:3": "outgoing_buddy",
  "outgoing:4": "outgoing_extrovert",
};

// 코드 → 한글 유형명 (data/personalities.yaml 기준).
export const PERSONALITY_NAMES: Record<string, string> = {
  easygoing_softie: "외유내강형",
  easygoing_optimist: "다정다감형",
  easygoing_carer: "우유부단형",
  easygoing_dreamer: "순진무구형",
  independent_dogooder: "완전무결형",
  independent_perfectionist: "유비무환형",
  independent_introvert: "우물쭈물형",
  independent_thinker: "묵묵부답형",
  confident_busybee: "시원시원형",
  confident_gogetter: "속전속결형",
  confident_freespirit: "유아독존형",
  confident_brainiac: "거두절미형",
  outgoing_charmer: "좌충우돌형",
  outgoing_dynamo: "시끌벅적형",
  outgoing_buddy: "재기발랄형",
  outgoing_extrovert: "명랑쾌활형",
};

const GROUP_NAMES: Record<string, string> = {
  easygoing: "안정파",
  independent: "신중파",
  confident: "주도파",
  outgoing: "사교파",
};

// 코드 → 한 줄 설명 (data/personalities.yaml 기준).
export const PERSONALITY_DESC: Record<string, string> = {
  easygoing_softie: "온화하고 포근한 분위기로 주변 사람을 편안하게 해주는 성격",
  easygoing_optimist: "항상 미소를 잃지 않고 작은 일에도 행복을 느끼는 밝은 성격",
  easygoing_carer: "상대방의 기분을 세심하게 살피며 헌신적으로 챙기는 따뜻한 성격",
  easygoing_dreamer: "느긋하게 자기만의 세계에 빠져드는 자유로운 영혼",
  independent_dogooder: "수줍음이 많지만 마음속은 따뜻하고 의외로 도움을 잘 주는 성격",
  independent_perfectionist: "정확하고 꼼꼼하며 높은 기준을 가진 완벽주의 성격",
  independent_introvert: "조용하고 혼자만의 공간을 소중히 여기는 내향적인 성격",
  independent_thinker: "깊이 생각하고 신중하게 판단하는 철학적인 성격",
  confident_busybee: "빠릿빠릿하게 행동하고 효율을 중시하는 부지런한 성격",
  confident_gogetter: "목표를 세우면 끝까지 밀어붙이는 강한 추진력의 성격",
  confident_freespirit: "시원시원하고 솔직하며 격식 없이 편하게 대하는 성격",
  confident_brainiac: "명석하고 단호하며 리더십이 강한 실력파 성격",
  outgoing_charmer: "빛나는 존재감으로 주목을 받는 매력적인 성격",
  outgoing_dynamo: "폭발적인 에너지로 주변을 이끄는 강렬한 성격",
  outgoing_buddy: "왁자지껄한 분위기를 만들고 사람들을 즐겁게 하는 성격",
  outgoing_extrovert: "뜨거운 열정과 감정으로 주변을 물들이는 외향적인 성격",
};

export function personalityDesc(code: string): string {
  return PERSONALITY_DESC[code] ?? "";
}

export function determinePersonality(t: TraitValues): string {
  const msAvg = (norm(t.movement) + norm(t.speech)) / 2;
  const eaAvg = (norm(t.expressiveness) + norm(t.attitude)) / 2;
  const group = GROUP_THRESHOLDS.find(([th]) => msAvg < th)![1];
  const typeIdx = TYPE_SUFFIXES.find(([th]) => eaAvg < th)![1];
  return GROUP_TYPE_CODES[`${group}:${typeIdx}`];
}

export function personalityLabel(code: string): string {
  const group = code.split("_")[0];
  return `${GROUP_NAMES[group] ?? ""} · ${PERSONALITY_NAMES[code] ?? code}`;
}
