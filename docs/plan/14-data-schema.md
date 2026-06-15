# 데이터 스키마

모든 참조는 숫자 ID 기반. 카테고리는 필드명/파일명으로 구분.

## 파일 구조

세이브 데이터는 파일별로 분리:
- `game.json` — 게임 전역 상태 + 카탈로그
- `char_{id}.json` — 캐릭터별 개별 파일
- `events.json` — 이벤트 로그
- `shop.json` — 상점 상태 (daily + 아침 장터)

아이템 마스터 데이터(음식/의류/인테리어/보물/도구 정의)는 세이브에 포함하지 않음. 별도 마스터 파일.

상수값 (하루 리셋 시간 05:00, 이벤트 빈도 등)은 코드에 상수로. 세이브/설정에 포함하지 않음.

## 1. game.json

```json
{
  "island_name": "별빛 마을",
  "day_count": 52,
  "money": 45000,
  "time_flip": false,
  "today_announcer": 2,
  "catalog": {
    "food": [2, 4, 7],
    "clothing": [12],
    "interior": [5],
    "treasure": [1, 15]
  }
}
```

*   `day_count`: 게임 시작 후 경과한 날 수. 하루 리셋(새벽 5시)마다 +1.
*   `today_announcer`: 오늘의 뉴스 아나운서 캐릭터 ID. 하루 리셋 시 랜덤 선정.
*   `catalog`: 전역 입수 기록. 한번이라도 입수한 아이템은 재구매 가능. 플레이어(전역) 단위.

## 2. char_{id}.json

### 구조 분류

| 분류 | 설명 | 비고 |
|------|------|------|
| profile | 기본 정보 | 시청에서 수정 (gender만 수정 불가) |
| preferences | 선호도 | food_ranks는 불변(코드에서 상수 처리), food_eaten은 변동 |
| state | 현재 상태 | 수시 변동 |
| customizable | 방에서 변경 가능 | 말버릇, 미니 개성, 별명, 노래 |
| relationships | 이 캐릭터 → 상대 수치 | 상대→나는 상대 파일에서 조회 |
| slots | 지정 관계 | 베프/연인/원수 각 1명 |
| tags | 관계 태그 | 전 연인 등 |
| records | 누적 기록 | 보물, 고백 횟수, 사진 |

### satisfaction vs mood

| | satisfaction | mood |
|--|-------------|------|
| 성격 | 장기, 레벨업/절망용 | 단기, 현재 감정 |
| 변동 | 이벤트로 크게 변동 | 일상적으로 수시 변동 |
| 마이너스 | → 절망 상태 (파생) | → 기분 나쁨 |
| 영향 | 경험치 (레벨업 임계값 통일) | LLM 대사 톤, 표정/이펙트 |

### mood 3축

| 축 | 범위 | ↑ 요인 | ↓ 요인 |
|---|------|--------|--------|
| happiness | 0~10 | 좋아하는 음식, 친구 대화 | 싫어하는 음식, 싸움 |
| energy | 0~10 | 대화, 활동 | 배고픔, 거절 |
| stress | 0~10 | 싸움, 배고픔, 거절 | 친구 대화, 시간 경과 |

시간 경과 시 중립(5)으로 수렴.

### 수치 범위

| 필드 | 범위 | 비고 |
|------|------|------|
| satisfaction | -100 ~ 100 | < 0 이면 절망. 100 초과 시 레벨업 + 리셋 |
| level | 1 ~ 99 | 99 도달 후에도 레벨업 판정 시 보상만 지급 (수치 고정) |
| hunger | 0 ~ 100 | 0 = 배부름, 100 = 매우 배고픔 |
| friendship | -100 ~ 100 | 방향성 |
| romance | 0 ~ 100 | 방향성 |
| money | 0 ~ 999,999,999 | 전역. 초과 시 클램핑 |

모든 수치는 범위 밖으로 나가지 않도록 **클램핑** 처리. 하한/상한 초과 시 더 쌓이거나 빠지지 않음.

### sick

`null`(건강), `"cold"`(감기), `"stomachache"`(배탈).

### 절망

저장하지 않음. `satisfaction < 0`이면 절망 상태 (런타임 판정).

### food 선호도

*   `food_ranks`: 인덱스 = 음식 ID, 값 = 순위. 배열 길이 = 전체 음식 수. 생성 시 확정(불변).
*   `food_eaten`: 인덱스 = 음식 ID, 값 = 이 캐릭터에게 먹여봤는지. 변동.
*   표시: eaten=true인 것 중 rank 기준 정렬 → 최애 2개, like 상위 n개, 최악 2개.

### clothing/interior 선호도

스타일 카테고리 기반 (likes/dislikes). 아이템에 스타일 태그 필요. (태그 목록 TODO)

### pet_preference

*   선호하는 동물 종류: `"dog"`, `"cat"`, `"rabbit"`, `"hamster"`, `"bird"`, `"turtle"`
*   `null`이면 펫 무관심 (안 키우는 게 best).

### mini_traits

카테고리별 보유 풀. `active: null`이면 성격 기본값 사용.

### songs

boolean 배열 (길이 8). 인덱스 = 장르 순서 (트로트/아이돌/발라드/락/랩/뮤지컬·오페라/동요/찬송가).

### relationships

이 캐릭터 → 상대 수치만 저장. 상대 → 나는 상대 파일에서 조회.

## 3. events.json

```json
[
  {
    "id": 1,
    "type": "conversation",
    "participants": [1, 2],
    "location": "living_room",
    "day": 15,
    "time": "14:32"
  }
]
```

*   type: conversation, fight, reconciliation, confession, breakup, nickname, donation, birthday, travel, dream, cheating 등
*   **공통 필드:** id, type, participants, day
*   **선택 필드:**
    *   `time`: 해당 이벤트가 일어난 시간 (게임 내 시간, HH:MM). 장소 기반 이벤트에 주로 사용
    *   `location`: 이벤트 발생 장소 ID. 위치가 의미 있는 이벤트에만
    *   `reason`: 이별 사유 (mutual/fight/cheating/boredom/triangle/misunderstanding). breakup에만
    *   `result`: 성공/실패 (accepted/rejected, success/failed). confession, reconciliation 등에
*   summary 없음. 필요 시 LLM이 재구성.

## 4. shop.json

```json
{
  "daily": {
    "food": [3, 17, 55],
    "clothing": [22, 45],
    "interior": [8]
  },
  "morning_market": {
    "item": 28,
    "discount_price": 1500
  }
}
```

*   daily: 새벽 5시에 코드에서 랜덤 갱신.
*   morning_market: 아침 장터. daily food와 비중복.
*   seasonal: 날짜 기반으로 코드에서 결정. 저장 불필요.
*   catalog: game.json에서 전역 관리.

## 5. 마스터 데이터 (세이브 외)

아이템 정의, 성격 유형 정의, 미니 개성 정의, 장소 정의 등은 별도 마스터 파일로 관리.

실제 구조 예시는 `mock/` 디렉토리 참조.
