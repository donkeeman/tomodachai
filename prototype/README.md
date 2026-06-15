# AI Tomodachi Life — Prototype (Terminal + Web 3D)

A prototype of the observation-sim game described in `../docs/plan/`. It started as a
text-only terminal build of the core loop (observe → events → intervene), and now also
ships a **Babylon.js** web 3D client (`web_server.py` + `web/`) on top of the same
simulation. (An earlier Three.js cut lives on the `feat/threejs-frontend` branch.)

The LLM backend is temporarily the **Codex CLI** (`codex exec`, uses your logged-in account).
The provider layer is abstracted so it can later be swapped for litellm / claude-cli / Ollama.

## Requirements

- Python 3.9+ (stdlib only, no pip installs)
- `codex` CLI on PATH and logged in (only for `--provider codex`, the default)

## Run

```bash
cd prototype
python3 main.py              # real LLM via codex exec (each event takes a few seconds)
python3 main.py --mock       # no LLM, canned lines — for fast engine testing
python3 main.py --seed 42    # reproducible RNG
```

Press Enter to advance time (1 tick = 30 in-game minutes). Commands:

| Command | Description |
|---------|-------------|
| `s [n]` / Enter | advance n ticks |
| `auto [sec]` | background auto mode: time flows by itself (default 3s/tick) while you can still type commands; pending bubbles and major events (fight, breakup, new best friend/enemy) pause it |
| `pause` | turn off auto mode (`auto off` also works) |
| `status [name]` | village / character status |
| `rel` | village-wide relationship map summary (slots, budding ties, crushes, ex-lover history) |
| `rel <name>` | one character's relationships (status text only, numbers hidden) |
| `map` | who is where |
| `bubbles` | answer pending speech bubbles (confession approval etc.) |
| `feed <name> [food]` | give food (discover preferences) |
| `feed all [food]` | debug helper: feed everyone at once (random safe pick per character if food omitted) |
| `dex <name>` | food preference dex (only what you've tried) |
| `log [n]` | recent event log |
| `news [weird]` | announcer briefing of yesterday / absurd fake news |
| `save` / `load` | manual persist to `saves/` (game.json / char_N.json / events.json per data schema doc) |

Autosave: every 10 ticks and on exit. On startup the saved village is resumed
automatically if `saves/` exists; pass `--new` to start a fresh village.

## Web 3D client (Babylon.js)

The visual client from `00-overview.md` (web frontend + Python backend). The same
`game/` simulation runs server-side; the browser only renders. This is the path toward
a lightweight desktop app (intended shell: **Tauri** — native webview, small footprint).

```bash
cd prototype
python3 web_server.py             # realtime mode: 1 real minute = 1 game minute
python3 web_server.py --codex     # real LLM lines via Codex CLI
python3 web_server.py --interval 3   # turbo mode: one 30-min tick every 3s (dev/testing)
# then open http://127.0.0.1:8765
```

Realtime mode (default, per plan doc 03 §4): the game clock syncs to your wall clock,
villagers sleep 23:00–07:00, the day rolls over at 05:00, and there is no catch-up
simulation for time the server was off. `--interval N` switches to the old turbo mode.

- Low-poly village (fountain, apartment, balcony, park, cafe, beach) mapped 1:1 from
  `LOCATIONS`; villagers walk between places, tick events replay as speech/thought
  bubbles (💭 spark musings included), the right panel streams the village log, and
  clicking a villager shows a mood/relationship card.
- Babylon.js 7 (core + glTF loaders) is vendored at `web/lib/` — no CDN/network at runtime.
- **Blender → glTF pipeline:** drop `villager.glb` (or `villager_m.glb`/`villager_f.glb`)
  into `web/models/` and the client loads it automatically; absent files fall back to
  procedural primitive figures so it always runs. Export guide: `web/models/README.md`.
  The HUD shows `엔진: …+glb` when a model loaded.
- Camera: drag-rotate, right/Shift-drag or arrows to pan, wheel/pinch zoom. Click a
  villager to inspect (centers + they turn to face you); slide the ground reticle near a
  villager to auto-follow them; double-click for the whole-village view; click the house
  to enter the interior as a separate space.
- Player intervention works on the web too: click a villager → 🍙 feed menu (same
  preference-tier reactions and dex tracking as the terminal), and confession-permission
  bubbles pop up bottom-center with allow/stop buttons (same `resolve_confession` flow).
- The web village persists in its own `saves_web/` (the terminal `saves/` is untouched):
  autosave every 10 ticks, after every intervention, and on exit (Ctrl+C / SIGTERM).
  Restart resumes automatically; `--new` starts a fresh village, `--save-dir` relocates.

## What is implemented (from the plan docs)

- 16 personality types from 5 sliders (01), intensity hints, mini-traits, speech habits
- Directional friendship/romance, status-text mapping, slots (best friend / lover / enemy),
  ex-lover tags with breakup reasons, natural decay, affinity coefficient (02)
- Spark (반함) trigger gating romance: it stays at 0 until a character falls for someone.
  Both paths play out as conversation scenes — contextual spark (LLM decides during a normal
  conversation, piggybacked on the same call) and chance-encounter spark (system decides
  randomly, mirroring the original game's street-bump crush; LLM only narrates the encounter
  with an absurd cute reason). Cooled feelings clear the spark; capped at one spark per day
  village-wide to keep it special (02)
- Jealousy (02 §11): when A's grown crush is already someone else's lover, number
  tables occasionally fire a jealousy scene — picking at the rival or venting to a
  friend (LLM narrates, relationships/moods shift, one per day max)
- Condition-based movement (03 §3): villagers drift toward their lover/best friend,
  head home when starving, or just wander — no timetable
- Park ranking board (03): best couple / most popular / most-fought pairs; on the web
  client, click the board object in the park
- Number-table-triggered events, LLM called only for the selected event (04):
  conversations, fights, confession bubbles → player approval → **LLM contextual accept/reject judgment**
  with fuzzy values (no raw numbers in prompts), guardrails included (13)
- Breakup reason auto-decision (system, not LLM) + cheating path via accepted confession
- mood 3-axis / satisfaction / hunger / despair, food preference tiers with reactions;
  hunger surfaces as a single persistent speech bubble (cleared by feeding), not log spam
- Tool items (05 §5): camera → villager shoots a titled photo into the gallery,
  frying pan → improvised dish into the catalog (`give` in terminal, 🎁 on the web;
  `album` / 📒 기록 to browse)
- Daily reset at 05:00, random announcer, news briefing + absurd news
- Save files mirroring the data schema doc (14)

## Out of scope (by design)

Shop/economy, songs/TTS, dreams, pets, travel, photos, minigames, baths, birthdays,
multi-island, catch-up simulation. The point here is to validate the core AI
relationship loop in text form first; `web_server.py` + `web/` is the first slice of
the web client on top of it.
