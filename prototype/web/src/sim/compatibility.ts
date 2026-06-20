/**
 * 호환성 시스템 — Python relationship.py 포팅
 * personalityGroup, calculateCompatibility
 */

// ---------------------------------------------------------------------------
// Tables
// ---------------------------------------------------------------------------

const CODE_TO_GROUP: Record<string, string> = {
  easygoing: "안정파",
  outgoing: "사교파",
  confident: "주도파",
  independent: "신중파",
};

const GROUP_COMPAT: Record<string, number> = {
  "안정파,사교파": 0.85,
  "사교파,안정파": 0.85,
  "신중파,주도파": 0.85,
  "주도파,신중파": 0.85,
  "안정파,안정파": 0.60,
  "사교파,사교파": 0.60,
  "신중파,신중파": 0.60,
  "주도파,주도파": 0.60,
  "안정파,신중파": 0.40,
  "신중파,안정파": 0.40,
  "안정파,주도파": 0.35,
  "주도파,안정파": 0.35,
  "사교파,신중파": 0.45,
  "신중파,사교파": 0.45,
  "사교파,주도파": 0.40,
  "주도파,사교파": 0.40,
};

const BLOOD_COMPAT: Record<string, number> = {
  "O,A": 0.85,
  "A,O": 0.85,
  "O,B": 0.75,
  "B,O": 0.75,
  "O,O": 0.80,
  "A,A": 0.75,
  "B,B": 0.75,
  "AB,O": 0.70,
  "O,AB": 0.70,
  "AB,A": 0.60,
  "A,AB": 0.60,
  "AB,B": 0.60,
  "B,AB": 0.60,
  "AB,AB": 0.55,
  "A,B": 0.35,
  "B,A": 0.35,
};

const ZODIAC_ELEMENTS: Record<string, string> = {
  양자리: "불",
  사자자리: "불",
  사수자리: "불",
  황소자리: "땅",
  처녀자리: "땅",
  염소자리: "땅",
  쌍둥이자리: "바람",
  천칭자리: "바람",
  물병자리: "바람",
  게자리: "물",
  전갈자리: "물",
  물고기자리: "물",
};

// Complementary element pairs (unordered)
const COMPLEMENTARY = [
  new Set(["불", "바람"]),
  new Set(["땅", "물"]),
];

// ---------------------------------------------------------------------------
// Banker's rounding to 4 decimal places (matches Python round(x, 4))
// ---------------------------------------------------------------------------
function roundHalfEven(x: number, decimals: number): number {
  const factor = Math.pow(10, decimals);
  const shifted = x * factor;
  const floor = Math.floor(shifted);
  const diff = shifted - floor;

  if (Math.abs(diff - 0.5) > 1e-10) {
    // Not exactly halfway — standard round
    return Math.round(shifted) / factor;
  }
  // Exactly halfway — round to even
  if (floor % 2 === 0) {
    return floor / factor;
  }
  return (floor + 1) / factor;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Extract personality group from a code like 'easygoing_softie'. Returns null if unrecognized. */
export function personalityGroup(code: string): string | null {
  const prefix = code.includes("_") ? code.split("_")[0] : code;
  return CODE_TO_GROUP[prefix] ?? null;
}

/**
 * Calculate compatibility score between two characters.
 * Weights: personality 50%, blood type 30%, zodiac 20%.
 * Returns a value rounded to 4 decimal places (Python-compatible banker's rounding).
 */
export function calculateCompatibility(
  pA: string,
  pB: string,
  bloodA: string,
  bloodB: string,
  zodiacA: string,
  zodiacB: string,
): number {
  // --- Personality (50%) ---
  const groupA = personalityGroup(pA);
  const groupB = personalityGroup(pB);
  let personalityScore: number;
  if (groupA && groupB) {
    personalityScore = GROUP_COMPAT[`${groupA},${groupB}`] ?? 0.50;
  } else {
    personalityScore = 0.50;
  }

  // --- Blood type (30%) ---
  const bloodScore = BLOOD_COMPAT[`${bloodA.toUpperCase()},${bloodB.toUpperCase()}`] ?? 0.55;

  // --- Zodiac (20%) ---
  const elemA = ZODIAC_ELEMENTS[zodiacA];
  const elemB = ZODIAC_ELEMENTS[zodiacB];
  let zodiacScore: number;
  if (elemA && elemB) {
    if (elemA === elemB) {
      zodiacScore = 0.80;
    } else if (COMPLEMENTARY.some((s) => s.has(elemA) && s.has(elemB))) {
      zodiacScore = 0.70;
    } else {
      zodiacScore = 0.45;
    }
  } else {
    zodiacScore = 0.55;
  }

  const raw = personalityScore * 0.5 + bloodScore * 0.3 + zodiacScore * 0.2;
  return roundHalfEven(raw, 4);
}
