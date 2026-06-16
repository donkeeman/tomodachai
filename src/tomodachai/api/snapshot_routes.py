"""Babylon 프론트 계약 라우터 (snapshot 폴링 + save/reset).

prototype/web_server.py의 HTTP 계약을 FastAPI로 옮긴 것.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tomodachai.api.routes import _gs
from tomodachai.api.snapshot import build_snapshot

compat_router = APIRouter()


@compat_router.get("/snapshot")
def get_snapshot(since: int = 0):
    return build_snapshot(_gs(), since)


@compat_router.post("/save")
def save_snapshot():
    # _save_manager는 set_save_manager()로 교체될 수 있어 호출 시점에 참조 (top-level import 금지).
    # Babylon 레거시 계약용 alias — 동작은 routes.py의 /save/temp와 동일(save_temp).
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
    gs.reset_world()
    return {"message": "🔄 새 마을이 시작되었습니다"}


class FeedRequest(BaseModel):
    char_id: int
    food_id: int


@compat_router.post("/feed")
def feed_character(body: FeedRequest):
    from tomodachai.food import feed

    gs = _gs()
    char = gs.get_character(body.char_id)
    if char is None:
        raise HTTPException(status_code=404, detail=f"Character {body.char_id} not found")
    try:
        msg = feed(char, body.food_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # 결과를 이벤트 로그에 기록 → 다음 폴링에서 피드 스트림에 재생 (scene = msg)
    gs.record_events([{"type": "feed", "participants": [char.name], "summary": msg}])
    return {"message": msg}
