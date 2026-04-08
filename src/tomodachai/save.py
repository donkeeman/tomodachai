"""Save/load system for tomodachai.

Manual save only — no autosave.
Supports 3 slots + crash-recovery temp slot.

Directory layout:
    saves/
      slot_1/
        game.json
        characters/
          1.json
          2.json
          ...
        events.json
        relationships.json
      slot_2/
      slot_3/
      _temp/          ← crash recovery
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from tomodachai.character import (
    Appearance,
    AppearanceAdjust,
    Body,
    Character,
    CharacterState,
    ClothingPreference,
    Customizable,
    Eye,
    Eyebrow,
    Hair,
    InteriorPreference,
    MiniTrait,
    MiniTraits,
    Mood,
    Mouth,
    Nose,
    PersonalityGroup,
    Preferences,
    Profile,
    Records,
    SpeechHabits,
)
from tomodachai.character import Personality as CharacterPersonality
from tomodachai.character import Voice as CharacterVoice
from tomodachai.memory import MemoryStore, SocialEvent
from tomodachai.relationship import (
    BreakupReason,
    ExLoverTag,
    Fight,
    Relationship,
    RelationshipEvent,
    RelationshipSlots,
    RelationshipStage,
    RelationshipTracker,
)

# ---------------------------------------------------------------------------
# Slot constants
# ---------------------------------------------------------------------------

NUM_SLOTS = 3
_TEMP_DIR = "_temp"
_META_FILE = "meta.json"


# ---------------------------------------------------------------------------
# Pydantic schemas used by SaveManager
# ---------------------------------------------------------------------------


class SlotInfo(BaseModel):
    slot: int
    exists: bool
    island_name: str = ""
    day_count: int = 0
    last_saved: str = ""  # ISO 8601


# ---------------------------------------------------------------------------
# Serialization helpers — Character
# ---------------------------------------------------------------------------


def _serialize_character(char: Character) -> dict[str, Any]:
    """Convert a Character to the char_{id}.json mock format."""
    p = char.profile
    app = p.appearance

    def _adj(a: AppearanceAdjust) -> dict[str, int]:
        return {"spacing": a.spacing, "height": a.height, "size": a.size, "angle": a.angle}

    appearance: dict[str, Any] = {
        "face_shape": app.face_shape,
        "skin_color": app.skin_color,
        "eye": {
            "base": app.eye.base,
            "lash": app.eye.lash,
            "color": app.eye.color,
            "adjust": _adj(app.eye.adjust),
        },
        "eyebrow": {
            "id": app.eyebrow.id,
            "adjust": _adj(app.eyebrow.adjust),
        },
        "nose": {
            "id": app.nose.id,
            "adjust": {"height": app.nose.adjust.height, "size": app.nose.adjust.size},
        },
        "mouth": {
            "id": app.mouth.id,
            "adjust": {"height": app.mouth.adjust.height, "size": app.mouth.adjust.size},
        },
        "hair": {
            "front": app.hair.front,
            "back": app.hair.back,
            "color": app.hair.color,
        },
        "glasses": app.glasses,
        "body": {"height": app.body.height, "build": app.body.build},
    }

    profile: dict[str, Any] = {
        "name": p.name,
        "birthday": p.birthday,
        "blood_type": p.blood_type,
        "favorite_color": p.favorite_color,
        "gender": p.gender,
        "appearance": appearance,
        "personality": {
            "movement": p.personality.movement,
            "speech": p.personality.speech,
            "expressiveness": p.personality.expressiveness,
            "attitude": p.personality.attitude,
            "overall": p.personality.overall,
        },
        "voice": {
            "preset": p.voice.preset,
            "pitch": p.voice.pitch,
            "speed": p.voice.speed,
            "quality": p.voice.quality,
            "tone": p.voice.tone,
            "accent": p.voice.accent,
            "intonation": p.voice.intonation,
        },
    }

    pref = char.preferences
    preferences: dict[str, Any] = {
        "food_ranks": pref.food_ranks,
        "food_eaten": pref.food_eaten,
        "clothing": {
            "likes": pref.clothing.likes,
            "dislikes": pref.clothing.dislikes,
        },
        "interior": {
            "likes": pref.interior.likes,
            "dislikes": pref.interior.dislikes,
        },
        "personality_group": {
            "group": pref.personality_group.group,
            "is_positive": pref.personality_group.is_positive,
        },
    }

    st = char.state
    state: dict[str, Any] = {
        "satisfaction": st.satisfaction,
        "level": st.level,
        "hunger": st.hunger,
        "mood": {
            "happiness": st.mood.happiness,
            "energy": st.mood.energy,
            "stress": st.mood.stress,
        },
        "sick": st.sick,
        "current_location": st.current_location,
        "current_outfit": st.current_outfit,
        "current_interior": st.current_interior,
        "photo_frame": st.photo_frame,
    }

    cust = char.customizable
    sh = cust.speech_habits
    customizable: dict[str, Any] = {
        "speech_habits": {
            "normal": sh.normal,
            "happy": sh.happy,
            "angry": sh.angry,
            "sad": sh.sad,
            "worried": sh.worried,
        },
        "mini_traits": {
            "walking": {
                "owned": cust.mini_traits.walking.owned,
                "active": cust.mini_traits.walking.active,
            },
            "eating": {
                "owned": cust.mini_traits.eating.owned,
                "active": cust.mini_traits.eating.active,
            },
            "idle": {
                "owned": cust.mini_traits.idle.owned,
                "active": cust.mini_traits.idle.active,
            },
        },
        "nicknames": cust.nicknames,
        "songs": cust.songs,
    }

    rec = char.records
    records: dict[str, Any] = {
        "treasure_collection": rec.treasure_collection,
        "confession_count": rec.confession_count,
        "photos": rec.photos,
    }

    return {
        "id": char.id,
        "personality_code": char.personality_code,
        "profile": profile,
        "preferences": preferences,
        "state": state,
        "customizable": customizable,
        "records": records,
    }


def _deserialize_character(data: dict[str, Any]) -> Character:
    """Reconstruct a Character from the char_{id}.json format."""
    return Character(**data)


# ---------------------------------------------------------------------------
# Serialization helpers — Relationships
# ---------------------------------------------------------------------------


def _serialize_relationships(tracker: RelationshipTracker) -> dict[str, Any]:
    """Serialize RelationshipTracker to a dict.

    Format mirrors char_{id}.json per-character relationship sections plus
    slots and tags, but aggregated into a single file.

    Structure:
    {
      "pairs": {
        "1:2": {"friendship": ..., "romance": ..., "stage": ..., "events": [...]},
        ...
      },
      "slots": {
        "1": {"best_friend": ..., "lover": ..., "enemy": ...},
        ...
      },
      "ex_lover_tags": {
        "1": [{"target": ..., "reason": ..., "day": ...}, ...],
        ...
      },
      "fights": [
        {"participants": [a, b], "cause": ..., "resolved": ..., "witnessed_by_player": ...},
        ...
      ]
    }
    """
    pairs: dict[str, Any] = {}
    for a, b, rel in tracker.all_pairs():
        key = f"{a}:{b}"
        events = [
            {
                "day": ev.day,
                "event_type": ev.event_type,
                "summary": ev.summary,
            }
            for ev in rel.event_log
        ]
        pairs[key] = {
            "friendship": rel.friendship,
            "romance": rel.romance,
            "stage": rel.stage.value,
            "events": events,
        }

    slots: dict[str, Any] = {}
    for char_id, sl in tracker._slots.items():
        slots[str(char_id)] = {
            "best_friend": sl.best_friend,
            "lover": sl.lover,
            "enemy": sl.enemy,
        }

    ex_lover_tags: dict[str, Any] = {}
    for char_id, tags in tracker._ex_lover_tags.items():
        ex_lover_tags[str(char_id)] = [
            {
                "target": t.target,
                "reason": t.reason.value,
                "day": t.day,
            }
            for t in tags
        ]

    fights = [
        {
            "participants": list(f.participants),
            "cause": f.cause,
            "resolved": f.resolved,
            "witnessed_by_player": f.witnessed_by_player,
        }
        for f in tracker._fights
    ]

    return {
        "pairs": pairs,
        "slots": slots,
        "ex_lover_tags": ex_lover_tags,
        "fights": fights,
    }


def _deserialize_relationships(data: dict[str, Any]) -> RelationshipTracker:
    """Reconstruct a RelationshipTracker from serialized dict."""
    tracker = RelationshipTracker()

    for key, rel_data in data.get("pairs", {}).items():
        parts = key.split(":", 1)
        a, b = int(parts[0]), int(parts[1])
        events = [
            RelationshipEvent(
                day=ev["day"],
                event_type=ev["event_type"],
                summary=ev["summary"],
            )
            for ev in rel_data.get("events", [])
        ]
        rel = Relationship(
            friendship=rel_data["friendship"],
            romance=rel_data["romance"],
            stage=RelationshipStage(rel_data["stage"]),
            event_log=events,
        )
        tracker._relationships[(a, b)] = rel

    for char_id_str, sl_data in data.get("slots", {}).items():
        char_id = int(char_id_str)
        tracker._slots[char_id] = RelationshipSlots(
            best_friend=sl_data.get("best_friend"),
            lover=sl_data.get("lover"),
            enemy=sl_data.get("enemy"),
        )

    for char_id_str, tags in data.get("ex_lover_tags", {}).items():
        char_id = int(char_id_str)
        tracker._ex_lover_tags[char_id] = [
            ExLoverTag(
                target=t["target"],
                reason=BreakupReason(t["reason"]),
                day=t["day"],
            )
            for t in tags
        ]

    for f_data in data.get("fights", []):
        participants_list = f_data["participants"]
        tracker._fights.append(
            Fight(
                participants=(participants_list[0], participants_list[1]),
                cause=f_data["cause"],
                resolved=f_data.get("resolved", False),
                witnessed_by_player=f_data.get("witnessed_by_player", False),
            )
        )

    return tracker


# ---------------------------------------------------------------------------
# Serialization helpers — MemoryStore (events)
# ---------------------------------------------------------------------------


def _serialize_events(memory: MemoryStore) -> list[dict[str, Any]]:
    """Serialize all events in MemoryStore."""
    return [
        {
            "tick": e.tick,
            "event_type": e.event_type,
            "participants": e.participants,
            "summary": e.summary,
            "emotional_impact": e.emotional_impact,
        }
        for e in memory._events
    ]


def _deserialize_events(data: list[dict[str, Any]]) -> MemoryStore:
    """Reconstruct a MemoryStore from serialized list."""
    store = MemoryStore()
    for item in data:
        store.add_event(
            SocialEvent(
                tick=item["tick"],
                event_type=item["event_type"],
                participants=item["participants"],
                summary=item["summary"],
                emotional_impact=item.get("emotional_impact", {}),
            )
        )
    return store


# ---------------------------------------------------------------------------
# SaveManager
# ---------------------------------------------------------------------------


class SaveManager:
    """Manages save slots on disk.

    Args:
        save_dir: Root directory for save data. Defaults to ``./saves``.
    """

    def __init__(self, save_dir: Path | str = Path("saves")) -> None:
        self.save_dir = Path(save_dir)

    # ------------------------------------------------------------------
    # Internal path helpers
    # ------------------------------------------------------------------

    def _slot_dir(self, slot: int) -> Path:
        self._validate_slot(slot)
        return self.save_dir / f"slot_{slot}"

    def _temp_dir(self) -> Path:
        return self.save_dir / _TEMP_DIR

    @staticmethod
    def _validate_slot(slot: int) -> None:
        if slot < 1 or slot > NUM_SLOTS:
            raise ValueError(f"slot must be between 1 and {NUM_SLOTS}, got {slot}")

    # ------------------------------------------------------------------
    # Low-level JSON helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _read_json(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # Core save/load
    # ------------------------------------------------------------------

    def _write_slot(self, slot_dir: Path, game_state: "GameState") -> None:  # noqa: F821
        """Write all save files into *slot_dir*."""
        from tomodachai.game_state import GameState  # local import avoids circular

        # 1. game.json
        game_data: dict[str, Any] = {
            "island_name": game_state.island_name,
            "day_count": game_state.day_count,
            "money": game_state.money,
            "time_flip": game_state.time_flip,
        }
        self._write_json(slot_dir / "game.json", game_data)

        # 2. characters/
        chars_dir = slot_dir / "characters"
        chars_dir.mkdir(parents=True, exist_ok=True)
        # Remove stale character files that no longer exist
        existing = {str(c.id) for c in game_state.characters}
        for old_file in chars_dir.glob("*.json"):
            if old_file.stem not in existing:
                old_file.unlink(missing_ok=True)
        for char in game_state.characters:
            char_data = _serialize_character(char)
            self._write_json(chars_dir / f"{char.id}.json", char_data)

        # 3. events.json
        events_data = _serialize_events(game_state.memory)
        self._write_json(slot_dir / "events.json", events_data)

        # 4. relationships.json
        rel_data = _serialize_relationships(game_state.relationships)
        self._write_json(slot_dir / "relationships.json", rel_data)

    def _read_slot(self, slot_dir: Path) -> "GameState":  # noqa: F821
        """Reconstruct a GameState from *slot_dir*."""
        from tomodachai.game_state import GameState

        # 1. game.json
        game_data = self._read_json(slot_dir / "game.json")
        gs = GameState(
            island_name=game_data.get("island_name", "우리 마을"),
            day_count=game_data.get("day_count", 0),
            money=game_data.get("money", 0),
            time_flip=game_data.get("time_flip", False),
        )

        # 2. characters/
        chars_dir = slot_dir / "characters"
        if chars_dir.exists():
            for char_file in sorted(chars_dir.glob("*.json")):
                try:
                    char_data = self._read_json(char_file)
                    char = _deserialize_character(char_data)
                    gs.add_character(char)
                except Exception as exc:  # noqa: BLE001
                    # Skip corrupted character files but don't abort
                    import warnings
                    warnings.warn(
                        f"Skipping corrupted character file {char_file}: {exc}",
                        stacklevel=2,
                    )

        # 3. events.json
        events_path = slot_dir / "events.json"
        if events_path.exists():
            try:
                events_data = self._read_json(events_path)
                restored_memory = _deserialize_events(events_data)
                # Inject into the simulation's memory store
                gs.simulation.memory._events = restored_memory._events
            except Exception as exc:  # noqa: BLE001
                import warnings
                warnings.warn(f"Could not restore events: {exc}", stacklevel=2)

        # 4. relationships.json
        rel_path = slot_dir / "relationships.json"
        if rel_path.exists():
            try:
                rel_data = self._read_json(rel_path)
                restored_rel = _deserialize_relationships(rel_data)
                # Replace the tracker inside simulation
                gs.simulation.relationships._relationships = restored_rel._relationships
                gs.simulation.relationships._slots = restored_rel._slots
                gs.simulation.relationships._ex_lover_tags = restored_rel._ex_lover_tags
                gs.simulation.relationships._fights = restored_rel._fights
            except Exception as exc:  # noqa: BLE001
                import warnings
                warnings.warn(f"Could not restore relationships: {exc}", stacklevel=2)

        return gs

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, slot: int, game_state: "GameState") -> None:  # noqa: F821
        """Save current game to *slot* (1-indexed).

        Writes atomically via a sibling temp dir, then renames.
        """
        self._validate_slot(slot)
        slot_dir = self._slot_dir(slot)
        staging = slot_dir.with_suffix(".staging")

        # Clean up any leftover staging dir
        if staging.exists():
            shutil.rmtree(staging)

        try:
            self._write_slot(staging, game_state)

            # Write metadata
            meta = {
                "island_name": game_state.island_name,
                "day_count": game_state.day_count,
                "last_saved": datetime.now(tz=timezone.utc).isoformat(),
            }
            self._write_json(staging / _META_FILE, meta)

            # Atomic replace
            if slot_dir.exists():
                shutil.rmtree(slot_dir)
            staging.rename(slot_dir)
        except Exception:
            # Clean up staging on failure
            if staging.exists():
                shutil.rmtree(staging)
            raise

    def load(self, slot: int) -> "GameState":  # noqa: F821
        """Load game from *slot*.

        Raises FileNotFoundError if the slot does not exist.
        """
        self._validate_slot(slot)
        slot_dir = self._slot_dir(slot)
        if not slot_dir.exists():
            raise FileNotFoundError(f"Save slot {slot} does not exist")
        return self._read_slot(slot_dir)

    def list_slots(self) -> list[SlotInfo]:
        """Return info about all slots (1 to NUM_SLOTS)."""
        result: list[SlotInfo] = []
        for slot in range(1, NUM_SLOTS + 1):
            slot_dir = self._slot_dir(slot)
            meta_path = slot_dir / _META_FILE
            if slot_dir.exists() and meta_path.exists():
                try:
                    meta = self._read_json(meta_path)
                    result.append(
                        SlotInfo(
                            slot=slot,
                            exists=True,
                            island_name=meta.get("island_name", ""),
                            day_count=meta.get("day_count", 0),
                            last_saved=meta.get("last_saved", ""),
                        )
                    )
                    continue
                except Exception:  # noqa: BLE001
                    pass
            result.append(SlotInfo(slot=slot, exists=False))
        return result

    def delete_slot(self, slot: int) -> None:
        """Remove a save slot. No-op if the slot does not exist."""
        self._validate_slot(slot)
        slot_dir = self._slot_dir(slot)
        if slot_dir.exists():
            shutil.rmtree(slot_dir)

    # ------------------------------------------------------------------
    # Temp (crash recovery)
    # ------------------------------------------------------------------

    def save_temp(self, game_state: "GameState") -> None:  # noqa: F821
        """Write crash-recovery data to _temp/."""
        temp_dir = self._temp_dir()
        staging = temp_dir.with_suffix(".staging")
        if staging.exists():
            shutil.rmtree(staging)
        try:
            self._write_slot(staging, game_state)
            meta = {
                "island_name": game_state.island_name,
                "day_count": game_state.day_count,
                "last_saved": datetime.now(tz=timezone.utc).isoformat(),
            }
            self._write_json(staging / _META_FILE, meta)
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            staging.rename(temp_dir)
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            raise

    def has_temp_save(self) -> bool:
        """Return True if crash-recovery data exists."""
        temp_dir = self._temp_dir()
        return (temp_dir / "game.json").exists()

    def load_temp(self) -> "GameState":  # noqa: F821
        """Load crash-recovery data.

        Raises FileNotFoundError if no temp save exists.
        """
        temp_dir = self._temp_dir()
        if not self.has_temp_save():
            raise FileNotFoundError("No crash-recovery save found")
        return self._read_slot(temp_dir)

    def clear_temp(self) -> None:
        """Remove crash-recovery data after a successful normal load."""
        temp_dir = self._temp_dir()
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
