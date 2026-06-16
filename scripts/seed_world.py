#!/usr/bin/env python3
"""데모용 마을 시딩: 기본 캐스트 12명을 생성하고 마을 곳곳에 배치한다.

FastAPI 서버(기본 :8000)가 떠 있는 상태에서 실행:

    python3 scripts/seed_world.py
    python3 scripts/seed_world.py --base http://127.0.0.1:8000/api

reset_world()가 빈 마을을 만들기 때문에, 프론트(Babylon)에서 주민을 보려면
이 스크립트로 월드를 채운다. (표준 라이브러리만 사용)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

# (이름, 성별, 성격 코드, 배치 장소) — 그리스 신 캐스트, 15개 장소에 분산
CAST = [
    ("제우스", "M", "confident_gogetter", "plaza"),
    ("헤라", "F", "confident_freespirit", "city_hall"),
    ("포세이돈", "M", "independent_thinker", "beach"),
    ("데메테르", "F", "easygoing_carer", "grocery"),
    ("아테나", "F", "independent_perfectionist", "news_station"),
    ("아폴론", "M", "outgoing_charmer", "concert_hall"),
    ("아르테미스", "F", "independent_introvert", "park"),
    ("아레스", "M", "confident_busybee", "amusement_park"),
    ("아프로디테", "F", "outgoing_charmer", "clothing"),
    ("헤파이스토스", "M", "independent_thinker", "interior"),
    ("헤르메스", "M", "outgoing_dynamo", "fountain"),
    ("헤스티아", "F", "easygoing_softie", "cafe"),
]


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
        print(f"  ⚠️ 서버 연결 실패: {e}. 서버가 떠 있는지 확인하세요.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="데모 마을 시딩")
    ap.add_argument("--base", default="http://127.0.0.1:8000/api", help="API 베이스 URL")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    created = 0
    for i, (name, gender, code, dest) in enumerate(CAST, start=1):
        status, out = _post(base, "/characters", {
            "id": i, "name": name, "gender": gender, "personality_code": code,
        })
        if status in (200, 201):
            created += 1
            # 장소로 이동
            ms, _ = _post(base, f"/locations/move/{i}/{dest}", None)
            placed = "→ " + dest if ms in (200, 201) else f"(이동 실패 {ms})"
            print(f"  ✅ {name} ({gender}, {code}) {placed}")
        elif status == 409:
            print(f"  • {name}: 이미 존재 (스킵)")
        else:
            print(f"  ❌ {name}: HTTP {status} {out}")

    print(f"\n시딩 완료: {created}명 생성. 프론트 새로고침하면 주민이 보입니다.")


if __name__ == "__main__":
    main()
