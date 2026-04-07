# Tomodachai

AI 기반 관찰형 시뮬레이션 게임 프로토타입.

## 기술 스택
- **언어:** Python 3.11+
- **LLM:** litellm (추상화), claude-cli, codex-cli 지원. 기본 타겟: 로컬 Ollama
- **프레임워크:** pydantic (데이터 모델), pyyaml (설정)
- **테스트:** pytest, pytest-mock
- **린트/포맷:** ruff

## 명령어

```bash
# 린트 검사
ruff check src/ tests/

# 린트 자동 수정
ruff check --fix src/ tests/

# 포맷 검사
ruff format --check src/ tests/

# 포맷 적용
ruff format src/ tests/

# 테스트
pytest tests/ -v

# 시뮬레이션 실행
python -m tomodachai.main --ticks 6
```

## 규칙
- [Git 작업 규칙](docs/git-rules.md) — force push 전 리모트 확인 필수
- 기획서: [docs/plan/](docs/plan/) 참조
