/**
 * memory.ts
 * Python memory.py (SocialEvent + MemoryStore) 포팅.
 * 오라클: src/tomodachai/memory.py
 */

// ---------------------------------------------------------------------------
// SocialEvent
// ---------------------------------------------------------------------------

export interface SocialEvent {
  id: number;
  type: string;
  participants: number[];
  day: number;
  time: string | null;
  location: string | null;
  reason: string | null;
  result: string | null;
}

/**
 * SocialEvent 기본값 팩토리.
 * time / location / reason / result 기본값 null.
 * Python pydantic BaseModel 기본값 동작과 동일.
 */
export function defaultSocialEvent(partial: Partial<SocialEvent> & Pick<SocialEvent, "id" | "type" | "participants" | "day">): SocialEvent {
  return {
    time: null,
    location: null,
    reason: null,
    result: null,
    ...partial,
  };
}

// ---------------------------------------------------------------------------
// MemoryStore
// ---------------------------------------------------------------------------

export class MemoryStore {
  private _events: SocialEvent[] = [];
  private _nextId: number = 1;

  /**
   * 이벤트 추가.
   * - e.id === 0 이면 _nextId를 부여한 복사본으로 교체.
   * - _nextId = max(_nextId, e.id) + 1 갱신.
   * Python model_copy(update={...})와 동일하게 불변 복사본 저장.
   */
  addEvent(e: SocialEvent): void {
    let stored: SocialEvent;
    if (e.id === 0) {
      stored = { ...e, id: this._nextId };
    } else {
      stored = { ...e };
    }
    this._nextId = Math.max(this._nextId, stored.id) + 1;
    this._events.push(stored);
  }

  /**
   * charId가 participants에 포함된 이벤트 반환.
   * day 내림차순 정렬 (stable), 최대 limit개.
   */
  getEventsFor(charId: number, limit: number = 10): SocialEvent[] {
    const relevant = this._events.filter(e => e.participants.includes(charId));
    // stable sort: 삽입 순서 보존 (V8/Node 22 Array.prototype.sort is stable)
    relevant.sort((a, b) => b.day - a.day);
    return relevant.slice(0, limit);
  }

  /**
   * charA와 charB 모두 participants에 포함된 이벤트 반환.
   * day 내림차순 정렬 (stable), 최대 limit개.
   */
  getEventsBetween(charA: number, charB: number, limit: number = 5): SocialEvent[] {
    const relevant = this._events.filter(
      e => e.participants.includes(charA) && e.participants.includes(charB)
    );
    relevant.sort((a, b) => b.day - a.day);
    return relevant.slice(0, limit);
  }
}
