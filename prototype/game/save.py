# 세이브/로드 (14-data-schema.md의 파일 분리 구조를 따름)
# game.json / char_{id}.json / events.json
from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Optional

from .models import Bubble, Character, ExLoverTag, GameEvent, GameState, Mood, RelValues


def save_game(state: GameState, save_dir: str) -> None:
    os.makedirs(save_dir, exist_ok=True)

    game = {
        "island_name": state.village_name,
        "day_count": state.day,
        "minutes": state.minutes,
        "money": state.money,
        "today_announcer": state.announcer,
        "next_event_id": state.next_event_id,
        "bubbles": [asdict(b) for b in state.bubbles],
        "photos": state.photos,
        "dishes": state.dishes,
    }
    with open(os.path.join(save_dir, "game.json"), "w", encoding="utf-8") as f:
        json.dump(game, f, ensure_ascii=False, indent=2)

    for char in state.characters.values():
        data = {
            "id": char.id,
            "profile": {
                "name": char.name, "gender": char.gender,
                "birthday": char.birthday, "blood_type": char.blood_type,
                "personality": {
                    "movement": char.movement, "speech": char.speech,
                    "expressiveness": char.expressiveness,
                    "attitude": char.attitude, "overall": char.overall,
                },
            },
            "preferences": {
                "food_ranks": char.food_ranks,
                "food_eaten": char.food_eaten,
            },
            "state": {
                "satisfaction": char.satisfaction, "level": char.level,
                "hunger": char.hunger,
                "mood": asdict(char.mood),
                "current_location": char.location,
            },
            "customizable": {
                "speech_habits": char.speech_habits,
                "mini_traits": char.mini_traits,
                "nicknames": {str(k): v for k, v in char.nicknames.items()},
            },
            "relationships": {str(k): asdict(v) for k, v in char.relationships.items()},
            "slots": char.slots,
            "tags": {"ex_lovers": [asdict(t) for t in char.ex_lovers]},
            "records": {"confession_count": {str(k): v for k, v in char.confession_count.items()}},
            "seed": char.seed,
        }
        with open(os.path.join(save_dir, f"char_{char.id}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    with open(os.path.join(save_dir, "events.json"), "w", encoding="utf-8") as f:
        json.dump([asdict(e) for e in state.events], f, ensure_ascii=False, indent=2)


def load_game(save_dir: str) -> Optional[GameState]:
    game_path = os.path.join(save_dir, "game.json")
    if not os.path.exists(game_path):
        return None

    with open(game_path, encoding="utf-8") as f:
        game = json.load(f)
    state = GameState(
        village_name=game["island_name"], day=game["day_count"],
        minutes=game["minutes"], money=game["money"],
        announcer=game.get("today_announcer"),
        next_event_id=game.get("next_event_id", 1),
    )
    state.bubbles = [Bubble(**b) for b in game.get("bubbles", [])]
    state.photos = game.get("photos", [])
    state.dishes = game.get("dishes", [])

    for fname in sorted(os.listdir(save_dir)):
        if not (fname.startswith("char_") and fname.endswith(".json")):
            continue
        with open(os.path.join(save_dir, fname), encoding="utf-8") as f:
            d = json.load(f)
        p = d["profile"]
        char = Character(
            id=d["id"], name=p["name"], gender=p["gender"],
            birthday=p["birthday"], blood_type=p["blood_type"],
            **p["personality"],
        )
        char.food_ranks = d["preferences"]["food_ranks"]
        char.food_eaten = d["preferences"]["food_eaten"]
        s = d["state"]
        char.satisfaction = s["satisfaction"]
        char.level = s["level"]
        char.hunger = s["hunger"]
        char.mood = Mood(**s["mood"])
        char.location = s["current_location"]
        c = d["customizable"]
        char.speech_habits = c["speech_habits"]
        char.mini_traits = c["mini_traits"]
        char.nicknames = {int(k): v for k, v in c["nicknames"].items()}
        char.relationships = {int(k): RelValues(**v) for k, v in d["relationships"].items()}
        # 반함 도입 전 세이브 호환: 이미 연심이 자라 있던 상대는 반한 상태로 간주
        for rel in char.relationships.values():
            if rel.romance >= 10:
                rel.spark = True
        char.slots = d["slots"]
        char.ex_lovers = [ExLoverTag(**t) for t in d["tags"]["ex_lovers"]]
        char.confession_count = {int(k): v for k, v in d["records"]["confession_count"].items()}
        char.seed = d["seed"]
        state.characters[char.id] = char

    events_path = os.path.join(save_dir, "events.json")
    if os.path.exists(events_path):
        with open(events_path, encoding="utf-8") as f:
            state.events = [GameEvent(**e) for e in json.load(f)]

    return state
