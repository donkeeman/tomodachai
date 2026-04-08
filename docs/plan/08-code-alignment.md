# 코드 ↔ 기획서 정렬 명세

기획서 기준으로 코드를 수정해야 하는 항목을 파일별로 정리합니다.
코드 리팩토링(Phase 1→기획서 정렬)은 일부 완료됨. 아래는 **현재 코드 대비 아직 미반영된 기획서 내용**.

---

## 1. `data/personalities.yaml` — 한국 공식명 반영

- [ ] 16가지 유형에 한국 공식명 반영 (안정파/사교파/주도파/신중파 × 4형)
- [ ] 각 유형의 name_kr 필드 추가 (외유내강형, 다정다감형 등)
- [ ] 슬라이더 5개 체계 (Movement/Speech/Expressiveness/Attitude + Overall)
- [ ] Overall(특이↔평범): 유형 판정에 불참, 병맛 강도에만 영향
- [ ] `personality[major][minor]` 접근 구조

---

## 2. `src/tomodachai/character.py` — 필드 대폭 추가

**추가 필드:**
- [ ] `birthday: str` — 생일 (→ 별자리 자동 도출)
- [ ] `zodiac: str` — 별자리 (birthday에서 자동 계산)
- [ ] `blood_type: str` — 혈액형 (A/B/O/AB)
- [ ] `favorite_color: str` — 좋아하는 색
- [ ] `gender: str` — 성별 (생성 시 확정, 수정 불가)
- [ ] `speech_habits: dict[str, str]` — 말버릇 5종류 (normal/happy/angry/sad/worried)
- [ ] `satisfaction: float` — 만족도
- [ ] `experience: float` — 경험치 (만족도 배율로 획득)
- [ ] `level: int` — 레벨 (레벨업 시 보상 선택)
- [ ] `hunger: float` — 배고픔
- [ ] `current_mood: str` — 현재 기분 (이모티콘/이펙트/표정)
- [ ] `is_sick: bool` — 아픔 상태 (약 아이템으로 회복)
- [ ] `is_despair: bool` — 절망 상태 (시간 경과 또는 여행으로 회복)
- [ ] `food_preferences: dict` — 음식 선호도 (5단계 구간 + 구간 내 순위, 생성 시 확정, 변동 없음)
- [ ] `clothing_preferences: dict` — 의류 선호도 (생성 시 확정)
- [ ] `interior_preferences: dict` — 인테리어 선호도 (생성 시 확정)
- [ ] `preferred_personality_group: tuple[str, bool]` — 성격 계통 선호 or 비선호 1개
- [ ] `nicknames: dict[str, str]` — 다른 캐릭터가 부르는 별명 (이벤트 기반)
- [ ] `mini_traits: dict` — 미니 개성 (보유 풀 내 변경만, 되돌리기 불가)
- [ ] `idle_animation: str` — 대기 모션 (성격 기본값 + 미니 개성 덮어쓰기)
- [ ] `given_items: dict` — 줘본 아이템 기록 (도감)
- [ ] `confession_count: dict[str, int]` — 상대별 고백 횟수 (최대 3회)
- [ ] `slider_values: dict` — 슬라이더 5개 세부 값 (행동/말투 강도)

---

## 3. `src/tomodachai/relationship.py` — 대폭 확장

### 3-1. 수치 체계 변경
- [ ] `jealousy`, `tension` 독립 수치 제거 → 파생 상태로 전환
- [ ] friendship(-100~100), romance(0~100)만 독립 수치 (방향성)

### 3-2. 관계 슬롯 + 태그
- [ ] 지정 관계 슬롯: 베프(≥70 양방향)/연인/원수(≤-50 양방향) 각 1명
- [ ] 관계 태그: 전 연인 (복수, 이별 사유 reason 포함, 슬롯과 독립)
- [ ] 관계 단계: STRANGER → ACQUAINTANCE → FRIEND → BEST_FRIEND → LOVER → MARRIED
- [ ] 상태 텍스트 매핑 (friendship 8구간, romance 4구간)

### 3-3. 이벤트 트리거
- [ ] 고백: A→B romance≥50 + friendship≥20, 플레이어 허락, 상대 수치 미참조 랜덤
- [ ] 고백 재시도: 최대 3회, 3회차 단념 (romance 강제 하락)
- [ ] 프로포즈: 고백과 동일 방식, 부재 중 보류
- [ ] 이별 사유 6가지 시스템 자동 판정
- [ ] 바람: 자연 발생(romance 상승) + 고백 수락 (연인 있는 캐릭터에게 고백 가능)
- [ ] 바람 플레이어 선택지 ("솔직해져 봐"/"다시 생각해 봐"/"B를 생각해")
- [ ] 헤어지고 싶다 이벤트 ("그래"/"다시 생각해 봐" → LLM 최종 판단)

### 3-4. 싸움/질투
- [ ] 싸움 1종류 (목격: 말리기/지켜보기, 부재: 사과 이벤트)
- [ ] 질투: 파생 상태 판정 + AI 자율 행동 + 플레이어 요청
- [ ] 관계 슬롯별 확률 보정 (베프→싸움↓ 등)

### 3-5. 수치 변동
- [ ] 대화 기본 델타: friendship +1~4, romance +0.5~2
- [ ] 궁합 배율: x0.7~x1.3 (초기 관계만)
- [ ] 이벤트별 수치 변동표
- [ ] 자연 감소: 하루 1회 -0.5~1
- [ ] 첫인상 보너스

### 3-6. 관계 자유성
- [ ] 관계 해제/전환 (베프→해제, 원수→화해, 이별→재회)
- [ ] 원수+연인 동시 허용
- [ ] MVP: 연애 남녀 간만

---

## 4. `src/tomodachai/conversation.py` — 프롬프트 대폭 수정

- [ ] 관계 수치 직접 노출 제거 → 슬롯 + 상태 텍스트 + 태그
- [ ] 말버릇 5종류 감정별 주입
- [ ] 별명 데이터 주입
- [ ] 미니 개성, Overall(특이↔평범), 현재 기분/아픔/절망 주입
- [ ] LLM 가드레일 프롬프트
- [ ] 상황별 프롬프트 분리 (13-llm-usage.md 참조)

---

## 5. `src/tomodachai/simulation.py` — 실시간 전환 + 이벤트 확장

- [ ] **틱 기반 → 실시간 전환**: 랜덤 간격(10~30분)으로 이벤트 체크
- [ ] 시간대 구분: 아침/낮/저녁/밤 (현실 시간, 반전 모드)
- [ ] 하루 리셋: 새벽 5시
- [ ] 이벤트 타입 확장 (대화, 싸움, 고백, 별명, 요청, 모금, 방 방문, 실시간 관찰, 생일 등)
- [ ] 캐릭터 동선: 조건 기반 랜덤
- [ ] 만족도 → 경험치 배율 → 레벨업
- [ ] 배고픔 시간 경과
- [ ] catch-up: 경량 산출, 큰 이벤트 보류, 하루 3~5건 상한

---

## 6. `src/tomodachai/memory.py`

- [ ] `event_type` 확장: conversation, fight, confession, breakup, reconciliation, nickname, donation, birthday, travel, dream, cheating 등
- [ ] 이별 사유 `reason` 필드

---

## 7. `config.yaml` — 장소 + 상점 + 시간

**장소 13개:**
공동주택(개인 방+거실+발코니), 식료품점, 의류점, 인테리어점, 분수대, 방송국, 콘서트홀, 사진관, 시청, 공원, 카페, 해변, 놀이공원

**상점:** Daily/Seasonal/Catalog, 아침 장터, 기념일 아이템

**시간:** 실시간 연동, 새벽 5시 리셋

---

## 8. 신규 모듈

- [ ] `shop.py` — 상점 (Daily/Seasonal/Catalog, 가격 체계, 기념일)
- [ ] `save.py` — 세이브 (수동 저장 + 크래시 임시 보관)
- [ ] `news.py` — 뉴스 (실제 이벤트 1건 + 병맛 뉴스)
- [ ] `dream.py` — 꿈 (템플릿 풀, 보상 조건: 밤 수면만)
- [ ] `song.py` — 노래 (8장르, 가사 4방식, 솔로/듀엣/그룹)
- [ ] `travel.py` — 여행 (티켓, 사진 3장, 기념품, 절망 시 혼자)
- [ ] `photo.py` — 사진 (촬영 경로 4가지, 갤러리, 액자)
- [ ] `minigame.py` — 미니게임 (관찰형 + 참여형)
- [ ] `compatibility.py` — 궁합 (성격+혈액형+별자리+랜덤, 초기 관계만 보정)
- [ ] `treasure.py` — 보물 (컬렉션 + 선물 + 판매)

---

## 9. `tests/` — 전체 업데이트

기존 테스트 수정 + 신규 모듈 테스트 추가.

---

## 우선순위 제안

1. **personalities.yaml** — 한국 공식명, 5슬라이더
2. **character.py** — 필드 대폭 추가
3. **relationship.py** — 수치 체계, 슬롯, 트리거, 이별 사유
4. **simulation.py** — 틱→실시간, 이벤트 확장
5. **conversation.py** — 프롬프트 상황별 분리
6. **config.yaml** — 장소 13개, 상점, 시간
7. **신규 모듈** — shop, save, news, dream, song, travel, photo, minigame, compatibility, treasure
8. **tests/**
