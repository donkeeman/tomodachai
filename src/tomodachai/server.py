"""FastAPI application entry point."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from tomodachai.api.routes import _event_to_out, _ws_clients, router, set_game_state
from tomodachai.api.snapshot_routes import compat_router
from tomodachai.config import load_config
from tomodachai.game_state import GameState
from tomodachai.time_system import (
    EVENT_INTERVAL_MAX_SECONDS,
    EVENT_INTERVAL_MIN_SECONDS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Background event loop
# ---------------------------------------------------------------------------

_bg_task: asyncio.Task | None = None


async def _event_loop(game: GameState) -> None:
    """실시간 이벤트 루프: 10~30분마다 랜덤 간격으로 step() 실행."""
    while True:
        interval = random.uniform(EVENT_INTERVAL_MIN_SECONDS, EVENT_INTERVAL_MAX_SECONDS)
        await asyncio.sleep(interval)

        if not game.characters:
            continue

        try:
            raw_events = game.step()
        except Exception:
            logger.exception("Background step() failed")
            continue

        if not raw_events or not _ws_clients:
            continue

        events_payload = [_event_to_out(e).model_dump() for e in raw_events]
        msg = json.dumps(
            {
                "type": "realtime_event",
                "time_period": game.current_time_period,
                "events": events_payload,
            }
        )

        dead: set[WebSocket] = set()
        for ws in list(_ws_clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        _ws_clients.difference_update(dead)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(config_path: Path | None = None) -> FastAPI:
    # Game state 초기화 (lifespan 클로저에 캡처)
    config = load_config(config_path)
    game = GameState(config)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        global _bg_task
        _bg_task = asyncio.create_task(_event_loop(game))
        logger.info("Real-time event loop started")
        yield
        if _bg_task is not None:
            _bg_task.cancel()
            try:
                await _bg_task
            except asyncio.CancelledError:
                pass

    app = FastAPI(
        title="tomodachai",
        description="AI 우리 동네 이야기 — 게임 서버",
        version="0.3.0",
        lifespan=lifespan,
    )

    # CORS — Godot HTTP client, 브라우저 디버그 등 허용
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    set_game_state(game)
    app.include_router(router, prefix="/api")
    app.include_router(compat_router, prefix="/api")
    _register_realtime_routes(app, game)

    return app


# ---------------------------------------------------------------------------
# Real-time endpoints (registered directly on app to avoid circular import)
# ---------------------------------------------------------------------------


def _register_realtime_routes(app: FastAPI, game: GameState) -> None:
    from fastapi import APIRouter

    rt = APIRouter(prefix="/api")

    @rt.get("/time")
    def get_time():
        """현재 게임 시간 정보 반환."""
        clock = game._clock
        now = clock.now()
        return {
            "game_hour": clock.get_game_hour(now),
            "time_period": clock.get_time_period(now),
            "time_flip": game.time_flip,
            "day_count": game.day_count,
            "last_online": game.last_online.isoformat(),
        }

    @rt.post("/connect")
    def reconnect():
        """재접속 처리 — catch-up 이벤트 + 시간 정보 반환."""
        result = game.connect()
        catchup = result.pop("catchup_events")
        result["catchup_events"] = [_event_to_out(e).model_dump() for e in catchup]
        return result

    app.include_router(rt)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="tomodachai game server")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    app = create_app(args.config)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
