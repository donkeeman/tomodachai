from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel

if TYPE_CHECKING:
    from tomodachai.llm import LLMClient

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


_MATCHER_SYSTEM = "당신은 성격 분석 전문가입니다. 주어진 성격 설명을 분석하여 가장 적합한 유형을 선택하세요. 반드시 JSON으로만 응답하세요."


def match_personality(
    llm: LLMClient,
    personalities: dict[str, PersonalityType],
    description: str,
) -> str:
    type_list = "\n".join(
        f"- {p.code} ({p.name}): {p.description}"
        for p in personalities.values()
    )
    prompt = f"""아래 성격 설명을 읽고, 가장 적합한 성격 유형 코드를 선택하세요.

## 입력된 성격 설명
{description}

## 성격 유형 목록
{type_list}

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "code": "선택한 5글자 코드",
  "reason": "선택 이유 한 줄"
}}"""

    messages = [
        {"role": "system", "content": _MATCHER_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    result = llm.chat_json(messages)
    code = result["code"]
    if code not in personalities:
        raise ValueError(f"LLM returned invalid personality code: {code}")
    return code
