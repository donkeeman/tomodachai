from __future__ import annotations

import json
import re

import litellm
from tomodachai.config import LLMConfig


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config

    def chat(self, messages: list[dict], **kwargs) -> str:
        params: dict = {
            "model": self.config.model,
            "messages": messages,
            "temperature": kwargs.pop("temperature", self.config.temperature),
            "max_tokens": kwargs.pop("max_tokens", self.config.max_tokens),
        }
        if self.config.api_key:
            params["api_key"] = self.config.api_key
        if self.config.api_base:
            params["api_base"] = self.config.api_base
        params.update(kwargs)
        response = litellm.completion(**params)
        return response.choices[0].message.content

    def chat_json(self, messages: list[dict], **kwargs) -> dict:
        content = self.chat(messages, **kwargs)
        return self._parse_json(content)

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        return json.loads(text)
