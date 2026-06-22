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


def dump_zodiac() -> None:
    from tomodachai.character import calculate_zodiac

    # 12 별자리 각 경계 양끝 + 무효 입력
    inputs = [
        "03-21", "04-19", "04-20", "05-20", "05-21", "06-20",
        "06-21", "07-22", "07-23", "08-22", "08-23", "09-22",
        "09-23", "10-22", "10-23", "11-21", "11-22", "12-21",
        "12-22", "01-19", "01-20", "02-18", "02-19", "03-20",
        "", "bad", "13-99",
    ]
    cases = [{"input": b, "expected": calculate_zodiac(b)} for b in inputs]
    _write("zodiac", cases)


def dump_character_defaults() -> None:
    from tomodachai.character import (
        Appearance, Mood, CharacterState, Preferences, Customizable, Records, Voice,
        Character, Profile,
    )

    # 각 서브모델의 기본 인스턴스를 JSON 직렬화 → TS 기본값이 일치해야 함
    cases = [
        {"input": "Appearance", "expected": Appearance().model_dump()},
        {"input": "Voice", "expected": Voice().model_dump()},
        {"input": "Mood", "expected": Mood().model_dump()},
        {"input": "CharacterState", "expected": CharacterState().model_dump()},
        {"input": "Preferences", "expected": Preferences().model_dump()},
        {"input": "Customizable", "expected": Customizable().model_dump()},
        {"input": "Records", "expected": Records().model_dump()},
        {"input": "Character", "expected": Character(id=1, profile=Profile(name="테스트")).model_dump()},
    ]
    _write("character_defaults", cases)


def dump_personality() -> None:
    from tomodachai.character import Personality
    from tomodachai.personality import PersonalitySliders, determine_personality

    # determine_personality: 16코드 전부 커버하도록 4분면×4분면 격자
    vals = [0.1, 0.4, 0.6, 0.9]  # 각 임계 구간(<0.25,<0.5,<0.75,<1.01)을 대표
    det_cases = []
    for ms in vals:          # movement=speech=ms → ms_avg=ms
        for ea in vals:      # expr=attitude=ea → ea_avg=ea
            s = PersonalitySliders(movement=ms, speech=ms, expressiveness=ea, attitude=ea)
            det_cases.append({
                "input": {"movement": ms, "speech": ms, "expressiveness": ea, "attitude": ea},
                "expected": determine_personality(s),
            })
    _write("determine_personality", det_cases)

    # personalityCode: Personality(0~10 int) → 코드
    code_inputs = [
        {"movement": 8, "speech": 8, "expressiveness": 7, "attitude": 5, "overall": 5},
        {"movement": 2, "speech": 2, "expressiveness": 8, "attitude": 8, "overall": 5},
        {"movement": 5, "speech": 5, "expressiveness": 5, "attitude": 5, "overall": 5},
        {"movement": 0, "speech": 0, "expressiveness": 0, "attitude": 0, "overall": 0},
        {"movement": 10, "speech": 10, "expressiveness": 10, "attitude": 10, "overall": 10},
    ]
    code_cases = []
    for pi in code_inputs:
        p = Personality(**pi)
        sliders = PersonalitySliders(
            movement=p.movement / 10.0, speech=p.speech / 10.0,
            expressiveness=p.expressiveness / 10.0, attitude=p.attitude / 10.0,
        )
        code_cases.append({"input": pi, "expected": determine_personality(sliders)})
    _write("personality_code", code_cases)


def dump_relationship_core() -> None:
    from tomodachai.relationship import (
        Relationship, RelationshipStage, check_breakup_conditions,
    )

    # friendshipStage / status / friendship_text / romance_text — friendship/romance 격자
    f_vals = [-100, -70, -69, -50, -49, -20, -19, 0, 10, 20, 39, 40, 59, 60, 79, 80, 100]
    r_vals = [-5, 0, 1, 20, 21, 49, 50, 79, 80, 100]
    label_cases = []
    for f in f_vals:
        rel = Relationship(friendship=f, romance=0)
        label_cases.append({
            "input": {"friendship": f},
            "expected": {
                "stage": rel._friendship_stage().value,
                "friendship_text": rel.get_friendship_text(),
            },
        })
    romance_cases = [
        {"input": {"romance": r}, "expected": {"romance_text": Relationship(romance=r).get_romance_text()}}
        for r in r_vals
    ]
    status_cases = [
        {"input": {"stage": s.value}, "expected": Relationship(stage=s).get_status_text()}
        for s in RelationshipStage
    ]
    _write("rel_friendship_labels", label_cases)
    _write("rel_romance_text", romance_cases)
    _write("rel_status_text", status_cases)

    # computeStage — (f, r, stage, allowRomantic) 매트릭스
    stages = [s.value for s in RelationshipStage]
    cs_cases = []
    for stage in stages:
        for r in [0, 55, 60, 89, 90, 100]:
            for allow in (False, True):
                rel = Relationship(friendship=50, romance=r, stage=stage)
                cs_cases.append({
                    "input": {"friendship": 50, "romance": r, "stage": stage, "allow": allow},
                    "expected": rel._compute_stage(allow_romantic_transition=allow).value,
                })
    _write("rel_compute_stage", cs_cases)

    # checkBreakupConditions
    bc_cases = []
    for stage in stages:
        for r in [10, 19, 20, 30]:
            for cheat in (False, True):
                for tri in (False, True):
                    for fu in (False, True):
                        res = check_breakup_conditions(
                            Relationship(romance=r, stage=stage), cheat, tri, fu,
                        )
                        bc_cases.append({
                            "input": {"stage": stage, "romance": r, "cheating": cheat,
                                      "triangle": tri, "fightUnresolved": fu},
                            "expected": res.value if res is not None else None,
                        })
    _write("rel_breakup", bc_cases)

    # applyDeltas / applyNaturalDecay
    delta_cases = []
    for f, r, d in [(50, 50, {"friendship": 60}), (50, 50, {"romance": -70}),
                    (-90, 10, {"friendship": -30}), (50, 50, {"unknown": 5})]:
        rel = Relationship(friendship=f, romance=r)
        rel.apply_deltas(d)
        delta_cases.append({"input": {"friendship": f, "romance": r, "deltas": d},
                            "expected": {"friendship": rel.friendship, "romance": rel.romance}})
    decay_cases = []
    for f, r in [(10, 5), (-10, 0), (0.5, 0.4), (0, 0), (-0.5, 0)]:
        rel = Relationship(friendship=f, romance=r)
        rel.apply_natural_decay()
        decay_cases.append({"input": {"friendship": f, "romance": r},
                            "expected": {"friendship": rel.friendship, "romance": rel.romance}})
    _write("rel_apply_deltas", delta_cases)
    _write("rel_decay", decay_cases)


def dump_compatibility() -> None:
    from tomodachai.relationship import _personality_group, calculate_compatibility

    codes = ["easygoing_softie", "outgoing_charmer", "confident_busybee",
             "independent_thinker", "weird_unknown"]
    group_cases = [{"input": c, "expected": _personality_group(c)} for c in codes]
    _write("personality_group", group_cases)

    # 대표 매트릭스 (성격쌍×혈액쌍×별자리쌍 일부 + null/미인식)
    samples = [
        ("easygoing_softie", "outgoing_charmer", "O", "A", "양자리", "천칭자리"),
        ("confident_busybee", "independent_thinker", "AB", "AB", "황소자리", "게자리"),
        ("easygoing_softie", "easygoing_optimist", "A", "B", "양자리", "양자리"),
        ("outgoing_charmer", "independent_thinker", "B", "B", "사자자리", "물병자리"),
        ("weird_x", "outgoing_charmer", "X", "A", "??", "양자리"),
    ]
    comp_cases = [
        {"input": {"pA": a, "pB": b, "bloodA": ba, "bloodB": bb, "zA": za, "zB": zb},
         "expected": calculate_compatibility(a, b, ba, bb, za, zb)}
        for (a, b, ba, bb, za, zb) in samples
    ]
    _write("calculate_compatibility", comp_cases)


def dump_location_catalog() -> None:
    from tomodachai.location import DEFAULT_LOCATIONS, _DEFAULT_PUBLIC_WEIGHTS

    locs = [loc.model_dump() for loc in DEFAULT_LOCATIONS]
    # location_type은 str Enum이므로 model_dump()가 .value(str)로 직렬화함
    _write("location_catalog", [{"input": "DEFAULT_LOCATIONS", "expected": locs}])
    _write("location_weights", [{"input": "weights", "expected": dict(_DEFAULT_PUBLIC_WEIGHTS)}])


def dump_destination_weights() -> None:
    import random
    from tomodachai.character import Character, Profile
    from tomodachai.location import LocationManager
    from tomodachai.relationship import RelationshipTracker

    class _Recorder(random.Random):
        def __init__(self, rand_value: float = 0.99) -> None:
            super().__init__()
            self.captured: dict | None = None
            self._rv = rand_value
        def random(self) -> float:
            return self._rv
        def choices(self, population, weights=None, *, cum_weights=None, k=1):
            self.captured = dict(zip(population, weights))
            return [population[0]]

    def make_char(cid: int, hunger: float = 0.0, satisfaction: float = 50.0, stress: int = 2) -> Character:
        c = Character(id=cid, profile=Profile(name=f"c{cid}"))
        c.state.hunger = hunger
        c.state.satisfaction = satisfaction
        c.state.mood.stress = stress
        return c

    cases: list[dict] = []

    mgr = LocationManager(); rec = _Recorder()
    mgr.choose_destination(make_char(1), None, time_of_day="낮", rng=rec)
    cases.append({"input": "baseline", "expected": rec.captured})

    mgr = LocationManager(); rec = _Recorder()
    mgr.choose_destination(make_char(1, hunger=80.0), None, "낮", rng=rec)
    cases.append({"input": "hungry", "expected": rec.captured})

    mgr = LocationManager(); rec = _Recorder()
    mgr.choose_destination(make_char(1, satisfaction=10.0), None, "낮", rng=rec)
    cases.append({"input": "unsatisfied", "expected": rec.captured})

    mgr = LocationManager(); rec = _Recorder()
    mgr.choose_destination(make_char(1, stress=9), None, "낮", rng=rec)
    cases.append({"input": "stressed", "expected": rec.captured})

    mgr = LocationManager(); rec = _Recorder()
    mgr.move_character(2, "park")
    tr = RelationshipTracker(); tr.update(1, 2, {"friendship": 65.0})
    mgr.choose_destination(make_char(1), tr, "낮", rng=rec)
    cases.append({"input": "follow_friend", "expected": rec.captured})

    mgr = LocationManager(); rec = _Recorder()
    mgr.move_character(10, "news_station"); mgr.move_character(11, "news_station")  # cap=2 full
    mgr.choose_destination(make_char(1), None, "낮", rng=rec)
    cases.append({"input": "capacity", "expected": rec.captured})

    mgr = LocationManager(); rec = _Recorder()
    mgr.move_character(2, "beach")
    for cid in (20, 21, 22, 23):  # grocery cap=4 full
        mgr.move_character(cid, "grocery")
    tr = RelationshipTracker(); tr.update(1, 2, {"friendship": 70.0})
    mgr.choose_destination(make_char(1, hunger=80.0, satisfaction=10.0, stress=9), tr, "낮", rng=rec)
    cases.append({"input": "combined", "expected": rec.captured})

    _write("destination_weights", cases)


def dump_shop() -> None:
    from tomodachai.shop import (
        CATEGORIES, HOLIDAYS, _DEFAULT_POOL, _DAILY_COUNT,
        _MORNING_MARKET_DISCOUNT_RATE, _MORNING_MARKET_BASE_PRICE, ShopManager,
    )
    pool_bounds = {c: [min(r), max(r), len(r)] for c, r in _DEFAULT_POOL.items()}

    sm = ShopManager()
    sm.add_to_catalog("food", 5)
    sm.add_to_catalog("food", 1)
    sm.add_to_catalog("clothing", 150)
    serialized = sm.serialize()

    sample_state = {
        "daily": {"food": [1, 2, 3], "clothing": [101, 102], "interior": [201]},
        "morning_market": {"item": 7, "discount_price": 1500},
        "seasonal": [301, 302],
        "catalog": {"food": [1, 5], "clothing": [150], "interior": []},
    }
    sm2 = ShopManager()
    sm2.deserialize(sample_state)
    roundtrip = sm2.serialize()

    cases = [
        {"input": "categories", "expected": list(CATEGORIES)},
        {"input": "holidays", "expected": dict(HOLIDAYS)},
        {"input": "daily_count", "expected": dict(_DAILY_COUNT)},
        {"input": "pool_bounds", "expected": pool_bounds},
        {"input": "discount_price", "expected": int(_MORNING_MARKET_BASE_PRICE * _MORNING_MARKET_DISCOUNT_RATE)},
        {"input": "discount_rate", "expected": _MORNING_MARKET_DISCOUNT_RATE},
        {"input": "base_price", "expected": _MORNING_MARKET_BASE_PRICE},
        {"input": "catalog_food_sorted", "expected": sm.get_catalog("food")},
        {"input": "serialize_after_adds", "expected": serialized},
        {"input": "deserialize_roundtrip", "expected": roundtrip},
    ]
    _write("shop_constants", cases)


def dump_personality_types() -> None:
    from tomodachai.personality import load_personalities
    types = {code: pt.model_dump() for code, pt in load_personalities().items()}
    _write("personality_types", [{"input": "load", "expected": types}])


def main() -> None:
    dump_parse_json()
    dump_game_clock()
    dump_zodiac()
    dump_character_defaults()
    dump_personality()
    dump_relationship_core()
    dump_compatibility()
    dump_location_catalog()
    dump_destination_weights()
    dump_shop()
    dump_personality_types()


if __name__ == "__main__":
    main()
