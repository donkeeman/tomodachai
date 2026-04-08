"""Real-time game clock and time utilities.

Pure Python, no async — fully testable standalone.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DAILY_RESET_HOUR = 5  # 새벽 5시 기준으로 하루 리셋

_TIME_PERIODS: list[tuple[int, int, str]] = [
    # (시작 시, 끝 시, 이름)  — 끝 시는 exclusive
    (5, 12, "아침"),
    (12, 17, "낮"),
    (17, 21, "저녁"),
    (21, 24, "밤"),
    (0, 5, "밤"),  # 자정~새벽 5시도 밤
]

# 이벤트 랜덤 간격 (초 단위)
EVENT_INTERVAL_MIN_SECONDS = 10 * 60  # 10분
EVENT_INTERVAL_MAX_SECONDS = 30 * 60  # 30분

# 오프라인 catch-up 하루 이벤트 상한
CATCHUP_MAX_EVENTS_PER_DAY = 5

# 오프라인으로 간주하는 최소 시간 (분)
OFFLINE_THRESHOLD_MINUTES = 5


# ---------------------------------------------------------------------------
# GameClock
# ---------------------------------------------------------------------------


class GameClock:
    """현실 시간 기반 게임 클럭.

    실시간 1일 = 게임 1일. 새벽 5시 리셋.
    """

    def __init__(self, time_flip: bool = False) -> None:
        self.time_flip = time_flip

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------

    def now(self) -> datetime:
        """현재 UTC 시각."""
        return datetime.now(tz=timezone.utc)

    def get_game_hour(self, at: datetime | None = None, time_flip: bool | None = None) -> int:
        """0~23 사이의 게임 내 현재 시(hour).

        time_flip=True이면 12시간 반전. 밤에 플레이하는 유저 배려.
        """
        t = at or self.now()
        hour = t.hour
        flip = self.time_flip if time_flip is None else time_flip
        if flip:
            hour = (hour + 12) % 24
        return hour

    def get_time_period(self, at: datetime | None = None) -> str:
        """현재 시각 기반 시간대 반환: '아침'/'낮'/'저녁'/'밤'."""
        hour = self.get_game_hour(at)
        for start, end, name in _TIME_PERIODS:
            if start <= hour < end:
                return name
        # fallback — shouldn't happen but satisfies linter
        return "밤"

    def is_new_day(self, last_check: datetime) -> bool:
        """last_check 이후 새벽 5시 경계를 넘었으면 True.

        둘 다 UTC 기준으로 비교한다.
        """
        now = self.now()
        if now <= last_check:
            return False

        # last_check 날짜의 "오늘 리셋 시각" 계산
        reset_today = last_check.replace(
            hour=_DAILY_RESET_HOUR,
            minute=0,
            second=0,
            microsecond=0,
        )
        # last_check이 이미 리셋 이후면 다음날 리셋을 봐야 함
        if last_check >= reset_today:
            reset_today += timedelta(days=1)

        return now >= reset_today

    def calculate_offline_duration(self, last_online: datetime) -> timedelta:
        """last_online 이후 경과 시간 반환."""
        return self.now() - last_online

    def is_offline(self, last_online: datetime) -> bool:
        """OFFLINE_THRESHOLD_MINUTES 이상 접속 안 했으면 True."""
        elapsed = self.calculate_offline_duration(last_online)
        return elapsed.total_seconds() >= OFFLINE_THRESHOLD_MINUTES * 60

    def catchup_event_count(self, offline_hours: float) -> int:
        """오프라인 시간으로부터 생성할 catch-up 이벤트 수 계산.

        하루(24h) = 최대 CATCHUP_MAX_EVENTS_PER_DAY건. 비례 산출, 최소 1건.
        """
        if offline_hours <= 0:
            return 0
        days = offline_hours / 24.0
        count = round(days * CATCHUP_MAX_EVENTS_PER_DAY)
        # 최소 1, 최대 = 일수 × 상한
        max_count = max(1, int(days + 1)) * CATCHUP_MAX_EVENTS_PER_DAY
        return max(1, min(count, max_count))


# ---------------------------------------------------------------------------
# Module-level singleton (서버에서 편하게 import해서 쓸 수 있도록)
# ---------------------------------------------------------------------------

_default_clock: GameClock | None = None


def get_clock(time_flip: bool = False) -> GameClock:
    """글로벌 GameClock 인스턴스 반환 (필요 시 생성)."""
    global _default_clock
    if _default_clock is None:
        _default_clock = GameClock(time_flip=time_flip)
    return _default_clock


def reset_clock(time_flip: bool = False) -> GameClock:
    """테스트용: 새 인스턴스로 교체."""
    global _default_clock
    _default_clock = GameClock(time_flip=time_flip)
    return _default_clock
