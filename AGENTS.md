# AGENTS.md

## Quick Start

- Install deps: `pip install -r requirements.txt`
- Run the desktop app: `python main.py`
- Run the browser-plugin API separately: `python api_server.py`
- For macOS packaging, prefer `bash build_macos.sh` or `pyinstaller VideoDownloader.spec --noconfirm`
- `build_exe.py` is not the most reliable build path today: it references missing `LICENSE`, `icons/`, and `assets/icon.svg`

## Where The Real Logic Lives

- `main.py` only bootstraps Qt and opens `ui.YoutubeDownloader`
- `ui.py` is the real app hub: page wiring, download start/cancel, history updates, subtitle actions, and dialog/thread orchestration all converge there
- `tabs/history_tab.py` and `tabs/settings_tab.py` are mostly UI surfaces that emit signals or persist settings; do not expect core business flow to live there
- `download_manager.py` is the source of truth for yt-dlp option assembly (`prepare_download_options`) and shared task metadata
- Background work is thread-based, not async-in-UI: `download_thread.py`, `whisper_thread.py`, and `subtitle_merger.py`
- The browser extension lives entirely under `chrome-plugin/`; `popup.js` and `background.js` both talk to the local FastAPI server

## State, Files, And Secrets

- App startup calls `Config.load_config()` in `ui.YoutubeDownloader.__init__()`, so repo-local `config.json` affects runtime immediately
- Settings edits persist through `tabs/settings_tab.py -> Config.save_config()` on every change
- Download history does not use the repo's `history.json`; `HistoryManager` defaults to `~/youtube_downloader_history.json`
- `config.py` defaults and `config.json` may contain real API keys; treat both as sensitive and do not echo or commit new secrets

## Browser Plugin Coupling

- The extension defaults to `http://localhost:8765/api/v1/download` in `chrome-plugin/popup.js` and `chrome-plugin/background.js`
- `chrome-plugin/manifest.json` only grants host permission for `http://localhost:8765/*`
- `api_server.py` binds `127.0.0.1:8765` by default via `Config.API_HOST` / `Config.API_PORT`
- The desktop app does not auto-start the API server; if you test plugin flows, start `python api_server.py` yourself
- If you change the API host, port, or route shape, update `api_server.py`, `popup.js`, `background.js`, and `manifest.json` together

## Verification

- There is no repo test suite, linter, typechecker, pre-commit config, or CI workflow to rely on
- Minimum safe check for Python edits: `python -m py_compile <touched .py files>`
- For UI changes, do a smoke run with `python main.py`
- For API or plugin changes, run `python api_server.py` and verify `/api/v1/download` plus `/api/v1/status/{task_id}` behavior
- Subtitle merge and Whisper flows require `ffmpeg` on `PATH`; both `subtitle_merger.py` and `whisper_thread.py` shell out to it

## Generated Or Local-Only Paths

- Ignore `build/`, `dist/`, `graphify-out/`, `__pycache__/`, and `venv/` unless the task is explicitly about packaging or graph artifacts
- Use root source files, `tabs/`, and `chrome-plugin/` as the editable codebase; existing packaged artifacts are not source of truth
