# LLM 프로바이더: Codex CLI (codex exec) 임시 연동 + 오프라인 Mock
# 향후 litellm / claude-cli 등으로 교체 가능하도록 인터페이스 분리
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from typing import Any, Dict, Optional


class LLMError(Exception):
    pass


class LLMProvider:
    def complete(self, prompt: str, kind: str = "") -> str:
        raise NotImplementedError

    def complete_json(self, prompt: str, kind: str = "") -> Dict[str, Any]:
        raw = self.complete(prompt, kind)
        return extract_json(raw)


def extract_json(text: str) -> Dict[str, Any]:
    # 응답에서 첫 JSON 오브젝트만 추출 (모델이 부연 설명을 붙여도 견디도록)
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|```$", "", text, flags=re.M).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError(f"JSON을 찾을 수 없음: {text[:200]}")
    return json.loads(text[start:end + 1])


class CodexProvider(LLMProvider):
    """codex exec 비대화형 호출. 사용자의 로그인된 Codex CLI 계정을 그대로 사용."""

    def __init__(self, model: Optional[str] = None, reasoning_effort: str = "low",
                 timeout: int = 180):
        self.model = model or os.environ.get("TOMODACHI_CODEX_MODEL")
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout

    def complete(self, prompt: str, kind: str = "") -> str:
        # --output-last-message 파일로 최종 응답만 수집 (stdout에는 로그가 섞임)
        with tempfile.NamedTemporaryFile(mode="r", suffix=".txt", delete=False) as f:
            out_path = f.name
        cmd = [
            "codex", "exec",
            "--skip-git-repo-check",
            "-s", "read-only",
            "--output-last-message", out_path,
            "-c", f'model_reasoning_effort="{self.reasoning_effort}"',
        ]
        if self.model:
            cmd += ["-m", self.model]
        cmd.append(prompt)
        try:
            proc = subprocess.run(
                cmd, cwd=tempfile.gettempdir(),
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                timeout=self.timeout, text=True,
            )
            if proc.returncode != 0:
                raise LLMError(f"codex exec 실패 (exit {proc.returncode}): {proc.stderr[-300:]}")
            with open(out_path, encoding="utf-8") as fh:
                result = fh.read().strip()
            if not result:
                raise LLMError("codex exec 응답이 비어 있음")
            return result
        except subprocess.TimeoutExpired:
            raise LLMError(f"codex exec 타임아웃 ({self.timeout}초)")
        finally:
            try:
                os.unlink(out_path)
            except OSError:
                pass


class MockProvider(LLMProvider):
    """LLM 없이 시뮬레이션 엔진을 빠르게 검증하기 위한 고정 응답 프로바이더."""

    def __init__(self):
        import random
        self.rng = random.Random(0)

    def complete(self, prompt: str, kind: str = "") -> str:
        # 프롬프트에서 화자 이름 추출 시도 (없으면 기본값)
        names = re.findall(r"## 캐릭터: (\S+)", prompt)
        a = names[0] if names else "A"
        b = names[1] if len(names) > 1 else "B"

        if kind == "conversation":
            return json.dumps({
                "lines": [
                    {"speaker": a, "text": "(mock) 오늘 날씨 진짜 좋네요."},
                    {"speaker": b, "text": "(mock) 그러게요, 산책이라도 갈까요?"},
                    {"speaker": a, "text": "(mock) 좋아요! 분수대 쪽으로 가요."},
                ],
                "summary": f"{a}와(과) {b}이(가) 날씨 이야기를 하며 산책 약속을 잡음",
                # 반함 후보 플래그가 있을 때만 시뮬레이션이 참조 (없으면 무시됨)
                "spark": self.rng.random() < 0.4,
                "spark_reason": "(mock) 산책 가자며 웃는 모습이 좋아 보여서",
                "spark_monologue": "(mock) 같이 걷자는 말이... 왜 자꾸 생각나죠? 이상한 날이네요.",
            }, ensure_ascii=False)
        if kind == "confession":
            accept = self.rng.random() < 0.5
            return json.dumps({
                "decision": "accept" if accept else "reject",
                "reason": "(mock) 요즘 같이 있으면 편해서" if accept else "(mock) 아직 친구가 더 좋아서",
                "lines": [
                    {"speaker": a, "text": "(mock) 저... 사실 좋아해요."},
                    {"speaker": b, "text": "(mock) 네?! 음... " + ("저도요." if accept else "미안해요...")},
                ],
                "summary": f"{a}이(가) {b}에게 고백 ({'성공' if accept else '거절'})",
            }, ensure_ascii=False)
        if kind == "fight":
            return json.dumps({
                "lines": [
                    {"speaker": a, "text": "(mock) 그건 좀 너무한 거 아니에요?"},
                    {"speaker": b, "text": "(mock) 내가 뭘요! 적반하장이네."},
                ],
                "summary": f"{a}와(과) {b}이(가) 사소한 일로 말다툼",
            }, ensure_ascii=False)
        if kind == "photo":
            return json.dumps({
                "title": "(mock) 분수대와 점프하는 구름",
                "caption": "(mock) 오늘따라 물방울이 반짝여서 안 찍을 수가 없었어요.",
            }, ensure_ascii=False)
        if kind == "cook":
            return json.dumps({
                "dish": "(mock) 폭신폭신 자신감 오믈렛",
                "comment": "(mock) 모양은 좀 그렇지만... 맛은 자신 있어요!",
            }, ensure_ascii=False)
        if kind == "news":
            return json.dumps({
                "text": "(mock) 어제 마을에서는 훈훈한 소식이 있었습니다. 자세한 내용은 주민들에게 직접 들어보시죠!",
            }, ensure_ascii=False)
        if kind == "weird_news":
            return json.dumps({
                "text": "(mock) [속보] 마을 분수대의 물이 잠시 거꾸로 솟았다가 민망한 듯 다시 내려갔습니다.",
            }, ensure_ascii=False)
        return json.dumps({"text": "(mock) ..."}, ensure_ascii=False)


def make_provider(name: str) -> LLMProvider:
    if name == "codex":
        return CodexProvider()
    if name == "mock":
        return MockProvider()
    raise ValueError(f"알 수 없는 프로바이더: {name}")
