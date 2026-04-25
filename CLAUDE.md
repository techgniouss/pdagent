# CLAUDE.md — Pocket Desk Agent

This file provides guidance for AI assistants (Claude Code and similar tools) working on this repository.

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
│   │   ├── automation.py       # /clicktext, /findtext, /smartclick, /findelements, etc.
│   │   ├── custom_commands.py  # /savecommand, /done, /listcommands, /deletecommand
│   │   ├── claude.py           # /claudeask, /clauderepo, /claudechat, /clauderemote, etc.
│   │   ├── antigravity.py      # /openantigravity, /antigravitychat, /claudecli, etc.
│   │   ├── build.py            # /build, /getapk
│   │   ├── scheduling.py       # /schedule, /claudeschedule, /listschedules, /cancelschedule
│   │   ├── remote.py           # /remote, /stopremote, session lifecycle + auto-install flow
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
│   ├── antigravity_auth.py     # OAuth 2.0 PKCE implementation
│   ├── auth.py                 # User allowlist + multi-mode auth wrapper
│   ├── gemini_cli_auth.py      # Gemini CLI OAuth PKCE implementation
│   ├── scheduler_registry.py   # Persistent scheduled task storage
│   ├── startup_manager.py      # Windows logon-task startup management
│   ├── rate_limiter.py         # Token-bucket rate limiter
│   ├── updater.py              # Auto-update manager (git pull)
│   ├── automation_utils.py     # OCR/UI automation helpers
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
| Computer Vision | opencv-python, numpy (contour detection for /findelements) |
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
git clone https://github.com/techgniouss/pocket-desk-agent.git
cd pocket-desk-agent
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
make run         # run bot (foreground)
make test        # pytest -v
make lint        # flake8 + mypy
make format      # black pocket_desk_agent/ scripts/
make build       # build sdist + wheel
make clean       # remove caches and build artifacts
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
| `APPROVED_DIRECTORIES` | No | `Path.home()` | Comma-separated allowed paths for file ops |
| `CLAUDE_DEFAULT_REPO_PATH` | No | `~/Documents` | Default repo root for Claude integration |
| `UPLOAD_EXPIRY_TIME` | No | `1h` | Dropbox link expiry (`1h`/`12h`/`24h`/`72h`) |
| `AUTO_UPDATE_ENABLED` | No | `true` | Enable periodic git-pull auto-update |
| `AUTO_UPDATE_INTERVAL_MINUTES` | No | `60` | Update check interval |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `MAX_TOKENS_PER_REQUEST` | No | `8000` | Gemini token limit |
| `SYSTEM_PROMPT` | No | — | Custom Gemini system prompt |
| `CLOUDFLARED_PATH` | No | auto-discovered | Override path to the `cloudflared` binary used by `/remote` |

### Secrets — never commit

- `.env`, `~/.pdagent/.env`, `~/.pdagent/config`
- `~/.pdagent/credentials` (OAuth client secrets)
- `~/.config/antigravity-chatbot/tokens.json` and `~/.config/pdagent-gemini/tokens.json` (OAuth access/refresh tokens)

---

## Architecture Patterns

### 1. `safe_command` decorator (every handler must use it)

Located in `handlers/_shared.py`. Wraps every command/callback handler to:
- Silently reject unauthorized users (from `AUTHORIZED_USER_IDS`)
- Enforce per-user rate limits (token-bucket in `rate_limiter.py`)
- Catch all exceptions and send a sanitized error message
- Prevent bot process crashes

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

- `_ALLOWED_TOOLS` frozenset in `gemini_client.py` restricts which tool names the AI can invoke
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

1. **Write the handler** in the appropriate file under `pocket_desk_agent/handlers/` (or create a new module for a new domain). Decorate with `@safe_command`.

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
from pocket_desk_agent.handlers._shared import safe_command

@safe_command
async def mycommand_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args  # list of whitespace-split args after /mycommand
    await update.message.reply_text("Result here")
```

---

## Adding a New Gemini AI Tool

1. Implement the function in `file_manager.py` or a new module.
2. Add the JSON tool definition to `gemini_client.py` → `_get_api_tools()`.
3. Handle the tool call in `gemini_client.py` → `send_message()`.
4. Add the tool name to `_ALLOWED_TOOLS` frozenset.

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
- All handlers **must** use `@safe_command` (authorization + rate limiting).
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

- **opencv-python + numpy** (~60-80 MB) — loaded only when `/findelements` is used
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
| Change Gemini AI tools | `gemini_client.py` |
| Change sandboxed file ops | `file_manager.py` |
| Change config variables | `config.py` |
| Change rate limiting | `rate_limiter.py` |
| Change auto-update logic | `updater.py` |
| Change scheduling | `scheduler_registry.py` + `handlers/scheduling.py` |
| Change OAuth flow | `antigravity_auth.py` + `gemini_cli_auth.py` |
| Change remote desktop server | `remote/web_server.py` |
| Change remote input handling | `remote/input_bridge.py` |
| Change remote screen capture | `remote/capture.py` |
| Change cloudflared tunnel | `remote/tunnel.py` |
| See all commands | `docs/COMMANDS.md` |
| See architecture notes | `PROJECT_STRUCTURE.md` |
