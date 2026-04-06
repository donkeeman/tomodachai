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
        id="char_1", name="민수", personality_code="nori_dynamo",
        backstory="동네 반장을 맡고 있는 활발한 청년. 모임을 좋아한다.",
        birthday="03-15", blood_type="B", gender="남성",
        favorite_color="파란색",
        speech_habits={
            "normal": "~인 거지",
            "happy": "이야, 진짜 최고인 거지!",
            "angry": "아 진짜, 이게 말이 돼?",
            "sad": "...뭐, 어쩔 수 없는 거지.",
            "worried": "이거 괜찮긴 한 건지 모르겠는 거지.",
        },
        mini_personality=["걸을 때 팔을 크게 흔든다", "밥 먹을 때 먼저 주변에 권한다", "대화 중 자주 손뼉을 친다"],
    ),
    Character(
        id="char_2", name="지은", personality_code="nagomi_dreamer",
        backstory="동네 카페를 운영하는 몽상가. 창밖을 자주 바라본다.",
        birthday="11-02", blood_type="A", gender="여성",
        favorite_color="라벤더",
        speech_habits={
            "normal": "그치~?",
            "happy": "어머, 이런 날도 있구나~",
            "angry": "...그게 맞는 말인 거야?",
            "sad": "뭔가... 괜찮지 않은 것 같아.",
            "worried": "어떡하지, 이거 좀 이상한 것 같은데~",
        },
        mini_personality=["멍하게 창밖을 바라보는 버릇이 있다", "커피를 홀짝홀짝 천천히 마신다", "말하다 종종 중간에 멈추고 생각에 잠긴다"],
    ),
    Character(
        id="char_3", name="태호", personality_code="nori_extrovert",
        backstory="자유분방한 대학생. 새로운 자극을 찾아다닌다.",
        birthday="07-28", blood_type="O", gender="남성",
        favorite_color="형광 노란색",
        speech_habits={
            "normal": "ㅋㅋ 뭐 어때",
            "happy": "ㅋㅋㅋ 이거 실화냐고!!",
            "angry": "아 진짜 ㅋㅋ 웃기고 있어",
            "sad": "...뭐야 갑자기 왜 이래",
            "worried": "ㅋ 이거 좀 아닌 것 같긴 한데",
        },
        mini_personality=["계단을 두 칸씩 뛰어오른다", "음식을 빠르게 먹는다", "대화 중 수시로 핸드폰을 꺼냈다 넣었다 한다"],
    ),
    Character(
        id="char_4", name="순자", personality_code="nagomi_carer",
        backstory="동네에서 오래 산 20대 후반 여성. 정이 많아서 모든 주민의 안부가 궁금하다.",
        birthday="09-09", blood_type="AB", gender="여성",
        favorite_color="연두색",
        speech_habits={
            "normal": "아이고~",
            "happy": "아이고, 이래서 사는 맛이 나지~",
            "angry": "아이고, 진짜 못 봐주겠네.",
            "sad": "아이고... 어쩌다 이렇게 됐어.",
            "worried": "아이고, 이거 어떡하나, 어떡해.",
        },
        mini_personality=["길에서 아는 사람 보면 무조건 먼저 인사한다", "뭔가 줄 게 없나 주머니를 뒤지는 버릇이 있다", "밥 먹을 때 반찬을 골고루 먹는다"],
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
