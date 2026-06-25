// Python src/tomodachai/time_system.py GameClock 미러. 순수 TS, now()만 주입 가능.

// Python round()는 banker's rounding (half-to-even). JS Math.round는 half-up.
// Python 동작에 맞게 구현.
function bankersRound(x: number): number {
  const floor = Math.floor(x);
  const frac = x - floor;
  if (frac !== 0.5) return Math.round(x);
  // 정확히 .5이면 가장 가까운 짝수로
  return floor % 2 === 0 ? floor : floor + 1;
}

const DAILY_RESET_HOUR = 5;
const TIME_PERIODS: readonly [number, number, string][] = [
  [5, 12, "아침"],
  [12, 17, "낮"],
  [17, 21, "저녁"],
  [21, 24, "밤"],
  [0, 5, "밤"],
];

export const EVENT_INTERVAL_MIN_SECONDS = 10 * 60;
export const EVENT_INTERVAL_MAX_SECONDS = 30 * 60;
export const CATCHUP_MAX_EVENTS_PER_DAY = 5;
export const OFFLINE_THRESHOLD_MINUTES = 5;

export class GameClock {
  constructor(
    public timeFlip = false,
    private nowFn: () => Date = () => new Date(),
  ) {}

  now(): Date {
    return this.nowFn();
  }

  getGameHour(at?: Date, timeFlip?: boolean): number {
    const t = at ?? this.now();
    let hour = t.getUTCHours();
    const flip = timeFlip ?? this.timeFlip;
    if (flip) hour = (hour + 12) % 24;
    return hour;
  }

  getTimePeriod(at?: Date): string {
    const hour = this.getGameHour(at);
    for (const [start, end, name] of TIME_PERIODS) {
      if (start <= hour && hour < end) return name;
    }
    return "밤";
  }

  isNewDay(lastCheck: Date): boolean {
    const now = this.now();
    if (now <= lastCheck) return false;
    let reset = new Date(
      Date.UTC(
        lastCheck.getUTCFullYear(),
        lastCheck.getUTCMonth(),
        lastCheck.getUTCDate(),
        DAILY_RESET_HOUR,
        0,
        0,
        0,
      ),
    );
    if (lastCheck >= reset) reset = new Date(reset.getTime() + 86_400_000);
    return now >= reset;
  }

  catchupEventCount(offlineHours: number): number {
    if (offlineHours <= 0) return 0;
    const days = offlineHours / 24.0;
    const count = bankersRound(days * CATCHUP_MAX_EVENTS_PER_DAY);
    const maxCount = Math.max(1, Math.trunc(days + 1)) * CATCHUP_MAX_EVENTS_PER_DAY;
    return Math.max(1, Math.min(count, maxCount));
  }
}
