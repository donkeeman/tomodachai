"""Python 정답지(src/tomodachai)를 결정론 입력으로 호출해 골든 JSON을 덤프한다.

규칙 변경 시 재실행: python scripts/dump_golden.py
산출물은 prototype/web/src/sim/__golden__/*.json (커밋 대상).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# src 레이아웃 임포트 보장
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

GOLDEN_DIR = ROOT / "prototype" / "web" / "src" / "sim" / "__golden__"


def _write(name: str, cases: list[dict]) -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    path = GOLDEN_DIR / f"{name}.json"
    path.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(cases)} cases)")


def dump_parse_json() -> None:
    from tomodachai.llm import LLMClient

    inputs = [
        '{"a": 1}',
        '```json\n{"b": 2}\n```',
        '```\n{"c": 3}\n```',
        '설명입니다 {"d": 4} 끝',
        '앞 {"e": {"f": 5}} 뒤',
    ]
    throwing = ["", "no json here"]

    cases: list[dict] = []
    for text in inputs:
        cases.append({"input": text, "expected": LLMClient._parse_json(text)})
    for text in throwing:
        try:
            LLMClient._parse_json(text)
        except (ValueError, json.JSONDecodeError):
            cases.append({"input": text, "throws": True})
        else:
            raise AssertionError(f"expected _parse_json to raise for {text!r}")
    _write("parse_json", cases)


def dump_game_clock() -> None:
    from datetime import datetime, timezone
    from tomodachai.time_system import GameClock

    clock = GameClock()

    def iso(y, mo, d, h, mi=0):
        return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)

    # getGameHour / getTimePeriod — (iso, flip) → {hour, period}
    period_inputs = [
        (iso(2026, 6, 19, 7), False),
        (iso(2026, 6, 19, 13), False),
        (iso(2026, 6, 19, 19), False),
        (iso(2026, 6, 19, 22), False),
        (iso(2026, 6, 19, 2), False),
        (iso(2026, 6, 19, 7), True),   # flip → 19시
        (iso(2026, 6, 19, 23), True),  # flip → 11시
    ]
    period_cases = [
        {
            "input": {"at": t.isoformat(), "flip": flip},
            "expected": {
                "hour": clock.get_game_hour(t, time_flip=flip),
                "period": clock.get_time_period(t) if not flip else None,
            },
        }
        for t, flip in period_inputs
    ]
    _write("game_clock_period", period_cases)

    # isNewDay — (lastCheck, now) → bool. now를 주입하기 위해 monkeypatch.
    new_day_inputs = [
        (iso(2026, 6, 19, 3), iso(2026, 6, 19, 6)),   # 같은날 5시 경계 넘음 → True
        (iso(2026, 6, 19, 6), iso(2026, 6, 19, 9)),   # 둘 다 리셋 이후, 다음날 안 넘음 → False
        (iso(2026, 6, 19, 6), iso(2026, 6, 20, 6)),   # 다음날 5시 도달 → True
        (iso(2026, 6, 19, 10), iso(2026, 6, 19, 9)),  # now < lastCheck → False
    ]
    nd_cases = []
    for last, now in new_day_inputs:
        # GameClock.is_new_day는 self.now()를 쓰므로, now를 주입한 임시 서브클래스로 평가
        fixed = type("Fixed", (GameClock,), {"now": lambda self, _n=now: _n})()
        nd_cases.append(
            {"input": {"lastCheck": last.isoformat(), "now": now.isoformat()},
             "expected": fixed.is_new_day(last)}
        )
    _write("game_clock_newday", nd_cases)

    # catchupEventCount — offline_hours → int (0.5 경계 회피)
    catchup_inputs = [0, 0.4, 6, 12, 24, 48, 100]
    cc_cases = [
        {"input": h, "expected": clock.catchup_event_count(h)} for h in catchup_inputs
    ]
    _write("game_clock_catchup", cc_cases)


def main() -> None:
    dump_parse_json()
    dump_game_clock()


if __name__ == "__main__":
    main()
