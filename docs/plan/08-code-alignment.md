# 코드 ↔ 기획서 정렬 명세

기획서 기준으로 코드를 수정해야 하는 항목을 파일별로 정리합니다.
코드 리팩토링(Phase 1→기획서 정렬)은 일부 완료됨. 아래는 **현재 코드 대비 아직 미반영된 기획서 내용**.

데이터 구조 기준: `docs/plan/mock/*.json` + `14-data-schema.md`

---

## 1. `data/personalities.yaml` — 한국 공식명 반영

- [ ] 16가지 유형에 한국 공식명 반영 (안정파/사교파/주도파/신중파 × 4형)
- [ ] 각 유형의 name_kr 필드 추가 (외유내강형, 다정다감형 등)
- [ ] 슬라이더 5개 체계 (movement/speech/expressiveness/attitude/overall)
- [ ] Overall: 유형 판정에 불참, 병맛 강도에만 영향
- [ ] 계통 영어 키: easygoing (안정파), outgoing (사교파), confident (주도파), independent (신중파)
- [ ] 마스터 데이터는 `personality[group][type]` 형태로 접근 (계통명/유형명 → 설명/행동 가이드)

---

## 2. `src/tomodachai/character.py` — 중첩 구조로 재설계

데이터 구조는 mock/char_1.json 참조. 최상위 필드는 다음과 같이 **중첩**:

```
Character
├── id: int
├── profile: {name, birthday, blood_type, favorite_color, gender, appearance, personality, voice}
├── preferences: {food_ranks, food_eaten, clothing, interior, personality_group}
├── state: {satisfaction, level, hunger, mood, sick, current_location, current_outfit, current_interior, photo_frame}
├── customizable: {speech_habits, mini_traits, nicknames, songs}
├── relationships: {상대_id: {friendship, romance}}
├── slots: {best_friend, lover, enemy}
├── tags: {ex_lovers: [...]}
└── records: {treasure_collection, confession_count, photos}
```

### 2-1. profile
- [ ] `name: str` (성/이름 분리 안 함)
- [ ] `birthday: str` (MM-DD 형식)
- [ ] `blood_type: str` (A/B/O/AB) — enum
- [ ] `favorite_color: str` — enum
- [ ] `gender: str` (M/F) — 수정 불가
- [ ] `appearance: dict` — face_shape, skin_color, eye(base/lash/color/adjust), eyebrow(id/adjust), nose(id/adjust), mouth(id/adjust), hair(front/back/color), glasses, body(height/build)
- [ ] `personality: dict` — movement/speech/expressiveness/attitude/overall (슬라이더 값만 저장, group/type은 런타임 계산)
- [ ] `voice: dict` — preset, pitch, speed, quality/tone/accent/intonation (후자 4개는 TTS 미지원이라 null)
- [ ] **zodiac은 저장하지 않음** — birthday에서 런타임 계산

### 2-2. preferences
- [ ] `food_ranks: list[int]` — 인덱스=음식ID, 값=순위. 생성 시 확정, 불변 (코드에서 상수 처리)
- [ ] `food_eaten: list[bool]` — 인덱스=음식ID, 이 캐릭터에게 먹여봤는지. 변동
- [ ] `clothing: dict` — `{likes: str, dislikes: str}` 스타일 카테고리
- [ ] `interior: dict` — `{likes: str, dislikes: str}` 테마 카테고리
- [ ] `personality_group: dict` — `{group: str, is_positive: bool}` 성격 계통 선호/비선호

### 2-3. state
- [ ] `satisfaction: float` — 만족도 (레벨업 경험치 역할). < 0이면 절망 상태 — **런타임 판정, 별도 필드 없음**
- [ ] `level: int` — 레벨. 임계값 통일. 레벨업 시 satisfaction 리셋
- [ ] `hunger: float` — 배고픔
- [ ] `mood: dict` — `{happiness: int, energy: int, stress: int}` 3축
- [ ] `sick: str|null` — `null`(건강), `"cold"`(감기), `"stomachache"`(배탈)
- [ ] `current_location: str` — 현재 위치
- [ ] `current_outfit: int` — 현재 착용 의류 ID
- [ ] `current_interior: int` — 현재 방 인테리어 ID
- [ ] `photo_frame: int|null` — 방 액자 사진 ID

### 2-4. customizable
- [ ] `speech_habits: dict` — `{normal, happy, angry, sad, worried}` 5종
- [ ] `mini_traits: dict` — `{walking: {owned, active}, eating: {owned, active}, idle: {owned, active}}`. active=null이면 성격 기본값. (카테고리 3개: walking/eating/idle)
- [ ] `nicknames: dict[str, str]` — 상대 ID → 별명 (이벤트 기반 획득)
- [ ] `songs: list[bool]` — 장르별 보유 여부. 길이 8 (트로트/아이돌/발라드/락/랩/뮤지컬·오페라/동요/찬송가)

### 2-5. relationships/slots/tags/records
- [ ] `relationships: dict[str, dict]` — `{"상대ID": {friendship, romance}}`. 이 캐릭터→상대만. 상대→나는 상대 파일에서 조회.
- [ ] `slots: dict` — `{best_friend: int|null, lover: int|null, enemy: int|null}`
- [ ] `tags: dict` — `{ex_lovers: [{target, reason, day}, ...]}`
- [ ] `records: dict` — `{treasure_collection: list[int], confession_count: dict, photos: list[int]}`

---

## 3. `src/tomodachai/relationship.py` — 대폭 확장

### 3-1. 수치 체계 변경
- [ ] `jealousy`, `tension` 독립 수치 제거 → 파생 상태로 전환
- [ ] friendship(-100~100), romance(0~100)만 독립 수치 (방향성)

### 3-2. 관계 슬롯 + 태그
- [ ] 지정 관계 슬롯: 베프(≥70 양방향)/연인/원수(≤-50 양방향) 각 1명
- [ ] 관계 태그: 전 연인 (복수, 이별 사유 reason 포함, 슬롯과 독립)
- [ ] 관계 단계: STRANGER → ACQUAINTANCE → FRIEND → BEST_FRIEND → LOVER → MARRIED (파생 판정)
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
- [ ] 화해 이벤트 (별도 타입, result=success/failed)
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
- [ ] 기억 유지: 수치 리셋되어도 이벤트 로그는 남음

---

## 4. `src/tomodachai/conversation.py` — 프롬프트 대폭 수정

- [ ] 관계 수치 직접 노출 제거 → 슬롯 + 상태 텍스트 + 태그
- [ ] 말버릇 5종류 감정별 주입
- [ ] 별명 데이터 주입
- [ ] 미니 개성, Overall(특이↔평범), mood, sick 상태 주입
- [ ] LLM 가드레일 프롬프트
- [ ] 상황별 프롬프트 분리 (13-llm-usage.md 참조)

---

## 5. `src/tomodachai/simulation.py` — 실시간 전환 + 이벤트 확장

- [ ] **틱 기반 → 실시간 전환**: 랜덤 간격(10~30분)으로 이벤트 체크
- [ ] 시간대 구분: 아침/낮/저녁/밤 (현실 시간, 반전 모드)
- [ ] 하루 리셋: 새벽 5시 (코드 상수)
- [ ] 이벤트 타입 확장 (대화, 싸움, 화해, 고백, 별명, 요청, 모금, 방 방문, 실시간 관찰, 생일 등)
- [ ] 캐릭터 동선: 조건 기반 랜덤
- [ ] 만족도 레벨업 (임계값 통일)
- [ ] 배고픔 시간 경과
- [ ] mood 시간 경과 → 중립 수렴
- [ ] catch-up: 경량 산출, 큰 이벤트 보류, 하루 3~5건 상한

---

## 6. `src/tomodachai/memory.py`

- [ ] event 구조: `{id, type, participants, day, time?, location?, reason?, result?}`
- [ ] event type: conversation, fight, reconciliation, confession, breakup, nickname, donation, birthday, travel, dream, cheating 등
- [ ] 이별 시 `reason` 필드 (mutual/fight/cheating/boredom/triangle/misunderstanding)
- [ ] 고백/화해 시 `result` 필드 (accepted/rejected, success/failed)
- [ ] time/location은 해당되는 이벤트에만 (선택 필드)
- [ ] **summary 필드 없음** — 필요 시 LLM이 재구성

---

## 7. `config.yaml` / 코드 상수

**장소 13개:**
공동주택(개인 방+거실+발코니), 식료품점, 의류점, 인테리어점, 분수대, 방송국, 콘서트홀, 사진관, 시청, 공원, 카페, 해변, 놀이공원

**상점:** daily + 아침 장터 (seasonal/catalog은 저장 안 함, seasonal은 날짜 기반 코드 결정, catalog는 game.json에 전역)

**코드 상수 (저장/설정 불필요):**
- 하루 리셋: 05:00
- 이벤트 빈도 (플레이어 설정 없음)

---

## 8. 신규 모듈

- [ ] `shop.py` — 상점 (daily 랜덤 갱신, 아침 장터, 기념일)
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

## 9. `game.json` (신규)

- [ ] `island_name: str`
- [ ] `day_count: int`
- [ ] `money: int`
- [ ] `time_flip: bool`
- [ ] `ending_credit_seen: bool`
- [ ] `catalog: dict` — 전역 입수 기록 `{food, clothing, interior, treasure}` (플레이어 단위)

---

## 10. `tests/` — 전체 업데이트

기존 테스트 수정 + 신규 모듈 테스트 추가.

---

## 우선순위 제안

1. **personalities.yaml** — 한국 공식명, 5슬라이더
2. **character.py** — 중첩 구조로 재설계
3. **relationship.py** — 수치 체계, 슬롯, 트리거, 이별 사유
4. **simulation.py** — 틱→실시간, 이벤트 확장
5. **conversation.py** — 프롬프트 상황별 분리
6. **config.yaml / 코드 상수** — 장소 13개
7. **game.json + save.py**
8. **신규 모듈** — shop, news, dream, song, travel, photo, minigame, compatibility, treasure
9. **tests/**
