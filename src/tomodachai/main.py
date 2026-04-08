from __future__ import annotations

import argparse
from pathlib import Path

from tomodachai.character import Character, CharacterState, Customizable, Preferences, Profile, SpeechHabits
from tomodachai.config import load_config
from tomodachai.llm import LLMClient
from tomodachai.personality import load_personalities
from tomodachai.simulation import Simulation

_DEMO_CHARACTERS = [
    Character(
        id=1,
        personality_code="nori_dynamo",
        profile=Profile(
            name="민수",
            birthday="03-15",
            blood_type="B",
            gender="남성",
            favorite_color="파란색",
        ),
        state=CharacterState(satisfaction=50.0, hunger=0.0),
        customizable=Customizable(
            speech_habits=SpeechHabits(
                normal="~인 거지",
                happy="이야, 진짜 최고인 거지!",
                angry="아 진짜, 이게 말이 돼?",
                sad="...뭐, 어쩔 수 없는 거지.",
                worried="이거 괜찮긴 한 건지 모르겠는 거지.",
            ),
        ),
    ),
    Character(
        id=2,
        personality_code="nagomi_dreamer",
        profile=Profile(
            name="지은",
            birthday="11-02",
            blood_type="A",
            gender="여성",
            favorite_color="라벤더",
        ),
        state=CharacterState(satisfaction=50.0, hunger=0.0),
        customizable=Customizable(
            speech_habits=SpeechHabits(
                normal="그치~?",
                happy="어머, 이런 날도 있구나~",
                angry="...그게 맞는 말인 거야?",
                sad="뭔가... 괜찮지 않은 것 같아.",
                worried="어떡하지, 이거 좀 이상한 것 같은데~",
            ),
        ),
    ),
    Character(
        id=3,
        personality_code="nori_extrovert",
        profile=Profile(
            name="태호",
            birthday="07-28",
            blood_type="O",
            gender="남성",
            favorite_color="형광 노란색",
        ),
        state=CharacterState(satisfaction=50.0, hunger=0.0),
        customizable=Customizable(
            speech_habits=SpeechHabits(
                normal="ㅋㅋ 뭐 어때",
                happy="ㅋㅋㅋ 이거 실화냐고!!",
                angry="아 진짜 ㅋㅋ 웃기고 있어",
                sad="...뭐야 갑자기 왜 이래",
                worried="ㅋ 이거 좀 아닌 것 같긴 한데",
            ),
        ),
    ),
    Character(
        id=4,
        personality_code="nagomi_carer",
        profile=Profile(
            name="순자",
            birthday="09-09",
            blood_type="AB",
            gender="여성",
            favorite_color="연두색",
        ),
        state=CharacterState(satisfaction=50.0, hunger=0.0),
        customizable=Customizable(
            speech_habits=SpeechHabits(
                normal="아이고~",
                happy="아이고, 이래서 사는 맛이 나지~",
                angry="아이고, 진짜 못 봐주겠네.",
                sad="아이고... 어쩌다 이렇게 됐어.",
                worried="아이고, 이거 어떡하나, 어떡해.",
            ),
        ),
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
