from __future__ import annotations

import argparse
from pathlib import Path

from tomodachai.character import (
    Character,
    CharacterState,
    Customizable,
    Personality,
    Profile,
    SpeechHabits,
)
from tomodachai.config import load_config
from tomodachai.llm import LLMClient
from tomodachai.personality import load_personalities
from tomodachai.simulation import Simulation

_DEMO_CHARACTERS = [
    Character(
        id=1,
        profile=Profile(
            name="민수",
            birthday="03-15",
            blood_type="B",
            gender="남",
            personality=Personality(movement=8, speech=8, expressiveness=7, attitude=5, overall=5),
        ),
        state=CharacterState(),
        customizable=Customizable(
            speech_habits=SpeechHabits(
                normal="~인 거지",
                happy="완전 좋은 거지!",
                angry="이건 아닌 거지...",
                sad="좀 힘든 거지.",
                worried="괜찮을까, 이거.",
            ),
        ),
    ),
    Character(
        id=2,
        profile=Profile(
            name="지은",
            birthday="11-02",
            blood_type="A",
            gender="여",
            personality=Personality(movement=2, speech=2, expressiveness=8, attitude=8, overall=5),
        ),
        state=CharacterState(),
        customizable=Customizable(
            speech_habits=SpeechHabits(
                normal="그치~?",
                happy="좋네요, 그치~?",
                angry="그건 좀... 그치?",
                sad="흠... 그치.",
                worried="어떡하지, 그치?",
            ),
        ),
    ),
]


def _print_step(step_num: int, events: list[dict]) -> None:
    print(f"\n{'=' * 60}")
    print(f"  스텝 {step_num}")
    print(f"{'=' * 60}")
    if not events:
        print("  (아무 일도 일어나지 않았다)")
        return
    for event in events:
        etype = event["type"]
        if etype == "conversation":
            result = event["result"]
            print(f"\n  [{event.get('location', '?')}] {result.summary}")
            for line in result.dialogue:
                print(f"  {line.speaker}: {line.text}")
            for name, deltas in result.deltas.items():
                parts = [f"{k}:{v:+.0f}" for k, v in deltas.items() if v != 0]
                if parts:
                    print(f"  [{name}] {', '.join(parts)}")
        elif etype == "fight":
            print(f"\n  [싸움] {event.get('summary', '')}")
        elif etype.startswith("confession"):
            label = "고백 성공" if etype == "confession_success" else "고백 실패"
            print(f"\n  [{label}] {event.get('summary', '')}")
        else:
            print(f"\n  {event.get('summary', etype)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI 우리 동네 이야기")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--steps", type=int, default=6)
    args = parser.parse_args()

    config = load_config(args.config)
    personalities = load_personalities()
    llm = LLMClient(config.llm)

    print("AI 우리 동네 이야기")
    print(f"모델: {config.llm.model}")
    print(f"주민: {', '.join(c.name for c in _DEMO_CHARACTERS)}")

    sim = Simulation(
        config=config,
        characters=_DEMO_CHARACTERS,
        llm=llm,
        personalities=personalities,
    )

    for i in range(args.steps):
        events = sim.step()
        _print_step(i, events)

    print(f"\n{'=' * 60}")
    print("  시뮬레이션 종료 — 최종 관계")
    print(f"{'=' * 60}")
    for a_id, b_id, rel in sim.relationships.all_pairs():
        a_name = next(c.name for c in _DEMO_CHARACTERS if c.id == a_id)
        b_name = next(c.name for c in _DEMO_CHARACTERS if c.id == b_id)
        print(
            f"  {a_name} -> {b_name}: 우정={rel.friendship:.0f} "
            f"로맨스={rel.romance:.0f} ({rel.get_status_text()})"
        )


if __name__ == "__main__":
    main()
