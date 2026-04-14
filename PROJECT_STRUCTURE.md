# Project Structure

This document provides a high-level overview of the **Pocket Desk Agent** codebase to help developers navigate and extend the system.

## Core Architecture

The system is built on a modular architecture: Telegram as the interface, Google Gemini as the AI brain, and local automation tools for system control.

```
pocket-desk-agent/
├── pocket_desk_agent/              # Main application package
│   ├── handlers/                   # Command handlers split into 13 focused modules
│   │   ├── __init__.py             # Re-exports all public handler names
│   │   ├── _shared.py              # Singleton clients, safe_command decorator, global state
│   │   ├── auth.py                 # /login, /authcode, /checkauth, /logout
│   │   ├── core.py                 # /start, /help, /status, /new, /enhance, /sync, etc.
│   │   ├── filesystem.py           # /pwd, /cd, /ls, /cat, /find, /info
│   │   ├── system.py               # /screenshot, /hotkey, /clipboard, /battery, /shutdown, etc.
│   │   ├── automation.py           # /clicktext, /findtext, /smartclick, /findelements, etc.
│   │   ├── custom_commands.py      # /savecommand, /done, /cancelrecord, /listcommands, etc.
│   │   ├── claude.py               # /claudeask, /clauderepo, /claudechat, /clauderemote, etc.
│   │   ├── antigravity.py          # /openantigravity, /antigravitychat, /claudecli, etc.
│   │   ├── build.py                # /build, /getapk
│   │   ├── scheduling.py           # /schedule, /claudeschedule, /listschedules, /cancelschedule
│   │   └── callbacks.py            # Inline keyboard button handlers
│   ├── cli.py                      # pdagent console-script entry point
│   ├── main.py                     # Application bootstrap & scheduler loop
│   ├── config.py                   # Config class — reads from os.environ via load()
│   ├── configure.py                # Interactive setup wizard + INI config loader
│   ├── command_map.py              # Centralized registry: maps command names → handlers
│   ├── command_registry.py         # Persistent storage for user-defined macros
│   ├── file_manager.py             # Sandboxed file I/O (path traversal prevention)
│   ├── gemini_actions.py           # Gemini UI automation tools and confirmation flows
│   ├── gemini_client.py            # Gemini API client with tool-calling
│   ├── antigravity_auth.py         # OAuth 2.0 PKCE implementation
│   ├── auth.py                     # User allowlist + multi-mode auth wrapper
│   ├── gemini_cli_auth.py          # Gemini CLI OAuth PKCE implementation
│   ├── window_utils.py             # Window inventory + activation helpers for /windows
│   ├── scheduler_registry.py       # Persistent scheduled task storage
│   ├── startup_manager.py          # Windows logon-task startup management
│   ├── rate_limiter.py             # Token-bucket rate limiter (per-user, per-command)
│   ├── updater.py                  # Auto-update manager (git pull)
│   ├── automation_utils.py         # OCR and UI automation helpers
│   └── constants.py                # API endpoints and header constants
├── scripts/
│   ├── manage_auth.py              # Gemini authentication management (pdagent auth)
│   └── manage_service.py           # Daemon lifecycle (stop/restart/status)
├── docs/                           # Feature-specific documentation
│   ├── COMMANDS.md                 # Complete command reference
│   ├── BUILD_WORKFLOW.md           # React Native APK build automation guide
│   ├── AUTHENTICATION_REQUIREMENTS.md  # Which commands need auth vs. not
│   ├── MOBILE_AUTHENTICATION.md    # OAuth flow step-by-step guide
│   ├── ANTIGRAVITY_LOGIN_IMPLEMENTATION.md  # OAuth architecture reference
│   ├── LOCAL_DEVELOPMENT.md        # Local development workflow and tooling
│   └── dropbox-setup.md            # Dropbox integration setup guide
├── .github/workflows/
│   └── publish.yml                 # Automated PyPI publishing on release
├── Makefile                        # Dev task automation (install, test, lint, format)
├── pyproject.toml                  # PEP 621 metadata, dependencies, build config
├── requirements.txt                # Pinned dependency list (mirrors pyproject.toml)
├── .env.example                    # Configuration template
├── setup.sh / setup.bat            # Platform setup helpers
├── README.md
└── CONTRIBUTING.md
```

---

## Key Components

### 1. `handlers/` package
All Telegram command handlers live here, split across 13 focused modules by domain. Every handler **must** be decorated with `@safe_command` from `_shared.py`, which enforces authorization, rate limiting, and exception safety.

The `_shared.py` module holds three module-level singletons used across all handler files:
- `auth_client` — `AntigravityAuth` instance for OAuth token management
- `gemini_client` — `GeminiClient` for Gemini API + conversation history
- `file_manager` — `FileManager` for sandboxed file I/O

Despite the legacy class name, `auth_client` now acts as the multi-provider auth manager for Antigravity OAuth and Gemini CLI OAuth.

### 2. `command_map.py`
Centralized registry of `(command_name, handler_func, description)` tuples. `main.py` reads this at startup to register all `CommandHandler`s and sync Telegram's command menu. Adding a new command here is the only wiring step needed.

### 3. `config.py`
`Config` is a class whose attributes are populated by `Config.load()`. This allows tests to patch `os.environ` before calling `load()` without global side-effects. Config is auto-loaded at import time for backward compatibility.

Config precedence (highest to lowest):
1. Shell environment variables
2. `~/.pdagent/config`
3. `~/.pdagent/.env`
4. `.env` in cwd

### 4. `file_manager.py`
Secure file system abstraction. All paths are validated against `APPROVED_DIRECTORIES` using `Path.relative_to()` (not string prefix matching). Always route new file operations through `FileManager._is_safe_path()`.

### 5. `gemini_client.py` & `gemini_actions.py`
Hand-rolled HTTPS client for the Gemini API (`gemini_client.py`). Implements extensive tool-calling capabilities (`gemini_actions.py`) allowing Gemini to browse files and automate the desktop. All side-effecting tools require human-in-the-loop inline confirmations to prevent prompt-injection attacks. History is trimmed to 40 turns to bound memory usage.

### 6. `rate_limiter.py`
Token-bucket rate limiter keyed by `(user_id, command)`. The global `rate_limiter` instance in `_shared.py` has per-command overrides for expensive or dangerous operations (e.g., `/shutdown` is capped at 1 per 5 minutes).

### 7. `scheduler_registry.py`
Manages `~/.pdagent/scheduled_tasks.json`. The scheduler loop in `main.py` polls every 60 seconds. Tasks older than 7 days are automatically cleaned up.

### 8. `auth.py`, `antigravity_auth.py`, `gemini_cli_auth.py`
Multi-provider authentication stack. `auth.py` selects the active provider per user, while `antigravity_auth.py` and `gemini_cli_auth.py` implement the provider-specific OAuth PKCE flows. Tokens are stored in provider-specific config directories with restricted file permissions.

---

## Performance Conventions

### Lazy Imports

Heavy dependencies are imported **inside handler functions**, not at module level, so they don't add to idle RAM:

- `opencv-python`, `numpy` — inside `automation_utils.py` functions
- `dropbox` — inside `handlers/build.py` upload functions
- `pytesseract` — inside `automation_utils.py` OCR functions
- `pywinauto`, `pygetwindow`, `PIL.ImageGrab` — loaded on first use via `_load_win_deps()` in `handlers/claude.py` and `handlers/antigravity.py`

When adding new features that require heavy dependencies, follow this pattern.

### Dev-Mode Reloader

`main.py` starts a file-watching reloader thread (`start_reloader()`) only when a `.git` directory exists in the project root. This means:

- **Git checkout** (developer): reloader runs, auto-restarts on `.py` changes
- **pip install** (end-user): reloader is disabled, no CPU overhead

---

## Extending the Bot

### Adding a New Command

1. **Write the handler** in the appropriate module under `pocket_desk_agent/handlers/`. Use `@safe_command`.

   ```python
   from telegram import Update
   from telegram.ext import ContextTypes
   from pocket_desk_agent.handlers._shared import safe_command

   @safe_command
   async def mycommand_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
       await update.message.reply_text("Result here")
   ```

2. **Export it** from `pocket_desk_agent/handlers/__init__.py`.

3. **Register it** in `pocket_desk_agent/command_map.py`:
   ```python
   ("mycommand", handlers.mycommand_command, "Short description"),
   ```

4. **Document it** in `docs/COMMANDS.md` and the README quick reference.

5. *(Optional)* Set a custom rate limit in `rate_limiter.py` if the command is expensive or sensitive.

### Adding a New Gemini AI Tool

1. Implement the tool definition in `gemini_actions.py` → `get_gemini_action_tools()`.
2. Add the execution logic in `gemini_actions.py` → `dispatch_gemini_tool()`. If it has side effects, use `await _queue_confirmation()` to require user approval.
3. If adding a new tool with side-effects, add its name to `_RATE_LIMITED_TOOLS` and define a rate limit in `gemini_actions.py`.

### Modifying AI Behavior

Edit the system instruction in `gemini_client.py` to change the AI's personality, rules, or available context.
