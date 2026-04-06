from __future__ import annotations

import json
import re
import subprocess

import litellm
from tomodachai.config import LLMConfig


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config

    def chat(self, messages: list[dict], **kwargs) -> str:
        provider = self.config.provider
        if provider == "claude-cli":
            return self._chat_claude_cli(messages)
        elif provider == "codex-cli":
            return self._chat_codex_cli(messages)
        else:
            return self._chat_litellm(messages, **kwargs)

    def _chat_litellm(self, messages: list[dict], **kwargs) -> str:
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

    def _chat_claude_cli(self, messages: list[dict]) -> str:
        prompt = self._messages_to_prompt(messages)
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"claude CLI error: {result.stderr.strip()}")
        return result.stdout.strip()

    def _chat_codex_cli(self, messages: list[dict]) -> str:
        prompt = self._messages_to_prompt(messages)
        result = subprocess.run(
            ["codex", "-q", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"codex CLI error: {result.stderr.strip()}")
        return result.stdout.strip()

    @staticmethod
    def _messages_to_prompt(messages: list[dict]) -> str:
        """Convert chat messages to a single prompt string for CLI tools."""
        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                parts.append(f"[System]\n{content}")
            elif role == "user":
                parts.append(content)
            elif role == "assistant":
                parts.append(f"[Assistant]\n{content}")
        return "\n\n".join(parts)

    def chat_json(self, messages: list[dict], retries: int = 2, **kwargs) -> dict:
        last_err = None
        for attempt in range(retries + 1):
            content = self.chat(messages, **kwargs)
            try:
                return self._parse_json(content)
            except (json.JSONDecodeError, ValueError) as e:
                last_err = e
                if attempt < retries:
                    continue
        raise ValueError(
            f"JSON 파싱 실패 ({retries + 1}회 시도): {last_err}\n응답 내용: {content[:500]}"
        )

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        if not text:
            raise ValueError("빈 응답")
        # 마크다운 코드블록 안의 JSON
        match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())
        # 첫 번째 { ... } 블록 찾기
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            return json.loads(brace_match.group(0))
        return json.loads(text)
