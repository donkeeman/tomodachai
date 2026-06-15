# 별빛 마을 — Tauri 데스크탑 셸

Wraps the Babylon.js web client (`../web`, served by `../web_server.py`) in a native
desktop window using the OS webview — small footprint, no bundled Chromium (unlike
Electron). This is the "lightweight desktop app you keep open while multitasking" target.

## How it works (dev)

`tauri dev` runs `beforeDevCommand` first — it starts the Python server
(`python3 ../web_server.py`), which serves **both** the static frontend and the `/api`
simulation endpoints on `http://127.0.0.1:8765`. Tauri then opens a native window
pointed at that URL. Same origin, so no CORS. Closing the window stops the dev server.

```
desktop/
  package.json          # @tauri-apps/cli (JS side)
  src-tauri/
    tauri.conf.json      # window + beforeDevCommand + devUrl
    Cargo.toml           # Rust deps (tauri)
    src/main.rs          # opens the window
```

## Prerequisites

- **Rust** (Tauri builds a native binary): `curl https://sh.rustup.rs -sSf | sh`
- macOS: Xcode Command Line Tools (`xcode-select --install`) for the linker + WKWebView.
  Windows: WebView2 (preinstalled on Win 10/11). Linux: `webkit2gtk`.
- Node/npm (for the Tauri CLI), Python 3.9+ (the backend).

## Run

```bash
cd prototype/desktop
npm install            # fetches @tauri-apps/cli (no Rust needed for this step)
npm run dev            # = tauri dev — first run compiles Rust crates (a few minutes)
```

A native window titled "별빛 마을" should open showing the 3D village. **That render IS
the WebGL-in-webview spike** — if the village draws, Babylon/WebGL works in the system
webview (expected: Babylon officially supports WebKit/WebView2). If it's blank, check the
devtools (right-click → Inspect in dev) for WebGL context errors.

Want realtime instead of the demo's 5s turbo tick? Edit `beforeDevCommand` in
`tauri.conf.json` — drop `--interval 5` for wall-clock time.

## Packaging a distributable (next step, not done yet)

`tauri build` bundles `frontendDist` (`../web`) as static assets, but the **Python API
won't be running** inside the bundle. For a real installer you need to ship the backend
as a **sidecar**:

1. Freeze the server: `pyinstaller --onefile ../web_server.py` → a standalone binary.
2. Declare it under `tauri.conf.json` → `bundle.externalBin` (or `app` sidecar) and spawn
   it from `main.rs` on startup, then point the window at its localhost port.
3. Alternatively (lightest long-term): port the `game/` simulation to JS so no Python
   process is needed at all and only the LLM is called over the network.

## Notes

- Icons: `npm run tauri icon path/to/source.png` generates `src-tauri/icons/*`. Dev runs
  without them; `tauri build` needs them.
- `node_modules/`, `src-tauri/target/`, `src-tauri/gen/` are gitignored.
