# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Code Change Quality Standard

After **every** code change — no matter how small — you must:

1. **Re-read every file you touched**, end-to-end, in its final state.
2. **Run a gaps analysis**: check for ordering bugs, stale docstrings, broken execution paths, type mismatches, blocking calls in async contexts, magic strings, and incorrect output for each distinct code path.
3. **Fix every issue found** before reporting completion.
4. **Repeat steps 1–3** until a full re-read of all changed files produces zero issues.

Do not claim a task is complete after a single pass. Do not self-certify without evidence from the re-read. The loop ends only when you find nothing left to fix.

---

## Project Overview

**Pocket Desk Agent** is a Python Telegram bot that provides secure remote control of a Windows PC, powered by Google Gemini 2.0 Flash AI. It is distributed as a PyPI package (`pocket-desk-agent`) and runs as a local CLI daemon (`pdagent`).

Key capabilities: AI chat (Gemini), file system browsing, desktop screenshots, keyboard/clipboard control, OCR-based UI automation, macro recording, Claude Desktop/VS Code integration, build automation (React Native APKs), and task scheduling.

**Platform target:** Windows (UI automation features). File system and AI features are cross-platform.

---

## Repository Layout

```
pocket-desk-agent/
├── pocket_desk_agent/          # Main Python package
│   ├── handlers/               # Bot command handlers (14 modules)
│   │   ├── _shared.py          # Singleton clients, safe_command decorator, global state
│   │   ├── auth.py             # /login, /authcode, /checkauth, /logout
│   │   ├── core.py             # /start, /help, /status, /new, /enhance, /sync, etc.
│   │   ├── filesystem.py       # /pwd, /cd, /ls, /cat, /find, /info
│   │   ├── system.py           # /screenshot, /hotkey, /clipboard, /battery, /shutdown, etc.
│   │   ├── automation.py       # /clicktext, /findtext, /smartclick, etc.
│   │   ├── custom_commands.py  # /savecommand, /done, /listcommands, /deletecommand
│   │   ├── claude.py           # /openclaude, /claudescreen + Claude composer helpers
│   │   ├── antigravity.py      # /openantigravity, /openclaudeinvscode, /claudecli, /openbrowser, etc.
│   │   ├── build.py            # /build, /getapk, /stopbuildscreenshot
│   │   ├── scheduling.py       # /schedule, /scheduleshutdown, /claudeschedule, /listschedules, /cancelschedule
│   │   ├── remote.py           # /remote, /stopremote, session lifecycle + auto-install flow
│   │   ├── workflow_recipes.py # /recipe, /runrecipe, /listrecipes — multi-step automation flows
│   │   └── callbacks.py        # Inline keyboard button handlers
│   ├── remote/                 # Live remote-desktop subsystem
│   │   ├── session.py          # RemoteSession dataclass + ACTIVE_SESSIONS registry
│   │   ├── capture.py          # Async JPEG frame iterator (mss screen capture)
│   │   ├── input_bridge.py     # InputDispatcher — translates JSON events to pyautogui calls
│   │   ├── tunnel.py           # Cloudflared quick-tunnel supervisor (spawn + URL capture)
│   │   ├── install.py          # Winget-based auto-installer for the cloudflared binary
│   │   └── web_server.py       # aiohttp server: /ws/video, /ws/input, / (viewer HTML)
│   ├── cli.py                  # Entry point for `pdagent` CLI
│   ├── main.py                 # Application bootstrap, scheduler loop
│   ├── config.py               # Config class — reads from os.environ
│   ├── configure.py            # Interactive setup wizard + INI loader
│   ├── command_map.py          # Centralized list of (command, handler, description)
│   ├── command_registry.py     # User-defined macro storage
│   ├── file_manager.py         # Sandboxed file I/O (path traversal prevention)
│   ├── gemini_client.py        # Gemini API client with tool-calling
│   ├── gemini_actions.py       # Gemini tool definitions, rate-limiting, and confirmation flows
│   ├── nvidia_client.py        # NVIDIA NIM (OpenAI-compatible) fallback AI client
│   ├── ai_router.py            # Cross-provider fallback — tries providers in AI_PROVIDER_ORDER
│   ├── ai_history.py           # Gemini <-> OpenAI history/tool-call format converters
│   ├── ai_tool_loop.py         # Shared tool allowlist + dispatch loop used by both providers
│   ├── ai_types.py             # ProviderResult — the common return type for both AI clients
│   ├── scheduling_utils.py     # Shared date/time parsing helpers for scheduling commands
│   ├── antigravity_auth.py     # OAuth 2.0 PKCE implementation
│   ├── auth.py                 # User allowlist + multi-mode auth wrapper
│   ├── gemini_cli_auth.py      # Gemini CLI OAuth PKCE implementation
│   ├── scheduler_registry.py   # Persistent scheduled task storage
│   ├── startup_manager.py      # Windows logon-task startup management
│   ├── rate_limiter.py         # Token-bucket rate limiter
│   ├── updater.py              # Auto-update manager (PyPI only via pip upgrade, regardless of install type; /update)
│   ├── automation_utils.py     # OCR/UI automation helpers
│   ├── desktop_adapters.py     # Centralized find/activate logic for Claude, Antigravity, etc.
│   ├── recipe_registry.py      # Persistent workflow recipe storage (~/.pdagent/workflow_recipes.json)
│   ├── telegram_commands.py    # trim_registry_for_telegram() — caps command list at Telegram's 100-command limit
│   ├── app_paths.py            # app_path() / existing_app_path() helpers for ~/.pdagent/* paths
│   ├── app_control.py          # App launch/focus helpers
│   ├── app_catalog.py          # Catalog of known applications (paths, window titles)
│   ├── window_utils.py         # Low-level window enumeration / focus utilities
│   └── constants.py            # API endpoints and header constants
├── scripts/
│   ├── manage_auth.py          # Gemini authentication management script
│   └── manage_service.py       # Daemon lifecycle script
├── docs/                       # Feature documentation (markdown)
├── .github/workflows/
│   └── publish.yml             # PyPI publish on GitHub release
├── .env.example                # Config template
├── pyproject.toml              # PEP 621 metadata, dependencies, build config
├── requirements.txt            # Pinned dependency list
├── Makefile                    # Dev task automation
├── setup.sh / setup.bat        # Platform setup helpers
├── README.md
├── CONTRIBUTING.md
└── PROJECT_STRUCTURE.md
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Bot Framework | python-telegram-bot ≥ 21.0 (async) |
| AI | Google Gemini 2.0 Flash (via REST API) |
| Auth | Multi-mode auth: Antigravity OAuth PKCE, Gemini CLI OAuth PKCE, or API key |
| UI Automation | pywinauto, pyautogui, pygetwindow (Windows only) |
| OCR | pytesseract (Tesseract engine) |
| Remote Desktop | aiohttp (WebSocket server), mss (screen capture), cloudflared (HTTPS tunnel) |
| File Uploads | Dropbox SDK |
| Build Backend | hatchling (PEP 517) |
| Packaging | PyPI (`pocket-desk-agent`) |
| CI/CD | GitHub Actions, OIDC trusted publishing |

---

## Development Workflows

### Setup

```bash
git clone https://github.com/techgniouss/pdagent.git
cd pdagent
pip install -e ".[dev]"
cp .env.example .env          # then fill in credentials
# OR use interactive wizard:
pdagent configure
```

The `[2/3] Gemini AI Authentication` step in the wizard offers four options:
- `1` — Antigravity OAuth (opens browser immediately, uses built-in credentials)
- `2` — Gemini CLI OAuth (browser login against the public Gemini API)
- `3` — API Key (paste a Google AI Studio key)
- `4` — Setup Later (skip; authenticate anytime via `/login` in Telegram)

### Run / Test

```bash
make run                               # run bot (foreground)
pytest tests/                          # run all tests (make test does NOT run pytest)
pytest tests/test_specific.py -v       # run a single test file
pytest tests/ -k "test_name" -v       # run tests matching a name pattern
make lint                              # flake8 + mypy
make format                            # black pocket_desk_agent/ scripts/
make build                             # build sdist + wheel
make clean                             # remove caches and build artifacts
```

### CLI daemon commands

```bash
pdagent              # foreground run
pdagent start        # background daemon
pdagent stop         # graceful shutdown
pdagent restart      # restart daemon
pdagent status       # is it running?
pdagent configure    # interactive setup wizard
pdagent auth         # manage Gemini authentication credentials
pdagent startup ...  # manage automatic startup after Windows login
pdagent version      # print version
```

---

## Configuration

Config is loaded in this precedence order:

1. Shell environment variables (highest priority)
2. `~/.pdagent/config` (INI format, new)
3. `~/.pdagent/.env` (legacy dotenv support)
4. `~/.pd-agent/config` and `~/.pd-agent/.env` (temporary compatibility fallback)

All values live in `pocket_desk_agent/config.py` → `Config` class.

### Key variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot auth token from BotFather |
| `TELEGRAM_BOT_USERNAME` | Yes | — | Bot `@username` |
| `AUTHORIZED_USER_IDS` | Yes | — | Comma-separated Telegram user IDs |
| `GOOGLE_OAUTH_ENABLED` | No | `true` | Use OAuth instead of direct API key |
| `GOOGLE_OAUTH_CLIENT_ID` | No | built-in | Override the built-in Antigravity plugin OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | No | built-in | Override the built-in Antigravity plugin OAuth client secret |
| `GOOGLE_API_KEY` | API key mode | — | Gemini API key (used when `GOOGLE_OAUTH_ENABLED=false`) |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model selection |
| `NVIDIA_API_KEY` | No | — | NVIDIA NIM (build.nvidia.com) API key, enables the NVIDIA fallback provider |
| `NVIDIA_BASE_URL` | No | `https://integrate.api.nvidia.com/v1` | NVIDIA NIM OpenAI-compatible API base URL |
| `NVIDIA_MODEL` | No | `meta/llama-3.3-70b-instruct` | NVIDIA NIM model selection |
| `AI_PROVIDER_ORDER` | No | `gemini,nvidia` | Comma-separated AI provider fallback order |
| `APPROVED_DIRECTORIES` | No | `Path.home()` | Comma-separated allowed paths for file ops |
| `CLAUDE_DEFAULT_REPO_PATH` | No | `~/Documents` | Default repo root for Claude integration |
| `UPLOAD_EXPIRY_TIME` | No | `1h` | Dropbox link expiry (`1h`/`12h`/`24h`/`72h`) |
| `AUTO_UPDATE_ENABLED` | No | `true` | Enable periodic PyPI update check |
| `AUTO_UPDATE_INTERVAL_MINUTES` | No | `60` | Update check interval (minutes) |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `MAX_TOKENS_PER_REQUEST` | No | `8000` | Gemini token limit |
| `SYSTEM_PROMPT` | No | — | Custom Gemini system prompt |
| `REMOTE_ENABLED` | No | `true` | Enable the `/remote` live desktop feature |
| `REMOTE_AI_TOOLS_ENABLED` | No | `true` | Allow Gemini to start/stop remote sessions via tool-calling |
| `REMOTE_BIND_HOST` | No | `127.0.0.1` | Local host the aiohttp WebSocket server binds to |
| `REMOTE_IDLE_TIMEOUT_SECS` | No | `900` | Seconds of inactivity before auto-close (min 60) |
| `REMOTE_DEFAULT_FPS` | No | `10` | Default stream frame rate (clamped 2–20) |
| `REMOTE_JPEG_QUALITY` | No | `60` | Default JPEG quality (clamped 30–85) |
| `REMOTE_MAX_WIDTH` | No | `1280` | Max downscale width for desktop frames (640–1920) |
| `CLOUDFLARED_PATH` | No | auto-discovered | Override path to the `cloudflared` binary used by `/remote` |

### Secrets — never commit

- `.env`, `~/.pdagent/.env`, `~/.pdagent/config`
- `~/.pdagent/credentials` (OAuth client secrets)
- `~/.config/antigravity-chatbot/tokens.json` and `~/.config/pdagent-gemini/tokens.json` (OAuth access/refresh tokens)

---

## Architecture Patterns

### 1. `safe_command` wrapper (applied automatically at registration)

Located in `handlers/_shared.py`. `main.py` wraps every handler from `COMMAND_REGISTRY` with `safe_command(handler_func)` at registration time — **do not add `@safe_command` as a decorator on individual handler functions**, as that causes double-wrapping. The wrapper:
- Silently rejects unauthorized users (from `AUTHORIZED_USER_IDS`)
- Enforces per-user rate limits (token-bucket in `rate_limiter.py`)
- Catches all exceptions and sends a sanitized error message
- Prevents bot process crashes

**Never add manual `is_user_allowed()` checks in handlers** — `safe_command` already handles this.

### 2. Shared singletons

`handlers/_shared.py` holds module-level singletons used across all handler files:

```python
auth_client   # AntigravityAuth — OAuth token management
gemini_client # GeminiClient — Gemini API + conversation history
file_manager  # FileManager — sandboxed file I/O
```

### 3. Command registry

`command_map.py` contains `COMMAND_REGISTRY`: a flat list of `(command_name, handler_func, description)` tuples. `main.py` iterates this list at startup to register all handlers and sync Telegram's command menu.

### 4. `Config.load()` pattern

`Config` is a class with class-level attributes populated by `Config.load()`. This allows tests to patch `os.environ` before calling `load()` to inject test values without affecting global state.

### 5. FileManager path sandboxing

`FileManager._is_safe_path()` uses `Path.relative_to()` (not string prefix matching) to validate that requested paths stay inside `APPROVED_DIRECTORIES`. **Always use this method for any new file operation** — never roll your own path check.

### 6. Gemini AI safety

- The tool allowlist lives in `ai_tool_loop.py` as `ALLOWED_TOOLS` — it is re-exported (not duplicated) from `gemini_client.py` as `_ALLOWED_TOOLS` for backward compat. Both `GeminiClient` and `NvidiaClient` dispatch every tool call through `ai_tool_loop.run_tool_turn`, which checks this allowlist before calling `gemini_actions.dispatch_gemini_tool`. That is the whole point of the extraction: **one allowlist, one dispatch path, both AI providers.**
- History is trimmed to 40 turns (`_trim_history`) to bound memory usage
- Never expose `execute_command` or raw shell access to the AI — this is a prompt-injection-to-RCE vector

### 7. Scheduler loop

`main.py` runs a background task (`scheduler_loop`) that polls for due tasks every **5 seconds** (`SCHEDULER_POLL_INTERVAL_SECONDS = 5`). `SchedulerRegistry` persists tasks to `~/.pdagent/scheduled_tasks.json` and cleans up entries older than 7 days. Task types: `custom_cmd`, `claude_prompt`, `permission_watch`, `screen_watch`.

### 8. Remote desktop subsystem

`pocket_desk_agent/remote/` is a self-contained subsystem:
- `RemoteSession` (session.py) tracks per-user state: cloudflared process, aiohttp runner, JPEG capture queue, idle timer, session token, and browser fingerprint.
- `capture.py` feeds JPEG frames via an async generator into `/ws/video` WebSocket clients.
- `input_bridge.py` (`InputDispatcher`) translates JSON events (`click`, `move`, `down`, `up`, `scroll`, `key`, `hotkey`, `text`, `relmove`, `pointer_click`) into pyautogui calls.
- `tunnel.py` spawns cloudflared, reads the `trycloudflare.com` URL from its stdout, and retries once on failure.
- `install.py` can auto-install cloudflared via `winget` when the binary is missing; the handler prompts the user for approval before running.
- `web_server.py` serves the mobile viewer (inline HTML — no static files) and enforces cookie + browser-fingerprint session binding on all WebSocket routes. Backpressure is applied when the write buffer exceeds 512 KB.

---

## Adding a New Bot Command

1. **Write the handler** in the appropriate file under `pocket_desk_agent/handlers/` (or create a new module for a new domain). No `@safe_command` decorator needed — it is applied automatically at registration time by `main.py`.

2. **Export it** from `pocket_desk_agent/handlers/__init__.py`.

3. **Register it** in `pocket_desk_agent/command_map.py` by appending a tuple to `COMMAND_REGISTRY`:
   ```python
   ("mycommand", handlers.mycommand_command, "Short description"),
   ```

4. **Document it** in `docs/COMMANDS.md` and the quick-reference table in `README.md`.

### Handler boilerplate

```python
from telegram import Update
from telegram.ext import ContextTypes

async def mycommand_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args  # list of whitespace-split args after /mycommand
    await update.message.reply_text("Result here")
```

---

## Adding a New Gemini AI Tool

1. Implement the function in `file_manager.py` or a new module.
2. Add the JSON tool definition to `gemini_client.py` → `_get_api_tools()` (unchanged — both providers share this declaration).
3. Add the tool name to `ai_tool_loop.py`'s `ALLOWED_TOOLS` frozenset (NOT `gemini_client.py` — the allowlist now lives in `ai_tool_loop.py` and is only re-exported from `gemini_client.py`).
4. Handle the tool call in `gemini_actions.dispatch_gemini_tool` (invoked via `ai_tool_loop.run_tool_turn`).

Once a tool is allowlisted and dispatched this way, **both** `GeminiClient` and `NvidiaClient` pick it up automatically — no per-provider wiring needed.

---

## Coding Standards

- **Formatter:** `black` — run `make format` before committing
- **Linter:** `flake8` — run `make lint`
- **Types:** `mypy` — all new functions need type hints
- **Logging:** use `logger = logging.getLogger(__name__)`, never `print()`
- **Windows guard:** wrap Windows-only imports with `if platform.system() == "Windows":`
- **No raw path strings:** use `pathlib.Path` throughout

---

## Security Rules

- All file operations **must** go through `FileManager._is_safe_path()`.
- All handlers get `safe_command` applied automatically at registration — never add it as a decorator (double-wrapping).
- Never call `subprocess`/shell from a Gemini tool — no RCE vectors.
- Never commit secrets (`.env`, OAuth token files, `credentials`).
- OAuth tokens are stored with `chmod 600` / `icacls` restricted permissions.

---

## Resource Profile

The bot is designed to be lightweight when running as a background daemon.

### Idle Footprint

| Metric | Value |
|---|---|
| Idle RAM | ~55-70 MB |
| Idle CPU | <0.5% |
| Disk (installed) | ~140 MB (all deps) |

### Lazy-Import Convention

Heavy dependencies are loaded **on-demand**, not at startup:

- **aiohttp** (~5 MB) — loaded only when `/remote` starts the WebSocket server
- **mss** (~1 MB) — loaded only when `/remote` starts screen capture
- **qrcode** (~1 MB) — loaded only when `/remote` generates a QR code
- **dropbox** (~10 MB) — loaded only when `/getapk` uploads to Dropbox
- **pytesseract** (~1 MB) — loaded only when `/findtext` or `/smartclick` is used
- **pyautogui** (~3 MB) — loaded only when `/screenshot`, `/hotkey`, etc. are used
- **pywinauto + pygetwindow** (~8 MB) — loaded only when Claude/Antigravity UI automation commands are used

When adding new features, follow this pattern: if a dependency is only needed for a specific command, import it inside the handler function, not at module level.

### Dev-Mode Reloader

The file reloader in `main.py` (`start_reloader()`) only runs when a `.git` directory exists in the project root (i.e., running from a git checkout). When installed via pip, the reloader is disabled to avoid unnecessary CPU usage from scanning `.py` files every 1.5 seconds.

---

## Publishing to PyPI

Releases are published automatically via GitHub Actions (`publish.yml`) when a GitHub release is created:

1. CI verifies the git tag matches `version` in `pyproject.toml`.
2. Builds sdist + wheel with `python -m build`.
3. Publishes via OIDC trusted publishing (no long-lived API tokens stored in GitHub).

To bump the version, update `version` in `pyproject.toml`, commit, tag, and create a GitHub release.

---

## Key File Quick Reference

| Need to... | Go to |
|---|---|
| Add/change a bot command | `handlers/<domain>.py` + `command_map.py` |
| Change Gemini AI tools | `gemini_client.py` (declarations) + `ai_tool_loop.py` (allowlist + dispatch) |
| Change cross-provider fallback order/logic | `ai_router.py` |
| Change Gemini↔OpenAI history/tool-call conversion | `ai_history.py` |
| Change the NVIDIA fallback client | `nvidia_client.py` |
| Change sandboxed file ops | `file_manager.py` |
| Change config variables | `config.py` |
| Change rate limiting | `rate_limiter.py` |
| Change auto-update logic | `updater.py` |
| Change scheduling | `scheduler_registry.py` + `handlers/scheduling.py` |
| Change OAuth flow | `antigravity_auth.py` + `gemini_cli_auth.py` |
| Add/change workflow recipes | `recipe_registry.py` + `handlers/workflow_recipes.py` |
| Change desktop app targeting | `desktop_adapters.py` |
| Change remote desktop server | `remote/web_server.py` |
| Change remote input handling | `remote/input_bridge.py` |
| Change remote screen capture | `remote/capture.py` |
| Change cloudflared tunnel | `remote/tunnel.py` |
| See all commands | `docs/COMMANDS.md` |
| See architecture notes | `PROJECT_STRUCTURE.md` |
