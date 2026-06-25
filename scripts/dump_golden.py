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


def dump_character_accessors() -> None:
    from tomodachai.character import Character, Profile, Personality, Customizable, SpeechHabits

    def case(label, char):
        return {"input": label, "expected": {
            "name": char.name,
            "personality_code": char.personality_code,
            "speech_habits": char.speech_habits,
            "backstory": char.backstory,
        }}

    cases = []
    # 1: 일부 speech_habits 채움(빈값 포함 → as_dict 필터 검증), 명확한 성격
    c1 = Character(
        id=1,
        profile=Profile(name="민수", personality=Personality(movement=8, speech=8, expressiveness=7, attitude=5, overall=5)),
        customizable=Customizable(speech_habits=SpeechHabits(normal="~이에요", happy="신나요", angry="", sad="", worried="걱정돼요")),
    )
    cases.append(case("filled_partial", c1))
    # 2: speech_habits 전부 빈값 → {} 기대, 다른 성격 사분면
    c2 = Character(
        id=2,
        profile=Profile(name="지은", personality=Personality(movement=2, speech=2, expressiveness=8, attitude=8, overall=5)),
        customizable=Customizable(speech_habits=SpeechHabits()),
    )
    cases.append(case("empty_habits", c2))
    # 3: 또 다른 사분면
    c3 = Character(
        id=3,
        profile=Profile(name="현우", personality=Personality(movement=5, speech=5, expressiveness=2, attitude=2, overall=5)),
        customizable=Customizable(speech_habits=SpeechHabits(happy="기뻐요", normal="안녕하세요")),
    )
    cases.append(case("two_habits", c3))

    _write("character_accessors", cases)


def dump_personality_types() -> None:
    from tomodachai.personality import load_personalities
    types = {code: pt.model_dump() for code, pt in load_personalities().items()}
    _write("personality_types", [{"input": "load", "expected": types}])


def dump_conversation_prompt() -> None:
    from tomodachai.character import (
        Character, Profile, Personality, Customizable, SpeechHabits,
    )
    from tomodachai.conversation import build_conversation_prompt
    from tomodachai.memory import SocialEvent
    from tomodachai.personality import load_personalities
    from tomodachai.relationship import Relationship, RelationshipStage

    personalities = load_personalities()

    def make_char(cid, name, personality, habits):
        return Character(
            id=cid,
            profile=Profile(name=name, personality=Personality(**personality)),
            customizable=Customizable(speech_habits=SpeechHabits(**habits)),
        )

    # ── Case 1: 기억 있음 (None 필드 일부 포함), 양쪽 말버릇 채움 ──────────
    p1 = {"movement": 8, "speech": 8, "expressiveness": 7, "attitude": 5, "overall": 5}
    p2 = {"movement": 2, "speech": 2, "expressiveness": 8, "attitude": 8, "overall": 5}
    char_a1 = make_char(1, "민수", p1, {"normal": "~이에요", "happy": "신나요", "worried": "걱정돼요"})
    char_b1 = make_char(2, "지은", p2, {"normal": "~랍니다"})
    code_a1 = char_a1.personality_code
    code_b1 = char_b1.personality_code
    rel_ab1 = Relationship(friendship=65.0, romance=10.0, stage=RelationshipStage.FRIEND)
    rel_ba1 = Relationship(friendship=30.0, romance=0.0, stage=RelationshipStage.ACQUAINTANCE)
    mems1 = [
        SocialEvent(id=1, type="conversation", participants=[1, 2], day=3,
                    location="공원", reason=None, result="더 친해짐"),
        SocialEvent(id=2, type="fight", participants=[1, 2], day=5,
                    location=None, reason="오해", result=None),
        SocialEvent(id=3, type="unknown_type", participants=[1, 2], day=7),
    ]
    prompt1 = build_conversation_prompt(
        char_a=char_a1, char_b=char_b1,
        personality_a=personalities[code_a1], personality_b=personalities[code_b1],
        rel_ab=rel_ab1, rel_ba=rel_ba1, memories=mems1,
        location="카페", time_of_day="아침",
    )

    # ── Case 2: 기억 없음, char_b 말버릇 비움(→ "없음") ──────────────────
    p3 = {"movement": 5, "speech": 5, "expressiveness": 2, "attitude": 2, "overall": 5}
    p4 = {"movement": 9, "speech": 9, "expressiveness": 9, "attitude": 9, "overall": 5}
    char_a2 = make_char(3, "현우", p3, {"normal": "안녕하세요", "happy": "기뻐요"})
    char_b2 = make_char(4, "수진", p4, {})
    code_a2 = char_a2.personality_code
    code_b2 = char_b2.personality_code
    rel_ab2 = Relationship(friendship=-60.0, romance=0.0, stage=RelationshipStage.STRANGER)
    rel_ba2 = Relationship(friendship=85.0, romance=70.0, stage=RelationshipStage.LOVER)
    prompt2 = build_conversation_prompt(
        char_a=char_a2, char_b=char_b2,
        personality_a=personalities[code_a2], personality_b=personalities[code_b2],
        rel_ab=rel_ab2, rel_ba=rel_ba2, memories=[],
        location="해변", time_of_day="오후",
    )

    cases = [
        {
            "input": {
                "char_a": {"id": 1, "name": "민수", "personality": p1,
                           "speech_habits": {"normal": "~이에요", "happy": "신나요", "worried": "걱정돼요"}},
                "char_b": {"id": 2, "name": "지은", "personality": p2,
                           "speech_habits": {"normal": "~랍니다"}},
                "code_a": code_a1, "code_b": code_b1,
                "rel_ab": {"friendship": 65.0, "romance": 10.0, "stage": "friend"},
                "rel_ba": {"friendship": 30.0, "romance": 0.0, "stage": "acquaintance"},
                "memories": [m.model_dump() for m in mems1],
                "location": "카페", "time_of_day": "아침",
            },
            "expected": prompt1,
        },
        {
            "input": {
                "char_a": {"id": 3, "name": "현우", "personality": p3,
                           "speech_habits": {"normal": "안녕하세요", "happy": "기뻐요"}},
                "char_b": {"id": 4, "name": "수진", "personality": p4,
                           "speech_habits": {}},
                "code_a": code_a2, "code_b": code_b2,
                "rel_ab": {"friendship": -60.0, "romance": 0.0, "stage": "stranger"},
                "rel_ba": {"friendship": 85.0, "romance": 70.0, "stage": "lover"},
                "memories": [],
                "location": "해변", "time_of_day": "오후",
            },
            "expected": prompt2,
        },
    ]
    _write("conversation_prompt", cases)


def dump_donation() -> None:
    from tomodachai.fountain import FountainManager

    class _GameState:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def add_money(self, n: int) -> None:
            self.calls.append(n)

        @property
        def total(self) -> int:
            return sum(self.calls)

    def result_dict(res):
        if res is None:
            return None
        return {
            "day": res.day,
            "characterCount": res.character_count,
            "amount": res.amount,
        }

    cases: list[dict] = []

    # (a) fresh manager, day=1, count=3 → amount 300, money 300.
    #     has_donated 전이: 호출 전 False, 호출 후 True.
    mgr = FountainManager()
    gs = _GameState()
    before = mgr.has_donated(1)
    res_a = mgr.run_donation(1, 3, gs)
    after = mgr.has_donated(1)
    cases.append({
        "input": {"day": 1, "characterCount": 3},
        "expected": {
            "result": result_dict(res_a),
            "money_added": gs.total,
            "hasDonatedBefore": before,
            "hasDonatedAfter": after,
        },
    })

    # (b) SAME manager, day=1 again → None, no second add_money call.
    res_b = mgr.run_donation(1, 3, gs)
    cases.append({
        "input": {"day": 1, "characterCount": 3, "reuse": "a"},
        "expected": {
            "result": result_dict(res_b),
            "money_added": gs.total,
        },
    })

    # (c) fresh manager, count=0 → amount 0, add_money NOT called.
    mgr_c = FountainManager()
    gs_c = _GameState()
    res_c = mgr_c.run_donation(1, 0, gs_c)
    cases.append({
        "input": {"day": 1, "characterCount": 0},
        "expected": {
            "result": result_dict(res_c),
            "money_added": gs_c.total,
            "add_money_calls": len(gs_c.calls),
        },
    })

    # (d) fresh manager, count=-5 → max(0,-5)*100 = 0, add_money NOT called.
    mgr_d = FountainManager()
    gs_d = _GameState()
    res_d = mgr_d.run_donation(1, -5, gs_d)
    cases.append({
        "input": {"day": 1, "characterCount": -5},
        "expected": {
            "result": result_dict(res_d),
            "money_added": gs_d.total,
            "add_money_calls": len(gs_d.calls),
        },
    })

    _write("donation", cases)


def dump_event_summary() -> None:
    from tomodachai.character import Character, Profile
    from tomodachai.memory import SocialEvent
    from tomodachai.news import _build_event_summary

    def make_char(cid: int, name: str) -> Character:
        return Character(id=cid, profile=Profile(name=name))

    chars = [make_char(1, "민수"), make_char(2, "지은")]

    cases: list[dict] = []

    # ── _build_event_summary 케이스 (실제 오라클 호출) ──────────────────────
    # (a) participants 2명 + location/reason/result 전부.
    ev_full = SocialEvent(
        id=1, type="marriage", participants=[1, 2], day=3,
        location="공원", reason="사랑", result="결혼 성공",
    )
    cases.append({
        "input": {
            "kind": "summary",
            "event": ev_full.model_dump(),
            "characters": [{"id": 1, "name": "민수"}, {"id": 2, "name": "지은"}],
        },
        "expected": {"summary": _build_event_summary(ev_full, chars)},
    })

    # (b) participants 1명, type만 (location/reason/result 없음).
    ev_solo = SocialEvent(id=2, type="conversation", participants=[1], day=4)
    cases.append({
        "input": {
            "kind": "summary",
            "event": ev_solo.model_dump(),
            "characters": [{"id": 1, "name": "민수"}, {"id": 2, "name": "지은"}],
        },
        "expected": {"summary": _build_event_summary(ev_solo, chars)},
    })

    # (c) participant id가 characters에 없음 → str(id) 폴백.
    ev_unknown = SocialEvent(id=3, type="fight", participants=[1, 99], day=5,
                             reason="오해")
    cases.append({
        "input": {
            "kind": "summary",
            "event": ev_unknown.model_dump(),
            "characters": [{"id": 1, "name": "민수"}, {"id": 2, "name": "지은"}],
        },
        "expected": {"summary": _build_event_summary(ev_unknown, chars)},
    })

    # (d) participants 빈 리스트 → "주민".
    ev_empty = SocialEvent(id=4, type="donation", participants=[], day=6,
                           result="100원 기부")
    cases.append({
        "input": {
            "kind": "summary",
            "event": ev_empty.model_dump(),
            "characters": [{"id": 1, "name": "민수"}, {"id": 2, "name": "지은"}],
        },
        "expected": {"summary": _build_event_summary(ev_empty, chars)},
    })

    # ── 우선순위 선택 케이스 ────────────────────────────────────────────────
    # _PRIORITY는 generate_real_news 내부 지역변수라 임포트 불가.
    # news.py(39-50)의 점수 맵을 그대로 미러하여 max(events, key=score) 복제.
    # (Python max는 동점 시 첫 항목을 유지 — 안정적.)
    _PRIORITY = {
        "marriage": 10, "breakup": 9, "confession": 8, "fight": 7,
        "reconciliation": 6, "birthday": 5, "travel": 4, "nickname": 3,
        "donation": 2, "conversation": 1,
    }

    def score(e: SocialEvent) -> int:
        return _PRIORITY.get(e.type, 0)

    # (e) 혼합 타입 — marriage가 최고점.
    sel_mixed = [
        SocialEvent(id=10, type="conversation", participants=[1, 2], day=7),
        SocialEvent(id=11, type="marriage", participants=[1, 2], day=7),
        SocialEvent(id=12, type="fight", participants=[1, 2], day=7),
    ]
    hi_mixed = max(sel_mixed, key=score)
    cases.append({
        "input": {
            "kind": "selection",
            "events": [e.model_dump() for e in sel_mixed],
            "characters": [{"id": 1, "name": "민수"}, {"id": 2, "name": "지은"}],
        },
        "expected": {
            "highlight_index": sel_mixed.index(hi_mixed),
            "highlight_type": hi_mixed.type,
            "summary": _build_event_summary(hi_mixed, chars),
        },
    })

    # (f) 동점(fight 둘) — 첫 항목 유지.
    sel_tie = [
        SocialEvent(id=20, type="fight", participants=[1], day=8, reason="첫번째"),
        SocialEvent(id=21, type="travel", participants=[2], day=8),
        SocialEvent(id=22, type="fight", participants=[2], day=8, reason="두번째"),
    ]
    hi_tie = max(sel_tie, key=score)
    cases.append({
        "input": {
            "kind": "selection",
            "events": [e.model_dump() for e in sel_tie],
            "characters": [{"id": 1, "name": "민수"}, {"id": 2, "name": "지은"}],
        },
        "expected": {
            "highlight_index": sel_tie.index(hi_tie),
            "highlight_type": hi_tie.type,
            "summary": _build_event_summary(hi_tie, chars),
        },
    })

    _write("event_summary", cases)


def dump_config() -> None:
    """AppConfig 기본값 — 클라이언트 makeDefaultConfig()와 1:1.

    클라엔 YAML/env 없음 → load_config의 병합부는 범위 밖. 기본값만 검증.
    """
    from tomodachai.config import AppConfig

    _write("config_defaults", [{"input": "AppConfig", "expected": AppConfig().model_dump()}])


def dump_game_state() -> None:
    """GameState 기본값(config 무관 부분) — 클라이언트 GameState 기본 상태와 1:1.

    island_name/day_count/money/time_flip/ending_credit_seen/catalog/카테고리는
    config.yaml과 무관(생성자 기본값). config(locations/llm)는 config_defaults 골든이 담당.
    """
    from tomodachai.game_state import GameState

    gs = GameState()
    _write(
        "game_state_defaults",
        [
            {
                "input": "GameState()",
                "expected": {
                    "island_name": gs.island_name,
                    "day_count": gs.day_count,
                    "money": gs.money,
                    "time_flip": gs.time_flip,
                    "ending_credit_seen": gs.ending_credit_seen,
                    "catalog": gs.catalog,
                    "catalog_categories_sorted": sorted(GameState._CATALOG_CATEGORIES),
                },
            }
        ],
    )


def _sample_character():
    """직렬화/라운드트립 골든용 샘플 캐릭터 (모든 섹션 비기본값).

    TS 테스트는 이 동일 캐릭터를 defaultCharacter + 명시적 override로 재구성한다.
    슬라이더(8/8/7/5)는 personality_code 계산을 위해 고정.
    """
    from tomodachai.character import (
        Appearance, AppearanceAdjust, Body, Character, CharacterState,
        ClothingPreference, Customizable, Eye, Eyebrow, Hair, InteriorPreference,
        MiniTrait, MiniTraits, Mood, Mouth, Nose, Personality, PersonalityGroup,
        Preferences, Profile, Records, SpeechHabits, Voice,
    )

    return Character(
        id=7,
        profile=Profile(
            name="민지",
            birthday="07-15",
            blood_type="A",
            favorite_color="#FF8800",
            gender="여",
            appearance=Appearance(
                face_shape=3,
                skin_color="#F5D6B8",
                eye=Eye(base=2, lash=1, color="#3A2A1A",
                        adjust=AppearanceAdjust(spacing=1, height=-2, size=3, angle=-1)),
                eyebrow=Eyebrow(id=4, adjust=AppearanceAdjust(spacing=0, height=1, size=-1, angle=2)),
                nose=Nose(id=2, adjust=AppearanceAdjust(spacing=0, height=2, size=-1, angle=0)),
                mouth=Mouth(id=5, adjust=AppearanceAdjust(spacing=0, height=-1, size=1, angle=0)),
                hair=Hair(front=3, back=2, color="#5B3A1A"),
                glasses=2,
                body=Body(height=6, build=4),
            ),
            personality=Personality(movement=8, speech=8, expressiveness=7, attitude=5, overall=6),
            voice=Voice(preset="bright", pitch=7, speed=4, quality="clear",
                        tone="warm", accent=None, intonation="rising"),
        ),
        preferences=Preferences(
            food_ranks=[3, 1, 2],
            food_eaten=[True, False, True],
            clothing=ClothingPreference(likes="원피스", dislikes="정장"),
            interior=InteriorPreference(likes="식물", dislikes="금속"),
            personality_group=PersonalityGroup(group="활발", is_positive=True),
        ),
        state=CharacterState(
            satisfaction=72,
            level=3,
            hunger=20,
            mood=Mood(happiness=7, energy=6, stress=3),
            sick="감기",
            current_location="cafe",
            current_outfit=11,
            current_interior=22,
            photo_frame=5,
        ),
        customizable=Customizable(
            speech_habits=SpeechHabits(normal="~지", happy="개좋아", angry="아오", sad="흑", worried="음..."),
            mini_traits=MiniTraits(
                walking=MiniTrait(owned=[1, 2], active=1),
                eating=MiniTrait(owned=[3], active=None),
                idle=MiniTrait(owned=[], active=None),
            ),
            nicknames={"2": "민지짱"},
            songs=[True, False, True, False, False, False, False, False],
        ),
        records=Records(
            treasure_collection=[1, 5, 9],
            confession_count={"2": 1},
            photos=[10, 20],
        ),
    )


def dump_save_character() -> None:
    """_serialize_character 골든 — TS serializeCharacter와 1:1.

    라운드트립(deserialize∘serialize)은 TS 단위테스트가 담당(순수 TS 불변식).
    """
    from tomodachai.save import _serialize_character

    char = _sample_character()
    _write("save_character", [{"input": "sample", "expected": _serialize_character(char)}])


def dump_save_relationships() -> None:
    """_serialize_relationships 골든 — TS serializeRelationships와 1:1.

    내부 저장(_relationships/_slots/_ex_lover_tags/_fights)을 직접 구성.
    싸움 하나는 resolved=True로 둬서 '전체 읽기'(getFights 미해결-only와 구분)를 검증.
    """
    from tomodachai.relationship import (
        BreakupReason, ExLoverTag, Fight, Relationship, RelationshipSlots,
        RelationshipStage, RelationshipTracker,
    )

    tr = RelationshipTracker()
    # pairs (방향 있음, "a:b" 직렬화 키)
    tr._relationships[(1, 2)] = Relationship(
        friendship=65.0, romance=40.0, stage=RelationshipStage.LOVER)
    tr._relationships[(2, 1)] = Relationship(
        friendship=60.0, romance=35.0, stage=RelationshipStage.FRIEND)
    tr._relationships[(3, 4)] = Relationship(
        friendship=-55.0, romance=0.0, stage=RelationshipStage.STRANGER)
    # slots
    tr._slots[1] = RelationshipSlots(best_friend=None, lover=2, enemy=None)
    tr._slots[3] = RelationshipSlots(best_friend=None, lover=None, enemy=4)
    # ex-lover tags
    tr._ex_lover_tags[1] = [
        ExLoverTag(target=5, reason=BreakupReason.FIGHT, day=3),
        ExLoverTag(target=6, reason=BreakupReason.BOREDOM, day=7),
    ]
    # fights — 두 번째는 resolved=True (allFightsRaw 전체 읽기 검증)
    tr._fights = [
        Fight(participants=(1, 2), cause="오해", resolved=False, witnessed_by_player=True),
        Fight(participants=(3, 4), cause="질투", resolved=True, witnessed_by_player=False),
    ]

    from tomodachai.save import _serialize_relationships
    _write("save_relationships", [{"input": "sample", "expected": _serialize_relationships(tr)}])


def dump_save_events() -> None:
    """_serialize_events 골든 — TS serializeEvents와 1:1.

    None 필드 조건부 생략(time/location/reason/result)을 케이스별로 검증.
    add_event는 id 보존(id≠0)이라 직렬화 id가 입력과 동일.
    """
    from tomodachai.memory import MemoryStore, SocialEvent
    from tomodachai.save import _serialize_events

    store = MemoryStore()
    # 전체 필드
    store.add_event(SocialEvent(
        id=1, type="marriage", participants=[1, 2], day=3,
        time="아침", location="공원", reason="사랑", result="결혼 성공"))
    # 일부 None (location/result만)
    store.add_event(SocialEvent(
        id=2, type="fight", participants=[1, 2], day=5,
        location="카페", result="화해"))
    # 전부 None (type/participants/day만)
    store.add_event(SocialEvent(id=3, type="conversation", participants=[1], day=7))

    _write("save_events", [{"input": "sample", "expected": _serialize_events(store)}])


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
    dump_character_accessors()
    dump_personality_types()
    dump_conversation_prompt()
    dump_donation()
    dump_event_summary()
    dump_config()
    dump_game_state()
    dump_save_character()
    dump_save_relationships()
    dump_save_events()


if __name__ == "__main__":
    main()
