# Phase 7 — save.py 직렬화 / SaveManager (마이그레이션 최종)

base: HEAD (feat/client-sim-migration, Phase 0~6 완료, 636 vitest + check 0 + build ✓)
plan 작성일: 2026-06-24

## 목표

Python `save.py`(680)를 `prototype/web/src/sim/`로 포팅. 마이그레이션 마지막 모듈.
- 순수 직렬화/역직렬화(_serialize/_deserialize ×3) = 골든 + 라운드트립 검증.
- SaveManager 파일시스템부 = 주입형 FS seam(Tauri fs는 후속). 슬롯 로직만 검증.

## 핵심 제약 (사전 조사 결과)

- `_serialize_character`는 model_dump가 아니라 **손수 만든 중첩 dict("mock format")**.
  `_deserialize_character`는 `Character(**data)` (pydantic). TS는 중첩 dict 빌드 +
  Character 객체 재구성(누락 레거시 필드 food_preferences/clothing_preferences/
  mini_personality는 기본값). 직렬화 키 셋: id/personality_code/profile/preferences/
  state/customizable/records.
- `_serialize_relationships`는 tracker._slots / _ex_lover_tags / _fights **전체**를 읽음.
  TS RelationshipTracker엔 "전체" 접근자 없음(getFights는 미해결만!) → **추가 필요**:
  allSlots()/allExLoverTags()/allFightsRaw() (additive, 비파괴). pairs는 allPairs()로 충분.
  직렬화 pair 키는 `"a:b"`(콜론), 내부 저장키는 `"a,b"`(콤마)와 무관.
- `_deserialize_relationships`는 대부분 public API로 복원 가능: pair는 get(a,b)후 in-place
  세팅, slots는 getSlots 후 세팅(또는 setter), ex_lover_tags는 addExLoverTag, fights는 addFight.
  단 stage는 RelationshipStage 문자열 그대로, reason은 BreakupReason 문자열 그대로.
- `_serialize_events`는 memory._events **전체** + None 필드 생략(조건부 키). TS MemoryStore엔
  allEvents() 접근자 **추가 필요**. `_deserialize_events`는 add_event(public)로 복원.

## 태스크 분해

### P7 T1: serializeCharacter / deserializeCharacter (골든 + 라운드트립)
- saveSerialize.ts(또는 save.ts)에 serializeCharacter(char)→중첩 dict, deserializeCharacter(data)→Character.
- nose/mouth adjust는 {height,size}만(스칼라 일부), eye/eyebrow adjust는 4필드(_adj).
- 골든: dump _serialize_character(샘플 캐릭터) → TS 1:1. 라운드트립: deserialize(serialize(c)) 동등성.
- 누락 레거시 필드는 defaultCharacter 기반 기본값으로 채움(Character(**data) 의미).

### P7 T2: serializeRelationships / deserializeRelationships (골든 + 라운드트립)
- RelationshipTracker에 allSlots()/allExLoverTags()/allFightsRaw() 추가(additive).
- serialize: pairs(allPairs, "a:b" 키, stage 문자열), slots(charId→{best_friend,lover,enemy}),
  ex_lover_tags(charId→[{target,reason,day}]), fights([{participants,cause,resolved,witnessed_by_player}]).
- deserialize: pairs get+세팅, slots 복원, ex_lover_tags 복원, fights 복원. 키 "a:b" split.
- 골든 + 라운드트립.

### P7 T3: serializeEvents / deserializeEvents (골든 + 라운드트립)
- MemoryStore에 allEvents() 추가(additive).
- serialize: 전체 이벤트, null 필드(time/location/reason/result) 생략(조건부 키).
- deserialize: add_event로 복원(id 보존 — id≠0이면 그대로).
- 골든 + 라운드트립.

### P7 T4: SaveManager (FS seam, 통합)
- 파일시스템 추상화 인터페이스 SaveFs(read/write/list/mkdir/remove/exists/rename 등) 주입.
- SaveManager: 슬롯 검증, save(슬롯별 game.json/characters/{id}.json/events.json/relationships.json,
  원자적 temp→rename), load, list_slots(메타), delete_slot, temp save/load/clear.
- game.json: island_name/day_count/money/time_flip/ending_credit_seen/catalog/last_online.
- 결정론(직렬화 조립/슬롯 검증/메타)=단위, FS=주입 stub로 구조 검증.
- 주의: Python의 atomic write(temp dir rename) 의미 보존. 슬롯 번호 검증 메시지 byte단위.

## 게이트 (태스크마다)
- npm test --run + npm run check 둘 다 green. TDD Red→Green.
- 각 태스크: 구현 → 독립 sonnet 리뷰(오라클 충실+범위) → inline fix → ledger.
- Phase 종료: opus 최종 리뷰 → 푸시 → PR #7 갱신(제목 Phase 0~7, 마이그레이션 완료).

## 산출물
- prototype/web/src/sim/save.ts (+test, +golden)
- prototype/web/src/sim/relationshipTracker.ts (allSlots/allExLoverTags/allFightsRaw 추가)
- prototype/web/src/sim/memory.ts (allEvents 추가)
- scripts/dump_golden.py에 serialize 골든 덤프 추가
- __golden__/*.json + loadGolden.ts 등록

## 완료 정의 (마이그레이션 종료)
P7 머지 시 src/tomodachai의 게임 로직 모듈 전부 포팅 완료(server.py=서버 제거, main.py=CLI 불필요).
클라(TS) 시뮬레이션이 Python 오라클과 규칙 충실 동치 + 세이브 라운드트립 보장.
