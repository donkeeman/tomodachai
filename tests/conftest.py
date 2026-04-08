import pytest
from unittest.mock import MagicMock

from tomodachai.config import AppConfig, LLMConfig, SimulationConfig, LocationConfig
from tomodachai.llm import LLMClient
from tomodachai.character import Character, Profile, CharacterState, Customizable, SpeechHabits
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
        id=1,
        personality_code="outgoing_dynamo",
        profile=Profile(
            name="민수", birthday="03-15", blood_type="B", gender="남성",
        ),
        state=CharacterState(),
        customizable=Customizable(
            speech_habits=SpeechHabits(normal="~인 거지"),
        ),
    )


@pytest.fixture
def char_jieun():
    return Character(
        id=2,
        personality_code="easygoing_dreamer",
        profile=Profile(
            name="지은", birthday="11-02", blood_type="A", gender="여성",
        ),
        state=CharacterState(),
        customizable=Customizable(
            speech_habits=SpeechHabits(normal="그치~?"),
        ),
    )


@pytest.fixture
def char_taeho():
    return Character(
        id=3,
        personality_code="outgoing_extrovert",
        profile=Profile(
            name="태호", birthday="07-28", blood_type="O", gender="남성",
        ),
        state=CharacterState(),
        customizable=Customizable(
            speech_habits=SpeechHabits(normal="ㅋㅋ"),
        ),
    )
