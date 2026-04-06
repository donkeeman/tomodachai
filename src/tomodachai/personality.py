from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from tomodachai.llm import LLMClient

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Slider thresholds for family and type-within-family
_FAMILY_THRESHOLDS = [
    (0.25, "nagomi"),
    (0.50, "cool"),
    (0.75, "dry"),
    (1.01, "nori"),
]

_TYPE_SUFFIXES = [
    (0.25, 1),
    (0.50, 2),
    (0.75, 3),
    (1.01, 4),
]

# Maps (family, type_index) → personality code
_FAMILY_TYPE_CODES: dict[tuple[str, int], str] = {
    ("nagomi", 1): "nagomi_softie",
    ("nagomi", 2): "nagomi_optimist",
    ("nagomi", 3): "nagomi_carer",
    ("nagomi", 4): "nagomi_dreamer",
    ("cool", 1): "cool_dogooder",
    ("cool", 2): "cool_perfectionist",
    ("cool", 3): "cool_introvert",
    ("cool", 4): "cool_thinker",
    ("dry", 1): "dry_busybee",
    ("dry", 2): "dry_gogetter",
    ("dry", 3): "dry_freespirit",
    ("dry", 4): "dry_brainiac",
    ("nori", 1): "nori_charmer",
    ("nori", 2): "nori_dynamo",
    ("nori", 3): "nori_buddy",
    ("nori", 4): "nori_extrovert",
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
    family: str
    description: str
    behavior_guide: str


def determine_personality(sliders: PersonalitySliders) -> str:
    """Map slider values to one of the 16 personality type codes.

    Family is determined by the average of movement and speech.
    Type within family is determined by the average of expressiveness and attitude.
    """
    ms_avg = (sliders.movement + sliders.speech) / 2.0
    ea_avg = (sliders.expressiveness + sliders.attitude) / 2.0

    family = next(name for threshold, name in _FAMILY_THRESHOLDS if ms_avg < threshold)
    type_idx = next(idx for threshold, idx in _TYPE_SUFFIXES if ea_avg < threshold)

    return _FAMILY_TYPE_CODES[(family, type_idx)]


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
