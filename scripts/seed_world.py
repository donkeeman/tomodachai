#!/usr/bin/env python3
"""사용자 캐릭터 파일(JSON)을 FastAPI 월드에 적재한다.

캐릭터는 기본 캐스트가 아니라 **사용자별로 본인이 만든 캐릭터를 불러오는** 모델이다.
이 스크립트는 그 로드 과정을 재현한다 — JSON 파일 하나(= 한 사용자의 캐릭터 목록)를
읽어 생성(POST /api/characters)하고, location 이 있으면 그 장소로 배치한다.

    python3 scripts/seed_world.py                          # data/characters.example.json
    python3 scripts/seed_world.py --file my_characters.json
    python3 scripts/seed_world.py --base http://127.0.0.1:8000/api --file ...

파일 형식 (data/characters.example.json 참고):
    [ { "id": 1, "name": "...", "gender": "M|F",
        "personality_code": "confident_gogetter", "location": "park" }, ... ]
표준 라이브러리만 사용. (location 은 선택)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_FILE = Path(__file__).resolve().parent.parent / "data" / "characters.example.json"


def _post(base: str, path: str, body: dict | None) -> tuple[int, dict | str]:
    data = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(
        base + path, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:200]
    except urllib.error.URLError as e:
        print(f"  ⚠️ 서버 연결 실패: {e}. FastAPI 서버가 떠 있는지 확인하세요.", file=sys.stderr)
        sys.exit(1)


def load_characters(path: Path) -> list[dict]:
    if not path.exists():
        print(f"  ❌ 캐릭터 파일이 없습니다: {path}", file=sys.stderr)
        print(f"     형식 예시는 {DEFAULT_FILE} 를 참고하세요.", file=sys.stderr)
        sys.exit(1)
    try:
        chars = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON 파싱 실패 ({path}): {e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(chars, list):
        print(f"  ❌ 최상위는 캐릭터 목록(배열)이어야 합니다: {path}", file=sys.stderr)
        sys.exit(1)
    return chars


def main() -> None:
    ap = argparse.ArgumentParser(description="사용자 캐릭터 파일을 월드에 로드")
    ap.add_argument("--file", type=Path, default=DEFAULT_FILE, help="캐릭터 JSON 파일 경로")
    ap.add_argument("--base", default="http://127.0.0.1:8000/api", help="API 베이스 URL")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    chars = load_characters(args.file)
    print(f"📂 {args.file.name} 에서 {len(chars)}명 로드 중...")

    created = 0
    for c in chars:
        name = c.get("name", "?")
        cid = c.get("id")
        location = c.get("location")
        # 생성에는 location 을 빼고 보냄 (배치는 move 로)
        body = {k: v for k, v in c.items() if k != "location"}
        status, out = _post(base, "/characters", body)
        if status in (200, 201):
            created += 1
            placed = ""
            if location and cid is not None:
                ms, _ = _post(base, f"/locations/move/{cid}/{location}", None)
                placed = f" → {location}" if ms in (200, 201) else f" (이동 실패 {ms})"
            print(f"  ✅ {name}{placed}")
        elif status == 409:
            print(f"  • {name}: 이미 존재 (스킵)")
        else:
            print(f"  ❌ {name}: HTTP {status} {out}")

    print(f"\n로드 완료: {created}명. 프론트 새로고침하면 주민이 보입니다.")


if __name__ == "__main__":
    main()
