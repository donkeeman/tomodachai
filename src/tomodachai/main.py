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
        id="char_1", name="민수", personality_code="EWSOB",
        speech_habit="~인 거지",
        backstory="동네 반장을 맡고 있는 활발한 청년. 모임을 좋아한다.",
    ),
    Character(
        id="char_2", name="지은", personality_code="IWVOG",
        speech_habit="그치~?",
        backstory="동네 카페를 운영하는 몽상가. 창밖을 자주 바라본다.",
    ),
    Character(
        id="char_3", name="태호", personality_code="ECVOB",
        speech_habit="ㅋㅋ",
        backstory="자유분방한 대학생. 새로운 자극을 찾아다닌다.",
    ),
    Character(
        id="char_4", name="순자", personality_code="EWSTG",
        speech_habit="아이고~",
        backstory="동네 터줏대감 할머니. 모든 주민의 안부가 궁금하다.",
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
