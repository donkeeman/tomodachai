from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    api_key: str | None = None
    api_base: str | None = None
    temperature: float = 0.8
    max_tokens: int = 1000


class SimulationConfig(BaseModel):
    ticks_per_day: int = 6
    max_characters: int = 10


class LocationConfig(BaseModel):
    name: str
    capacity: int = 4


class AppConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    locations: list[LocationConfig] = Field(default_factory=lambda: [
        LocationConfig(name="공원", capacity=5),
        LocationConfig(name="편의점", capacity=3),
        LocationConfig(name="카페", capacity=4),
    ])


def load_config(path: Path | None = None) -> AppConfig:
    if path is None:
        path = Path("config.yaml")
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        config = AppConfig(**data)
    else:
        config = AppConfig()
    if config.llm.api_key is None:
        config.llm.api_key = os.environ.get("LLM_API_KEY")
    return config
