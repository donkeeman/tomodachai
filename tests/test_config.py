import os
from pathlib import Path

import yaml

from tomodachai.config import AppConfig, LLMConfig, load_config


def test_default_config():
    config = AppConfig()
    assert config.llm.model == "claude-sonnet-4-20250514"
    assert config.llm.temperature == 0.8
    assert config.simulation.ticks_per_day == 6
    assert len(config.locations) == 3


def test_load_config_from_yaml(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump({
        "llm": {"model": "gpt-4o", "temperature": 0.5},
        "simulation": {"ticks_per_day": 4},
        "locations": [{"name": "학교", "capacity": 10}],
    }), encoding="utf-8")
    config = load_config(cfg_path)
    assert config.llm.model == "gpt-4o"
    assert config.llm.temperature == 0.5
    assert config.simulation.ticks_per_day == 4
    assert config.locations[0].name == "학교"


def test_load_config_missing_file():
    config = load_config(Path("nonexistent.yaml"))
    assert config.llm.model == "claude-sonnet-4-20250514"


def test_api_key_from_env(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump({"llm": {"model": "test"}}), encoding="utf-8")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-123")
    config = load_config(cfg_path)
    assert config.llm.api_key == "sk-test-123"
