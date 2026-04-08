from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from tomodachai.llm import LLMClient

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Slider thresholds for family and type-within-family
# Slider thresholds for group and type-within-group
_GROUP_THRESHOLDS = [
    (0.25, "easygoing"),
    (0.50, "independent"),
    (0.75, "confident"),
    (1.01, "outgoing"),
]

_TYPE_SUFFIXES = [
    (0.25, 1),
    (0.50, 2),
    (0.75, 3),
    (1.01, 4),
]

# Maps (group, type_index) → personality code
_GROUP_TYPE_CODES: dict[tuple[str, int], str] = {
    # 안정파 (Easygoing): 외유내강/다정다감/우유부단/순진무구
    ("easygoing", 1): "easygoing_softie",
    ("easygoing", 2): "easygoing_optimist",
    ("easygoing", 3): "easygoing_carer",
    ("easygoing", 4): "easygoing_dreamer",
    # 신중파 (Independent): 완전무결/유비무환/우물쭈물/묵묵부답
    ("independent", 1): "independent_dogooder",
    ("independent", 2): "independent_perfectionist",
    ("independent", 3): "independent_introvert",
    ("independent", 4): "independent_thinker",
    # 주도파 (Confident): 시원시원/속전속결/유아독존/거두절미
    ("confident", 1): "confident_busybee",
    ("confident", 2): "confident_gogetter",
    ("confident", 3): "confident_freespirit",
    ("confident", 4): "confident_brainiac",
    # 사교파 (Outgoing): 좌충우돌/시끌벅적/재기발랄/명랑쾌활
    ("outgoing", 1): "outgoing_charmer",
    ("outgoing", 2): "outgoing_dynamo",
    ("outgoing", 3): "outgoing_buddy",
    ("outgoing", 4): "outgoing_extrovert",
}


class PersonalitySliders(BaseModel):
    """Four personality sliders, each a float in [0.0, 1.0].

    Movement    : 0.0 = slow/calm,      1.0 = fast/energetic
    Speech      : 0.0 = gentle/soft,    1.0 = direct/assertive
    Expressiveness: 0.0 = reserved,     1.0 = emotionally expressive
    Attitude    : 0.0 = serious,        1.0 = relaxed/carefree
    """

    movement: float = Field(ge=0.0, le=1.0)
    speech: float = Field(ge=0.0, le=1.0)
    expressiveness: float = Field(ge=0.0, le=1.0)
    attitude: float = Field(ge=0.0, le=1.0)


class PersonalityType(BaseModel):
    code: str
    name: str
    group: str  # easygoing / outgoing / confident / independent
    description: str
    behavior_guide: str


def determine_personality(sliders: PersonalitySliders) -> str:
    """Map slider values to one of the 16 personality type codes.

    Family is determined by the average of movement and speech.
    Type within family is determined by the average of expressiveness and attitude.
    """
    ms_avg = (sliders.movement + sliders.speech) / 2.0
    ea_avg = (sliders.expressiveness + sliders.attitude) / 2.0

    group = next(name for threshold, name in _GROUP_THRESHOLDS if ms_avg < threshold)
    type_idx = next(idx for threshold, idx in _TYPE_SUFFIXES if ea_avg < threshold)

    return _GROUP_TYPE_CODES[(group, type_idx)]


def load_personalities(path: Path | None = None) -> dict[str, PersonalityType]:
    if path is None:
        path = _DATA_DIR / "personalities.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    result = {}
    for entry in data["types"]:
        p = PersonalityType(**entry)
        result[p.code] = p
    return result


_MATCHER_SYSTEM = (
    "당신은 성격 분석 전문가입니다. 주어진 성격 설명을 분석하여 "
    "가장 적합한 슬라이더 값을 추정하세요. 반드시 JSON으로만 응답하세요."
)


def match_personality(
    llm: LLMClient,
    description: str,
) -> PersonalitySliders:
    """Infer PersonalitySliders from a free-text character description.

    Returns a PersonalitySliders instance whose values can be passed to
    determine_personality() to obtain the matching type code.
    """
    prompt = f"""아래 성격 설명을 읽고, 각 슬라이더 값(0.0~1.0)을 추정하세요.

## 슬라이더 기준

- movement  (움직임): 0.0 = 느리고 차분함 / 1.0 = 빠르고 활동적임
- speech    (말투): 0.0 = 부드럽고 유순함 / 1.0 = 직접적이고 단호함
- expressiveness (표현력): 0.0 = 감정을 잘 드러내지 않음 / 1.0 = 감정 표현이 풍부함
- attitude  (태도): 0.0 = 진지하고 엄격함 / 1.0 = 여유롭고 느긋함

## 입력된 성격 설명
{description}

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "movement": 0.0~1.0 사이 숫자,
  "speech": 0.0~1.0 사이 숫자,
  "expressiveness": 0.0~1.0 사이 숫자,
  "attitude": 0.0~1.0 사이 숫자,
  "reason": "판단 근거 한 줄"
}}"""

    messages = [
        {"role": "system", "content": _MATCHER_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    result = llm.chat_json(messages)
    return PersonalitySliders(
        movement=float(result["movement"]),
        speech=float(result["speech"]),
        expressiveness=float(result["expressiveness"]),
        attitude=float(result["attitude"]),
    )
