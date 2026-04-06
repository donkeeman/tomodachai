# 코드 ↔ 기획서 정렬 명세

기획서 기준으로 코드를 수정해야 하는 항목을 파일별로 정리합니다.

---

## 1. `data/personalities.yaml` — 전면 재작성

**현재:** 32가지 성격 유형, 5축(Energy/Warmth/Stability/Openness/Assertiveness)
**기획서:** 16가지 성격 유형, 4계통(나고미/노리/쿨/드라이) × 4형

- [ ] 32가지 → 16가지로 축소
- [ ] 5축 → 4축(Movement/Speech/Expressiveness/Attitude)으로 변경
- [ ] 원작 4계통 체계로 재구성
- [ ] 각 유형의 name, description, behavior_guide 재작성
- [ ] 07-research.md의 성격 리서치 데이터 참고

---

## 2. `src/tomodachai/personality.py` — 대폭 수정

**현재:** 5축 트레이트 맵, 5글자 코드 체계
**기획서:** 4축 슬라이더 기반, 슬라이더 조합으로 16가지 유형 자동 결정

- [ ] `_TRAIT_MAP` 5축 → 4축으로 변경
- [ ] 코드 체계 변경 (EWSOB 5자리 → 슬라이더 값 기반)
- [ ] 슬라이더 값(Movement+Speech, Expressiveness+Attitude) → 16가지 유형 매핑 로직 추가
- [ ] `match_personality()` — 자연어 입력 → 슬라이더 값 자동 세팅으로 변경

---

## 3. `src/tomodachai/character.py` — 필드 대폭 추가

**현재 필드:** `id, name, personality_code, speech_habit, backstory`

추가해야 할 필드:
- [ ] `birthday: str` — 생일 (→ 별자리 자동 도출, 생일 이벤트 트리거)
- [ ] `zodiac: str` — 별자리 (birthday에서 자동 계산)
- [ ] `blood_type: str` — 혈액형 (A/B/O/AB)
- [ ] `favorite_color: str` — 좋아하는 색
- [ ] `gender: str` — 성별
- [ ] `speech_habits: dict[str, str]` — 말버릇 5종류 (normal/happy/angry/sad/worried). 기존 단일 `speech_habit` 대체
- [ ] `satisfaction: float` — 만족도/행복도
- [ ] `hunger: float` — 배고픔
- [ ] `food_preferences: dict[str, str]` — 음식 선호도 (아이템ID → 최애/좋아함/보통/싫어함/최악). 생성 시 랜덤 부여
- [ ] `clothing_preferences: dict` — 의류 선호도. 생성 시 랜덤 부여
- [ ] `nicknames: dict[str, str]` — 다른 캐릭터가 부르는 별명 (char_id → 별명)

---

## 4. `src/tomodachai/relationship.py` — 구조 확장

### 4-1. 관계 단계 추가
- [ ] `RelationshipStage` enum: `STRANGER → ACQUAINTANCE → FRIEND → LOVER → MARRIED`
- [ ] `Relationship` 모델에 `stage: RelationshipStage` 필드 추가
- [ ] 수치 → 관계 단계 자동 전환 로직 (임계값 기반)
- [ ] 상태 텍스트 매핑: 내부 수치 구간 → 표시 텍스트 ("좋아함", "엄청 좋아함" 등)

### 4-2. 싸움 시스템
- [ ] `Fight` 모델: participants, cause, resolved, witnessed
- [ ] 플레이어 목격 시: "말린다" / "지켜본다" 분기
- [ ] 플레이어 부재 시: 이미 싸운 상태, "사과하고 싶다" 이벤트 발생 가능

### 4-3. 질투 시스템 확장
- [ ] 기존 수치 기반 질투에 AI 자율 행동 타입 추가 (뒷담화, 회피, 시비, 하소연)
- [ ] 플레이어 요청: "저 커플 헤어지게 해줘" → 수락/거절

### 4-4. 궁합 시스템
- [ ] 성격 + 혈액형 + 별자리 복합 궁합 계산 함수

### 4-5. LLM 가드레일
- [ ] 관계 전환(우정→연애)은 숫자 테이블 트리거가 먼저 발생해야 LLM에 지시
- [ ] 트리거 없이 LLM이 단독으로 관계 변경 불가

### 4-6. 관계의 자유성
- [ ] 이별 후 재결합 가능 (낮은 확률 또는 LLM 판단)
- [ ] 베스트 프렌드 → 연인 전환 제한 없음
- [ ] 성별에 의한 연애 제한 없음

---

## 5. `src/tomodachai/conversation.py` — 프롬프트 수정

- [ ] 관계 수치 직접 노출 제거 → 관계 단계 + 상태 텍스트로 대체
- [ ] 말버릇 5종류 감정별 주입 (현재 감정 상태에 맞는 말버릇 선택)
- [ ] 별명 데이터 프롬프트 주입 ("A는 B를 '수수'라고 부른다")
- [ ] 미니 개성 필드 프롬프트 주입
- [ ] LLM 가드레일 프롬프트 추가 ("우정이 깊어진다고 반드시 연애로 발전하지는 않는다")
- [ ] 혈액형/별자리 정보 프롬프트 주입 (궁합 참고용)

---

## 6. `src/tomodachai/simulation.py` — 이벤트 시스템 확장

- [ ] 대화 외 이벤트 타입 추가: 싸움, 고백, 별명 짓기, 요청, 모금 등
- [ ] 이벤트 랜덤 선정 로직 (숫자 테이블 트리거 → 이벤트 풀에서 선택)
- [ ] 만족도/배고픔 시간 경과 처리 (틱마다 감소)
- [ ] 관계 단계 자동 전환 체크 (틱 종료 시)
- [ ] 만족도 레벨업 보상 시스템

---

## 7. `src/tomodachai/memory.py` — 소규모 수정

- [ ] `event_type` 확장: "conversation" 외에 "fight", "confession", "breakup", "reconciliation", "nickname", "donation" 등

---

## 8. `config.yaml` — 장소 업데이트

**현재:** 공원, 편의점, 카페, 정자
**기획서 필수 장소:** 개별 주택, 식료품점, 의류점, 인테리어점, 분수대, 방송국

- [ ] 장소 목록 기획서 기준으로 변경
- [ ] 후보 장소(공원, 카페, 해변/강변, 광장, 콘서트홀) 추가 여부는 추후 결정

---

## 9. `tests/` — 전체 업데이트

- [ ] `test_personality.py` — 16가지 유형 + 4축 슬라이더 테스트
- [ ] `test_character.py` — 새 필드(생일, 혈액형, 말버릇 5종 등) 테스트
- [ ] `test_relationship.py` — 관계 단계, 싸움, 질투 확장, 궁합 테스트
- [ ] `test_conversation.py` — 변경된 프롬프트 구조 테스트
- [ ] `test_simulation.py` — 새 이벤트 타입, 만족도/배고픔 테스트
- [ ] `test_memory.py` — 확장된 event_type 테스트

---

## 우선순위 제안

1. **personalities.yaml + personality.py** — 가장 기본. 다른 모듈이 전부 의존
2. **character.py** — 필드 추가
3. **relationship.py** — 관계 단계 + 가드레일
4. **conversation.py** — 프롬프트 수정
5. **simulation.py** — 이벤트 확장
6. **config.yaml** — 장소
7. **tests/** — 위 변경에 맞춰 수정
