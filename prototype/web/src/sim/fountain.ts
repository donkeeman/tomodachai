// 분수대 이벤트 시스템 — 모금 (donation) 부분.
//
// Python 정답지: src/tomodachai/fountain.py
//   - FountainManager.__init__ / has_donated / run_donation
//   - _DONATION_PER_CHARACTER = 100
//
// 모금은 하루 1회 필수. 캐릭터 수에 비례한 금액을 플레이어 자금에 추가한다.
// 랩배틀/끝말잇기는 LLM seam — LLM 호출은 비결정적이나 후처리는 결정론.

import type { Character } from "./character";
import type { LlmClient, Msg } from "../llm";
import { characterName, characterPersonalityCode } from "./characterAccessors";

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

// ---------------------------------------------------------------------------
// 랩배틀 / 끝말잇기 result models (Python fountain.py 36-57 미러)
// ---------------------------------------------------------------------------

export interface RapVerse {
  name: string;
  line: string;
}

export interface RapBattleResult {
  participants: string[];
  verses: RapVerse[];
  winner: string;
}

export interface WordChainRound {
  name: string;
  word: string;
}

export interface WordChainResult {
  participants: string[];
  rounds: WordChainRound[];
  eliminated: string | null;
  winner: string;
}

/** Python str(x) 동등. undefined/null → "". */
function toStr(x: unknown): string {
  return String(x ?? "");
}

/** 객체(배열/null 제외) 여부 — Python isinstance(x, dict) 동등. */
function isObject(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
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

  // ------------------------------------------------------------------
  // 랩배틀 (rap battle) — Python generate_rap_battle 110-147 미러.
  // LLM seam: 호출은 비결정적, 후처리는 결정론.
  // ------------------------------------------------------------------

  async generateRapBattle(
    charA: Character,
    charB: Character,
    llm: LlmClient,
  ): Promise<RapBattleResult> {
    const names = [characterName(charA), characterName(charB)];
    const messages: Msg[] = [
      {
        role: "system",
        content:
          "당신은 마을 분수대 랩배틀의 진행자 겸 라임 작가입니다. " +
          "두 캐릭터가 번갈아 가며 서로를 디스하는 랩 가사를 씁니다. " +
          "디스는 과격하지 않고 유쾌한 병맛 톤으로, 각 캐릭터의 성격을 반영하세요. " +
          "총 4줄(각자 2줄씩) 정도, 마지막에 승자를 한 명 정하세요. " +
          "JSON 형식으로 반환: " +
          '{"verses": [{"name": "...", "line": "..."}], "winner": "..."}',
      },
      {
        role: "user",
        content:
          `'${characterName(charA)}'(${characterPersonalityCode(charA)})와(과) ` +
          `'${characterName(charB)}'(${characterPersonalityCode(charB)})의 랩배틀을 만들어주세요. ` +
          "번갈아 가며 디스하는 라임으로요. 승자도 정해주세요.",
      },
    ];

    const raw = await llm.chatJson(messages, { maxTokens: 512 });

    const rawVerses = raw.verses;
    const verses: RapVerse[] = (Array.isArray(rawVerses) ? rawVerses : [])
      .filter(isObject)
      .map((v) => ({ name: toStr(v.name), line: toStr(v.line) }));

    const rawWinner = raw.winner;
    const winner =
      typeof rawWinner === "string" && names.includes(rawWinner)
        ? rawWinner
        : names[0];

    return { participants: names, verses, winner };
  }

  // ------------------------------------------------------------------
  // 끝말잇기 (word chain) — Python generate_word_chain 153-210 미러.
  // ------------------------------------------------------------------

  async generateWordChain(
    characters: Character[],
    itemPool: string[],
    llm: LlmClient,
  ): Promise<WordChainResult> {
    if (characters.length < 2) {
      throw new Error("끝말잇기는 최소 2명이 필요합니다.");
    }
    if (itemPool.length === 0) {
      throw new Error("끝말잇기 아이템 풀이 비어 있습니다.");
    }

    const names = characters.map(characterName);
    const messages: Msg[] = [
      {
        role: "system",
        content:
          "당신은 마을 분수대 끝말잇기 게임의 진행자입니다. " +
          "캐릭터들이 번갈아 주어진 단어 풀에서 끝말잇기 규칙에 맞는 단어를 고릅니다. " +
          "이어갈 단어를 못 찾는 캐릭터가 탈락하고, 마지막에 남은 캐릭터가 승자입니다. " +
          "JSON 형식으로 반환: " +
          '{"rounds": [{"name": "...", "word": "..."}], ' +
          '"eliminated": "...", "winner": "..."}',
      },
      {
        role: "user",
        content:
          `참가자: ${names.join(", ")}\n` +
          `사용 가능한 단어 풀: ${itemPool.join(", ")}\n\n` +
          "끝말잇기 게임을 진행해주세요. 풀 안의 단어만 사용하세요.",
      },
    ];

    const raw = await llm.chatJson(messages, { maxTokens: 512 });

    const rawRounds = raw.rounds;
    const rounds: WordChainRound[] = (Array.isArray(rawRounds) ? rawRounds : [])
      .filter(isObject)
      .map((r) => ({ name: toStr(r.name), word: toStr(r.word) }));

    const rawWinner = raw.winner;
    const winner =
      typeof rawWinner === "string" && names.includes(rawWinner)
        ? rawWinner
        : names[0];

    let eliminated: string | null = (raw.eliminated as string | null | undefined) ?? null;
    if (eliminated !== null && !names.includes(eliminated)) {
      eliminated = null;
    }

    return { participants: names, rounds, eliminated, winner };
  }
}
