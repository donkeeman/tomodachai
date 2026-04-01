import json
from unittest.mock import MagicMock, patch

from tomodachai.config import LLMConfig
from tomodachai.llm import LLMClient


def test_chat_returns_content():
    config = LLMConfig(model="test-model", api_key="test-key")
    client = LLMClient(config)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "안녕하세요!"

    with patch("tomodachai.llm.litellm") as mock_litellm:
        mock_litellm.completion.return_value = mock_response
        result = client.chat([{"role": "user", "content": "Hi"}])

    assert result == "안녕하세요!"


def test_chat_passes_config_params():
    config = LLMConfig(
        model="claude-sonnet-4-20250514",
        api_key="sk-test",
        api_base="http://localhost:11434",
        temperature=0.5,
        max_tokens=500,
    )
    client = LLMClient(config)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"

    with patch("tomodachai.llm.litellm") as mock_litellm:
        mock_litellm.completion.return_value = mock_response
        client.chat([{"role": "user", "content": "test"}])

    call_kwargs = mock_litellm.completion.call_args
    assert call_kwargs.kwargs["model"] == "claude-sonnet-4-20250514"
    assert call_kwargs.kwargs["api_key"] == "sk-test"
    assert call_kwargs.kwargs["api_base"] == "http://localhost:11434"
    assert call_kwargs.kwargs["temperature"] == 0.5
    assert call_kwargs.kwargs["max_tokens"] == 500


def test_chat_json_parses_response():
    config = LLMConfig(model="test-model", api_key="test-key")
    client = LLMClient(config)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"name": "민수", "mood": "happy"}'

    with patch("tomodachai.llm.litellm") as mock_litellm:
        mock_litellm.completion.return_value = mock_response
        result = client.chat_json([{"role": "user", "content": "test"}])

    assert result == {"name": "민수", "mood": "happy"}


def test_chat_json_handles_markdown_wrapped():
    config = LLMConfig(model="test-model", api_key="test-key")
    client = LLMClient(config)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '```json\n{"key": "value"}\n```'

    with patch("tomodachai.llm.litellm") as mock_litellm:
        mock_litellm.completion.return_value = mock_response
        result = client.chat_json([{"role": "user", "content": "test"}])

    assert result == {"key": "value"}
