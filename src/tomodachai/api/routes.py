"""FastAPI route definitions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from tomodachai.api.schemas import (
    CharacterCreate,
    CharacterOut,
    CustomizableOut,
    EventOut,
    GameStatusOut,
    LoadResponse,
    LocationOut,
    MiniTraitEntry,
    MoodOut,
    MoveResponse,
    PersonalitySliders,
    PersonalityTypeOut,
    PreferencesOut,
    RecordsOut,
    RelationshipOut,
    SaveResponse,
    SlotInfoOut,
    StateOut,
    StatusResponse,
    TickRequest,
    TickResponse,
)
from tomodachai.character import Character
from tomodachai.game_state import GameState
from tomodachai.save import SaveManager

router = APIRouter()

# Singleton game state — created on startup, injected via app.state
_game: GameState | None = None
_save_manager: SaveManager = SaveManager()


def set_game_state(game: GameState) -> None:
    global _game
    _game = game


def set_save_manager(manager: SaveManager) -> None:
    global _save_manager
    _save_manager = manager


def _gs() -> GameState:
    if _game is None:
        raise HTTPException(status_code=503, detail="Game not initialized")
    return _game


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/status", response_model=StatusResponse)
def get_status():
    gs = _gs()
    return StatusResponse(
        status="running",
        characters=len(gs.characters),
        tick=gs.simulation._tick_count,
        locations=[loc.name for loc in gs.config.locations],
    )


@router.get("/game", response_model=GameStatusOut)
def get_game():
    gs = _gs()
    return GameStatusOut(
        island_name=gs.island_name,
        day_count=gs.day_count,
        money=gs.money,
        time_flip=gs.time_flip,
        characters=len(gs.characters),
        locations=[loc.name for loc in gs.config.locations],
    )


# ---------------------------------------------------------------------------
# Characters
# ---------------------------------------------------------------------------

@router.get("/characters", response_model=list[CharacterOut])
def list_characters():
    return [_char_to_out(c) for c in _gs().characters]


def _parse_char_id(char_id: str) -> int | str:
    """Path param을 int로 변환 시도.

    순수 숫자 → int 변환.
    "char_1" 형태 → 숫자 부분 추출 → int.
    그 외 → str 반환 (fallback).
    """
    try:
        return int(char_id)
    except ValueError:
        digits = "".join(filter(str.isdigit, char_id))
        if digits:
            return int(digits)
        return char_id


@router.post("/characters", response_model=CharacterOut, status_code=201)
def create_character(body: CharacterCreate):
    gs = _gs()
    raw = body.model_dump()
    # id가 str이면 int 변환 시도
    raw_id = raw.get("id")
    if isinstance(raw_id, str):
        try:
            raw["id"] = int(raw_id)
        except ValueError:
            # "char_1" 형태 → 숫자 부분 추출 시도
            digits = "".join(filter(str.isdigit, raw_id))
            raw["id"] = int(digits) if digits else abs(hash(raw_id)) % 100000
    char = Character(**raw)
    try:
        gs.add_character(char)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _char_to_out(char)


@router.get("/characters/generate-name")
def generate_name(gender: str = ""):
    """LLM으로 한국 이름 하나 생성. ?gender=남 또는 ?gender=여"""
    gs = _gs()
    existing = [c.name for c in gs.characters]
    existing_text = ", ".join(existing) if existing else "없음"

    gender_hint = ""
    if gender in ("남", "남성", "M", "male"):
        gender_hint = "남성 이름"
    elif gender in ("여", "여성", "F", "female"):
        gender_hint = "여성 이름"
    else:
        gender_hint = "남성 또는 여성 이름"

    prompt = (
        f"한국 {gender_hint}을 하나만 생성하세요. 성+이름 형태 (예: 김민수, 이지은).\n"
        f"기존 캐릭터: {existing_text}\n"
        f"기존 이름과 겹치지 않게 해주세요.\n"
        f"이름만 출력하세요. 다른 설명 없이 이름 하나만."
    )
    messages = [
        {"role": "system", "content": "한국 이름 생성기. 이름만 출력."},
        {"role": "user", "content": prompt},
    ]
    try:
        name = gs.llm.chat(messages).strip().strip('"').strip("'")
        # 혹시 여러 줄이면 첫 줄만
        name = name.split("\n")[0].strip()
        return {"name": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 호출 실패: {e}")


@router.get("/characters/{char_id}", response_model=CharacterOut)
def get_character(char_id: str):
    gs = _gs()
    char = gs.get_character(_parse_char_id(char_id))
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return _char_to_out(char)


@router.delete("/characters/{char_id}", status_code=204)
def delete_character(char_id: str):
    if not _gs().remove_character(_parse_char_id(char_id)):
        raise HTTPException(status_code=404, detail="Character not found")


def _char_to_out(c: Character) -> CharacterOut:
    # personality sliders — profile.personality (Personality 모델)
    p = c.profile.personality
    personality = PersonalitySliders(
        movement=p.movement,
        speech=p.speech,
        expressiveness=p.expressiveness,
        attitude=p.attitude,
        overall=p.overall,
    )

    # preferences
    pref = c.preferences
    clothing_dict: dict[str, str] = {}
    if pref.clothing.likes:
        clothing_dict["likes"] = pref.clothing.likes
    if pref.clothing.dislikes:
        clothing_dict["dislikes"] = pref.clothing.dislikes
    interior_dict: dict[str, str] = {}
    if pref.interior.likes:
        interior_dict["likes"] = pref.interior.likes
    if pref.interior.dislikes:
        interior_dict["dislikes"] = pref.interior.dislikes

    preferences = PreferencesOut(
        food_ranks=pref.food_ranks,
        clothing=clothing_dict,
        interior=interior_dict,
    )

    # state
    st = c.state
    mood = MoodOut(
        happiness=st.mood.happiness,
        energy=st.mood.energy,
        stress=st.mood.stress,
    )
    state = StateOut(
        satisfaction=st.satisfaction,
        level=st.level,
        hunger=st.hunger,
        mood=mood,
        sick=st.sick,
        current_location=st.current_location,
    )

    # customizable
    cust = c.customizable
    mini_traits: dict[str, MiniTraitEntry] = {
        "walking": MiniTraitEntry(
            owned=cust.mini_traits.walking.owned,
            active=cust.mini_traits.walking.active,
        ),
        "eating": MiniTraitEntry(
            owned=cust.mini_traits.eating.owned,
            active=cust.mini_traits.eating.active,
        ),
        "idle": MiniTraitEntry(
            owned=cust.mini_traits.idle.owned,
            active=cust.mini_traits.idle.active,
        ),
    }
    customizable = CustomizableOut(
        speech_habits=cust.speech_habits.as_dict(),
        mini_traits=mini_traits,
        nicknames=cust.nicknames,
    )

    # records
    rec = c.records
    records = RecordsOut(
        treasure_collection=rec.treasure_collection,
        confession_count=rec.confession_count,
        photos=rec.photos,
    )

    char_id = c.id if isinstance(c.id, int) else abs(hash(c.id)) % 100000

    return CharacterOut(
        id=char_id,
        name=c.name,
        birthday=c.birthday,
        zodiac=c.zodiac,
        blood_type=c.blood_type,
        favorite_color=c.favorite_color,
        gender=c.gender,
        personality_code=c.personality_code,
        personality=personality,
        preferences=preferences,
        state=state,
        customizable=customizable,
        records=records,
    )


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

@router.get("/relationships", response_model=list[RelationshipOut])
def list_relationships():
    gs = _gs()
    results = []
    for a_id, b_id, rel in gs.relationships.all_pairs():
        results.append(_rel_to_out(a_id, b_id, rel))
    return results


@router.get("/relationships/{char_a_id}/{char_b_id}", response_model=RelationshipOut)
def get_relationship(char_a_id: str, char_b_id: str):
    gs = _gs()
    a_id = _parse_char_id(char_a_id)
    b_id = _parse_char_id(char_b_id)
    rel = gs.relationships.get(a_id, b_id)
    return _rel_to_out(a_id, b_id, rel)


def _rel_to_out(a_id, b_id, rel) -> RelationshipOut:
    def _to_int(v) -> int:
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return abs(hash(v)) % 100000

    return RelationshipOut(
        char_a=_to_int(a_id),
        char_b=_to_int(b_id),
        friendship=rel.friendship,
        romance=rel.romance,
        stage=rel.stage.value,
        status_text=rel.get_status_text(),
    )


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

@router.post("/tick", response_model=TickResponse)
def do_tick(body: TickRequest | None = None):
    gs = _gs()
    seed = body.seed if body else None
    raw_events = gs.tick(seed=seed)
    events = [_event_to_out(e) for e in raw_events]
    return TickResponse(
        tick=gs.simulation._tick_count,
        events=events,
    )


def _event_to_out(event: dict) -> EventOut:
    etype = event["type"]
    raw_participants = event.get("participants", [])

    # coerce participant IDs to int where possible
    participants: list[int] = []
    for p in raw_participants:
        if isinstance(p, int):
            participants.append(p)
        elif isinstance(p, str) and p.isdigit():
            participants.append(int(p))
        else:
            participants.append(abs(hash(p)) % 100000)

    dialogue = None
    deltas = None
    result_str = event.get("result")

    if etype == "conversation":
        result = event.get("result")
        if result and not isinstance(result, str):
            dialogue = [{"speaker": ln.speaker, "text": ln.text} for ln in result.dialogue]
            deltas = result.deltas
            result_str = result.summary if hasattr(result, "summary") else None

    return EventOut(
        id=event.get("id"),
        type=etype,
        participants=participants,
        location=event.get("location"),
        day=event.get("day"),
        time=event.get("time"),
        reason=event.get("reason"),
        result=result_str if isinstance(result_str, str) else None,
        dialogue=dialogue,
        deltas=deltas,
    )


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

@router.get("/memory/{char_id}")
def get_memory(char_id: str, limit: int = 10):
    char_id = _parse_char_id(char_id)  # type: ignore[assignment]
    gs = _gs()
    events = gs.memory.get_events_for(char_id, limit=limit)
    return [
        {
            "tick": e.tick,
            "event_type": e.event_type,
            "summary": e.summary,
            "participants": e.participants,
        }
        for e in events
    ]


# ---------------------------------------------------------------------------
# Personalities
# ---------------------------------------------------------------------------

@router.get("/personalities", response_model=list[PersonalityTypeOut])
def list_personalities():
    gs = _gs()
    return [
        PersonalityTypeOut(
            code=p.code,
            name=p.name,
            group=p.group,
            description=p.description,
        )
        for p in gs.personalities.values()
    ]


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------


@router.get("/locations", response_model=list[LocationOut])
def list_locations():
    """모든 장소와 현재 입장 캐릭터 목록을 반환한다."""
    gs = _gs()
    snapshot = gs.location_manager.snapshot()
    return [LocationOut(**entry) for entry in snapshot]


@router.post(
    "/locations/move/{char_id}/{destination}",
    response_model=MoveResponse,
)
def move_character(char_id: str, destination: str):
    """플레이어가 캐릭터를 강제 이동시킨다 (물리적 간섭).

    destination은 장소 ID 또는 장소 이름 모두 허용.
    """
    gs = _gs()
    int_id = _parse_char_id(char_id)
    if isinstance(int_id, str):
        int_id = abs(hash(int_id)) % 100000

    # 캐릭터 존재 여부 확인
    char = gs.get_character(_parse_char_id(char_id))
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")

    success = gs.location_manager.move_character(int_id, destination)
    if not success:
        # 장소 ID/이름 찾기 실패
        raise HTTPException(
            status_code=404,
            detail=f"Location '{destination}' not found",
        )

    # Character.state.current_location도 동기화
    actual_loc_id = gs.location_manager.get_character_location(int_id)
    loc = gs.location_manager.get_location(actual_loc_id or destination)
    loc_name = loc.name if loc else destination
    char.state.current_location = loc_name

    return MoveResponse(
        char_id=int_id,
        destination=actual_loc_id or destination,
        success=True,
        message=f"{char.name}을(를) {loc_name}으로 이동시켰다.",
    )


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------


@router.get("/saves", response_model=list[SlotInfoOut])
def list_saves():
    """List all save slots with metadata."""
    slots = _save_manager.list_slots()
    return [
        SlotInfoOut(
            slot=s.slot,
            exists=s.exists,
            island_name=s.island_name,
            day_count=s.day_count,
            last_saved=s.last_saved,
        )
        for s in slots
    ]


@router.post("/save/{slot}", response_model=SaveResponse)
def save_game(slot: int):
    """Save current game to the given slot (1-3)."""
    gs = _gs()
    try:
        _save_manager.save(slot, gs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save failed: {e}")
    return SaveResponse(ok=True, slot=slot, message=f"Saved to slot {slot}")


@router.post("/load/{slot}", response_model=LoadResponse)
def load_game(slot: int):
    """Load game from the given slot and replace current game state."""
    global _game
    try:
        loaded = _save_manager.load(slot)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Save slot {slot} does not exist")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Load failed: {e}")
    _game = loaded
    return LoadResponse(
        ok=True,
        slot=slot,
        island_name=loaded.island_name,
        day_count=loaded.day_count,
        characters=len(loaded.characters),
    )


@router.delete("/save/{slot}", status_code=204)
def delete_save(slot: int):
    """Delete a save slot."""
    try:
        _save_manager.delete_slot(slot)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/save/temp", response_model=SaveResponse)
def save_temp():
    """Write crash-recovery temp save."""
    gs = _gs()
    try:
        _save_manager.save_temp(gs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Temp save failed: {e}")
    return SaveResponse(ok=True, slot=0, message="Temp save written")


@router.post("/load/temp", response_model=LoadResponse)
def load_temp():
    """Load from crash-recovery temp save."""
    global _game
    if not _save_manager.has_temp_save():
        raise HTTPException(status_code=404, detail="No crash-recovery save found")
    try:
        loaded = _save_manager.load_temp()
        _save_manager.clear_temp()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Temp load failed: {e}")
    _game = loaded
    return LoadResponse(
        ok=True,
        slot="temp",
        island_name=loaded.island_name,
        day_count=loaded.day_count,
        characters=len(loaded.characters),
    )


# ---------------------------------------------------------------------------
# WebSocket — real-time event stream
# ---------------------------------------------------------------------------

_ws_clients: set[WebSocket] = set()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    try:
        while True:
            # Client can send tick commands via WS too
            data = await ws.receive_json()
            if data.get("action") == "tick":
                gs = _gs()
                seed = data.get("seed")
                raw_events = gs.tick(seed=seed)
                events = [_event_to_out(e).model_dump() for e in raw_events]
                response = {
                    "type": "tick_result",
                    "tick": gs.simulation._tick_count,
                    "events": events,
                }
                # Broadcast to all connected clients
                for client in list(_ws_clients):
                    try:
                        await client.send_json(response)
                    except Exception:
                        _ws_clients.discard(client)
    except WebSocketDisconnect:
        _ws_clients.discard(ws)
