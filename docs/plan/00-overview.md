# AI-Powered 관찰형 시뮬레이션 게임 프로젝트 계획서
(가칭: AI 우리 동네 이야기)

> **📝 Note:** 이 문서는 실제 구현을 위한 **기획서**입니다. ⚠️ 표시는 원본 게임 리서치가 필요한 항목입니다.

## 1. 개요 및 기획 의도
*   **모티브:** 닌텐도 'トモダチコレクション(Tomodachi Collection, NDS)'을 기반으로, 후속작(Tomodachi Life, Living the Dream)에서 좋아보이는 요소들을 선별 채용 + 최신 AI 기술
*   **배경 컨셉:** 평범하고 정겨운 **'도시 또는 마을'**. 캐릭터는 전부 성인으로 통일. 분수대, 식료품점, 공원 등에서 자연스럽게 어우러지는 공간.
*   **핵심 재미:** 독립적인 AI 뇌를 가진 캐릭터(에이전트)들이 스스로 맺는 복잡한 인간관계(우정, 사랑, 질투, 갈등)를 관찰하고 가끔 개입하는 즐거움.
*   **AI 도입의 목적:** 정해진 스크립트를 탈피하여, 캐릭터 간의 서사와 관계의 깊이를 실시간으로 생성.

## 2. 시스템 아키텍처 (Client-Server 구조)
*   **프론트엔드 (Web 기반):** 브라우저 탭으로 가볍게 띄워두고 관찰하는 "서브 게임" 포지셔닝. PC에서는 탭으로 상주, 모바일 브라우저에서도 접근 가능해야 함.
    *   **그래픽:** 3D 로우폴리 (원작과 유사한 방향). 에셋 제작: 블렌더 MCP.
    *   **프레임워크 후보:**
        *   **Three.js (유력):** 3D 로우폴리 렌더링, 웹 기반.
        *   **Godot Engine:** 3D 지원 + 게임 엔진 기능 풍부. 웹 export 가능.
    *   ~~(기존안) Phaser — 2D 도트 방향일 경우 재검토.~~
    *   **반응형/모바일 대응:** 데스크탑과 모바일 양쪽에서 플레이 가능하도록 반응형 레이아웃 필수.
*   **백엔드 (Python + FastAPI):** 에이전트의 '뇌' 역할. LLM을 통해 대사 및 행동 결정. LLM 프레임워크는 미정 (LangGraph 검토 중, Phase 1에서는 litellm으로 프로토타이핑).
*   **LLM 연결:** BYOK(Bring Your Own Key) 및 로컬 LLM(Ollama 등) 지원.

## 3. 비고
*   저작권 이슈를 고려하여 개인 소장 및 지인 배포용으로 개발.
*   실행 편의를 위해 향후 파이썬 서버의 클라우드 호스팅 옵션 고려.

## 문서 구조
| 문서 | 내용 |
|------|------|
| [01-character.md](01-character.md) | 캐릭터 생성, 성격, 미니개성, 말버릇, 별명 |
| [02-relationship.md](02-relationship.md) | 관계 시스템, 싸움, 질투, 가드레일 |
| [03-space-and-events.md](03-space-and-events.md) | 공간, 시간, 공동구역 이벤트, 병맛요소 |
| [04-ai-system.md](04-ai-system.md) | AI 자율성, LLM 호출 전략, AI생성 콘텐츠 |
| [05-player.md](05-player.md) | 플레이어 개입, 아이템, 펫 |
| [06-milestones.md](06-milestones.md) | 마일스톤 |
| [07-research.md](07-research.md) | 리서치 결과 아카이브 |
| [09-save-system.md](09-save-system.md) | 세이브 시스템 |
| [10-shop-system.md](10-shop-system.md) | 상점 시스템 |
| [11-onboarding.md](11-onboarding.md) | 온보딩 |
| [12-ui-settings.md](12-ui-settings.md) | UI/UX & 설정 |
| [13-llm-usage.md](13-llm-usage.md) | LLM 사용 범위 |
