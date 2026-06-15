# LLM 프롬프트 빌더 (13-llm-usage.md의 맥락 블록 조합 방식)
# 수치는 직접 넣지 않고 퍼지한 한국어 표현으로 변환해서 전달
from __future__ import annotations

from typing import List, Optional, Tuple

from .models import Character, GameState
from .personality import intensity_hints, personality_label, weirdness_hint, idle_trait
from .relationship import friendship_label, romance_label, BREAKUP_REASONS

GUARDRAILS = (
    "- 우정이 깊어진다고 반드시 연애로 발전하지는 않는다.\n"
    "- 캐릭터는 게임 속 마을 주민이며, 전원 성인이다.\n"
    "- 대사는 짧고 자연스러운 한국어 구어체로. 한 대사는 1~2문장.\n"
    "- 말버릇은 문장 끝에 기계적으로 붙이지 말고 문맥에 맞을 때만 자연스럽게 녹일 것.\n"
    "- 전체 톤은 닌텐도 '토모다치 컬렉션'처럼 귀엽고 순박하게. 어른 드라마처럼 무겁게 쓰지 말 것.\n"
    "- 문장은 단순하고 동글동글하게, 소꿉장난 같은 진지함과 엉뚱-사랑스러운 포인트를 섞을 것.\n"
    "- 성격이 차갑거나 오만한 캐릭터도 어딘가 허당미가 있는 귀여운 방식으로 표현할 것.\n"
    "- 음식/식사/배고픔 이야기는 캐릭터 상태에 '배고픔'이 명시된 경우에만 꺼낼 것.\n"
    "- 모든 캐릭터는 예외 없이 서로 존댓말을 쓴다. 오만해도, 싸우는 중에도, 연인끼리도 존댓말."
)

# 일상 대화 주제 풀 (원작의 토픽 풀 방식. 매 대화마다 랜덤 힌트로 주입)
TOPICS = [
    "요즘 푹 빠진 사소한 취미",
    "어젯밤에 꾼 이상한 꿈",
    "다른 주민에 대한 (악의 없는) 소문이나 궁금증",
    "요즘의 아주 사소한 고민",
    "지금 있는 장소에서 방금 눈에 띈 것",
    "갖고 싶은 물건",
    "어릴 적의 엉뚱한 추억",
    "최근에 들은 노래나 흥얼거리는 멜로디",
    "자기만의 이상한 습관 고백",
    "오늘 날씨나 계절에 대한 감상",
    "상대방의 첫인상에 대한 이야기",
    "최근에 한 작은 실수담",
    "마을 생활에 대한 소소한 감상",
    "별자리나 운세 이야기",
    "상대방 옷차림이나 분위기 칭찬",
]


def fuzzy_friendship(v: float) -> str:
    return friendship_label(v)


def fuzzy_romance(v: float) -> str:
    label = romance_label(v)
    return label + " 마음" if label else "이성으로는 의식하지 않음"


def fuzzy_hunger(v: float) -> str:
    if v >= 80:
        return "몹시 배고픔"
    if v >= 50:
        return "슬슬 배고픔"
    return "배는 부른 편"


def character_block(char: Character) -> str:
    habits = ", ".join(f"{k}: \"{v}\"" for k, v in char.speech_habits.items() if v)
    lines = [
        f"## 캐릭터: {char.name}",
        f"- 성별: {'남성' if char.gender == 'M' else '여성'}, 혈액형 {char.blood_type}",
        f"- 성격: {personality_label(char)} ({intensity_hints(char)})",
        f"- 특이도: {weirdness_hint(char)}",
        f"- 평소 모습: {idle_trait(char)}" +
        (f", 걸음걸이 {char.mini_traits['walking']}" if char.mini_traits.get("walking") else ""),
        f"- 말버릇: {habits}" if habits else "",
        # 배고픔은 눈에 띄는 상태일 때만 주입 (항상 넣으면 대화가 온통 밥 이야기가 됨)
        f"- 지금 기분: {char.mood.label()}" +
        (f", {fuzzy_hunger(char.hunger)}" if char.hunger >= 50 else "") +
        (", 절망에 빠져 있음" if char.despair else ""),
    ]
    return "\n".join(l for l in lines if l)


def relation_block(state: GameState, a: Character, b: Character) -> str:
    rel_ab = a.rel(b.id)
    rel_ba = b.rel(a.id)
    lines = [
        f"## 두 사람의 관계",
        f"- {a.name} → {b.name}: {fuzzy_friendship(rel_ab.friendship)}, {fuzzy_romance(rel_ab.romance)}",
        f"- {b.name} → {a.name}: {fuzzy_friendship(rel_ba.friendship)}, {fuzzy_romance(rel_ba.romance)}",
    ]
    if a.slots["best_friend"] == b.id:
        lines.append("- 두 사람은 베스트 프렌드다.")
    if a.slots["lover"] == b.id:
        lines.append("- 두 사람은 연인이다.")
    if a.slots["enemy"] == b.id:
        lines.append("- 두 사람은 서로 원수지간이다.")
    for tag in a.ex_lovers:
        if tag.target == b.id:
            lines.append(f"- 두 사람은 전 연인이다 (이별 사유: {BREAKUP_REASONS[tag.reason]}). "
                         "어색함, 미련, 담담함 등을 대사 톤에 반영할 것.")
    nick_ab = a.nicknames.get(b.id)
    nick_ba = b.nicknames.get(a.id)
    if nick_ab:
        lines.append(f"- {a.name}은(는) {b.name}을(를) '{nick_ab}'(이)라고 부른다.")
    if nick_ba:
        lines.append(f"- {b.name}은(는) {a.name}을(를) '{nick_ba}'(이)라고 부른다.")
    return "\n".join(lines)


def memory_block(state: GameState, a: Character, b: Character, limit: int = 5) -> str:
    events = state.shared_events(a.id, b.id, limit)
    summaries = [e.summary for e in events if e.summary]
    if not summaries:
        return ""
    return "## 두 사람의 최근 기억\n" + "\n".join(f"- (day {e.day}) {e.summary}"
                                                  for e in events if e.summary)


def situation_block(state: GameState, location_name: str) -> str:
    hour = state.minutes // 60
    timeband = "아침" if hour < 11 else "낮" if hour < 17 else "저녁" if hour < 21 else "밤"
    return f"## 상황\n- 장소: {location_name}\n- 시간대: {timeband} (day {state.day})"


def conversation_prompt(state: GameState, a: Character, b: Character,
                        location_name: str, private: bool = False,
                        topic: str = "",
                        spark_candidate: Optional[Tuple[Character, Character]] = None) -> str:
    extra = ("- 프라이빗한 자리이므로 비밀, 고민, 연애 상담 같은 깊은 이야기를 해도 된다.\n"
             if private else "")
    topic_line = (f"- 대화 주제 힌트: \"{topic}\" (자연스럽다면 이 주제로, 어색하면 달라도 됨)\n"
                  if topic else "")
    # 반함 후보 (숫자 테이블이 게이트, 반할지 말지는 LLM이 맥락 판단)
    spark_line = ""
    spark_field = ""
    if spark_candidate:
        x, y = spark_candidate
        # 발동 확률은 숫자 테이블이 이미 통과시킴. LLM은 연출 + 거부권만 가짐.
        # 단, 계기는 반드시 이 대화 내용 자체에서 나와야 함 (대화가 곧 반하게 된 이유)
        spark_line = (f"- 오늘따라 {y.name}이(가) {x.name}의 눈에 들어오는 날이다. "
                      f"이 대화에서 {x.name}이(가) {y.name}에게 문득 반해버릴 절호의 순간이다. "
                      f"대화가 나쁜 분위기로 흐르지 않는 한 {x.name}이(가) 반한 것으로 (spark=true) 하라. "
                      f"반하게 된 계기는 이 대화 속에 실제로 있어야 한다 — {y.name}의 어떤 말, 반응, "
                      "엉뚱한 행동이 마음을 건드렸는지 대사 흐름에서 드러나게 하고, "
                      "그 떨림은 아주 살짝만 묻어나게 (대놓고 고백 금지). 흐름상 도저히 어색할 때만 false.\n")
        spark_field = (f', "spark": {x.name}이(가) {y.name}에게 반했으면 true 아니면 false'
                       ', "spark_reason": spark가 true면 이 대화의 어떤 순간이 계기였는지 짧게'
                       ' ("~해서" 꼴, 예: "별자리 얘기에 눈을 반짝여서"), false면 ""'
                       f', "spark_monologue": spark가 true면 대화가 끝나고 혼자 남은 {x.name}이(가) '
                       f'작게 중얼거리는 감상평 한 줄 — {y.name}의 어떤 점이 좋았는지 곱씹는 내용을 '
                       f'{x.name}의 말투로 1~2문장 (본인도 어리둥절한 느낌), false면 ""')
    return f"""너는 관찰형 시뮬레이션 게임의 대사 생성기다. 마을 주민 두 명의 자연스러운 대화를 만들어라.

{character_block(a)}

{character_block(b)}

{relation_block(state, a, b)}

{memory_block(state, a, b)}

{situation_block(state, location_name)}

## 규칙
{GUARDRAILS}
{topic_line}{spark_line}{extra}
## 출력 형식 (JSON만 출력, 다른 텍스트 금지)
{{"lines": [{{"speaker": "이름", "text": "대사"}}, ...3~5개...], "summary": "이 대화를 한 문장으로 요약 (이벤트 로그용)"{spark_field}}}"""


def spark_encounter_prompt(state: GameState, a: Character, b: Character,
                           location_name: str, reason: str) -> str:
    # 뜬금 반함: 반함 자체는 시스템이 이미 확정. LLM은 마주침 장면 연출만 담당
    return f"""너는 관찰형 시뮬레이션 게임의 대사 생성기다. 두 주민이 {location_name}에서 우연히 마주쳤다.
이 마주침에서 {a.name}이(가) {b.name}에게 문득 반해버렸다. 계기: "{reason}".

{character_block(a)}

{character_block(b)}

{relation_block(state, a, b)}

{memory_block(state, a, b)}

{situation_block(state, location_name)}

## 규칙
{GUARDRAILS}
- 계기 장면("{reason}")이 대화 속에서 자연스럽게 드러나게 할 것.
- {a.name}의 대사에 설렘이 아주 살짝만 묻어나게. 본인도 어리둥절한 느낌 (대놓고 고백 금지).
- {b.name}은(는) 아무것도 눈치채지 못하거나 살짝 갸웃하는 정도.

## 출력 형식 (JSON만 출력, 다른 텍스트 금지)
{{"lines": [{{"speaker": "이름", "text": "대사"}}, ...2~4개...], "summary": "이 마주침을 한 문장으로 요약",
"spark_monologue": "마주침이 끝나고 혼자 남은 {a.name}이(가) 작게 중얼거리는 감상평 한 줄 ({b.name}의 어떤 점이 좋았는지 곱씹는 내용, 본인 말투로 1~2문장)"}}"""


def confession_prompt(state: GameState, a: Character, b: Character,
                      location_name: str, retry_count: int) -> str:
    retry_note = (f"- {a.name}은(는) 이전에 {retry_count}번 거절당했지만 다시 용기를 냈다.\n"
                  if retry_count else "")
    lover_note = ""
    if b.slots["lover"] is not None and b.slots["lover"] != a.id:
        lover = state.characters[b.slots["lover"]]
        lover_note = f"- 주의: {b.name}에게는 이미 연인({lover.name})이 있다. 수락하면 기존 연인과 헤어지게 된다.\n"

    return f"""너는 관찰형 시뮬레이션 게임의 이벤트 판정기다. {a.name}이(가) {b.name}에게 고백한다.
{b.name}의 입장에서 수락할지 거절할지 판단하고, 고백 장면의 대사를 만들어라.

{character_block(a)}

{character_block(b)}

{relation_block(state, a, b)}

{memory_block(state, a, b)}

{situation_block(state, location_name)}

## 판단 가이드
- 수치 기반이 아닌, 캐릭터의 내면과 현재 상황을 종합해서 판단하라.
- 같은 사람이라도 그날의 기분과 상황에 따라 답이 달라질 수 있다.
{retry_note}{lover_note}
## 규칙
{GUARDRAILS}

## 출력 형식 (JSON만 출력, 다른 텍스트 금지)
{{"decision": "accept" 또는 "reject", "reason": "{b.name}이(가) 그렇게 결정한 속마음 한 문장",
"lines": [{{"speaker": "이름", "text": "대사"}}, ...고백 장면 3~5개...],
"summary": "이 장면을 한 문장으로 요약"}}"""


def fight_prompt(state: GameState, a: Character, b: Character, location_name: str) -> str:
    return f"""너는 관찰형 시뮬레이션 게임의 대사 생성기다. 사이가 좋지 않은 두 주민이 부딪혀 말다툼이 벌어졌다.
두 사람의 성격에 맞게 싸움 장면을 만들어라. 과격한 폭력/욕설은 금지, 유치하고 소소한 말다툼 수준.

{character_block(a)}

{character_block(b)}

{relation_block(state, a, b)}

{memory_block(state, a, b)}

{situation_block(state, location_name)}

## 규칙
{GUARDRAILS}

## 출력 형식 (JSON만 출력, 다른 텍스트 금지)
{{"lines": [{{"speaker": "이름", "text": "대사"}}, ...3~4개...], "summary": "무엇 때문에 싸웠는지 한 문장 요약"}}"""


def jealousy_prompt(state: GameState, a: Character, other: Character,
                    target: Character, rival: Character,
                    location_name: str, mode: str) -> str:
    # 02 문서 '질투 시스템': A→target 연심이 있는데 target은 rival의 연인.
    # 숫자 테이블이 발동을 확정했고, LLM은 질투가 배어나는 장면 연출만 담당
    if mode == "confront":
        situation = (f"{a.name}은(는) {target.name}을(를) 남몰래 좋아하지만, "
                     f"{target.name}의 연인은 {rival.name}이다. "
                     f"질투가 난 {a.name}이(가) 연적 {rival.name}에게 괜히 날카롭게 군다.")
        rules = (f"- {a.name}은(는) 질투를 들키기 싫어서 본심은 숨기고 사소한 트집을 잡는다 "
                 f"(인사가 건방지다, 자리를 차지했다 등 유치한 수준).\n"
                 f"- {rival.name}은(는) 영문을 모르거나, 살짝 눈치챈 듯한 반응도 좋다.\n"
                 f"- {target.name}의 이름이 대화에 직접 나오면 어색하므로 살짝 스치듯만.")
    else:
        situation = (f"{a.name}은(는) {target.name}을(를) 남몰래 좋아하지만, "
                     f"{target.name}의 연인은 {rival.name}이다. "
                     f"속이 상한 {a.name}이(가) 친한 {other.name}에게 하소연한다.")
        rules = (f"- {a.name}은(는) 두 사람 커플 이야기에 시무룩해하며 솔직하게 속앓이를 털어놓는다.\n"
                 f"- {other.name}은(는) 자기 성격대로 위로하거나, 엉뚱한 해결책을 내거나, 같이 흉을 본다.\n"
                 "- 신파 금지. 토모다치 컬렉션답게 짠하면서도 귀엽게.")

    return f"""너는 관찰형 시뮬레이션 게임의 대사 생성기다. 질투 장면을 연출한다.

## 상황
{situation}

{character_block(a)}

{character_block(other)}

{relation_block(state, a, other)}

{memory_block(state, a, other)}

{situation_block(state, location_name)}

## 규칙
{rules}
{GUARDRAILS}

## 출력 형식 (JSON만 출력, 다른 텍스트 금지)
{{"lines": [{{"speaker": "이름", "text": "대사"}}, ...3~4개...], "summary": "이 장면 한 문장 요약 (질투 맥락 포함)"}}"""


def photo_prompt(state: GameState, char: Character, subject: str) -> str:
    # 도구 아이템 '카메라' (05 문서): 주민이 사진을 찍어옴 (제목 포함, 갤러리 저장)
    return f"""너는 관찰형 시뮬레이션 게임의 콘텐츠 생성기다. 주민이 카메라를 받아 사진을 한 장 찍었다.

{character_block(char)}

## 피사체
{subject}

## 규칙
- 사진 제목은 이 캐릭터의 성격이 묻어나는 짧은 한 문장 (10자 내외, 엉뚱해도 좋음).
- 감상은 캐릭터 말투로 1문장.

## 출력 형식 (JSON만 출력, 다른 텍스트 금지)
{{"title": "사진 제목", "caption": "찍고 나서 한마디"}}"""


def cook_prompt(state: GameState, char: Character) -> str:
    # 도구 아이템 '프라이팬' (05 문서): 주민이 주방에서 랜덤 요리 → 카탈로그 추가
    return f"""너는 관찰형 시뮬레이션 게임의 콘텐츠 생성기다. 주민이 프라이팬을 받아 즉흥 요리를 했다.

{character_block(char)}

## 규칙
- 요리 이름은 캐릭터 성격이 드러나는 창작 요리 (실존 요리를 살짝 비틀어도 좋음, 15자 내외).
- 완성 소감은 캐릭터 말투로 1문장. 요리 실력은 복불복 (대성공/평범/수상한 결과물 모두 가능).

## 출력 형식 (JSON만 출력, 다른 텍스트 금지)
{{"dish": "요리 이름", "comment": "완성하고 한마디"}}"""


def news_prompt(state: GameState, announcer: Character, event_summary: str) -> str:
    return f"""너는 마을 방송국 뉴스 대본 작가다. 아나운서가 어제 있었던 일을 한 건 브리핑한다.

{character_block(announcer)}

## 브리핑할 사건
{event_summary}

## 규칙
- 아나운서의 성격이 묻어나는 말투로, 2~3문장의 짧은 브리핑.
- 마을 뉴스답게 약간 호들갑스럽거나 정겨운 톤. 토모다치 컬렉션처럼 귀엽고 순박하게.

## 출력 형식 (JSON만 출력, 다른 텍스트 금지)
{{"text": "뉴스 브리핑 내용"}}"""


def weird_news_prompt(state: GameState, announcer: Character) -> str:
    return f"""너는 마을 방송국의 병맛 뉴스 대본 작가다. 마을이나 주민 관계와 무관한, 쓸데없고 황당한 가짜 뉴스를 한 건 만들어라.

{character_block(announcer)}

## 규칙
- 2~3문장. 일상 소재(분수대, 식료품점, 공원, 비둘기 등)를 엉뚱하게 비틀 것.
- 특정 주민 이름은 언급하지 말 것.

## 출력 형식 (JSON만 출력, 다른 텍스트 금지)
{{"text": "병맛 뉴스 내용"}}"""
