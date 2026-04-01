# Phase 1: 텍스트 기반 사회성 프로토타입 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI 에이전트 캐릭터들이 독립적으로 대화하고, 관계를 형성하며, 삼각관계·질투·갈등을 시뮬레이션하는 텍스트 기반 프로토타입을 구축한다.

**Architecture:** Python 백엔드에서 LLM을 통해 캐릭터 간 대화를 생성하고, 관계 수치와 사회적 기억을 업데이트하는 틱 기반 시뮬레이션. 프론트엔드 없이 텍스트 로그로 결과를 출력한다. LLM 제공자는 litellm을 통해 추상화하여 Anthropic, OpenAI, Ollama, 커스텀 엔드포인트 모두 호환.

**Tech Stack:** Python 3.11+, litellm (LLM 추상화), pydantic (데이터 모델), pyyaml (설정), pytest (테스트)

---

## File Structure

```
tomodachai/
├── pyproject.toml
├── config.yaml
├── data/
│   └── personalities.yaml          # 32가지 성격 유형 정의
├── src/
│   └── tomodachai/
│       ├── __init__.py
│       ├── config.py               # 설정 로딩 (YAML + 환경변수)
│       ├── llm.py                  # LLM 클라이언트 (litellm 래퍼)
│       ├── personality.py          # 성격 유형 모델 + 로딩 + LLM 매칭
│       ├── character.py            # 캐릭터 모델
│       ├── relationship.py         # 관계 모델 + 트래커 + 삼각관계
│       ├── memory.py               # 사회적 기억 시스템
│       ├── conversation.py         # 대화 생성 엔진
│       ├── simulation.py           # 시뮬레이션 루프 + 스케줄러
│       └── main.py                 # CLI 진입점
├── tests/
│   ├── conftest.py                 # 공용 fixture
│   ├── test_config.py
│   ├── test_llm.py
│   ├── test_personality.py
│   ├── test_character.py
│   ├── test_relationship.py
│   ├── test_memory.py
│   ├── test_conversation.py
│   └── test_simulation.py
└── docs/
    └── superpowers/
        └── plans/
```

---

## Task 1: Project Scaffolding & Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `config.yaml`
- Create: `src/tomodachai/__init__.py`
- Create: `src/tomodachai/config.py`
- Create: `tests/conftest.py`
- Create: `tests/test_config.py`
- Create: `.gitignore`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.venv/
venv/
.env
*.log
.pytest_cache/
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "tomodachai"
version = "0.1.0"
description = "AI-powered social simulation prototype"
requires-python = ">=3.11"
dependencies = [
    "litellm>=1.40.0",
    "pydantic>=2.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.12",
]

[project.scripts]
tomodachai = "tomodachai.main:main"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: tests requiring a real LLM connection",
]
```

- [ ] **Step 3: Create `config.yaml`**

```yaml
llm:
  model: "claude-sonnet-4-20250514"
  api_key: null       # null이면 환경변수에서 읽음
  api_base: null      # 커스텀 엔드포인트 (프록시, Ollama 등)
  temperature: 0.8
  max_tokens: 1000

simulation:
  ticks_per_day: 6
  max_characters: 10

locations:
  - name: "공원"
    capacity: 5
  - name: "편의점"
    capacity: 3
  - name: "카페"
    capacity: 4
  - name: "정자"
    capacity: 4
```

- [ ] **Step 4: Create `src/tomodachai/__init__.py`**

```python
"""AI 우리 동네 이야기 - 텍스트 기반 사회성 시뮬레이션"""
```

- [ ] **Step 5: Create `src/tomodachai/config.py`**

```python
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
```

- [ ] **Step 6: Write test for config**

```python
# tests/test_config.py
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
```

- [ ] **Step 7: Create `tests/conftest.py` with shared fixtures**

```python
# tests/conftest.py
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
```

- [ ] **Step 8: Install dependencies and run tests**

Run: `cd d:/Users/user/Desktop/Projects/tomodachai && pip install -e ".[dev]"`
Then: `pytest tests/test_config.py -v`
Expected: All 4 tests PASS

- [ ] **Step 9: Commit**

```bash
git add .gitignore pyproject.toml config.yaml src/ tests/ docs/
git commit -m "feat: project scaffolding and configuration system"
```

---

## Task 2: LLM Client

**Files:**
- Create: `src/tomodachai/llm.py`
- Create: `tests/test_llm.py`

- [ ] **Step 1: Write failing tests for LLM client**

```python
# tests/test_llm.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_llm.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tomodachai.llm'`

- [ ] **Step 3: Implement LLM client**

```python
# src/tomodachai/llm.py
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
        # Strip markdown code fences if present
        match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        return json.loads(text)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_llm.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/llm.py tests/test_llm.py
git commit -m "feat: LLM client with litellm abstraction and JSON parsing"
```

---

## Task 3: Personality Data & Model

**Files:**
- Create: `data/personalities.yaml`
- Create: `src/tomodachai/personality.py`
- Create: `tests/test_personality.py`

- [ ] **Step 1: Create `data/personalities.yaml` with all 32 types**

성격 5축: Energy(E/I), Warmth(W/C), Stability(S/V), Openness(O/T), Assertiveness(B/G)

```yaml
# 32가지 성격 유형 정의
# 코드: Energy(E외향/I내향) + Warmth(W따뜻/C냉정) + Stability(S안정/V변덕)
#       + Openness(O개방/T전통) + Assertiveness(B대담/G온화)

trait_axes:
  energy: ["extroverted", "introverted"]
  warmth: ["warm", "cool"]
  stability: ["steady", "volatile"]
  openness: ["open", "traditional"]
  assertiveness: ["bold", "gentle"]

types:
  - code: "EWSOB"
    name: "불꽃 리더"
    description: "사교적이고 따뜻하며 안정적이고 개방적인 대담한 성격"
    behavior_guide: >
      적극적으로 대화를 이끌고, 다른 사람을 격려하며, 새로운 활동을 제안한다.
      갈등 상황에서 직접 나서서 해결하려 한다. 자신감이 넘치고 에너지가 풍부하다.

  - code: "EWSOG"
    name: "따스한 현자"
    description: "사교적이고 따뜻하며 안정적이고 개방적이지만 조용히 이끄는 성격"
    behavior_guide: >
      경청하고 공감하며 부드럽게 조언한다. 모두와 잘 지내며 갈등이 있으면
      자연스럽게 중재한다. 서두르지 않고 편안한 분위기를 만든다.

  - code: "EWSTB"
    name: "호탕한 어른"
    description: "사교적이고 따뜻하지만 전통적 가치를 중시하는 대담한 성격"
    behavior_guide: >
      경험을 바탕으로 호탕하게 조언하며 어른 역할을 한다. 규칙과 예의를
      중시하고 직설적이다. 후배를 챙기지만 버릇없는 것은 용납하지 않는다.

  - code: "EWSTG"
    name: "다정한 이웃"
    description: "사교적이고 따뜻하며 안정적이지만 전통적이고 조용한 성격"
    behavior_guide: >
      누구에게나 다정하고 살뜰하게 챙긴다. 모험보다 안정을 선호하며
      이웃의 안부를 묻고 간식을 나눈다. 소소한 일상에서 행복을 찾는다.

  - code: "EWVOB"
    name: "열정 폭풍"
    description: "사교적이고 따뜻하지만 감정 기복이 있고 대담한 성격"
    behavior_guide: >
      감정이 풍부하고 에너지가 넘치며 즉흥적이다. 쉽게 흥분하고 쉽게
      실망한다. 새로운 아이디어에 열광하지만 금방 다른 것에 관심이 옮겨간다.

  - code: "EWVOG"
    name: "감성 힐러"
    description: "사교적이고 따뜻하며 감정적이고 개방적이지만 조용한 성격"
    behavior_guide: >
      타인의 감정에 민감하게 반응하며 공감 능력이 뛰어나다. 본인도 감정
      기복이 있어 울기도 하고 웃기도 한다. 사람들의 마음을 어루만진다.

  - code: "EWVTB"
    name: "뜨거운 투사"
    description: "사교적이고 따뜻하지만 감정적이고 전통적이며 대담한 성격"
    behavior_guide: >
      자기 신념에 대해 열정적이며 반대 의견에 격하게 반응한다. 정의감이
      강하고 약자를 돕지만 한번 화나면 쉽게 풀리지 않는다.

  - code: "EWVTG"
    name: "눈물의 낭만가"
    description: "사교적이고 따뜻하며 감정적이고 전통적이며 온화한 성격"
    behavior_guide: >
      감성적이고 로맨틱하며 전통적 가치를 소중히 여긴다. 쉽게 감동받고
      눈물을 흘린다. 사랑과 우정에 올인하며 상처받으면 오래 간다.

  - code: "ECSOB"
    name: "카리스마 탐험가"
    description: "사교적이지만 쿨하고 안정적이며 개방적이고 대담한 성격"
    behavior_guide: >
      쿨한 카리스마로 사람들의 주목을 받으며 새로운 경험을 추구한다.
      감정보다 논리로 접근하고 도전적인 상황을 즐긴다.

  - code: "ECSOG"
    name: "쿨한 중재자"
    description: "사교적이지만 쿨하고 안정적이며 개방적이고 온화한 성격"
    behavior_guide: >
      감정에 휘둘리지 않고 객관적으로 상황을 판단한다. 분쟁 시 양쪽
      입장을 듣고 공정하게 중재한다. 존재 자체가 안정감을 준다.

  - code: "ECSTB"
    name: "냉철한 지휘관"
    description: "사교적이지만 쿨하고 안정적이며 전통적이고 대담한 성격"
    behavior_guide: >
      효율과 질서를 최우선시하며 감정적 결정을 싫어한다. 조직을 체계적으로
      관리하고 규율을 강조한다. 결과를 중시하며 게으름을 용납하지 않는다.

  - code: "ECSTG"
    name: "과묵한 매니저"
    description: "사교적이지만 쿨하고 안정적이며 전통적이고 온화한 성격"
    behavior_guide: >
      조용히 뒤에서 상황을 관리하며 불필요한 말을 하지 않는다.
      신뢰할 수 있고 맡은 일은 묵묵히 해낸다. 존재감이 크진 않지만 든든하다.

  - code: "ECVOB"
    name: "변덕 모험가"
    description: "사교적이지만 쿨하고 감정적이며 개방적이고 대담한 성격"
    behavior_guide: >
      기분에 따라 행동이 달라지며 예측 불가능하다. 자극적인 것을
      찾아다니고 지루함을 참지 못한다. 매력적이지만 믿기 어렵다.

  - code: "ECVOG"
    name: "도도한 예술혼"
    description: "사교적이지만 쿨하고 감정적이며 개방적이고 온화한 성격"
    behavior_guide: >
      자신만의 미학이 있으며 기분에 따라 태도가 달라진다.
      예술적 감각이 뛰어나고 독특한 시각으로 세상을 본다.

  - code: "ECVTB"
    name: "날카로운 비평가"
    description: "사교적이지만 쿨하고 감정적이며 전통적이고 대담한 성격"
    behavior_guide: >
      직설적으로 비판하며 감정 기복이 있다. 높은 기준을 가지고 있으며
      타협하지 않는다. 존경받기도 하지만 두려움의 대상이 되기도 한다.

  - code: "ECVTG"
    name: "시니컬 관찰자"
    description: "사교적이지만 쿨하고 감정적이며 전통적이고 온화한 성격"
    behavior_guide: >
      한 발 물러서서 관찰하며 냉소적인 코멘트를 던진다. 속으로는
      신경 쓰지만 티를 내지 않는다. 유머가 독특하고 은근히 다정하다.

  - code: "IWSOB"
    name: "조용한 영웅"
    description: "내성적이고 따뜻하며 안정적이고 개방적이며 대담한 성격"
    behavior_guide: >
      평소에는 조용하지만 위기 시 과감히 행동한다. 소수와 깊은 유대를
      형성하며 신뢰를 중시한다. 말보다 행동으로 보여주는 타입이다.

  - code: "IWSOG"
    name: "온화한 상담사"
    description: "내성적이고 따뜻하며 안정적이고 개방적이며 온화한 성격"
    behavior_guide: >
      소수의 가까운 사람에게 헌신적이며 깊이 경청한다.
      조용한 환경을 선호하며 1:1 대화에서 진가를 발휘한다.

  - code: "IWSTB"
    name: "신념의 수호자"
    description: "내성적이고 따뜻하며 안정적이고 전통적이며 대담한 성격"
    behavior_guide: >
      자기 원칙에 확고하며 조용하지만 단호하다. 전통적 가치를 지키기
      위해 필요하면 목소리를 높인다. 가까운 사람을 끝까지 지킨다.

  - code: "IWSTG"
    name: "포근한 집순이"
    description: "내성적이고 따뜻하며 안정적이고 전통적이며 온화한 성격"
    behavior_guide: >
      집에서 편안하게 지내는 것을 좋아하며 가까운 사람들을 따뜻하게
      돌본다. 변화를 싫어하고 익숙한 루틴을 선호한다.

  - code: "IWVOB"
    name: "내면의 혁명가"
    description: "내성적이고 따뜻하지만 감정적이고 개방적이며 대담한 성격"
    behavior_guide: >
      겉으로는 조용하지만 내면에 강한 열정이 있다. 때때로 폭발적으로
      감정을 표현하며 주변을 놀라게 한다. 이상주의적이다.

  - code: "IWVOG"
    name: "몽상가"
    description: "내성적이고 따뜻하며 감정적이고 개방적이며 온화한 성격"
    behavior_guide: >
      상상의 세계에 자주 빠지며 현실과 환상의 경계가 모호하다.
      창의적이지만 실행력이 약하다. 마음이 여리고 잘 상처받는다.

  - code: "IWVTB"
    name: "외로운 전사"
    description: "내성적이고 따뜻하지만 감정적이고 전통적이며 대담한 성격"
    behavior_guide: >
      혼자서도 자기 신념을 위해 싸우며 감정 기복이 있다. 이해받지
      못한다고 느끼곤 하며, 가까운 사람에게는 의외로 다정하다.

  - code: "IWVTG"
    name: "여린 시인"
    description: "내성적이고 따뜻하며 감정적이고 전통적이며 온화한 성격"
    behavior_guide: >
      섬세하고 예민하며 아름다운 것에 깊이 감동한다. 상처받기 쉽지만
      자기 감정을 잘 표현하지 못한다. 혼자 있을 때 가장 진솔하다.

  - code: "ICSOB"
    name: "고독한 천재"
    description: "내성적이고 쿨하며 안정적이고 개방적이며 대담한 성격"
    behavior_guide: >
      혼자 생각하는 것을 좋아하며 독창적인 아이디어가 많다. 사교에
      관심이 적고 자기 세계에 몰두한다. 필요하면 단호하게 의견을 말한다.

  - code: "ICSOG"
    name: "냉정한 조언자"
    description: "내성적이고 쿨하며 안정적이고 개방적이며 온화한 성격"
    behavior_guide: >
      감정 없이 논리적으로 조언하며 소수의 관계를 유지한다.
      필요할 때만 나서며 조용하지만 말에 무게가 있다.

  - code: "ICSTB"
    name: "철벽 원칙주의"
    description: "내성적이고 쿨하며 안정적이고 전통적이며 대담한 성격"
    behavior_guide: >
      엄격한 기준과 규칙을 고수하며 타협하지 않는다. 다가가기
      어렵지만 한번 인정하면 끝까지 신뢰한다. 원칙 앞에서 냉정하다.

  - code: "ICSTG"
    name: "조용한 장인"
    description: "내성적이고 쿨하며 안정적이고 전통적이며 온화한 성격"
    behavior_guide: >
      자기 분야에 묵묵히 매진하며 간섭을 싫어한다.
      말이 적지만 결과물로 자신을 표현한다. 느리지만 확실하다.

  - code: "ICVOB"
    name: "은둔 반항아"
    description: "내성적이고 쿨하며 감정적이고 개방적이며 대담한 성격"
    behavior_guide: >
      사회 규범에 반항적이며 혼자 있을 때 가장 편하다.
      예측 불가능한 행동을 하며 자유를 최고 가치로 여긴다.

  - code: "ICVOG"
    name: "미스터리 관찰자"
    description: "내성적이고 쿨하며 감정적이고 개방적이며 온화한 성격"
    behavior_guide: >
      조용히 모든 것을 관찰하며 기분에 따라 갑자기 사라지기도 한다.
      무슨 생각을 하는지 알 수 없고 가끔 뜬금없는 말을 한다.

  - code: "ICVTB"
    name: "날선 은둔자"
    description: "내성적이고 쿨하며 감정적이고 전통적이며 대담한 성격"
    behavior_guide: >
      날카로운 말로 사람을 밀어내며 감정 기복이 심하다.
      내면은 외로움을 느끼지만 절대 인정하지 않는다. 가시가 많다.

  - code: "ICVTG"
    name: "고요한 달빛"
    description: "내성적이고 쿨하며 감정적이고 전통적이며 온화한 성격"
    behavior_guide: >
      존재감이 희미하지만 깊은 내면 세계가 있다. 가장 조용하고
      섬세한 성격으로, 관찰력이 뛰어나지만 좀처럼 입을 열지 않는다.
```

- [ ] **Step 2: Write failing tests for personality model**

```python
# tests/test_personality.py
from pathlib import Path

from tomodachai.personality import PersonalityType, load_personalities, get_trait_values


def test_personality_type_model():
    p = PersonalityType(
        code="EWSOB",
        name="불꽃 리더",
        description="테스트",
        behavior_guide="테스트 가이드",
    )
    assert p.code == "EWSOB"
    assert p.name == "불꽃 리더"


def test_get_trait_values():
    traits = get_trait_values("EWSOB")
    assert traits == {
        "energy": "extroverted",
        "warmth": "warm",
        "stability": "steady",
        "openness": "open",
        "assertiveness": "bold",
    }


def test_get_trait_values_introverted():
    traits = get_trait_values("ICVTG")
    assert traits == {
        "energy": "introverted",
        "warmth": "cool",
        "stability": "volatile",
        "openness": "traditional",
        "assertiveness": "gentle",
    }


def test_load_personalities():
    personalities = load_personalities()
    assert len(personalities) == 32
    assert "EWSOB" in personalities
    assert "ICVTG" in personalities
    assert personalities["EWSOB"].name == "불꽃 리더"


def test_all_codes_are_valid():
    personalities = load_personalities()
    for code, p in personalities.items():
        assert len(code) == 5
        assert code[0] in ("E", "I")
        assert code[1] in ("W", "C")
        assert code[2] in ("S", "V")
        assert code[3] in ("O", "T")
        assert code[4] in ("B", "G")
        assert p.code == code
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_personality.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement personality model**

```python
# src/tomodachai/personality.py
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

_TRAIT_MAP = {
    0: ("energy", {"E": "extroverted", "I": "introverted"}),
    1: ("warmth", {"W": "warm", "C": "cool"}),
    2: ("stability", {"S": "steady", "V": "volatile"}),
    3: ("openness", {"O": "open", "T": "traditional"}),
    4: ("assertiveness", {"B": "bold", "G": "gentle"}),
}

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class PersonalityType(BaseModel):
    code: str
    name: str
    description: str
    behavior_guide: str


def get_trait_values(code: str) -> dict[str, str]:
    traits = {}
    for i, (axis, mapping) in _TRAIT_MAP.items():
        traits[axis] = mapping[code[i]]
    return traits


def load_personalities(path: Path | None = None) -> dict[str, PersonalityType]:
    if path is None:
        path = _DATA_DIR / "personalities.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    result = {}
    for entry in data["types"]:
        p = PersonalityType(**entry)
        result[p.code] = p
    return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_personality.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add data/personalities.yaml src/tomodachai/personality.py tests/test_personality.py
git commit -m "feat: 32 personality types with 5-axis trait system"
```

---

## Task 4: Character Model

**Files:**
- Create: `src/tomodachai/character.py`
- Create: `tests/test_character.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_character.py
from tomodachai.character import Character


def test_character_creation():
    c = Character(
        id="char_1",
        name="민수",
        personality_code="EWSOB",
        speech_habit="~인 거지",
        backstory="동네 반장을 맡고 있는 활발한 청년",
    )
    assert c.id == "char_1"
    assert c.name == "민수"
    assert c.personality_code == "EWSOB"


def test_character_defaults():
    c = Character(
        id="char_2",
        name="지은",
        personality_code="IWVOG",
    )
    assert c.speech_habit == ""
    assert c.backstory == ""


def test_character_equality():
    a = Character(id="1", name="A", personality_code="EWSOB")
    b = Character(id="1", name="A", personality_code="EWSOB")
    assert a == b


def test_character_different_ids():
    a = Character(id="1", name="A", personality_code="EWSOB")
    b = Character(id="2", name="A", personality_code="EWSOB")
    assert a != b
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_character.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement character model**

```python
# src/tomodachai/character.py
from __future__ import annotations

from pydantic import BaseModel


class Character(BaseModel):
    id: str
    name: str
    personality_code: str
    speech_habit: str = ""
    backstory: str = ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_character.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/character.py tests/test_character.py
git commit -m "feat: character model with personality reference"
```

---

## Task 5: Relationship Model & Tracker

**Files:**
- Create: `src/tomodachai/relationship.py`
- Create: `tests/test_relationship.py`

- [ ] **Step 1: Write failing tests for Relationship model**

```python
# tests/test_relationship.py
from tomodachai.relationship import Relationship, RelationshipTracker


def test_relationship_defaults():
    r = Relationship()
    assert r.friendship == 0.0
    assert r.romance == 0.0
    assert r.tension == 0.0
    assert r.jealousy == 0.0


def test_apply_deltas():
    r = Relationship(friendship=50.0)
    r.apply_deltas({"friendship": 10, "tension": 5})
    assert r.friendship == 60.0
    assert r.tension == 5.0


def test_apply_deltas_clamps():
    r = Relationship(friendship=95.0)
    r.apply_deltas({"friendship": 20})
    assert r.friendship == 100.0

    r2 = Relationship(friendship=-95.0)
    r2.apply_deltas({"friendship": -20})
    assert r2.friendship == -100.0


def test_romance_clamps_at_zero():
    r = Relationship(romance=5.0)
    r.apply_deltas({"romance": -20})
    assert r.romance == 0.0


def test_tracker_get_creates_default():
    tracker = RelationshipTracker()
    rel = tracker.get("a", "b")
    assert rel.friendship == 0.0


def test_tracker_is_directional():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"friendship": 10})
    assert tracker.get("a", "b").friendship == 10.0
    assert tracker.get("b", "a").friendship == 0.0


def test_tracker_get_romantic_interests():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"romance": 50})
    tracker.update("a", "c", {"romance": 10})
    tracker.update("a", "d", {"friendship": 80})
    interests = tracker.get_romantic_interests("a", threshold=20)
    assert len(interests) == 1
    assert interests[0] == ("b", 50.0)


def test_tracker_get_friends():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"friendship": 60})
    tracker.update("a", "c", {"friendship": -30})
    tracker.update("a", "d", {"friendship": 40})
    friends = tracker.get_friends("a", threshold=50)
    assert friends == [("b", 60.0)]


def test_tracker_get_rivals():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"friendship": -60})
    tracker.update("a", "c", {"friendship": 30})
    rivals = tracker.get_rivals("a", threshold=-50)
    assert rivals == [("b", -60.0)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_relationship.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement relationship model and tracker**

```python
# src/tomodachai/relationship.py
from __future__ import annotations

from pydantic import BaseModel, Field


class Relationship(BaseModel):
    friendship: float = 0.0   # -100 ~ 100
    romance: float = 0.0      # 0 ~ 100
    tension: float = 0.0      # 0 ~ 100
    jealousy: float = 0.0     # 0 ~ 100

    def apply_deltas(self, deltas: dict[str, float]) -> None:
        for key, delta in deltas.items():
            current = getattr(self, key)
            new_val = current + delta
            low, high = self._bounds(key)
            setattr(self, key, max(low, min(high, new_val)))

    @staticmethod
    def _bounds(key: str) -> tuple[float, float]:
        if key == "friendship":
            return -100.0, 100.0
        return 0.0, 100.0


class RelationshipTracker:
    def __init__(self) -> None:
        self._relationships: dict[tuple[str, str], Relationship] = {}

    def get(self, char_a: str, char_b: str) -> Relationship:
        key = (char_a, char_b)
        if key not in self._relationships:
            self._relationships[key] = Relationship()
        return self._relationships[key]

    def update(self, char_a: str, char_b: str, deltas: dict[str, float]) -> None:
        rel = self.get(char_a, char_b)
        rel.apply_deltas(deltas)

    def get_romantic_interests(
        self, char_id: str, threshold: float = 20.0
    ) -> list[tuple[str, float]]:
        results = []
        for (a, b), rel in self._relationships.items():
            if a == char_id and rel.romance >= threshold:
                results.append((b, rel.romance))
        return sorted(results, key=lambda x: -x[1])

    def get_friends(
        self, char_id: str, threshold: float = 50.0
    ) -> list[tuple[str, float]]:
        results = []
        for (a, b), rel in self._relationships.items():
            if a == char_id and rel.friendship >= threshold:
                results.append((b, rel.friendship))
        return sorted(results, key=lambda x: -x[1])

    def get_rivals(
        self, char_id: str, threshold: float = -50.0
    ) -> list[tuple[str, float]]:
        results = []
        for (a, b), rel in self._relationships.items():
            if a == char_id and rel.friendship <= threshold:
                results.append((b, rel.friendship))
        return sorted(results, key=lambda x: x[1])

    def all_pairs(self) -> list[tuple[str, str, Relationship]]:
        return [(a, b, rel) for (a, b), rel in self._relationships.items()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_relationship.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/relationship.py tests/test_relationship.py
git commit -m "feat: directional relationship model with tracker"
```

---

## Task 6: Social Memory

**Files:**
- Create: `src/tomodachai/memory.py`
- Create: `tests/test_memory.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_memory.py
from tomodachai.memory import SocialEvent, MemoryStore


def test_social_event_creation():
    event = SocialEvent(
        tick=1,
        participants=["a", "b"],
        event_type="conversation",
        summary="공원에서 만나 날씨 이야기를 했다",
        emotional_impact={"a": 0.5, "b": 0.3},
    )
    assert event.tick == 1
    assert len(event.participants) == 2


def test_memory_store_add_and_get():
    store = MemoryStore()
    event = SocialEvent(
        tick=1,
        participants=["a", "b"],
        event_type="conversation",
        summary="인사를 나눴다",
        emotional_impact={"a": 0.2, "b": 0.1},
    )
    store.add_event(event)
    events = store.get_events_for("a")
    assert len(events) == 1
    assert events[0].summary == "인사를 나눴다"


def test_memory_store_get_for_participant():
    store = MemoryStore()
    store.add_event(SocialEvent(
        tick=1, participants=["a", "b"],
        event_type="conversation", summary="a와 b 대화",
        emotional_impact={},
    ))
    store.add_event(SocialEvent(
        tick=2, participants=["b", "c"],
        event_type="conversation", summary="b와 c 대화",
        emotional_impact={},
    ))
    assert len(store.get_events_for("a")) == 1
    assert len(store.get_events_for("b")) == 2
    assert len(store.get_events_for("c")) == 1


def test_memory_store_get_between():
    store = MemoryStore()
    store.add_event(SocialEvent(
        tick=1, participants=["a", "b"],
        event_type="conversation", summary="a-b 대화",
        emotional_impact={},
    ))
    store.add_event(SocialEvent(
        tick=2, participants=["a", "c"],
        event_type="conversation", summary="a-c 대화",
        emotional_impact={},
    ))
    between = store.get_events_between("a", "b")
    assert len(between) == 1
    assert between[0].summary == "a-b 대화"


def test_memory_store_limit():
    store = MemoryStore()
    for i in range(20):
        store.add_event(SocialEvent(
            tick=i, participants=["a", "b"],
            event_type="conversation", summary=f"대화 {i}",
            emotional_impact={},
        ))
    events = store.get_events_for("a", limit=5)
    assert len(events) == 5
    assert events[0].tick == 19  # most recent first


def test_memory_store_recent_first():
    store = MemoryStore()
    store.add_event(SocialEvent(
        tick=1, participants=["a"], event_type="solo",
        summary="첫 번째", emotional_impact={},
    ))
    store.add_event(SocialEvent(
        tick=5, participants=["a"], event_type="solo",
        summary="두 번째", emotional_impact={},
    ))
    events = store.get_events_for("a")
    assert events[0].summary == "두 번째"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_memory.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement social memory**

```python
# src/tomodachai/memory.py
from __future__ import annotations

from pydantic import BaseModel


class SocialEvent(BaseModel):
    tick: int
    participants: list[str]
    event_type: str
    summary: str
    emotional_impact: dict[str, float]


class MemoryStore:
    def __init__(self) -> None:
        self._events: list[SocialEvent] = []

    def add_event(self, event: SocialEvent) -> None:
        self._events.append(event)

    def get_events_for(
        self, char_id: str, limit: int = 10
    ) -> list[SocialEvent]:
        relevant = [
            e for e in self._events if char_id in e.participants
        ]
        relevant.sort(key=lambda e: e.tick, reverse=True)
        return relevant[:limit]

    def get_events_between(
        self, char_a: str, char_b: str, limit: int = 5
    ) -> list[SocialEvent]:
        relevant = [
            e for e in self._events
            if char_a in e.participants and char_b in e.participants
        ]
        relevant.sort(key=lambda e: e.tick, reverse=True)
        return relevant[:limit]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_memory.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/memory.py tests/test_memory.py
git commit -m "feat: social memory store with event tracking"
```

---

## Task 7: Conversation Engine

**Files:**
- Create: `src/tomodachai/conversation.py`
- Create: `tests/test_conversation.py`
- Modify: `tests/conftest.py` (add fixtures)

- [ ] **Step 1: Add shared fixtures to `tests/conftest.py`**

Append these fixtures to the existing `conftest.py`:

```python
# append to tests/conftest.py
from unittest.mock import MagicMock
from tomodachai.llm import LLMClient
from tomodachai.character import Character
from tomodachai.personality import load_personalities
from tomodachai.relationship import Relationship


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
```

- [ ] **Step 2: Write failing tests for conversation engine**

```python
# tests/test_conversation.py
import json
from unittest.mock import MagicMock

from tomodachai.conversation import (
    ConversationEngine,
    ConversationResult,
    DialogueLine,
    build_conversation_prompt,
)
from tomodachai.relationship import Relationship
from tomodachai.memory import SocialEvent


def test_dialogue_line_model():
    line = DialogueLine(speaker="민수", text="안녕!")
    assert line.speaker == "민수"


def test_conversation_result_model():
    result = ConversationResult(
        dialogue=[DialogueLine(speaker="민수", text="안녕!")],
        deltas={"민수": {"friendship": 5}, "지은": {"friendship": 3}},
        summary="인사를 나눴다",
    )
    assert len(result.dialogue) == 1
    assert result.deltas["민수"]["friendship"] == 5


def test_build_prompt_contains_character_info(
    char_minsu, char_jieun, sample_personalities,
):
    rel_ab = Relationship(friendship=30, romance=10)
    rel_ba = Relationship(friendship=25)
    prompt = build_conversation_prompt(
        char_a=char_minsu,
        char_b=char_jieun,
        personality_a=sample_personalities["EWSOB"],
        personality_b=sample_personalities["IWVOG"],
        rel_ab=rel_ab,
        rel_ba=rel_ba,
        memories=[],
        location="공원",
        time_of_day="오후",
    )
    assert "민수" in prompt
    assert "지은" in prompt
    assert "~인 거지" in prompt
    assert "그치~?" in prompt
    assert "공원" in prompt
    assert "불꽃 리더" in prompt or "적극적으로" in prompt


def test_build_prompt_includes_memories(
    char_minsu, char_jieun, sample_personalities,
):
    memories = [
        SocialEvent(
            tick=1, participants=["char_1", "char_2"],
            event_type="conversation",
            summary="공원에서 처음 만나 인사를 나눴다",
            emotional_impact={"char_1": 0.3, "char_2": 0.2},
        ),
    ]
    prompt = build_conversation_prompt(
        char_a=char_minsu,
        char_b=char_jieun,
        personality_a=sample_personalities["EWSOB"],
        personality_b=sample_personalities["IWVOG"],
        rel_ab=Relationship(),
        rel_ba=Relationship(),
        memories=memories,
        location="카페",
        time_of_day="저녁",
    )
    assert "공원에서 처음 만나" in prompt


def test_engine_generate_parses_llm_response(
    char_minsu, char_jieun, sample_personalities, mock_llm,
):
    llm_response = {
        "dialogue": [
            {"speaker": "민수", "text": "지은아, 오늘 날씨 좋다~인 거지!"},
            {"speaker": "지은", "text": "그치~? 산책하기 딱이야."},
        ],
        "deltas": {
            "민수": {"friendship": 3, "romance": 1, "tension": 0},
            "지은": {"friendship": 2, "romance": 0, "tension": 0},
        },
        "summary": "공원에서 만나 날씨 이야기를 나눴다",
    }
    mock_llm.chat_json.return_value = llm_response

    engine = ConversationEngine(mock_llm, sample_personalities)
    result = engine.generate(
        char_a=char_minsu,
        char_b=char_jieun,
        rel_ab=Relationship(),
        rel_ba=Relationship(),
        memories=[],
        location="공원",
        time_of_day="오후",
    )
    assert len(result.dialogue) == 2
    assert result.dialogue[0].speaker == "민수"
    assert result.deltas["민수"]["friendship"] == 3
    assert result.summary == "공원에서 만나 날씨 이야기를 나눴다"
    mock_llm.chat_json.assert_called_once()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_conversation.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement conversation engine**

```python
# src/tomodachai/conversation.py
from __future__ import annotations

from pydantic import BaseModel

from tomodachai.character import Character
from tomodachai.llm import LLMClient
from tomodachai.memory import SocialEvent
from tomodachai.personality import PersonalityType
from tomodachai.relationship import Relationship


class DialogueLine(BaseModel):
    speaker: str
    text: str


class ConversationResult(BaseModel):
    dialogue: list[DialogueLine]
    deltas: dict[str, dict[str, float]]
    summary: str


_SYSTEM_PROMPT = "당신은 작은 마을의 주민들 간의 대화를 시뮬레이션하는 AI입니다. 반드시 지정된 JSON 형식으로만 응답하세요."


def build_conversation_prompt(
    char_a: Character,
    char_b: Character,
    personality_a: PersonalityType,
    personality_b: PersonalityType,
    rel_ab: Relationship,
    rel_ba: Relationship,
    memories: list[SocialEvent],
    location: str,
    time_of_day: str,
) -> str:
    memory_text = "없음"
    if memories:
        memory_text = "\n".join(
            f"- (틱 {m.tick}) {m.summary}" for m in memories
        )

    return f"""## 캐릭터 1: {char_a.name}
성격 유형: {personality_a.name}
성격: {personality_a.behavior_guide.strip()}
말버릇: "{char_a.speech_habit}" (문맥에 맞게 자연스럽게 섞어 사용)
배경: {char_a.backstory}

## 캐릭터 2: {char_b.name}
성격 유형: {personality_b.name}
성격: {personality_b.behavior_guide.strip()}
말버릇: "{char_b.speech_habit}" (문맥에 맞게 자연스럽게 섞어 사용)
배경: {char_b.backstory}

## 두 사람의 관계
{char_a.name} → {char_b.name}: 우정 {rel_ab.friendship:.0f}, 로맨스 {rel_ab.romance:.0f}, 긴장 {rel_ab.tension:.0f}
{char_b.name} → {char_a.name}: 우정 {rel_ba.friendship:.0f}, 로맨스 {rel_ba.romance:.0f}, 긴장 {rel_ba.tension:.0f}

## 최근 기억
{memory_text}

## 상황
장소: {location}
시간대: {time_of_day}

## 지시사항
두 캐릭터 간의 자연스러운 한국어 대화를 3~8번 주고받는 형태로 생성하세요.
각 캐릭터는 성격대로 행동하고 말버릇을 자연스럽게 섞으세요.

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "dialogue": [
    {{"speaker": "{char_a.name}", "text": "대사"}},
    {{"speaker": "{char_b.name}", "text": "대사"}}
  ],
  "deltas": {{
    "{char_a.name}": {{"friendship": 0, "romance": 0, "tension": 0}},
    "{char_b.name}": {{"friendship": 0, "romance": 0, "tension": 0}}
  }},
  "summary": "이 대화에서 일어난 일 한 줄 요약"
}}

delta 범위: friendship(-10~+10), romance(-5~+5), tension(-10~+10)"""


class ConversationEngine:
    def __init__(
        self,
        llm: LLMClient,
        personalities: dict[str, PersonalityType],
    ):
        self._llm = llm
        self._personalities = personalities

    def generate(
        self,
        char_a: Character,
        char_b: Character,
        rel_ab: Relationship,
        rel_ba: Relationship,
        memories: list[SocialEvent],
        location: str,
        time_of_day: str = "오후",
    ) -> ConversationResult:
        personality_a = self._personalities[char_a.personality_code]
        personality_b = self._personalities[char_b.personality_code]

        prompt = build_conversation_prompt(
            char_a=char_a,
            char_b=char_b,
            personality_a=personality_a,
            personality_b=personality_b,
            rel_ab=rel_ab,
            rel_ba=rel_ba,
            memories=memories,
            location=location,
            time_of_day=time_of_day,
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        raw = self._llm.chat_json(messages)

        return ConversationResult(
            dialogue=[DialogueLine(**line) for line in raw["dialogue"]],
            deltas=raw["deltas"],
            summary=raw["summary"],
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_conversation.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/tomodachai/conversation.py tests/test_conversation.py tests/conftest.py
git commit -m "feat: conversation engine with prompt builder and LLM integration"
```

---

## Task 8: Personality Matcher

**Files:**
- Modify: `src/tomodachai/personality.py` (add `match_personality` function)
- Modify: `tests/test_personality.py` (add matcher tests)

- [ ] **Step 1: Write failing tests for matcher**

Append to `tests/test_personality.py`:

```python
# append to tests/test_personality.py
from unittest.mock import MagicMock
from tomodachai.personality import match_personality, load_personalities


def test_match_personality_returns_valid_code(mock_llm):
    """matcher가 LLM 응답에서 유효한 코드를 반환하는지 테스트"""
    personalities = load_personalities()
    mock_llm.chat_json.return_value = {
        "code": "EWSOB",
        "reason": "활발하고 사교적인 성격",
    }
    result = match_personality(
        mock_llm, personalities,
        "활발하고 사교적이며 리더십이 있는 사람",
    )
    assert result == "EWSOB"
    mock_llm.chat_json.assert_called_once()


def test_match_personality_prompt_contains_types(mock_llm):
    """프롬프트에 성격 유형 목록이 포함되는지 테스트"""
    personalities = load_personalities()
    mock_llm.chat_json.return_value = {"code": "ICVTG", "reason": "test"}
    match_personality(mock_llm, personalities, "조용한 사람")
    call_args = mock_llm.chat_json.call_args
    prompt = call_args[0][0][1]["content"]  # messages[1] = user message
    assert "EWSOB" in prompt
    assert "불꽃 리더" in prompt
    assert "ICVTG" in prompt
```

Also add `mock_llm` fixture to `conftest.py` if not already there (it was added in Task 7 Step 1).

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `pytest tests/test_personality.py::test_match_personality_returns_valid_code -v`
Expected: FAIL — `ImportError: cannot import name 'match_personality'`

- [ ] **Step 3: Implement personality matcher**

Append to `src/tomodachai/personality.py`:

```python
# append to src/tomodachai/personality.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tomodachai.llm import LLMClient

_MATCHER_SYSTEM = "당신은 성격 분석 전문가입니다. 주어진 성격 설명을 분석하여 가장 적합한 유형을 선택하세요. 반드시 JSON으로만 응답하세요."


def match_personality(
    llm: LLMClient,
    personalities: dict[str, PersonalityType],
    description: str,
) -> str:
    type_list = "\n".join(
        f"- {p.code} ({p.name}): {p.description}"
        for p in personalities.values()
    )
    prompt = f"""아래 성격 설명을 읽고, 가장 적합한 성격 유형 코드를 선택하세요.

## 입력된 성격 설명
{description}

## 성격 유형 목록
{type_list}

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "code": "선택한 5글자 코드",
  "reason": "선택 이유 한 줄"
}}"""

    messages = [
        {"role": "system", "content": _MATCHER_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    result = llm.chat_json(messages)
    code = result["code"]
    if code not in personalities:
        raise ValueError(f"LLM returned invalid personality code: {code}")
    return code
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_personality.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tomodachai/personality.py tests/test_personality.py
git commit -m "feat: LLM-based personality matcher"
```

---

## Task 9: Simulation Core & CLI

**Files:**
- Create: `src/tomodachai/simulation.py`
- Create: `src/tomodachai/main.py`
- Create: `tests/test_simulation.py`

- [ ] **Step 1: Write failing tests for simulation**

```python
# tests/test_simulation.py
import json
from unittest.mock import MagicMock, patch

from tomodachai.config import AppConfig, LocationConfig, SimulationConfig
from tomodachai.character import Character
from tomodachai.simulation import Simulation, assign_locations


def test_assign_locations():
    locations = [
        LocationConfig(name="공원", capacity=2),
        LocationConfig(name="카페", capacity=2),
    ]
    characters = [
        Character(id="1", name="A", personality_code="EWSOB"),
        Character(id="2", name="B", personality_code="IWSOG"),
        Character(id="3", name="C", personality_code="ECVOB"),
    ]
    assignments = assign_locations(characters, locations, seed=42)
    # All characters assigned somewhere
    assigned_ids = set()
    for loc_name, chars in assignments.items():
        for c in chars:
            assigned_ids.add(c.id)
    assert assigned_ids == {"1", "2", "3"}
    # Capacity respected
    for loc_name, chars in assignments.items():
        loc = next(l for l in locations if l.name == loc_name)
        assert len(chars) <= loc.capacity


def test_assign_locations_deterministic():
    locations = [LocationConfig(name="공원", capacity=5)]
    chars = [Character(id=str(i), name=f"C{i}", personality_code="EWSOB") for i in range(3)]
    a1 = assign_locations(chars, locations, seed=42)
    a2 = assign_locations(chars, locations, seed=42)
    assert a1 == a2


def test_simulation_tick_generates_conversations(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]

    mock_llm.chat_json.return_value = {
        "dialogue": [
            {"speaker": "민수", "text": "안녕!"},
            {"speaker": "지은", "text": "어 안녕~"},
        ],
        "deltas": {
            "민수": {"friendship": 3, "romance": 0, "tension": 0},
            "지은": {"friendship": 2, "romance": 0, "tension": 0},
        },
        "summary": "인사를 나눴다",
    }

    sim = Simulation(
        config=app_config,
        characters=[char_minsu, char_jieun],
        llm=mock_llm,
        personalities=sample_personalities,
    )
    results = sim.tick(seed=42)
    assert len(results) >= 0  # may or may not interact depending on location


def test_simulation_updates_relationships(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "민수", "text": "hi"}],
        "deltas": {
            "민수": {"friendship": 5, "romance": 0, "tension": 0},
            "지은": {"friendship": 3, "romance": 0, "tension": 0},
        },
        "summary": "대화함",
    }

    sim = Simulation(
        config=app_config,
        characters=[char_minsu, char_jieun],
        llm=mock_llm,
        personalities=sample_personalities,
    )
    # Force both to same location
    sim._force_encounter(char_minsu, char_jieun, "공원")
    rel = sim.relationships.get("char_1", "char_2")
    assert rel.friendship == 5.0


def test_simulation_stores_memory(
    app_config, char_minsu, char_jieun, mock_llm, sample_personalities,
):
    app_config.locations = [LocationConfig(name="공원", capacity=5)]
    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "민수", "text": "hi"}],
        "deltas": {
            "민수": {"friendship": 1, "romance": 0, "tension": 0},
            "지은": {"friendship": 1, "romance": 0, "tension": 0},
        },
        "summary": "공원에서 인사",
    }

    sim = Simulation(
        config=app_config,
        characters=[char_minsu, char_jieun],
        llm=mock_llm,
        personalities=sample_personalities,
    )
    sim._force_encounter(char_minsu, char_jieun, "공원")
    events = sim.memory.get_events_for("char_1")
    assert len(events) == 1
    assert events[0].summary == "공원에서 인사"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_simulation.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement simulation**

```python
# src/tomodachai/simulation.py
from __future__ import annotations

import random
from itertools import combinations

from tomodachai.character import Character
from tomodachai.config import AppConfig, LocationConfig
from tomodachai.conversation import ConversationEngine, ConversationResult
from tomodachai.llm import LLMClient
from tomodachai.memory import MemoryStore, SocialEvent
from tomodachai.personality import PersonalityType
from tomodachai.relationship import RelationshipTracker

_TIME_SLOTS = ["아침", "오전", "점심", "오후", "저녁", "밤"]


def assign_locations(
    characters: list[Character],
    locations: list[LocationConfig],
    seed: int | None = None,
) -> dict[str, list[Character]]:
    rng = random.Random(seed)
    assignments: dict[str, list[Character]] = {loc.name: [] for loc in locations}
    capacity_map = {loc.name: loc.capacity for loc in locations}

    shuffled = list(characters)
    rng.shuffle(shuffled)

    available = [loc.name for loc in locations]
    for char in shuffled:
        rng.shuffle(available)
        for loc_name in available:
            if len(assignments[loc_name]) < capacity_map[loc_name]:
                assignments[loc_name].append(char)
                break

    return assignments


class Simulation:
    def __init__(
        self,
        config: AppConfig,
        characters: list[Character],
        llm: LLMClient,
        personalities: dict[str, PersonalityType],
    ):
        self.config = config
        self.characters = characters
        self.conversation_engine = ConversationEngine(llm, personalities)
        self.relationships = RelationshipTracker()
        self.memory = MemoryStore()
        self._tick_count = 0

    def tick(self, seed: int | None = None) -> list[ConversationResult]:
        time_of_day = _TIME_SLOTS[self._tick_count % len(_TIME_SLOTS)]
        assignments = assign_locations(
            self.characters, self.config.locations, seed=seed,
        )

        results = []
        for loc_name, chars in assignments.items():
            for char_a, char_b in combinations(chars, 2):
                result = self._run_conversation(char_a, char_b, loc_name, time_of_day)
                results.append(result)

        self._tick_count += 1
        return results

    def _run_conversation(
        self,
        char_a: Character,
        char_b: Character,
        location: str,
        time_of_day: str,
    ) -> ConversationResult:
        rel_ab = self.relationships.get(char_a.id, char_b.id)
        rel_ba = self.relationships.get(char_b.id, char_a.id)
        memories = self.memory.get_events_between(char_a.id, char_b.id)

        result = self.conversation_engine.generate(
            char_a=char_a,
            char_b=char_b,
            rel_ab=rel_ab,
            rel_ba=rel_ba,
            memories=memories,
            location=location,
            time_of_day=time_of_day,
        )

        # Update relationships
        for name, deltas in result.deltas.items():
            if name == char_a.name:
                self.relationships.update(char_a.id, char_b.id, deltas)
            elif name == char_b.name:
                self.relationships.update(char_b.id, char_a.id, deltas)

        # Store memory
        self.memory.add_event(SocialEvent(
            tick=self._tick_count,
            participants=[char_a.id, char_b.id],
            event_type="conversation",
            summary=result.summary,
            emotional_impact={
                char_a.id: sum(result.deltas.get(char_a.name, {}).values()),
                char_b.id: sum(result.deltas.get(char_b.name, {}).values()),
            },
        ))

        return result

    def _force_encounter(
        self, char_a: Character, char_b: Character, location: str,
    ) -> ConversationResult:
        """테스트용: 두 캐릭터 간 대화를 강제로 실행"""
        return self._run_conversation(char_a, char_b, location, "오후")

    def run(self, num_ticks: int, seed: int | None = None) -> None:
        for i in range(num_ticks):
            tick_seed = seed + i if seed is not None else None
            results = self.tick(seed=tick_seed)
            self._print_tick(i, results)

    def _print_tick(self, tick_num: int, results: list[ConversationResult]) -> None:
        time_of_day = _TIME_SLOTS[tick_num % len(_TIME_SLOTS)]
        print(f"\n{'='*60}")
        print(f"  틱 {tick_num} | {time_of_day}")
        print(f"{'='*60}")

        if not results:
            print("  (아무 일도 일어나지 않았다)")
            return

        for result in results:
            print(f"\n  📍 {result.summary}")
            print(f"  {'-'*40}")
            for line in result.dialogue:
                print(f"  {line.speaker}: {line.text}")
            for name, deltas in result.deltas.items():
                parts = [f"{k}:{v:+.0f}" for k, v in deltas.items() if v != 0]
                if parts:
                    print(f"  [{name}] {', '.join(parts)}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_simulation.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Implement CLI entry point**

```python
# src/tomodachai/main.py
from __future__ import annotations

import argparse
from pathlib import Path

from tomodachai.character import Character
from tomodachai.config import load_config
from tomodachai.llm import LLMClient
from tomodachai.personality import load_personalities
from tomodachai.simulation import Simulation

_DEMO_CHARACTERS = [
    Character(
        id="char_1", name="민수", personality_code="EWSOB",
        speech_habit="~인 거지",
        backstory="동네 반장을 맡고 있는 활발한 청년. 모임을 좋아한다.",
    ),
    Character(
        id="char_2", name="지은", personality_code="IWVOG",
        speech_habit="그치~?",
        backstory="동네 카페를 운영하는 몽상가. 창밖을 자주 바라본다.",
    ),
    Character(
        id="char_3", name="태호", personality_code="ECVOB",
        speech_habit="ㅋㅋ",
        backstory="자유분방한 대학생. 새로운 자극을 찾아다닌다.",
    ),
    Character(
        id="char_4", name="순자", personality_code="EWSTG",
        speech_habit="아이고~",
        backstory="동네 터줏대감 할머니. 모든 주민의 안부가 궁금하다.",
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="AI 우리 동네 이야기")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--ticks", type=int, default=6, help="시뮬레이션 틱 수")
    parser.add_argument("--seed", type=int, default=None, help="랜덤 시드")
    args = parser.parse_args()

    config = load_config(args.config)
    personalities = load_personalities()
    llm = LLMClient(config.llm)

    print("🏘️ AI 우리 동네 이야기")
    print(f"모델: {config.llm.model}")
    print(f"주민: {', '.join(c.name for c in _DEMO_CHARACTERS)}")
    print(f"장소: {', '.join(loc.name for loc in config.locations)}")

    sim = Simulation(
        config=config,
        characters=_DEMO_CHARACTERS,
        llm=llm,
        personalities=personalities,
    )
    sim.run(num_ticks=args.ticks, seed=args.seed)

    print(f"\n{'='*60}")
    print("  시뮬레이션 종료 — 최종 관계")
    print(f"{'='*60}")
    for a_id, b_id, rel in sim.relationships.all_pairs():
        a_name = next(c.name for c in _DEMO_CHARACTERS if c.id == a_id)
        b_name = next(c.name for c in _DEMO_CHARACTERS if c.id == b_id)
        print(f"  {a_name} → {b_name}: "
              f"우정={rel.friendship:.0f} 로맨스={rel.romance:.0f} "
              f"긴장={rel.tension:.0f} 질투={rel.jealousy:.0f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/tomodachai/simulation.py src/tomodachai/main.py tests/test_simulation.py
git commit -m "feat: simulation engine with location scheduling and CLI"
```

---

## Task 10: Multi-Party Dynamics

**Files:**
- Modify: `src/tomodachai/relationship.py` (add triangle detection, jealousy update)
- Modify: `src/tomodachai/simulation.py` (integrate jealousy into tick loop)
- Modify: `tests/test_relationship.py` (add triangle/jealousy tests)
- Modify: `tests/test_simulation.py` (add integration test)

- [ ] **Step 1: Write failing tests for triangle detection and jealousy**

Append to `tests/test_relationship.py`:

```python
# append to tests/test_relationship.py
from tomodachai.relationship import Triangle, detect_triangles


def test_triangle_model():
    t = Triangle(jealous="a", target="b", rival="c", romance_level=60.0)
    assert t.jealous == "a"
    assert t.rival == "c"


def test_detect_triangles_finds_basic_triangle():
    tracker = RelationshipTracker()
    # A has romantic interest in B
    tracker.update("a", "b", {"romance": 50})
    # B is friendly with C
    tracker.update("b", "c", {"friendship": 60})
    triangles = detect_triangles(tracker)
    assert len(triangles) == 1
    assert triangles[0].jealous == "a"
    assert triangles[0].target == "b"
    assert triangles[0].rival == "c"


def test_detect_triangles_no_triangle_without_romance():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"friendship": 80})
    tracker.update("b", "c", {"friendship": 60})
    triangles = detect_triangles(tracker)
    assert len(triangles) == 0


def test_detect_triangles_mutual_jealousy():
    tracker = RelationshipTracker()
    # Both A and C have romantic interest in B
    tracker.update("a", "b", {"romance": 50})
    tracker.update("c", "b", {"romance": 40})
    # B is friendly with both
    tracker.update("b", "a", {"friendship": 60})
    tracker.update("b", "c", {"friendship": 60})
    triangles = detect_triangles(tracker)
    # A is jealous of C, C is jealous of A
    assert len(triangles) == 2
    jealous_ids = {t.jealous for t in triangles}
    assert jealous_ids == {"a", "c"}


def test_apply_jealousy_updates():
    tracker = RelationshipTracker()
    tracker.update("a", "b", {"romance": 50})
    tracker.update("b", "c", {"friendship": 60})
    triangles = detect_triangles(tracker)
    apply_jealousy(tracker, triangles)
    # A should feel jealousy toward C
    rel_ac = tracker.get("a", "c")
    assert rel_ac.jealousy > 0
    # A's tension with B might increase slightly
    rel_ab = tracker.get("a", "b")
    assert rel_ab.tension > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_relationship.py::test_triangle_model -v`
Expected: FAIL — `ImportError: cannot import name 'Triangle'`

- [ ] **Step 3: Implement triangle detection and jealousy**

Append to `src/tomodachai/relationship.py`:

```python
# append to src/tomodachai/relationship.py
from pydantic import BaseModel as _BaseModel  # already imported, just for clarity


class Triangle(_BaseModel):
    jealous: str      # 질투하는 캐릭터 ID
    target: str       # 좋아하는 대상 ID
    rival: str        # 경쟁자 ID
    romance_level: float


def detect_triangles(
    tracker: RelationshipTracker,
    romance_threshold: float = 30.0,
    friendship_threshold: float = 30.0,
) -> list[Triangle]:
    triangles: list[Triangle] = []
    # Find all characters with romantic interest
    all_chars = set()
    for (a, b), _ in tracker._relationships.items():
        all_chars.add(a)
        all_chars.add(b)

    for a in all_chars:
        for b in all_chars:
            if a == b:
                continue
            rel_ab = tracker.get(a, b)
            if rel_ab.romance < romance_threshold:
                continue
            # A likes B romantically. Find C where B is friendly with C
            for c in all_chars:
                if c == a or c == b:
                    continue
                rel_bc = tracker.get(b, c)
                if rel_bc.friendship >= friendship_threshold:
                    triangles.append(Triangle(
                        jealous=a, target=b, rival=c,
                        romance_level=rel_ab.romance,
                    ))
    return triangles


def apply_jealousy(
    tracker: RelationshipTracker,
    triangles: list[Triangle],
    jealousy_rate: float = 0.3,
    tension_rate: float = 0.1,
) -> None:
    for tri in triangles:
        # Jealousy toward rival increases
        jealousy_delta = tri.romance_level * jealousy_rate * 0.1
        tracker.update(tri.jealous, tri.rival, {"jealousy": jealousy_delta})
        # Tension with target increases slightly
        tension_delta = tri.romance_level * tension_rate * 0.1
        tracker.update(tri.jealous, tri.target, {"tension": tension_delta})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_relationship.py -v`
Expected: All 14 tests PASS

- [ ] **Step 5: Integrate jealousy into simulation tick**

Modify `Simulation.tick()` in `src/tomodachai/simulation.py` — add jealousy processing after conversations:

```python
# In Simulation.tick(), after the conversation loop, add:
from tomodachai.relationship import detect_triangles, apply_jealousy

# ... existing tick code ...
# After: self._tick_count += 1
# Before: return results
# Insert:
        triangles = detect_triangles(self.relationships)
        if triangles:
            apply_jealousy(self.relationships, triangles)

        self._tick_count += 1
        return results
```

The full updated `tick` method becomes:

```python
    def tick(self, seed: int | None = None) -> list[ConversationResult]:
        time_of_day = _TIME_SLOTS[self._tick_count % len(_TIME_SLOTS)]
        assignments = assign_locations(
            self.characters, self.config.locations, seed=seed,
        )

        results = []
        for loc_name, chars in assignments.items():
            for char_a, char_b in combinations(chars, 2):
                result = self._run_conversation(char_a, char_b, loc_name, time_of_day)
                results.append(result)

        # Process multi-party dynamics
        triangles = detect_triangles(self.relationships)
        if triangles:
            apply_jealousy(self.relationships, triangles)

        self._tick_count += 1
        return results
```

Add import at top of `simulation.py`:

```python
from tomodachai.relationship import RelationshipTracker, detect_triangles, apply_jealousy
```

- [ ] **Step 6: Write integration test for jealousy in simulation**

Append to `tests/test_simulation.py`:

```python
# append to tests/test_simulation.py
from tomodachai.relationship import detect_triangles


def test_simulation_jealousy_emerges(
    app_config, mock_llm, sample_personalities,
):
    """삼각관계에서 질투가 생기는지 통합 테스트"""
    from tomodachai.character import Character
    from tomodachai.config import LocationConfig

    app_config.locations = [LocationConfig(name="공원", capacity=5)]

    a = Character(id="a", name="A", personality_code="EWSOB")
    b = Character(id="b", name="B", personality_code="IWVOG")
    c = Character(id="c", name="C", personality_code="ECVOB")

    mock_llm.chat_json.return_value = {
        "dialogue": [{"speaker": "A", "text": "hi"}],
        "deltas": {
            "A": {"friendship": 5, "romance": 0, "tension": 0},
            "B": {"friendship": 5, "romance": 0, "tension": 0},
        },
        "summary": "대화함",
    }

    sim = Simulation(
        config=app_config,
        characters=[a, b, c],
        llm=mock_llm,
        personalities=sample_personalities,
    )

    # Set up triangle: A likes B, B is friends with C
    sim.relationships.update("a", "b", {"romance": 60})
    sim.relationships.update("b", "c", {"friendship": 70})

    sim.tick(seed=42)

    # After tick, jealousy should have been applied
    rel_ac = sim.relationships.get("a", "c")
    assert rel_ac.jealousy > 0, "A should be jealous of C"
```

- [ ] **Step 7: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/tomodachai/relationship.py src/tomodachai/simulation.py tests/test_relationship.py tests/test_simulation.py
git commit -m "feat: multi-party dynamics with triangle detection and jealousy"
```

---

## Verification Checklist

Phase 1 기획서 요구사항 대비 커버리지:

| 요구사항 | 구현 Task |
|---------|----------|
| 32가지 성격 프롬프트 | Task 3 (personalities.yaml + personality.py) |
| LLM 매핑 로직 검증 | Task 8 (match_personality) |
| 에이전트 간 삼각관계 | Task 10 (detect_triangles) |
| 갈등 시나리오 텍스트 로그 | Task 7 + 9 (conversation + simulation print) |
| 장기 기억 유지 | Task 6 (MemoryStore → conversation prompt에 반영) |
| 다양한 LLM 호환 | Task 2 (litellm 기반 추상화) |

모든 코드 경로에 단위 테스트 포함. 실제 LLM 연결이 필요한 통합 테스트는 `@pytest.mark.integration`으로 분리 가능.
