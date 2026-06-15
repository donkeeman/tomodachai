# 데이터 모델 정의 (14-data-schema.md의 스키마를 터미널 프로토타입 범위로 축소)
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


def clamp(value: float, lo: float, hi: float) -> float:
    # 모든 수치는 범위 밖으로 나가지 않도록 클램핑 (스키마 문서 규칙)
    return max(lo, min(hi, value))


@dataclass
class Mood:
    # 단기 감정 3축 (0~10, 중립 5)
    happiness: float = 5.0
    energy: float = 5.0
    stress: float = 5.0

    def adjust(self, happiness: float = 0, energy: float = 0, stress: float = 0) -> None:
        self.happiness = clamp(self.happiness + happiness, 0, 10)
        self.energy = clamp(self.energy + energy, 0, 10)
        self.stress = clamp(self.stress + stress, 0, 10)

    def converge(self, step: float = 0.2) -> None:
        # 시간 경과 시 중립(5)으로 수렴
        for attr in ("happiness", "energy", "stress"):
            v = getattr(self, attr)
            if v > 5:
                setattr(self, attr, max(5.0, v - step))
            elif v < 5:
                setattr(self, attr, min(5.0, v + step))

    def label(self) -> str:
        # 3축 조합을 한 단어 감정으로 (LLM 프롬프트/표시용)
        if self.stress >= 7:
            return "짜증남" if self.energy >= 5 else "지침"
        if self.happiness >= 7:
            return "신남" if self.energy >= 6 else "흐뭇함"
        if self.happiness <= 3:
            return "우울함" if self.energy <= 4 else "심술남"
        if self.energy <= 3:
            return "나른함"
        return "평온함"


@dataclass
class RelValues:
    # 방향성 수치: A→B와 B→A는 별개
    friendship: float = 0.0   # -100 ~ 100
    romance: float = 0.0      # 0 ~ 100
    # 반함 여부 (02 문서 '반함 트리거'). False면 대화로 romance가 누적되지 않음
    spark: bool = False

    def add(self, friendship: float = 0, romance: float = 0) -> None:
        self.friendship = clamp(self.friendship + friendship, -100, 100)
        self.romance = clamp(self.romance + romance, 0, 100)


@dataclass
class ExLoverTag:
    target: int
    reason: str   # mutual / fight / cheating / boredom / triangle / misunderstanding
    day: int


@dataclass
class Character:
    id: int
    name: str
    gender: str               # "M" / "F"
    birthday: str             # "MM-DD"
    blood_type: str           # A / B / O / AB
    # 성격 슬라이더 (각 0~8)
    movement: int = 4
    speech: int = 4
    expressiveness: int = 4
    attitude: int = 4
    overall: int = 4
    # 말버릇 (감정별 5종)
    speech_habits: Dict[str, str] = field(default_factory=dict)
    # 미니 개성 (걷기/먹기/대기)
    mini_traits: Dict[str, str] = field(default_factory=dict)
    # 상태
    satisfaction: float = 30.0
    level: int = 1
    hunger: float = 20.0
    mood: Mood = field(default_factory=Mood)
    location: str = "living_room"
    # 관계 (이 캐릭터 → 상대)
    relationships: Dict[int, RelValues] = field(default_factory=dict)
    slots: Dict[str, Optional[int]] = field(
        default_factory=lambda: {"best_friend": None, "lover": None, "enemy": None}
    )
    ex_lovers: List[ExLoverTag] = field(default_factory=list)
    nicknames: Dict[int, str] = field(default_factory=dict)
    confession_count: Dict[int, int] = field(default_factory=dict)
    # 음식 선호 순위 (인덱스 = 음식 ID, 값 = 순위). 생성 시 확정, 불변
    food_ranks: List[int] = field(default_factory=list)
    food_eaten: List[bool] = field(default_factory=list)
    # 궁합 계산용 개인 시드
    seed: int = 0

    def rel(self, other_id: int) -> RelValues:
        if other_id not in self.relationships:
            self.relationships[other_id] = RelValues()
        return self.relationships[other_id]

    def has_met(self, other_id: int) -> bool:
        return other_id in self.relationships

    @property
    def despair(self) -> bool:
        # 절망 상태는 저장하지 않고 런타임 판정
        return self.satisfaction < 0


@dataclass
class GameEvent:
    id: int
    type: str                 # conversation / fight / confession / breakup / ...
    participants: List[int]
    day: int
    time: str = ""
    location: str = ""
    reason: str = ""          # breakup 사유 등
    result: str = ""          # accepted / rejected / success / failed
    summary: str = ""         # 프로토타입에서는 LLM 요약을 기억 주입에 활용


@dataclass
class Bubble:
    # 플레이어 응답 대기 말풍선 (고백 허락 요청 등)
    kind: str                 # confess_request / hungry / ...
    char_id: int
    target_id: Optional[int] = None
    text: str = ""


@dataclass
class GameState:
    village_name: str = "별빛 마을"
    day: int = 1
    minutes: int = 7 * 60     # 게임 내 시각 (분). 하루 리셋 새벽 5시
    money: int = 10000
    announcer: Optional[int] = None
    characters: Dict[int, Character] = field(default_factory=dict)
    events: List[GameEvent] = field(default_factory=list)
    next_event_id: int = 1
    bubbles: List[Bubble] = field(default_factory=list)
    # 도구 아이템 결과물 (05 문서: 카메라 갤러리 / 프라이팬 요리 카탈로그)
    photos: List[dict] = field(default_factory=list)
    dishes: List[dict] = field(default_factory=list)
    rng: random.Random = field(default_factory=random.Random)

    def clock(self) -> str:
        return f"{self.minutes // 60:02d}:{self.minutes % 60:02d}"

    def add_event(self, **kwargs) -> GameEvent:
        ev = GameEvent(id=self.next_event_id, day=self.day, time=self.clock(), **kwargs)
        self.next_event_id += 1
        self.events.append(ev)
        return ev

    def shared_events(self, a_id: int, b_id: int, limit: int = 5) -> List[GameEvent]:
        # 두 캐릭터의 공유 기억 (최근 이벤트 로그에서 선별 주입)
        out = [e for e in self.events if a_id in e.participants and b_id in e.participants]
        return out[-limit:]
