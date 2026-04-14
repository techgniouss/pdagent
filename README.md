# Pocket Desk Agent

<p align="center">
  <a href="https://pypi.org/project/pocket-desk-agent/"><img src="https://img.shields.io/pypi/v/pocket-desk-agent.svg?style=for-the-badge&color=3776AB" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Windows-Supported-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License" />
</p>

<p align="center"><strong>Your PC in your pocket — remote control, AI automation, and developer tools — all through Telegram.</strong></p>

<p align="center">
  <a href="docs/COMMANDS.md">Commands</a> •
  <a href="docs/LOCAL_DEVELOPMENT.md">Development</a> •
  <a href="CONTRIBUTING.md">Contributing</a> •
  <a href="SECURITY.md">Security</a>
</p>

<p align="center">
  <a href="README.md"><strong>English</strong></a> •
  <a href="README.zh-CN.md">中文</a> •
  <a href="README.ru.md">Русский</a> •
  <a href="README.es.md">Español</a> •
  <a href="README.de.md">Deutsch</a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.ja.md">日本語</a> •
  <a href="README.pt-BR.md">Português</a> •
  <a href="README.ko.md">한국어</a> •
  <a href="README.tr.md">Türkçe</a> •
  <a href="README.uk.md">Українська</a>
</p>

**Pocket Desk Agent** is a self-hosted Telegram bot that gives you full remote control of your Windows PC from any device. It runs entirely on your machine — no cloud relay, no subscription, no data leaving your network beyond Telegram's message relay and the optional Gemini API.

Out of the box, with zero AI setup:
- **Browse and read files** sandboxed to your approved directories
- **Control your desktop** — screenshots, keyboard shortcuts, clipboard, window switching, sleep, shutdown
- **Automate UI** with OCR-based text clicking (Tesseract) and element detection (OpenCV)
- **Drive Claude Desktop and VS Code** remotely without touching your keyboard
- **Record macros** and replay multi-step workflows with a single command
- **Schedule tasks** to run while you sleep — survives restarts
- **Build and deliver Android APKs** from React Native projects via Telegram

Add **Google Gemini 2.0 Flash** credentials to unlock:
- **Conversational AI chat** with multi-turn memory and image analysis
- **Agentic computer use** — Gemini can browse files, take screenshots, click, type, and automate your PC from natural language, with human-in-the-loop confirmation for any destructive action
- **Prompt enhancement** via `/enhance`

---

## Key Features

Everything below works with no AI configuration required:

- **File System Explorer**: Browse, read, and search local PC directories from your phone, sandboxed to approved paths.
- **Desktop Control**: Take screenshots, send keyboard shortcuts, manage the clipboard, switch open windows, check battery, and trigger sleep/shutdown.
- **Vision & UI Automation**: OCR-based clicking via Tesseract — find and click any visible text on screen. Computer vision (OpenCV) for icon and UI element detection.
- **Macro Recording**: Record multi-step UI sequences and replay them with a single command.
- **Claude Desktop Integration**: Remote control of Claude Desktop App — send prompts, switch models, manage workspaces, and automate chat flows without touching your PC.
- **VS Code / Antigravity Integration**: Open folders, switch AI models, and drive the Antigravity VS Code extension remotely.
- **Task Scheduler**: Schedule automation flows or Claude prompts to run at a specified time, even while you sleep. Tasks survive restarts.
- **Build Automation**: Trigger React Native Android builds and retrieve APKs through Telegram or large-file upload links when needed.
- **Auto-Update**: The bot can check for and apply updates on demand.
- **Lightweight**: ~55-70 MB idle RAM, <0.5% idle CPU. Heavy dependencies (OpenCV, NumPy, Dropbox) load on-demand only when their commands are used.

**Optional — requires Google Gemini credentials:**

- **AI Chat & Computer Use**: Google Gemini 2.0 Flash with multi-turn conversation, image analysis, and full agentic tool-calling. Send any text or photo directly to chat. Gemini acts as an autonomous agent that can natively browse your files, analyze screenshots, and use UI automation (click, type, navigate) to perform tasks on your PC in response to natural language requests. All destructive or system-altering actions require explicit human-in-the-loop confirmation via Telegram buttons.
- **Prompt Enhancement**: Use `/enhance` to let Gemini rewrite and improve a prompt before sending it anywhere.

---

## How It Works

Pocket Desk Agent runs as a local process on your Windows PC and connects **outbound** to Telegram's servers via long-polling — no inbound port forwarding, router configuration, or dynamic DNS is required.

```
Your Phone → Telegram servers → (outbound polling) → Pocket Desk Agent (local) → PC action → Reply
```

When you send a message from your phone, Telegram holds it until the bot's polling loop picks it up (typically under 1 second). The command runs locally on your PC and the result is sent back through the same Telegram relay.

**Key internal components:**

| Component | Role |
| :--- | :--- |
| `python-telegram-bot` | Async Telegram client — receives and dispatches all commands |
| `GeminiClient` | Manages Gemini API sessions, multi-turn history, and tool-calling |
| `FileManager` | Sandboxed file I/O — all paths are validated against `APPROVED_DIRECTORIES` |
| `AuthManager` | Multi-provider OAuth wrapper for Antigravity, Gemini CLI, and API key modes |
| `SchedulerRegistry` | Persists scheduled tasks to disk and checks every 60 s; survives restarts |
| `RateLimiter` | Per-user token-bucket rate limiter applied automatically to every command |

All 70 command handlers are registered centrally in `command_map.py`. Every handler is wrapped by `@safe_command`, which enforces authorization, rate limiting, and error reporting in a single place — no manual auth checks are needed in individual handlers.

---

## Platform Compatibility

| Feature | Windows | macOS / Linux |
| :--- | :---: | :---: |
| File system (browse, read, search) | ✅ | ✅ |
| AI chat & image analysis (Gemini) | ✅ | ✅ |
| Task scheduling | ✅ | ✅ |
| Auto-update | ✅ | ✅ |
| Screenshots | ✅ | ✅ |
| Keyboard shortcuts (`/hotkey`) | ✅ | ⚠️ partial |
| Clipboard read/write | ✅ | ⚠️ partial |
| Battery status | ✅ | ✅ |
| UI automation (OCR click, find text) | ✅ | ❌ |
| Element detection (OpenCV) | ✅ | ❌ |
| Window management (`/windows`, `/focuswindow`) | ✅ | ❌ |
| Claude Desktop integration | ✅ | ❌ |
| VS Code / Antigravity integration | ✅ | ❌ |
| React Native build automation | ✅ | ❌ |
| Automatic startup after login | ✅ | ❌ |

> macOS/Linux users can run the bot for file system access, Gemini AI chat, and scheduling. UI automation features require Windows and, for OCR commands, Tesseract.

---

## Before You Start

You only need two things to get started. Google credentials are optional and only needed if you want AI chat.

### 1. Create a Telegram Bot

1. Open Telegram and message **[@BotFather](https://t.me/BotFather)**
2. Send `/newbot` and follow the prompts to name your bot
3. Copy the **bot token** (looks like `123456789:ABCdef...`) — this is your `TELEGRAM_BOT_TOKEN`

### 2. Get Your Telegram User ID

1. Message **[@userinfobot](https://t.me/userinfobot)** on Telegram
2. It will reply with your numeric user ID — this is your `AUTHORIZED_USER_IDS`

> Only Telegram accounts listed in `AUTHORIZED_USER_IDS` can control the bot. Keep this to yourself.

### 3. (Optional) Get Google / Gemini Credentials

Only needed if you want AI chat, image analysis, or the `/enhance` command. All other features work without this.

Choose one option:

Provider note: **Gemini CLI OAuth** needs no project setup. **Antigravity OAuth** uses Google's internal code-assist API, usually auto-fetches a project, and supports `GOOGLE_PROJECT_ID` override if needed.

**Option A — OAuth (Recommended, zero config):** The bot includes built-in OAuth support — no separate GCP project or API key required for the recommended browser-login flow. During setup, choose **Antigravity OAuth** or **Gemini CLI OAuth**, or choose **Setup Later** and authenticate anytime via `/login` in Telegram.

**Option B — API Key:** No login flow, just paste a key.
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create an API key — this is your `GOOGLE_API_KEY`

> **Custom OAuth app:** If you want to use your own GCP OAuth credentials instead of the built-in ones, set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` in your config. The redirect URI to register is `http://localhost:51121/oauth-callback`.

---

## Quick Start & Installation

### System Requirements

- **Python 3.11+**
- **Windows 10 or later** — required for UI automation features (`pywinauto`, `pyautogui`, `pygetwindow`). File system access, Gemini AI chat, and task scheduling also work on macOS/Linux (see [Platform Compatibility](#platform-compatibility)).
- **Tesseract OCR** — needed for `/findtext`, `/smartclick`, and Claude/Antigravity UI automation. `pdagent` detects if it's missing on first run and offers to install it automatically via winget. Run `pdagent setup` at any time to re-check.
- **Visual C++ Redistributables** — required by `pywinauto` and `pyautogui` on Windows. Usually already present; install the latest from Microsoft if you hit `ImportError` on startup.

### Option A: Install from PyPI (Recommended)

```bash
pip install pocket-desk-agent
pdagent
```

On the first run, `pdagent` launches an interactive setup wizard that walks you through all configuration values and offers to install Tesseract OCR automatically. That's it.

```bash
pdagent start        # run as a background daemon instead
pdagent configure    # re-run the setup wizard at any time
pdagent setup        # re-check and install system dependencies (e.g. Tesseract)
pdagent startup status
pdagent startup configure
```

### Option B: Local Developer Mode

```bash
git clone https://github.com/techgniouss/pocket-desk-agent.git
cd pocket-desk-agent
pip install -e ".[dev]"
pdagent
```

For the full local development guide (virtual environment setup, live reloader, make targets, resource profile), see **[docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)**.

---

## Configuration

### Using the Setup Wizard (Recommended)

```bash
pdagent configure
```

This walks you through setting all required values and saves them to `~/.pdagent/config`.

On Windows, the wizard also offers optional **automatic background startup after login**. This is disabled by default. If you enable it, Pocket Desk Agent starts automatically in the background after you sign in, so you do not need to run `pdagent start` after every reboot. This is **not** a Windows Service and is designed to preserve screenshot, OCR, Claude Desktop, and VS Code automation features.

The Gemini authentication step offers four choices:

| Choice | Description | Best for |
| :--- | :--- | :--- |
| `1) Antigravity OAuth` | Opens browser immediately for sign-in using built-in credentials. Token auto-refreshes. | Most users — zero config, longest session lifetime |
| `2) Gemini CLI OAuth` | Browser login against the public Gemini API. No GCP project required. Token auto-refreshes. | Users already on the Gemini CLI ecosystem |
| `3) API Key` | Paste a Google AI Studio key. No login flow or browser needed. | Automation, headless servers, or API key preference |
| `4) Setup Later` | Skips Gemini setup. Start the bot and authenticate via `/login` in Telegram at any time. | Trying the bot without AI first |

> **Token refresh:** OAuth tokens (options 1 and 2) are stored locally in `~/.config/` and refresh automatically in the background. You will only need to re-authenticate if you explicitly log out or if the refresh token expires (typically after 7 days of inactivity).

> **Switching providers:** You can switch between auth modes at any time. Run `pdagent auth` and choose "Switch Provider", or use `/logout` then `/login` in Telegram to start a fresh auth flow.

### Manual Configuration

Copy the template and edit it:

```bash
cp .env.example .env
```

**Required variables:**

```ini
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
TELEGRAM_BOT_USERNAME="your_bot_username"
AUTHORIZED_USER_IDS="123456789"
APPROVED_DIRECTORIES="C:\Users\YourName\Documents"
```

**Google/Gemini authentication — optional, required only for AI chat and `/enhance`:**

```ini
# Option 1: OAuth (recommended — built-in credentials, no GCP setup needed)
# Use /login in Telegram to authenticate after starting the bot
GOOGLE_OAUTH_ENABLED=true

# Set GEMINI_AUTH_MODE=antigravity for the internal code-assist API
# or GEMINI_AUTH_MODE=gemini-cli for the public Gemini API.
# If Antigravity project auto-detection fails, set GOOGLE_PROJECT_ID.

# Option 2: Direct API key
# GEMINI_AUTH_MODE=apikey
GOOGLE_OAUTH_ENABLED=false
GOOGLE_API_KEY="your_google_ai_studio_key"

# Optional override: bring your own GCP OAuth client
# Register redirect URI: http://localhost:51121/oauth-callback
GOOGLE_OAUTH_CLIENT_ID="your_client_id"
GOOGLE_OAUTH_CLIENT_SECRET="your_client_secret"
```

**Optional variables:**

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model to use |
| `GEMINI_AUTH_MODE` | `antigravity` | Auth provider: `antigravity`, `gemini-cli`, or `apikey` |
| `GOOGLE_PROJECT_ID` | `(unset)` | Optional Antigravity project override if auto-detection fails |
| `UPLOAD_EXPIRY_TIME` | `1h` | TempFile upload expiry for large-file links (`1h`/`12h`/`24h`/`72h`) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `MAX_TOKENS_PER_REQUEST` | `8000` | Gemini token limit per request |
| `CLAUDE_DEFAULT_REPO_PATH` | `~/Documents` | Default repo root for Claude CLI integration |
| `SYSTEM_PROMPT` | — | Custom Gemini system prompt |
| `DROPBOX_ACCESS_TOKEN` | — | Dropbox token for optional large-file uploads (see [docs/dropbox-setup.md](docs/dropbox-setup.md)) |

### Legacy Config Aliases

If you are upgrading from an earlier version of Pocket Desk Agent, the following environment variable names still work but are deprecated. Migrate to the current names when convenient.

| Legacy name | Current name |
| :--- | :--- |
| `ALLOWED_USERS` | `AUTHORIZED_USER_IDS` |
| `SYSTEM_INSTRUCTION` | `SYSTEM_PROMPT` |
| `ANTIGRAVITY_ENABLED` | `GOOGLE_OAUTH_ENABLED` |
| `DEFAULT_REPO_PATH` | `CLAUDE_DEFAULT_REPO_PATH` |

### Config File Locations (precedence order)

1. Shell environment variables (highest priority)
2. `~/.pdagent/config` (INI format — written by `pdagent configure`)
3. `~/.pdagent/.env` (legacy dotenv)
4. `.env` in the current working directory (legacy dotenv)

---

## Running the Bot

| Command | Description |
| :--- | :--- |
| `pdagent` | Run in foreground (attached to terminal) |
| `pdagent start` | Start as background daemon |
| `pdagent stop` | Stop the background daemon |
| `pdagent restart` | Restart the daemon |
| `pdagent status` | Check if the daemon is running |
| `pdagent configure` | Run the interactive setup wizard |
| `pdagent setup` | Check and install system dependencies (e.g. Tesseract OCR) |
| `pdagent startup enable` | Enable automatic startup after Windows login |
| `pdagent startup disable` | Disable automatic startup after Windows login |
| `pdagent startup status` | Show automatic startup status |
| `pdagent startup configure` | Interactively configure automatic startup |
| `pdagent auth` | Manage Gemini authentication credentials |
| `pdagent version` | Print the installed version |

---

## Commands Quick Reference

> For the complete reference with all 70 built-in commands, see **[docs/COMMANDS.md](docs/COMMANDS.md)**.

<details>
<summary><strong>Expand cheat sheet</strong></summary>

### Authentication & Core

| Command | Description |
| :--- | :--- |
| `/start` | Initialize the bot |
| `/help` | Show the help menu |
| `/status` | Check Gemini API and session status |
| `/login` | Choose an authentication method and start the OAuth login flow |
| `/authcode <code>` | Enter an OAuth verification code |
| `/checkauth` | Check current authentication status |
| `/logout` | Sign out of Google |
| `/new` | Clear chat history and start fresh |
| `/enhance <prompt>` | Let Gemini improve a prompt |
| *(any text/photo)* | Chat with Gemini 2.0 Flash |

### File System

| Command | Description |
| :--- | :--- |
| `/pwd` | Show current directory |
| `/ls [path]` | List files |
| `/cd <path>` | Change directory |
| `/cat <file>` | Read file contents |
| `/find <pattern>` | Search files by glob |
| `/info <path>` | File/folder metadata |

### Desktop Control

| Command | Description |
| :--- | :--- |
| `/screenshot` | Capture the current display |
| `/hotkey <keys>` | Send a keyboard shortcut (e.g. `ctrl+c`) |
| `/windows` | List open application windows and let you switch by number |
| `/focuswindow <number>` | Activate a window from the most recent `/windows` list |
| `/clipboard <text>` | Set the clipboard |
| `/viewclipboard` | Read the clipboard |
| `/battery` | Battery status |
| `/sleep` | Put PC to sleep |
| `/shutdown` | Shut down the PC |
| `/wakeup` | Wake-on-LAN instructions |
| `/stopbot` | Stop the bot process |

### UI Automation

> Requires Tesseract OCR. Run `pdagent setup` to install.

| Command | Description |
| :--- | :--- |
| `/smartclick <text>` | Find text on screen and click it |
| `/findtext <text>` | Locate text on screen (returns coordinates, no click) |
| `/clicktext <x> <y>` | Click at specific coordinates |
| `/findelements` | Detect and number all visible UI icons |
| `/clickelement <id>` | Click a detected element by number |
| `/typeenter <text>` | Type text and press Enter |
| `/pasteenter` | Paste the current clipboard contents and press Enter |
| `/scrollup` / `/scrolldown` | Scroll the active window |

`/windows` and `/focuswindow` switch top-level application windows. They do not switch browser tabs inside a single app.

### Macro Recording

| Command | Description |
| :--- | :--- |
| `/savecommand <name>` | Start recording a custom macro |
| `/done` | Finish recording and save |
| `/cancelrecord` | Discard the current recording |
| `/listcommands` | List all saved macros |
| `/deletecommand <name>` | Delete a saved macro |

### Claude Desktop Integration

| Command | Description |
| :--- | :--- |
| `/openclaude` | Launch Claude Desktop |
| `/stopclaude` | Kill Claude Desktop |
| `/clauderemote` | Open cmd at default repo path and run `claude remote-control` |
| `/claudeask <prompt>` | Send a detailed prompt to Claude Desktop |
| `/claudechat <prompt>` | Automated Claude chat flow |
| `/claudenew` | Start a new Claude chat session |
| `/clauderepo <path>` | Sync a repository with Claude |
| `/claudebranch` | Claude branch management |
| `/claudelatest` | Get the latest Claude response |
| `/claudesearch <query>` | Search Claude chat history |
| `/claudeselect` | Select Claude workspace |
| `/claudemode` | Switch Claude mode |
| `/claudemodel` | Switch Claude model |
| `/claudescreen` | Screenshot of the Claude app |
| `/claudeschedule <HH:MM> <text>` | Schedule a Claude prompt |

### VS Code / Antigravity Integration

| Command | Description |
| :--- | :--- |
| `/openantigravity` | Open VS Code with Antigravity |
| `/antigravitychat` | Focus the Antigravity chat panel |
| `/antigravitymode` | Switch Antigravity mode |
| `/antigravitymodel` | Switch the Antigravity AI model |
| `/antigravityclaudecodeopen` | Open the Claude Code panel in VS Code |
| `/antigravityopenfolder <path>` | Open a folder in VS Code |
| `/claudecli [path]` | Open Claude Code CLI in a folder |
| `/claudeclisend <text>` | Send a prompt to an active Claude CLI session |
| `/openbrowser [browser]` | Open Edge, Chrome, Firefox, or Brave |

### Scheduling

| Command | Description |
| :--- | :--- |
| `/schedule <HH:MM>` | Start recording a scheduled automation sequence |
| `/claudeschedule <HH:MM> <text>` | Schedule a Claude prompt |
| `/listschedules` | View all pending scheduled tasks |
| `/cancelschedule <id>` | Cancel a scheduled task |

### Build Automation

| Command | Description |
| :--- | :--- |
| `/build` | Start a React Native Android build |
| `/getapk` | Download the latest built APK |

</details>

---

## Security

Pocket Desk Agent runs **entirely on your local machine** — no data is sent to any third-party server beyond Google's Gemini API and Telegram's message relay. Configure it carefully, as it provides system-level access to your workstation.

1. **User allowlist**: Every request is checked against `AUTHORIZED_USER_IDS`. Unrecognized Telegram accounts are silently rejected — no error is returned to the sender.
2. **Directory sandboxing**: File operations are restricted to `APPROVED_DIRECTORIES` using `Path.relative_to()` validation. Path traversal attacks (`../`) are blocked at the framework level.
3. **Rate limiting**: All commands are rate-limited per user. Sensitive or expensive operations have stricter limits than routine commands.
4. **Secret isolation**: Config and client credentials live in `~/.pdagent/`, while OAuth tokens are stored in provider-specific config directories such as `~/.config/antigravity-chatbot/` and `~/.config/pdagent-gemini/`, all with restricted file permissions. Never commit `.env` files, OAuth token files, or credential files.
5. **AI safety**: Gemini AI cannot execute shell commands directly. System automation tool access is tightly controlled, and any side-effecting UI interaction (keyboard, mouse, file modification, scheduling) triggers an inline confirmation prompt requiring explicit human-in-the-loop approval before execution.

---

## Troubleshooting

**Bot starts but doesn't respond to messages**
- Confirm your Telegram user ID is in `AUTHORIZED_USER_IDS` (get it from [@userinfobot](https://t.me/userinfobot))
- Check `bot.log` in your working directory for errors
- Verify the bot token is correct — a wrong token causes silent polling failures
- Run `/status` in the bot chat to verify the Gemini connection

**`/findtext` or `/smartclick` returns an error**
- Tesseract OCR is not installed or not on PATH
- Run `pdagent setup` to install it automatically, or manually: `winget install UB-Mannheim.TesseractOCR`
- After installing, restart your terminal before running the bot again

**Gemini authentication fails**
- Run `pdagent auth` and choose "Login" to re-authenticate, or use `/login` in Telegram
- For OAuth: make sure port `51121` is not blocked by a firewall or in use by another process; the bot starts a local HTTP server on that port to receive the OAuth callback
- For API key mode: check your key is valid at [Google AI Studio](https://aistudio.google.com/app/apikey)
- If you see "invalid_grant", your refresh token has expired — log out and re-authenticate

**Bot crashes on startup with `ImportError`**
- Run `pip install --upgrade pocket-desk-agent` to ensure all dependencies are current
- On Windows, some packages (`pywinauto`, `pyautogui`) require Visual C++ Redistributables — install the latest from Microsoft's website

**"Another bot instance is already running"**
- Run `pdagent stop` to clear the stale process lock, then `pdagent start`
- If `pdagent stop` does not resolve it, find and kill the process manually: `taskkill /F /IM python.exe` (Windows) or check for a leftover `.pid` file in `~/.pdagent/`

**File operation fails with "Access denied" or "Path not allowed"**
- The requested path is outside `APPROVED_DIRECTORIES`
- Add the path to your config: `APPROVED_DIRECTORIES="C:\Users\YourName\Documents,C:\projects"`
- Separate multiple directories with commas; use absolute paths

**Scheduled tasks don't fire**
- The bot must be running when the scheduled time arrives — tasks do not fire if the bot is stopped
- Run `/listschedules` to confirm the task is still pending and the time format is correct (`HH:MM` in 24-hour time)
- Check `LOG_LEVEL=DEBUG` output for scheduler errors

**Bot is running but commands respond very slowly**
- Gemini API latency can vary; non-AI commands should respond in under 2 seconds
- For UI automation, large screenshots slow OCR — try `/screenshot` first to confirm the display is being captured correctly
- Run `pdagent status` to check if a background command is still executing

**`/build` or `/getapk` reports "no APK found"**
- Ensure `CLAUDE_DEFAULT_REPO_PATH` points to a React Native project root containing `android/`
- Use `/clauderepo <path>` to set a different project directory for the session
- Check build logs in the Telegram chat for the exact Gradle error

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and how to add new commands.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
