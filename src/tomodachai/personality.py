from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

_TRAIT_MAP = {
    0: ("energy", {"E": "extroverted", "I": "introverted"}),
    1: ("warmth", {"W": "warm", "C": "cool"}),
    2: ("stability", {"S": "steady", "V": "volatile"}),
    3: ("openness", {"O": "open", "T": "traditional"}),
    4: ("assertiveness", {"B": "bold", "G": "gentle"}),
}

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class PersonalityType(BaseModel):
    code: str
    name: str
    description: str
    behavior_guide: str


def get_trait_values(code: str) -> dict[str, str]:
    traits = {}
    for i, (axis, mapping) in _TRAIT_MAP.items():
        traits[axis] = mapping[code[i]]
    return traits


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
