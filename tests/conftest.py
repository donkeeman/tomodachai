import pytest
from unittest.mock import MagicMock

from tomodachai.config import AppConfig, LLMConfig, SimulationConfig, LocationConfig


@pytest.fixture
def llm_config():
    return LLMConfig(model="test-model", api_key="test-key")


@pytest.fixture
def app_config(llm_config):
    return AppConfig(
        llm=llm_config,
        simulation=SimulationConfig(),
        locations=[
            LocationConfig(name="공원", capacity=5),
            LocationConfig(name="편의점", capacity=3),
        ],
    )
