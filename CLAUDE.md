# CLAUDE.md — Pocket Desk Agent

This file provides guidance for AI assistants (Claude Code and similar tools) working on this repository.

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
│   ├── handlers/               # Bot command handlers (13 modules)
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
│   │   └── callbacks.py        # Inline keyboard button handlers
│   ├── cli.py                  # Entry point for `pdagent` CLI
│   ├── main.py                 # Application bootstrap, scheduler loop
│   ├── config.py               # Config class — reads from os.environ
│   ├── configure.py            # Interactive setup wizard + INI loader
│   ├── command_map.py          # Centralized list of (command, handler, description)
│   ├── command_registry.py     # User-defined macro storage
│   ├── file_manager.py         # Sandboxed file I/O (path traversal prevention)
│   ├── gemini_client.py        # Gemini API client with tool-calling
│   ├── antigravity_auth.py     # OAuth 2.0 PKCE implementation
│   ├── auth.py                 # User allowlist + AntigravityAuth wrapper
│   ├── scheduler_registry.py   # Persistent scheduled task storage
│   ├── rate_limiter.py         # Token-bucket rate limiter
│   ├── updater.py              # Auto-update manager (git pull)
│   ├── automation_utils.py     # OCR/UI automation helpers
│   └── constants.py            # API endpoints and header constants
├── scripts/
│   ├── manage_auth.py          # OAuth credential management script
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
| Auth | OAuth 2.0 PKCE (`antigravity_auth.py`) |
| UI Automation | pywinauto, pyautogui, pygetwindow (Windows only) |
| Computer Vision | opencv-python, numpy (contour detection for /findelements) |
| OCR | pytesseract (Tesseract engine) |
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
pdagent auth         # manage OAuth credentials
pdagent version      # print version
```

---

## Configuration

Config is loaded in this precedence order:

1. Shell environment variables (highest priority)
2. `~/.pdagent/config.ini` (INI format, new)
3. `~/.pdagent/.env` (legacy)
4. `.env` in cwd (legacy)

All values live in `pocket_desk_agent/config.py` → `Config` class.

### Key variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot auth token from BotFather |
| `TELEGRAM_BOT_USERNAME` | Yes | — | Bot `@username` |
| `AUTHORIZED_USER_IDS` | Yes | — | Comma-separated Telegram user IDs |
| `GOOGLE_OAUTH_ENABLED` | No | `true` | Use OAuth instead of direct API key |
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth mode | — | GCP OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth mode | — | GCP OAuth client secret |
| `GOOGLE_API_KEY` | API key mode | — | Gemini API key (fallback) |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model selection |
| `APPROVED_DIRECTORIES` | No | `.` | Comma-separated allowed paths for file ops |
| `CLAUDE_DEFAULT_REPO_PATH` | No | `~/Documents` | Default repo root for Claude integration |
| `UPLOAD_EXPIRY_TIME` | No | `1h` | Dropbox link expiry (`1h`/`12h`/`24h`/`72h`) |
| `AUTO_UPDATE_ENABLED` | No | `true` | Enable periodic git-pull auto-update |
| `AUTO_UPDATE_INTERVAL_MINUTES` | No | `60` | Update check interval |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `MAX_TOKENS_PER_REQUEST` | No | `8000` | Gemini token limit |
| `SYSTEM_PROMPT` | No | — | Custom Gemini system prompt |

### Secrets — never commit

- `.env`, `~/.pdagent/.env`, `~/.pdagent/config.ini`
- `~/.pdagent/credentials` (OAuth client secrets)
- `~/.pdagent/tokens.json` (OAuth access/refresh tokens)

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

`main.py` runs a background task that calls `scheduler_registry.check_due_tasks()` every 60 seconds. `SchedulerRegistry` persists tasks to `~/.pdagent/scheduled_tasks.json` and cleans up entries older than 7 days.

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
- Never commit secrets (`.env`, `tokens.json`, `credentials`).
- OAuth tokens are stored with `chmod 600` / `icacls` restricted permissions.

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
| Change OAuth flow | `antigravity_auth.py` |
| See all 50+ commands | `docs/COMMANDS.md` |
| See architecture notes | `PROJECT_STRUCTURE.md` |
