from __future__ import annotations

import random
from itertools import combinations

from tomodachai.bubble import Bubble
from tomodachai.character import Character
from tomodachai.config import AppConfig, LocationConfig
from tomodachai.conversation import ConversationEngine, ConversationResult
from tomodachai.llm import LLMClient
from tomodachai.memory import MemoryStore, SocialEvent
from tomodachai.personality import PersonalityType
from tomodachai.relationship import (
    Fight,
    RelationshipStage,
    RelationshipTracker,
    apply_jealousy,
    detect_triangles,
)

# 오프라인 catch-up: 큰 이벤트는 생성 금지
_BIG_EVENT_TYPES = {"confession_success", "confession_fail", "marriage", "breakup"}

# catch-up 1회 이벤트 수치 변화 폭 (작게 유지)
_CATCHUP_FRIENDSHIP_DELTA_RANGE = (-3.0, 5.0)
_CATCHUP_ROMANCE_DELTA_RANGE = (-1.0, 3.0)

# Thresholds for auto-triggered events
_FIGHT_FRIENDSHIP_THRESHOLD = -30.0  # friendship below this can trigger fight
_FIGHT_CHANCE = 0.3
_CONFESSION_ROMANCE_THRESHOLD = 60.0
_CONFESSION_CHANCE = 0.2
_HUNGER_PER_TICK = 5.0
_SATISFACTION_DECAY = 1.0
_HUNGER_BUBBLE_THRESHOLD = 80.0  # 이 이상이면 "배고파요" 말풍선 (prototype 규칙)


def assign_locations(
    characters: list[Character],
    locations: list[LocationConfig],
    seed: int | None = None,
) -> dict[str, list[Character]]:
    rng = random.Random(seed)
    assignments: dict[str, list[Character]] = {loc.name: [] for loc in locations}
    capacity_map = {loc.name: loc.capacity for loc in locations}

    shuffled = list(characters)
    rng.shuffle(shuffled)

    available = [loc.name for loc in locations]
    for char in shuffled:
        rng.shuffle(available)
        for loc_name in available:
            if len(assignments[loc_name]) < capacity_map[loc_name]:
                assignments[loc_name].append(char)
                break

    return assignments


class Simulation:
    def __init__(
        self,
        config: AppConfig,
        characters: list[Character],
        llm: LLMClient,
        personalities: dict[str, PersonalityType],
    ):
        self.config = config
        self.characters = characters
        self.conversation_engine = ConversationEngine(llm, personalities)
        self.relationships = RelationshipTracker()
        self.memory = MemoryStore()
        self._step_count = 0
        self._char_map = {c.id: c for c in characters}
        self._rng = random.Random()
        # 플레이어 응답 대기 말풍선 큐 + 고백 거절 누적(세션 한정)
        self.bubbles: list[Bubble] = []
        # 키: (고백자 id, 대상 id) → 거절/단념 누적 횟수
        self._confession_count: dict[tuple[int, int], int] = {}

    def _run_conversation(
        self,
        char_a: Character,
        char_b: Character,
        location: str,
        time_of_day: str,
    ) -> ConversationResult:
        rel_ab = self.relationships.get(char_a.id, char_b.id)
        rel_ba = self.relationships.get(char_b.id, char_a.id)
        memories = self.memory.get_events_between(char_a.id, char_b.id)

        result = self.conversation_engine.generate(
            char_a=char_a,
            char_b=char_b,
            rel_ab=rel_ab,
            rel_ba=rel_ba,
            memories=memories,
            location=location,
            time_of_day=time_of_day,
        )

        for name, deltas in result.deltas.items():
            if name == char_a.name:
                self.relationships.update(char_a.id, char_b.id, deltas)
            elif name == char_b.name:
                self.relationships.update(char_b.id, char_a.id, deltas)

        self.memory.add_event(
            SocialEvent(
                id=0,  # auto-assigned
                type="conversation",
                participants=[int(char_a.id), int(char_b.id)],
                day=self._step_count,
                location=location,
            )
        )

        return result

    def _check_triggered_events(self) -> list[dict]:
        """[LEGACY] all-pairs 일괄 처리. live 경로는 _check_triggered_events_for_pair 사용.

        Check relationship metrics and trigger fights/confessions.
        """
        events: list[dict] = []

        for a_id, b_id, rel in self.relationships.all_pairs():
            # Fight trigger: very negative friendship
            if (
                rel.friendship <= _FIGHT_FRIENDSHIP_THRESHOLD
                and self._rng.random() < _FIGHT_CHANCE
                and rel.stage not in (RelationshipStage.STRANGER,)
            ):
                fight = self._trigger_fight(a_id, b_id, rel.friendship)
                if fight:
                    events.append(fight)

            # Confession trigger: high romance + friendship stage
            if (
                rel.romance >= _CONFESSION_ROMANCE_THRESHOLD
                and rel.stage
                in (
                    RelationshipStage.FRIEND,
                    RelationshipStage.BEST_FRIEND,
                )
                and self._rng.random() < _CONFESSION_CHANCE
            ):
                confession = self._trigger_confession(a_id, b_id)
                if confession:
                    events.append(confession)

        return events

    def _trigger_fight(self, a_id: int, b_id: int, friendship: float) -> dict | None:
        # Don't fight if already fighting
        active_fights = self.relationships.get_fights()
        for f in active_fights:
            if set(f.participants) == {a_id, b_id}:
                return None

        fight = Fight(
            participants=(a_id, b_id),
            cause=f"우정 {friendship:.0f} — 사이가 나쁨",
        )
        self.relationships.add_fight(fight)

        # Apply fight effects
        self.relationships.update(a_id, b_id, {"friendship": -5})
        self.relationships.update(b_id, a_id, {"friendship": -5})

        self.memory.add_event(
            SocialEvent(
                id=0,
                type="fight",
                participants=[int(a_id), int(b_id)],
                day=self._step_count,
            )
        )

        # Satisfaction hit
        for cid in (a_id, b_id):
            if cid in self._char_map:
                self._char_map[cid].satisfaction = max(0.0, self._char_map[cid].satisfaction - 10.0)

        a_name = self._name(a_id)
        b_name = self._name(b_id)
        return {
            "type": "fight",
            "participants": [a_name, b_name],
            "summary": f"{a_name}와(과) {b_name}의 긴장이 폭발하여 싸움이 벌어졌다!",
        }

    def _maybe_confession_bubble(self, a_id, b_id) -> dict | None:
        """조건 충족 시 confess_request 말풍선을 큐에 추가하고 알림 이벤트를 반환.

        prototype 규칙: A→B romance>=50 AND friendship>=20, 이미 연인 아님,
        거절 누적<3, 대기 중 confess_request 없음, 50% 확률.
        """
        if any(b.kind == "confess_request" for b in self.bubbles):
            return None  # 동시 1개만
        if self.relationships.get_slots(a_id).lover == b_id:
            return None  # 이미 연인
        if self._confession_count.get((a_id, b_id), 0) >= 3:
            return None  # 3회 거절 후 단념 (카운트는 resolve_confession이 증가시킴)
        rel = self.relationships.get(a_id, b_id)
        if not (rel.romance >= 50.0 and rel.friendship >= 20.0):
            return None
        if self._rng.random() > 0.5:
            return None

        a_name, b_name = self._name(a_id), self._name(b_id)
        rejection_count = self._confession_count.get((a_id, b_id), 0)
        suffix = " (재도전이에요...)" if rejection_count else ""
        self.bubbles.append(
            Bubble(
                kind="confess_request",
                char_id=a_id,
                target_id=b_id,
                text=f'{a_name}: "{b_name}에게 고백하고 싶어요...{suffix} 해도 될까요?"',
            )
        )
        return {
            "type": "bubble",
            "participants": [a_name, b_name],
            "summary": f"💗 {a_name}이(가) 할 말이 있대요. (말풍선 확인)",
        }

    def _trigger_confession(self, a_id: int, b_id: int) -> dict | None:
        rel_ab = self.relationships.get(a_id, b_id)
        rel_ba = self.relationships.get(b_id, a_id)

        # 기획서 §3-3: 상대 수치 미참조 랜덤
        success = self._rng.random() < 0.5

        if success:
            # Both transition to LOVER
            rel_ab.check_stage_transition(allow_romantic_transition=True)
            rel_ba.check_stage_transition(allow_romantic_transition=True)
            event_type = "confession_success"
            summary = f"{self._name(a_id)}가 {self._name(b_id)}에게 고백하여 연인이 되었다!"
        else:
            # Rejected: friendship hit, romance decreases
            self.relationships.update(a_id, b_id, {"friendship": -5, "romance": -10})
            event_type = "confession_fail"
            summary = f"{self._name(a_id)}가 {self._name(b_id)}에게 고백했지만 거절당했다."

        self.memory.add_event(
            SocialEvent(
                id=0,
                type="confession",
                participants=[int(a_id), int(b_id)],
                day=self._step_count,
                result="accepted" if success else "rejected",
            )
        )

        return {
            "type": event_type,
            "participants": [self._name(a_id), self._name(b_id)],
            "summary": summary,
        }

    def _check_stage_transitions(self) -> None:
        """Check all relationships for stage changes (friendship-based only)."""
        for _a, _b, rel in self.relationships.all_pairs():
            rel.check_stage_transition(allow_romantic_transition=False)

    def _update_needs(self) -> None:
        """Decay satisfaction and increase hunger each tick.

        Queues a 'hungry' bubble (once per character) when hunger reaches the threshold.
        """
        for char in self.characters:
            char.hunger = min(100.0, char.hunger + _HUNGER_PER_TICK)
            char.satisfaction = max(0.0, char.satisfaction - _SATISFACTION_DECAY)
            cid = char.id
            if char.hunger >= _HUNGER_BUBBLE_THRESHOLD and not any(
                b.kind == "hungry" and b.char_id == cid for b in self.bubbles
            ):
                self.bubbles.append(
                    Bubble(kind="hungry", char_id=cid, text=f'{char.name}: "배고파요..."')
                )

    def _name(self, char_id) -> str:
        return self._char_map[char_id].name if char_id in self._char_map else str(char_id)

    # ------------------------------------------------------------------
    # Real-time step (replaces all-pairs tick for live play)
    # ------------------------------------------------------------------

    def step(self, time_of_day: str | None = None) -> list[dict]:
        """실시간용: 랜덤으로 1~2쌍 캐릭터를 골라 단일 이벤트 생성.

        tick()과 달리 '모든 쌍 처리' 없음 — 이벤트 하나만 만들고 반환.
        backward compat을 위해 tick()은 그대로 유지.
        """
        if len(self.characters) < 2:
            return []

        if time_of_day is None:
            from tomodachai.time_system import get_clock

            time_of_day = get_clock().get_time_period()

        # 랜덤으로 캐릭터 2명 선택
        pair = self._rng.sample(self.characters, 2)
        char_a, char_b = pair[0], pair[1]

        # 랜덤 장소 선택
        if self.config.locations:
            loc = self._rng.choice(self.config.locations)
            location = loc.name
        else:
            location = "공동주택"

        events: list[dict] = []

        # 대화 이벤트 생성
        result = self._run_conversation(char_a, char_b, location, time_of_day)
        events.append(
            {
                "type": "conversation",
                "location": location,
                "participants": [char_a.name, char_b.name],
                "result": result,
            }
        )

        # 트리거 이벤트 체크 (이 쌍에 한해서만)
        triggered = self._check_triggered_events_for_pair(char_a.id, char_b.id)
        events.extend(triggered)

        # 단계 전환 체크
        self._check_stage_transitions()

        # 삼각관계 질투 체크
        triangles = detect_triangles(self.relationships)
        if triangles:
            apply_jealousy(self.relationships, triangles)

        # 욕구 업데이트
        self._update_needs()

        self._step_count += 1
        return events

    def _check_triggered_events_for_pair(self, a_id, b_id) -> list[dict]:
        """특정 쌍에 대해서만 fight/confession 체크."""
        events: list[dict] = []
        rel = self.relationships.get(a_id, b_id)

        if (
            rel.friendship <= _FIGHT_FRIENDSHIP_THRESHOLD
            and self._rng.random() < _FIGHT_CHANCE
            and rel.stage not in (RelationshipStage.STRANGER,)
        ):
            fight = self._trigger_fight(a_id, b_id, rel.friendship)
            if fight:
                events.append(fight)

        bubble_note = self._maybe_confession_bubble(a_id, b_id)
        if bubble_note:
            events.append(bubble_note)

        return events

    # ------------------------------------------------------------------
    # Offline catch-up (lightweight, no LLM)
    # ------------------------------------------------------------------

    def generate_catchup_events(self, offline_hours: float) -> list[dict]:
        """오프라인 기간 동안 일어났을 법한 이벤트를 숫자 테이블로만 산출.

        LLM 호출 없음. 큰 이벤트(고백/결혼 등) 금지.
        반환값: 경량 이벤트 dict 리스트.
        """
        from tomodachai.time_system import GameClock

        clock = GameClock()
        count = clock.catchup_event_count(offline_hours)

        if len(self.characters) < 2 or count == 0:
            return []

        events: list[dict] = []
        pairs = list(combinations(self.characters, 2))

        for _ in range(count):
            if not pairs:
                break
            char_a, char_b = self._rng.choice(pairs)

            f_delta = self._rng.uniform(*_CATCHUP_FRIENDSHIP_DELTA_RANGE)
            r_delta = self._rng.uniform(*_CATCHUP_ROMANCE_DELTA_RANGE)

            self.relationships.update(
                char_a.id,
                char_b.id,
                {
                    "friendship": f_delta,
                    "romance": r_delta,
                },
            )
            self.relationships.update(
                char_b.id,
                char_a.id,
                {
                    "friendship": f_delta * 0.8,  # 비대칭 허용
                    "romance": r_delta * 0.6,
                },
            )

            self._check_stage_transitions()

            self.memory.add_event(
                SocialEvent(
                    id=0,
                    type="catchup",
                    participants=[int(char_a.id), int(char_b.id)],
                    day=self._step_count,
                )
            )

            self._step_count += 1

            events.append(
                {
                    "type": "catchup",
                    "participants": [char_a.name, char_b.name],
                    "summary": f"{char_a.name}와(과) {char_b.name}이(가) 어울렸다.",
                    "deltas": {
                        char_a.name: {
                            "friendship": round(f_delta, 1),
                            "romance": round(r_delta, 1),
                        },
                        char_b.name: {
                            "friendship": round(f_delta * 0.8, 1),
                            "romance": round(r_delta * 0.6, 1),
                        },
                    },
                }
            )

        return events

    # ------------------------------------------------------------------

    def _force_encounter(
        self,
        char_a: Character,
        char_b: Character,
        location: str,
    ) -> ConversationResult:
        return self._run_conversation(char_a, char_b, location, "오후")

