/**
 * relationship.ts
 * Python tomodachai/relationship.py의 결정론적 코어를 포팅한 순수함수 모음.
 * 외부 의존 없음 (Babylon/Svelte/Tauri 임포트 금지).
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type RelationshipStage =
  | "stranger"
  | "acquaintance"
  | "friend"
  | "best_friend"
  | "lover"
  | "married";

export type BreakupReason =
  | "mutual"
  | "fight"
  | "cheating"
  | "boredom"
  | "triangle"
  | "misunderstanding";

export interface Relationship {
  friendship: number; // -100 ~ 100
  romance: number;    // 0 ~ 100
  stage: RelationshipStage;
}

export function defaultRelationship(): Relationship {
  return { friendship: 0, romance: 0, stage: "stranger" };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

// ---------------------------------------------------------------------------
// Stage / label functions
// ---------------------------------------------------------------------------

/**
 * 우정 수치만으로 비연애 스테이지 결정.
 * ≥80 → best_friend, ≥40 → friend, ≥10 → acquaintance, else → stranger
 */
export function friendshipStage(friendship: number): RelationshipStage {
  if (friendship >= 80) return "best_friend";
  if (friendship >= 40) return "friend";
  if (friendship >= 10) return "acquaintance";
  return "stranger";
}

/**
 * 현재 스테이지 + 수치로 다음 스테이지 계산 (순수).
 */
export function computeStage(
  friendship: number,
  romance: number,
  currentStage: RelationshipStage,
  allowRomantic: boolean,
): RelationshipStage {
  // married: romance<60 → lover, else married
  if (currentStage === "married") {
    return romance < 60 ? "lover" : "married";
  }

  // lover: allowRomantic&&romance≥90 → married; romance<60 → friendshipStage; else lover
  if (currentStage === "lover") {
    if (allowRomantic && romance >= 90) return "married";
    if (romance < 60) return friendshipStage(friendship);
    return "lover";
  }

  // friend|best_friend + allowRomantic + romance≥60 → lover
  if (
    (currentStage === "friend" || currentStage === "best_friend") &&
    allowRomantic &&
    romance >= 60
  ) {
    return "lover";
  }

  return friendshipStage(friendship);
}

/**
 * 스테이지 → 한국어 표시 텍스트
 */
export function getStatusText(stage: RelationshipStage): string {
  const map: Record<RelationshipStage, string> = {
    stranger: "모르는 사이",
    acquaintance: "아는 사이",
    friend: "친구",
    best_friend: "베프",
    lover: "연인",
    married: "부부",
  };
  return map[stage];
}

/**
 * 우정 수치 → 한국어 라벨
 * ≥80 "둘도 없는 친구", ≥60 "꽤 친한 사이", ≥40 "친해지는 중",
 * ≥20 "알고 지내는 사이", ≥-19 "그저 그런 사이", ≥-49 "서먹서먹",
 * ≥-69 "사이가 나쁨", else "앙숙"
 */
export function getFriendshipText(friendship: number): string {
  if (friendship >= 80) return "둘도 없는 친구";
  if (friendship >= 60) return "꽤 친한 사이";
  if (friendship >= 40) return "친해지는 중";
  if (friendship >= 20) return "알고 지내는 사이";
  if (friendship >= -19) return "그저 그런 사이";
  if (friendship >= -49) return "서먹서먹";
  if (friendship >= -69) return "사이가 나쁨";
  return "앙숙";
}

/**
 * 로맨스 수치 → 한국어 라벨 (≤0이면 null)
 * ≥80 "완전 반한", ≥50 "많이 좋아하는", ≥21 "좋아하는 것 같은", >0 "약간 신경 쓰이는"
 */
export function getRomanceText(romance: number): string | null {
  if (romance <= 0) return null;
  if (romance >= 80) return "완전 반한";
  if (romance >= 50) return "많이 좋아하는";
  if (romance >= 21) return "좋아하는 것 같은";
  return "약간 신경 쓰이는";
}

// ---------------------------------------------------------------------------
// Breakup conditions
// ---------------------------------------------------------------------------

/**
 * 연애/결혼 스테이지에서 이별 조건 자동 감지.
 * 우선순위: cheating → triangle → fight → boredom
 * stage∉(lover,married) → null
 */
export function checkBreakupConditions(
  stage: RelationshipStage,
  romance: number,
  hasCheating: boolean,
  hasTriangle: boolean,
  fightUnresolved: boolean,
  romanceThreshold = 20.0,
): BreakupReason | null {
  if (stage !== "lover" && stage !== "married") return null;
  if (hasCheating) return "cheating";
  if (hasTriangle) return "triangle";
  if (fightUnresolved && romance < romanceThreshold) return "fight";
  if (romance < romanceThreshold) return "boredom";
  return null;
}

// ---------------------------------------------------------------------------
// Relationship mutations (pure — always return a new object)
// ---------------------------------------------------------------------------

/**
 * 델타 적용 후 새 Relationship 반환 (원본 불변).
 * friendship 클램프 [-100, 100], romance 클램프 [0, 100].
 * 알 수 없는 키는 무시.
 */
export function applyDeltas(
  rel: Relationship,
  deltas: Record<string, number>,
): Relationship {
  const next = { ...rel };
  for (const [key, delta] of Object.entries(deltas)) {
    if (key === "friendship") {
      next.friendship = clamp(next.friendship + delta, -100, 100);
    } else if (key === "romance") {
      next.romance = clamp(next.romance + delta, 0, 100);
    }
    // unknown keys: ignore
  }
  return next;
}

/**
 * 자연 감소 적용 후 새 Relationship 반환 (원본 불변).
 * friendship>0 → max(0, f-0.75); friendship<0 → min(0, f+0.75)
 * romance>0 → max(0, r-0.5)
 */
export function applyNaturalDecay(
  rel: Relationship,
  decayFriendship = 0.75,
  decayRomance = 0.5,
): Relationship {
  const next = { ...rel };
  if (next.friendship > 0) {
    next.friendship = Math.max(0, next.friendship - decayFriendship);
  } else if (next.friendship < 0) {
    next.friendship = Math.min(0, next.friendship + decayFriendship);
  }
  if (next.romance > 0) {
    next.romance = Math.max(0, next.romance - decayRomance);
  }
  return next;
}
