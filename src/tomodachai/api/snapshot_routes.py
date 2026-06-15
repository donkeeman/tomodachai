"""Babylon 프론트 계약 라우터 (snapshot 폴링 + save/reset).

prototype/web_server.py의 HTTP 계약을 FastAPI로 옮긴 것.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tomodachai.api.routes import _gs
from tomodachai.api.snapshot import build_snapshot

compat_router = APIRouter()


@compat_router.get("/snapshot")
def get_snapshot(since: int = 0):
    return build_snapshot(_gs(), since)


@compat_router.post("/save")
def save_snapshot():
    from tomodachai.api import routes

    gs = _gs()
    try:
        routes._save_manager.save_temp(gs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"저장 실패: {e}")
    return {"message": f"💾 저장 완료 (Day {gs.day_count})"}


@compat_router.post("/reset")
def reset_world():
    gs = _gs()
    gs.characters.clear()
    gs.reset_world()
    return {"message": "🔄 새 마을이 시작되었습니다"}
