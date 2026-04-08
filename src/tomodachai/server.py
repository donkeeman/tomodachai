"""FastAPI application entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tomodachai.api.routes import router, set_game_state
from tomodachai.config import load_config
from tomodachai.game_state import GameState


def create_app(config_path: Path | None = None) -> FastAPI:
    app = FastAPI(
        title="tomodachai",
        description="AI 우리 동네 이야기 — 게임 서버",
        version="0.2.0",
    )

    # CORS — Godot HTTP client, 브라우저 디버그 등 허용
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Game state 초기화
    config = load_config(config_path)
    game = GameState(config)
    set_game_state(game)

    app.include_router(router, prefix="/api")

    return app


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
