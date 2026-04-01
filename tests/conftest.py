import pytest
from unittest.mock import MagicMock

from tomodachai.config import AppConfig, LLMConfig, SimulationConfig, LocationConfig
from tomodachai.llm import LLMClient
from tomodachai.character import Character
from tomodachai.personality import load_personalities
from tomodachai.relationship import Relationship


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


@pytest.fixture
def mock_llm():
    return MagicMock(spec=LLMClient)


@pytest.fixture
def sample_personalities():
    return load_personalities()


@pytest.fixture
def char_minsu():
    return Character(
        id="char_1", name="민수", personality_code="EWSOB",
        speech_habit="~인 거지", backstory="동네 반장을 맡고 있는 활발한 청년",
    )


@pytest.fixture
def char_jieun():
    return Character(
        id="char_2", name="지은", personality_code="IWVOG",
        speech_habit="그치~?", backstory="카페를 운영하는 몽상가",
    )


@pytest.fixture
def char_taeho():
    return Character(
        id="char_3", name="태호", personality_code="ECVOB",
        speech_habit="ㅋㅋ", backstory="자유분방한 대학생",
    )
