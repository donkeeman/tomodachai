// 분수대 이벤트 시스템 — 모금 (donation) 부분.
//
// Python 정답지: src/tomodachai/fountain.py
//   - FountainManager.__init__ / has_donated / run_donation
//   - _DONATION_PER_CHARACTER = 100
//
// 모금은 하루 1회 필수. 캐릭터 수에 비례한 금액을 플레이어 자금에 추가한다.
// 랩배틀/끝말잇기(LLM seam)는 별도 태스크에서 추가한다.

// 캐릭터 1명당 모금액. 캐릭터 수에 비례.
export const DONATION_PER_CHARACTER = 100;

export interface DonationResult {
  day: number;
  characterCount: number;
  amount: number;
}

// add_money(int)를 가진 게임 상태 (Python game_state 대응).
export interface MoneyAdder {
  addMoney(n: number): void;
}

/**
 * 분수대 이벤트 상태를 관리한다 (세션 한정).
 *
 * 모금의 '하루 1회' 제약만 상태로 추적한다.
 */
export class FountainManager {
  private lastDonationDay: number | null = null;

  /** day에 이미 모금이 진행됐는지 여부. */
  hasDonated(day: number): boolean {
    return this.lastDonationDay === day;
  }

  /**
   * 하루 1회 모금을 진행한다.
   *
   * 같은 날 이미 했다면 null을 반환하고 상태를 바꾸지 않는다.
   * amount는 max(0, characterCount) * DONATION_PER_CHARACTER이며,
   * amount > 0일 때만 gameState.addMoney를 호출한다 (Python `if amount:`).
   */
  runDonation(
    day: number,
    characterCount: number,
    gameState: MoneyAdder,
  ): DonationResult | null {
    if (this.hasDonated(day)) {
      return null;
    }

    const amount = Math.max(0, characterCount) * DONATION_PER_CHARACTER;
    if (amount > 0) {
      gameState.addMoney(amount);
    }

    this.lastDonationDay = day;
    return { day, characterCount, amount };
  }
}
