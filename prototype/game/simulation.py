# 시뮬레이션 엔진 (04-ai-system.md)
# 핵심 원칙: 숫자 테이블이 확률/조건 기반으로 이벤트를 트리거하고,
# 선정된 캐릭터의 대사 생성에만 LLM을 호출 (이벤트당 1회 수준)
from __future__ import annotations

from typing import List, Optional, Tuple

from .llm import LLMError, LLMProvider
from . import prompts, relationship
from .models import Bubble, Character, GameState

# 장소 목록 (03-space-and-events.md에서 프로토타입 범위만)
LOCATIONS = {
    "living_room": ("공동주택 거실", 4),
    "balcony": ("공동주택 발코니", 2),
    "fountain": ("분수대", 4),
    "park": ("공원", 4),
    "cafe": ("카페", 2),
    "beach": ("해변", 2),
}

TICK_MINUTES = 30          # 1틱 = 게임 내 30분 (기획은 실시간이지만 터미널용으로 턴제 변형)
DAY_START = 5 * 60         # 하루 리셋 새벽 5시
SLEEP_HOUR = 23            # 23시 이후는 취침 → 다음날로 넘어감
EVENT_CHANCE = 0.45        # 틱당 이벤트 발생 확률

# 반함 트리거 (02 문서): romance는 반함 전까지 누적되지 않음. 잠정값, 실험으로 조정
# 너무 자주 뜨면 이벤트감이 죽으므로 하루 최대 1건(마을 전체) 캡과 병행
SPARK_TALK_CHANCE = 0.08     # 경로 1: 대화 시 반함 후보 플래그 확률 (궁합 가중)
SPARK_RANDOM_CHANCE = 0.012  # 경로 2: 틱당 뜬금 반함 확률 (마을 전체, 원작 랜덤 이벤트 오마주)

# 질투 (02 문서 11절): A→target 연심 + target은 남의 연인일 때 파생 판정
JEALOUSY_ROMANCE_MIN = 25   # 이 정도는 마음이 자라야 질투가 남
JEALOUSY_CHANCE = 0.35      # 이벤트 슬롯에서 후보가 있을 때 발동 확률 (하루 1건 캡)

# 관계 기반 동선 (03 문서 3절): 시간표 없이 조건 기반 확률 이동
MOVE_CHANCE = 0.10          # 틱당 캐릭터별 자발 이동 확률

# 뜬금 반함의 엉뚱한 이유 풀
SPARK_REASONS = [
    "재채기하는 모습이 귀여워서",
    "비둘기를 진지하게 쫓는 모습을 봐서",
    "바람에 머리카락이 휘날리는 걸 봐서",
    "혼자 흥얼거리는 노래를 들어버려서",
    "떨어뜨린 빵을 줍는 손이 어쩐지 멋있어서",
    "분수대 물을 신기하게 바라보는 옆모습 때문에",
    "구름을 보며 감탄하는 모습이 어딘가 반짝여 보여서",
    "넘어질 뻔하다가 아무렇지 않은 척하는 게 귀여워서",
]


class TickResult:
    # 한 틱 동안 일어난 일 (CLI 출력용)
    def __init__(self):
        self.messages: List[str] = []   # 시스템 알림
        self.dialogue: List[Tuple[str, str]] = []  # (화자, 대사)
        self.scene: str = ""            # 장면 제목
        self.major: bool = False        # 큰 이벤트 (자동 진행 일시정지 대상)

    def say(self, speaker: str, text: str) -> None:
        self.dialogue.append((speaker, text))

    def note(self, msg: str) -> None:
        self.messages.append(msg)


class Simulation:
    def __init__(self, state: GameState, llm: LLMProvider):
        self.state = state
        self.llm = llm

    # ---------- 메인 틱 ----------

    def tick(self, tick_minutes: float = TICK_MINUTES) -> TickResult:
        # tick_minutes: 이 틱이 게임 내 몇 분인지. 리얼타임 모드는 1~5분 단위로 잘게 들어옴.
        # 확률/수치 잠정값은 모두 30분 틱 기준이므로 scale로 환산
        state = self.state
        result = TickResult()
        scale = tick_minutes / TICK_MINUTES
        state.minutes = int(state.minutes + tick_minutes)

        # 하루 리셋 (턴제 모드: 취침 시간 도달 시 다음날 아침으로 점프)
        if state.minutes >= SLEEP_HOUR * 60:
            self._day_reset(result)
            return result

        self._update_needs(result, scale)
        self._social_movement(scale)

        # 뜬금 반함 체크 (경로 2: 원작의 '길에서 부딪혀 반함'을 마주침 대화로 연출)
        # 발생 시 이 틱의 이벤트를 대신함
        if self._maybe_spark_encounter(result, scale):
            return result

        # 이벤트 발생 체크 (확률 트리거)
        if state.rng.random() < min(1.0, EVENT_CHANCE * scale):
            self._fire_event(result)

        return result

    def _day_reset(self, result: TickResult) -> None:
        # 턴제(터미널/터보) 모드 전용: 하루 전환 + 아침 7시로 시계 점프
        self.day_rollover(result)
        self.state.minutes = DAY_START + 120  # 기상 7시

    def day_rollover(self, result: TickResult) -> None:
        # 하루 전환 공통 처리 (리얼타임 모드는 새벽 5시에 시계 점프 없이 이것만 호출)
        state = self.state
        state.day += 1
        relationship.daily_decay(state)
        # 아나운서 랜덤 선정 (하루 고정)
        state.announcer = state.rng.choice(list(state.characters.keys()))
        # 수면으로 컨디션 일부 회복
        for char in state.characters.values():
            char.hunger = min(100.0, char.hunger + 10)  # 자는 동안 배고파짐
            char.mood.adjust(energy=2, stress=-1)
            char.location = state.rng.choice(list(LOCATIONS.keys()))
        result.note(f"☀️ Day {state.day} 아침이 밝았습니다. "
                    f"(오늘의 아나운서: {state.characters[state.announcer].name})"
                    f" — `news` 명령으로 어제 소식을 들을 수 있습니다.")

    def _update_needs(self, result: TickResult, scale: float = 1.0) -> None:
        state = self.state
        for char in state.characters.values():
            char.hunger = min(100.0, char.hunger + 1.5 * scale)
            char.mood.converge(0.15 * scale)
            if char.hunger >= 100:
                # 도트 데미지 (알림은 반복 출력 대신 아래 말풍선 1개로)
                char.satisfaction -= 1 * scale
                char.mood.adjust(happiness=-0.3 * scale, energy=-0.3 * scale,
                                 stress=0.4 * scale)
            if char.hunger >= 80 and not any(
                    b.kind == "hungry" and b.char_id == char.id for b in state.bubbles):
                # 배고픔은 다른 이벤트처럼 말풍선 1개로 (밥을 주면 사라짐)
                state.bubbles.append(Bubble(
                    kind="hungry", char_id=char.id,
                    text=f"{char.name}: \"배고파요...\""))
                result.note(f"🍚 {char.name}의 말풍선이 떴습니다: \"배고파요...\"")

    # ---------- 이벤트 선정 ----------

    def _fire_event(self, result: TickResult) -> None:
        state = self.state
        # 우선순위: 고백 트리거 > 질투 > 싸움 > 일상 대화 (숫자 테이블 기반 선정)
        if self._maybe_confession_bubble(result):
            return
        if self._maybe_jealousy(result):
            return
        if self._maybe_fight(result):
            return
        self._conversation(result)

    # ---------- 관계 기반 동선 (03 문서 3절) ----------

    def _social_movement(self, scale: float = 1.0) -> None:
        # 시간표 없이 조건 기반 확률 이동: 관계가 동선을 만든다.
        # 알림 없이 조용히 움직임 — 맵/화면에서 관찰하는 재미 요소
        state = self.state
        for char in state.characters.values():
            if state.rng.random() >= MOVE_CHANCE * scale:
                continue
            if char.hunger >= 70:
                char.location = "living_room"  # 배고프면 집(거실)으로
                continue
            moved = False
            for slot in ("lover", "best_friend"):
                other_id = char.slots[slot]
                if other_id is None:
                    continue
                other = state.characters[other_id]
                if other.location != char.location and state.rng.random() < 0.6:
                    char.location = other.location  # 보고 싶은 사람 곁으로
                    moved = True
                    break
            if not moved:
                # 특별한 일 없으면 그냥 마실
                char.location = state.rng.choice(list(LOCATIONS.keys()))

    # ---------- 질투 (02 문서 11절) ----------

    def _jealousy_candidates(self):
        # (질투하는 사람, 좋아하는 상대, 연적) 목록.
        # 파생 판정: A→target romance가 자랐는데 target은 이미 남의 연인
        state = self.state
        out = []
        for a in state.characters.values():
            for t_id, rel in a.relationships.items():
                if rel.romance < JEALOUSY_ROMANCE_MIN:
                    continue
                target = state.characters[t_id]
                rival_id = target.slots["lover"]
                if rival_id is None or rival_id == a.id:
                    continue
                out.append((a, target, state.characters[rival_id]))
        return out

    def _jealousy_allowed_today(self) -> bool:
        # 질투 장면도 하루 1건 캡 (매일 보면 피곤한 드라마)
        for e in reversed(self.state.events):
            if e.day < self.state.day:
                break
            if e.type == "jealousy":
                return False
        return True

    def _maybe_jealousy(self, result: TickResult) -> bool:
        state = self.state
        if not self._jealousy_allowed_today():
            return False
        candidates = self._jealousy_candidates()
        if not candidates:
            return False
        if state.rng.random() > JEALOUSY_CHANCE:
            return False
        a, target, rival = state.rng.choice(candidates)

        # 연출 분기: 연적에게 괜한 신경전 vs 친구에게 하소연
        mode = "confront" if state.rng.random() < 0.45 else "vent"
        other = rival
        if mode == "vent":
            friends = sorted(
                ((rel.friendship, oid) for oid, rel in a.relationships.items()
                 if oid not in (target.id, rival.id) and rel.friendship >= 10),
                reverse=True)
            if friends:
                other = state.characters[friends[0][1]]
            else:
                mode = "confront"  # 하소연할 친구가 없으면 신경전으로

        loc_name = self._move_pair(a, other)
        prompt = prompts.jealousy_prompt(state, a, other, target, rival, loc_name, mode)
        data = self._call(prompt, "conversation", result)

        icon = "😤" if mode == "confront" else "😮‍💨"
        label = "괜한 신경전" if mode == "confront" else "속앓이 하소연"
        if data is not None:
            result.scene = f"{icon} [{loc_name}] {a.name} ✕ {other.name} — {label}"
            for line in data.get("lines", [])[:5]:
                result.say(line.get("speaker", "?"), line.get("text", ""))

        # 수치 변동: 신경전은 관계 깎임, 하소연은 친구와 가까워지고 스트레스 해소
        rng = state.rng
        if mode == "confront":
            a.rel(other.id).add(friendship=-rng.uniform(4, 8))
            other.rel(a.id).add(friendship=-rng.uniform(2, 5))
            a.mood.adjust(stress=1.5, happiness=-0.5)
            other.mood.adjust(stress=1)
            fallback = f"{a.name}이(가) 질투심에 {other.name}에게 괜히 날카롭게 굴음"
        else:
            a.rel(other.id).add(friendship=rng.uniform(1, 2.5))
            other.rel(a.id).add(friendship=rng.uniform(0.5, 1.5))
            a.mood.adjust(stress=-1, happiness=-0.3)
            fallback = (f"{a.name}이(가) {other.name}에게 {target.name}·{rival.name} "
                        f"커플 때문에 속앓이를 털어놓음")

        summary = (data or {}).get("summary", fallback)
        state.add_event(type="jealousy", participants=[a.id, other.id],
                        location=a.location, reason=target.name, summary=summary)
        result.note(f"{icon} {a.name}이(가) {target.name}을(를) 향한 마음에 질투를 느끼고 있습니다...")
        for notice in relationship.update_slots(state, a, other):
            result.note(notice)
        return True

    def _pick_pair(self) -> Optional[Tuple[Character, Character]]:
        # 대화 상대 랜덤 선정. 친구/베프/연인은 같은 장소에 자주 배치되는 효과를
        # "만남 가중치"로 단순화 (동선 시스템의 텍스트 버전)
        state = self.state
        chars = list(state.characters.values())
        if len(chars) < 2:
            return None
        a = state.rng.choice(chars)
        weights = []
        for b in chars:
            if b.id == a.id:
                weights.append(0.0)
                continue
            # 주의: a.rel()은 엔트리를 생성하므로 여기서는 get으로만 조회 (첫 만남 판정 보존)
            w = 1.0
            rel = a.relationships.get(b.id)
            if a.slots["best_friend"] == b.id or a.slots["lover"] == b.id:
                w = 3.0
            elif rel is not None and rel.friendship >= 30:
                w = 2.0
            elif a.slots["enemy"] == b.id:
                w = 0.5
            weights.append(w)
        b = state.rng.choices(chars, weights=weights, k=1)[0]
        return a, b

    def _move_pair(self, a: Character, b: Character) -> str:
        # 두 사람을 수용 인원이 남는 장소로 이동
        state = self.state
        occupancy = {}
        for c in state.characters.values():
            occupancy[c.location] = occupancy.get(c.location, 0) + 1
        candidates = [key for key, (_, cap) in LOCATIONS.items()
                      if occupancy.get(key, 0) + 2 <= cap or key in (a.location, b.location)]
        loc = state.rng.choice(candidates) if candidates else "living_room"
        a.location = loc
        b.location = loc
        return LOCATIONS[loc][0]

    # ---------- 일상 대화 ----------

    def _conversation(self, result: TickResult) -> None:
        state = self.state
        pair = self._pick_pair()
        if not pair:
            return
        a, b = pair
        loc_name = self._move_pair(a, b)
        first_meet = not a.has_met(b.id)

        # 반함 후보 플래그 (경로 1: 숫자 테이블이 게이트 → 반할지 말지는 LLM이 맥락 판단)
        spark_candidate = None
        if self._spark_allowed_today():
            directions = [(a, b), (b, a)]
            state.rng.shuffle(directions)
            for x, y in directions:
                if not self._spark_eligible(x, y):
                    continue
                chance = SPARK_TALK_CHANCE * relationship.affinity(x, y)
                if x.slots["lover"] is not None:
                    chance *= 0.25  # 연인이 있으면 한눈팔 확률 급감 (삼각관계는 드물게만)
                if self._has_active_crush(x):
                    chance *= 0.2  # 이미 다른 사람을 마음에 둔 상태면 새로 잘 안 반함
                if state.rng.random() < chance:
                    spark_candidate = (x, y)
                    break

        # 매 대화마다 주제 풀에서 랜덤 힌트 주입 (밥 이야기 편중 방지)
        topic = state.rng.choice(prompts.TOPICS)
        prompt = prompts.conversation_prompt(state, a, b, loc_name,
                                             private=(a.location == "balcony"),
                                             topic=topic,
                                             spark_candidate=spark_candidate)
        data = self._call(prompt, "conversation", result)
        if data is None:
            return

        result.scene = f"🗨  [{loc_name}] {a.name} ✕ {b.name}"
        for line in data.get("lines", [])[:6]:
            result.say(line.get("speaker", "?"), line.get("text", ""))

        relationship.conversation_delta(state, a, b)
        summary = data.get("summary", f"{a.name}와(과) {b.name}이(가) 대화함")
        state.add_event(type="conversation", participants=[a.id, b.id],
                        location=a.location, summary=summary)
        if first_meet:
            result.note(f"✨ {a.name}와(과) {b.name}이(가) 처음 인사를 나눴습니다. (모르는 사이 → 지인)")
        if spark_candidate and data.get("spark") in (True, "true", "yes"):
            x, y = spark_candidate
            # 계기는 방금 그 대화에서 나옴 — LLM이 짚어준 순간을 그대로 기록
            spark_reason = str(data.get("spark_reason") or "").strip()
            # 대화가 끝난 뒤 혼자 곱씹는 감상평 (말풍선 속 마음의 소리)
            monologue = str(data.get("spark_monologue") or "").strip()
            if monologue:
                result.say(f"💭 {x.name}", monologue)
            result.note(relationship.do_spark(state, x, y, spark_reason))
        slot_notices = relationship.update_slots(state, a, b)
        for notice in slot_notices:
            result.note(notice)
        if slot_notices:
            result.major = True  # 베프/원수 성립 등은 큰 이벤트

    # ---------- 반함 (romance 누적 시작 트리거) ----------

    def _spark_eligible(self, a: Character, b: Character) -> bool:
        # a가 b에게 반할 수 있는 상태인가 (MVP: 연애는 남녀 간만)
        if a.gender == b.gender:
            return False
        rel = a.relationships.get(b.id)
        if rel is not None and rel.spark:
            return False  # 이미 반해 있음
        if a.confession_count.get(b.id, 0) >= 3:
            return False  # 3회 거절로 단념한 상대에게는 바로 다시 반하지 않음
        return True

    def _spark_allowed_today(self) -> bool:
        # 반함은 하루 최대 1건 (마을 전체). 매일 떠야 할 이벤트가 아니라 가끔의 사건이어야 함
        for e in reversed(self.state.events):
            if e.day < self.state.day:
                break
            if e.type == "spark":
                return False
        return True

    def _has_active_crush(self, a: Character) -> bool:
        # 연인이 아닌 누군가에게 이미 반해 있는가 (동시 다발 반함은 드물게만)
        return any(rel.spark and a.slots["lover"] != other_id
                   for other_id, rel in a.relationships.items())

    def _maybe_spark_encounter(self, result: TickResult, scale: float = 1.0) -> bool:
        # 경로 2: 우연한 마주침에서 뜬금없이 반함.
        # 원작의 '길가다 부딪혀 반함'에 해당 — 우리 게임에서 그 '부딪힘'은 대화 이벤트.
        # 반함 여부는 시스템이 이미 확정하고, LLM은 마주침 장면 연출만 담당
        state = self.state
        if state.rng.random() >= SPARK_RANDOM_CHANCE * scale:
            return False
        if not self._spark_allowed_today():
            return False
        outdoor = [c for c in state.characters.values()
                   if c.location in ("fountain", "park", "beach", "balcony")]
        if not outdoor:
            return False
        a = state.rng.choice(outdoor)
        if a.slots["lover"] is not None and state.rng.random() < 0.75:
            return False  # 연인이 있으면 대부분 마음이 흔들리지 않음
        if self._has_active_crush(a) and state.rng.random() < 0.8:
            return False  # 이미 다른 사람을 마음에 둔 상태면 새로 잘 안 반함
        targets = [c for c in state.characters.values()
                   if c.id != a.id and self._spark_eligible(a, c)]
        if not targets:
            return False
        # 만난 적 있는 상대 우선, 없으면 첫 만남에 첫눈에 반할 수도 있음
        met = [c for c in targets if a.has_met(c.id)]
        b = state.rng.choice(met or targets)
        first_meet = not a.has_met(b.id)

        loc_name = self._move_pair(a, b)
        reason = state.rng.choice(SPARK_REASONS)
        prompt = prompts.spark_encounter_prompt(state, a, b, loc_name, reason)
        data = self._call(prompt, "conversation", result)
        if data is not None:
            result.scene = f"💫 [{loc_name}] {a.name} ✕ {b.name} — 우연한 마주침!"
            for line in data.get("lines", [])[:5]:
                result.say(line.get("speaker", "?"), line.get("text", ""))
            monologue = str(data.get("spark_monologue") or "").strip()
            if monologue:
                result.say(f"💭 {a.name}", monologue)
        # LLM 실패 시에도 반함 자체는 성립 (장면 없이 알림만)
        if first_meet:
            result.note(f"✨ {a.name}와(과) {b.name}이(가) 처음 인사를 나눴습니다. (모르는 사이 → 지인)")
        result.note(relationship.do_spark(state, a, b, reason))
        relationship.conversation_delta(state, a, b)
        for notice in relationship.update_slots(state, a, b):
            result.note(notice)
        return True

    # ---------- 도구 아이템 (05 문서: 카메라 / 프라이팬) ----------

    def use_tool(self, char: Character, tool: str) -> TickResult:
        state = self.state
        result = TickResult()
        if tool == "camera":
            # 피사체: 같은 장소의 주민 또는 풍경 중 랜덤
            mates = [c for c in state.characters.values()
                     if c.id != char.id and c.location == char.location]
            loc_name = LOCATIONS[char.location][0]
            if mates and state.rng.random() < 0.5:
                m = state.rng.choice(mates)
                subject = f"{loc_name}에 있는 주민 {m.name}의 자연스러운 한 컷"
                subj_label = m.name
            else:
                subject = f"{loc_name}의 풍경"
                subj_label = loc_name
            data = self._call(prompts.photo_prompt(state, char, subject), "photo", result)
            title = (data or {}).get("title", f"무제 ({subj_label})")
            caption = str((data or {}).get("caption", "")).strip()
            state.photos.append({"day": state.day, "time": state.clock(),
                                 "author": char.name, "title": title,
                                 "subject": subj_label})
            char.mood.adjust(happiness=1)
            state.add_event(type="photo", participants=[char.id], location=char.location,
                            summary=f"{char.name}이(가) 사진 '{title}'을(를) 촬영")
            result.scene = f"📸 [{loc_name}] {char.name}의 촬영 시간!"
            if caption:
                result.say(char.name, caption)
            result.note(f"🖼 사진 '{title}' 갤러리에 저장 (작가: {char.name})")
            return result

        if tool == "frying_pan":
            data = self._call(prompts.cook_prompt(state, char), "cook", result)
            dish = (data or {}).get("dish", "정체불명 볶음")
            comment = str((data or {}).get("comment", "")).strip()
            char.hunger = max(0.0, char.hunger - 40)
            char.mood.adjust(happiness=1, energy=0.5)
            # 직접 만든 요리로 배고픔 말풍선도 해소
            state.bubbles = [b for b in state.bubbles
                             if not (b.kind == "hungry" and b.char_id == char.id)]
            state.dishes.append({"day": state.day, "author": char.name, "dish": dish})
            state.add_event(type="cooking", participants=[char.id], location=char.location,
                            summary=f"{char.name}이(가) 요리 '{dish}'을(를) 만듦")
            result.scene = f"🍳 {char.name}의 즉흥 요리!"
            if comment:
                result.say(char.name, comment)
            result.note(f"📒 요리 '{dish}' 카탈로그에 추가")
            return result

        result.note("❓ 알 수 없는 도구입니다. (카메라 / 프라이팬)")
        return result

    # ---------- 싸움 ----------

    def _maybe_fight(self, result: TickResult) -> bool:
        state = self.state
        # friendship 마이너스 구간 쌍에서 확률적 발생. 원수는 확률 높음, 베프는 매우 낮음
        candidates = []
        chars = list(state.characters.values())
        for a in chars:
            for b in chars:
                if a.id >= b.id or not a.has_met(b.id):
                    continue
                f_ab, f_ba = relationship.mutual(a, b, "friendship")
                if a.slots["enemy"] == b.id:
                    chance = 0.30
                elif f_ab < 0 or f_ba < 0:
                    chance = 0.15
                elif a.slots["best_friend"] == b.id:
                    chance = 0.01
                else:
                    continue
                candidates.append((a, b, chance))
        if not candidates:
            return False
        a, b, chance = state.rng.choice(candidates)
        if state.rng.random() > chance:
            return False

        loc_name = self._move_pair(a, b)
        prompt = prompts.fight_prompt(state, a, b, loc_name)
        data = self._call(prompt, "fight", result)
        if data is None:
            return False

        result.scene = f"💢 [{loc_name}] {a.name} ✕ {b.name} — 싸움이 벌어졌습니다!"
        result.major = True
        for line in data.get("lines", [])[:5]:
            result.say(line.get("speaker", "?"), line.get("text", ""))

        # 수치 변동표: 싸움 friendship -15~20 양쪽
        rng = state.rng
        a.rel(b.id).add(friendship=-rng.uniform(15, 20))
        b.rel(a.id).add(friendship=-rng.uniform(15, 20))
        for c in (a, b):
            c.mood.adjust(happiness=-1.5, stress=2)
        summary = data.get("summary", f"{a.name}와(과) {b.name}이(가) 싸움")
        state.add_event(type="fight", participants=[a.id, b.id],
                        location=a.location, summary=summary)
        for notice in relationship.update_slots(state, a, b):
            result.note(notice)
        # 연인이면 이별 조건 체크 (양방향 friendship ≤ -20)
        self._check_breakup(a, b, result, after_fight=True)
        return True

    def _check_breakup(self, a: Character, b: Character, result: TickResult,
                       after_fight: bool = False) -> None:
        state = self.state
        if a.slots["lover"] != b.id:
            return
        f_ab, f_ba = relationship.mutual(a, b, "friendship")
        if f_ab <= -20 and f_ba <= -20:
            reason = relationship.decide_breakup_reason(state, a, b, after_fight, False)
            result.note(relationship.do_breakup(state, a, b, reason))
            result.major = True

    # ---------- 고백 ----------

    def _maybe_confession_bubble(self, result: TickResult) -> bool:
        state = self.state
        # 트리거: A→B romance ≥ 50 AND A→B friendship ≥ 20 (A 기준만)
        # 조건 충족 시 "고백하고 싶어요" 말풍선 → 플레이어 허락 후 LLM 판정
        if any(bub.kind == "confess_request" for bub in state.bubbles):
            return False  # 대기 중 말풍선이 있으면 중복 발생 안 함
        candidates = []
        for a in state.characters.values():
            for b_id, rel in a.relationships.items():
                b = state.characters[b_id]
                if a.slots["lover"] == b_id:
                    continue  # 이미 연인
                if a.confession_count.get(b_id, 0) >= 3:
                    continue  # 3회 거절 후 단념
                if rel.romance >= 50 and rel.friendship >= 20:
                    candidates.append((a, b))
        if not candidates:
            return False
        if state.rng.random() > 0.5:
            return False
        a, b = state.rng.choice(candidates)
        retry = a.confession_count.get(b.id, 0)
        suffix = " (재도전이에요...)" if retry else ""
        state.bubbles.append(Bubble(
            kind="confess_request", char_id=a.id, target_id=b.id,
            text=f"{a.name}: \"{b.name}에게 고백하고 싶어요...{suffix} 해도 될까요?\"",
        ))
        result.note(f"💗 말풍선 도착! {a.name}이(가) 할 말이 있다고 합니다. (`bubbles` 로 확인)")
        return True

    def resolve_confession(self, bubble: Bubble, approved: bool) -> TickResult:
        # 플레이어가 "해!" / "하지 마" 선택한 뒤의 처리
        state = self.state
        result = TickResult()
        a = state.characters[bubble.char_id]
        b = state.characters[bubble.target_id]

        if not approved:
            # 플레이어가 말리면 즉시 단념 처리
            a.confession_count[b.id] = 3
            a.rel(b.id).add(romance=-state.rng.uniform(40, 50))
            a.mood.adjust(happiness=-1, stress=1)
            result.note(f"💧 {a.name}이(가) 마음을 접기로 했습니다... \"이제 포기할게요...\"")
            state.add_event(type="confession_giveup", participants=[a.id, b.id],
                            summary=f"{a.name}이(가) {b.name}에 대한 마음을 접음 (플레이어 만류)")
            return result

        # 발코니/해변 같은 감성 장소에서 고백
        loc = state.rng.choice(["balcony", "beach", "fountain"])
        a.location = loc
        b.location = loc
        loc_name = LOCATIONS[loc][0]
        retry = a.confession_count.get(b.id, 0)

        prompt = prompts.confession_prompt(state, a, b, loc_name, retry)
        data = self._call(prompt, "confession", result)
        if data is None:
            return result

        result.scene = f"💘 [{loc_name}] {a.name}의 고백!"
        for line in data.get("lines", [])[:6]:
            result.say(line.get("speaker", "?"), line.get("text", ""))

        accepted = data.get("decision") == "accept"
        reason = data.get("reason", "")
        rng = state.rng
        summary = data.get("summary", "")

        if accepted:
            # 기존 연인이 있으면 바람 이별 (경로 2: 고백 수락)
            if b.slots["lover"] is not None and b.slots["lover"] != a.id:
                old = state.characters[b.slots["lover"]]
                result.note(relationship.do_breakup(state, b, old, "cheating"))
            if a.slots["lover"] is not None and a.slots["lover"] != b.id:
                old = state.characters[a.slots["lover"]]
                result.note(relationship.do_breakup(state, a, old, "cheating"))
            a.slots["lover"] = b.id
            b.slots["lover"] = a.id
            # 연인이 되면 양쪽 모두 반함 상태 (고백받고 시작되는 사랑도 있음)
            a.rel(b.id).spark = True
            b.rel(a.id).spark = True
            a.rel(b.id).add(romance=rng.uniform(15, 20), friendship=10)
            b.rel(a.id).add(romance=10, friendship=10)
            a.satisfaction += 15
            b.satisfaction += 10
            a.mood.adjust(happiness=3, stress=-2)
            b.mood.adjust(happiness=2)
            a.confession_count[b.id] = 0
            result.note(f"💕 {b.name}이(가) 고백을 받아주었습니다! 두 사람은 연인이 되었습니다.")
            state.add_event(type="confession", participants=[a.id, b.id], result="accepted",
                            location=loc, summary=summary or f"{a.name}이(가) {b.name}에게 고백, 성공")
        else:
            a.rel(b.id).add(romance=-rng.uniform(5, 8), friendship=-rng.uniform(3, 5))
            b.rel(a.id).add(friendship=-3)
            a.satisfaction -= 12
            a.mood.adjust(happiness=-2.5, energy=-1.5, stress=2)
            a.confession_count[b.id] = a.confession_count.get(b.id, 0) + 1
            count = a.confession_count[b.id]
            result.note(f"💔 {b.name}이(가) 고백을 거절했습니다... ({reason})")
            if count >= 3:
                a.rel(b.id).add(romance=-rng.uniform(40, 50))
                result.note(f"💧 {a.name}: \"이제 포기할게요...\" (3회 거절로 단념)")
            state.add_event(type="confession", participants=[a.id, b.id], result="rejected",
                            location=loc, summary=summary or f"{a.name}이(가) {b.name}에게 고백, 거절당함")
        return result

    # ---------- 뉴스 ----------

    def news_briefing(self, weird: bool = False) -> TickResult:
        state = self.state
        result = TickResult()
        if state.announcer is None:
            state.announcer = state.rng.choice(list(state.characters.keys()))
        announcer = state.characters[state.announcer]

        if weird:
            prompt = prompts.weird_news_prompt(state, announcer)
            data = self._call(prompt, "weird_news", result)
        else:
            # 어제 이벤트 중 하이라이트 1건 (큰 이벤트 우선)
            yesterday = [e for e in state.events if e.day >= state.day - 1 and e.summary]
            if not yesterday:
                result.note("📺 아직 전할 만한 소식이 없네요. (`news weird` 로 병맛 뉴스는 볼 수 있습니다)")
                return result
            big = [e for e in yesterday if e.type in
                   ("confession", "breakup", "best_friend", "enemy", "fight")]
            target = (big or yesterday)[-1]
            prompt = prompts.news_prompt(state, announcer, target.summary)
            data = self._call(prompt, "news", result)

        if data is None:
            return result
        result.scene = f"📺 [{state.village_name} 뉴스] 아나운서: {announcer.name}"
        result.say(announcer.name, data.get("text", "..."))
        return result

    # ---------- 공통 ----------

    def _call(self, prompt: str, kind: str, result: TickResult):
        try:
            return self.llm.complete_json(prompt, kind)
        except LLMError as e:
            result.note(f"⚠️ LLM 호출 실패, 이벤트를 건너뜁니다: {e}")
            return None
        except Exception as e:  # JSON 파싱 실패 등
            result.note(f"⚠️ LLM 응답 처리 실패, 이벤트를 건너뜁니다: {e}")
            return None
