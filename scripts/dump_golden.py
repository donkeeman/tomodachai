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
        cases.append({"input": text, "throws": True})
    _write("parse_json", cases)


def main() -> None:
    dump_parse_json()
    # 이후 태스크에서 dump_game_clock() 추가


if __name__ == "__main__":
    main()
