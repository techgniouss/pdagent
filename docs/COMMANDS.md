# Pocket Desk Agent: Full Command Reference

Welcome to the definitive guide for interacting with your Pocket Desk Agent.
This document covers all commands organized by capability.

## Table of Contents

- [Core Bot Commands](#core-bot-commands)
- [Native AI Chat](#native-ai-chat-no-command-needed)
- [File System Operations](#file-system-operations)
- [System Settings & Controls](#system-settings--controls)
- [Vision & UI Automation](#vision--ui-automation)
- [Remote Desktop](#remote-desktop)
- [Custom Command Sequences](#custom-command-sequences)
- [Claude & CLI Integration](#claude--cli-integration)
- [Antigravity Controller](#antigravity-controller)
- [Browser Automation](#browser-automation)
- [Task Scheduling](#task-scheduling)
- [Workflow Builder](#workflow-builder)
- [Access & Security Notes](#access--security-notes)

---

## Core Bot Commands

Manage the fundamental runtime state, session lifecycle, and system capabilities of the bot.

| Command | Description | Example |
| :--- | :--- | :--- |
| `/start` | Initialize the bot and check authentication status. | `/start` |
| `/help` | Show the interactive help menu. | `/help` |
| `/status` | Verify Gemini API and session status. | `/status` |
| `/login` | Choose an authentication method and generate an OAuth link for Gemini access. | `/login` |
| `/authcode <code>` | Complete OAuth login with the authorization code from your browser. | `/authcode 4/1ABCDEF...` |
| `/checkauth` | Verify current authentication status and token health. | `/checkauth` |
| `/logout` | Sign out, revoke credentials, and clear the session. | `/logout` |
| `/new` | Purge current Gemini chat history and start a fresh session. | `/new` |
| `/enhance <text>` | Ask Gemini to rewrite or improve a prompt. | `/enhance write an email to my boss` |
| `/sync` | Force-sync the command list with Telegram's bot menu. Use this after saving a new macro or if the `/help` menu looks stale. | `/sync` |
| `/stopbot` | Shut down the bot process gracefully (requires confirmation). | `/stopbot` |

---

## Native AI Chat & Agentic Automation

You do not need a slash command to talk to the AI.

- **Text**: Send any message directly to chat with Gemini 2.0 Flash.
- **Vision**: Attach a photo and ask a question — Gemini will analyze the image.
- **Agentic Automation**: Gemini is equipped with tool-calling capabilities to actively browse files, capture screenshots, and automate UI tasks (clicking, typing, opening apps, scheduling actions) on your host PC via natural language. All destructive or system-altering actions require explicit human-in-the-loop approval via inline confirmation buttons.

---

## File System Operations

Browse, read, and search files on the host machine. All operations are confined to directories in your `APPROVED_DIRECTORIES` whitelist.

| Command | Description | Example |
| :--- | :--- | :--- |
| `/pwd` | Show the current working directory path. | `/pwd` |
| `/cd <path>` | Change directory. | `/cd src/components` |
| `/ls [path]` | List files and folders. | `/ls` or `/ls src/` |
| `/cat <file>` | Display the contents of a file. | `/cat README.md` |
| `/find <pattern>` | Search for files matching a glob pattern. | `/find *.py` |
| `/info <path>` | Show metadata, size, and permissions for a file or folder. | `/info C:\data\log.txt` |

---

## System Settings & Controls

Direct Windows system management.

| Command | Description | Example |
| :--- | :--- | :--- |
| `/screenshot` | Capture and return the host's primary display. | `/screenshot` |
| `/hotkey <keys>` | Send a keyboard shortcut to the host. | `/hotkey ctrl+shift+esc` |
| `/windows` | List open application windows and present numbered switch targets. | `/windows` |
| `/focuswindow <number>` | Activate a window from the most recent `/windows` list. | `/focuswindow 3` |
| `/clipboard <text>` | Overwrite the host clipboard with the given text. | `/clipboard https://example.com` |
| `/viewclipboard` | Read and return whatever is currently in the clipboard. | `/viewclipboard` |
| `/battery` | Check battery percentage and charging status. | `/battery` |
| `/privacy <on\|off\|status>` | Blank the display or wake it without locking the Windows session. | `/privacy on` |
| `/sleep` | Put the host PC to sleep immediately. | `/sleep` |
| `/wakeup` | Show wake-up instructions and last wake time. | `/wakeup` |
| `/shutdown` | Shut down the host PC (requires confirmation). | `/shutdown` |

---

## Vision & UI Automation

Robotic Process Automation using OCR and computer vision.

| Command | Description | Example |
| :--- | :--- | :--- |
| `/clicktext <x> <y>` | Click at specific screen coordinates. | `/clicktext 500 800` |
| `/findtext <text>` | Locate visible on-screen text with OCR and return click coordinates. | `/findtext Submit` |
| `/smartclick <text>` | Find visible on-screen text with OCR and let you choose which match to click. | `/smartclick Cancel` |
| `/findelements` | Scan the screen with computer vision and number all interactive icons/UI elements. | `/findelements` |
| `/clickelement <id>` | Click a numbered element from the last `/findelements` scan. | `/clickelement 4` |
| `/typeenter <text>` | Type text character-by-character and press Enter. | `/typeenter admin123` |
| `/pasteenter` | Paste the current clipboard contents and press Enter. | `/pasteenter` |
| `/scrollup [amount]` | Scroll up in the active window. | `/scrollup 500` |
| `/scrolldown [amount]` | Scroll down in the active window. | `/scrolldown 1200` |

> **Note:** OCR commands (`/findtext`, `/smartclick`) require Tesseract OCR installed on the host.
> `/findelements` uses computer vision (included in the standard installation).
> `/windows` and `/focuswindow` switch top-level application windows, not browser tabs within a single app.

---

## Remote Desktop

Stream your desktop to a mobile browser and control mouse + keyboard from anywhere over the internet. Backed by a [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) quick-tunnel (free, no account, no port forwarding).

| Command | Description | Example |
| :--- | :--- | :--- |
| `/remote` | Start a live remote-control session. Returns a public HTTPS URL and a QR code. The first browser that opens the link is bound to the session. | `/remote` |
| `/stopremote` | Stop the active remote session for this user. | `/stopremote` |

**Prerequisites:** `cloudflared` must be available. If it is missing, `/remote` detects this and offers to install it automatically via `winget` (Windows only) — approve with the inline button. To install manually: `winget install Cloudflare.cloudflared`. Set `CLOUDFLARED_PATH` in `~/.pdagent/config` to point to a custom binary location.

**Mobile controls (toolbar at bottom of viewer):**

| Control | Action |
| :--- | :--- |
| Tap | Left click |
| Drag | Click-and-drag |
| Long-press (500 ms) | Right click |
| Two-finger vertical scroll | Scroll up/down |
| **keys** button | Open on-screen keyboard input |
| **right click** button | Next tap sends a right click instead of left |
| **mouse pad** button | Toggle trackpad panel — drag to move cursor, tap to click, two-finger to scroll |
| **zoom** button | Cycle zoom levels: 1.0× → 1.5× → 2.0× → 3.0× → 1.0× |
| **view pan** button | When zoomed: drag the canvas to scroll the viewport (instead of dragging the remote mouse) |
| Quality slider | Adjust JPEG stream quality (30–85); lower = faster on slow connections |
| **end** button | Disconnect client (session stays alive until `/stopremote` or idle timeout) |

**Desktop browser:** full mouse (move, left/right/middle click, drag, scroll wheel) and keyboard are supported natively.

**Session security:** the viewer URL contains a one-shot token. After the first valid browser opens it, the session is bound to that browser's fingerprint (User-Agent + hashed IP). WebSocket connections are verified against the same token and fingerprint.

**Auto-end conditions:** explicit `/stopremote`, 15-minute idle timeout, or bot shutdown.

See [docs/REMOTE.md](REMOTE.md) for the full setup, security, and troubleshooting guide.

---

## Custom Command Sequences

Record, save, and replay multi-step automation workflows.

**Recordable actions:** `/hotkey`, `/clipboard`, `/findtext`, `/smartclick`, `/clicktext`, `/clickelement`, `/pasteenter`, `/typeenter`, `/scrollup`, `/scrolldown`, `/openclaude`, and more.

> **Non-recordable commands** (such as `/screenshot`, `/ls`, or Gemini chat messages) sent during recording are executed immediately as normal — they are not added to the macro sequence.

| Command | Description | Example |
| :--- | :--- | :--- |
| `/savecommand <name>` | Start recording a new macro. Subsequent supported commands are recorded rather than executed. | `/savecommand deploy` |
| `/done` | Stop recording and save the macro. | `/done` |
| `/cancelrecord` | Abort recording without saving. | `/cancelrecord` |
| `/listcommands` | Show all saved macros. | `/listcommands` |
| `/deletecommand <name>` | Delete a saved macro. | `/deletecommand deploy` |

To run a saved macro, send `/<name>` — e.g., `/deploy`. Macros replay each recorded command in sequence with no delay between steps. After saving, run `/sync` to make the macro appear in Telegram's command menu.

---

## Claude & CLI Integration

Control the Anthropic Claude Desktop app and Claude Code CLI from your phone.

### App Management

| Command | Description | Example |
| :--- | :--- | :--- |
| `/openclaude` | Launch or focus the Claude Desktop application. | `/openclaude` |
| `/stopclaude` | Stop the active `claude remote-control` terminal session. | `/stopclaude` |
| `/claudescreen` | Capture a screenshot of the Claude Desktop window. | `/claudescreen` |

### Interactions

| Command | Description | Example |
| :--- | :--- | :--- |
| `/clauderemote` | Open a cmd terminal at the current bot working directory (`/pwd`) and run `claude remote-control`. | `/clauderemote` |
| `/claudeask <prompt>` | Send a detailed multiline prompt to Claude Desktop. | `/claudeask optimize auth.py` |
| `/claudechat <msg>` | Append a message to the active Claude chat. | `/claudechat continue` |
| `/claudenew` | Open a new Claude Desktop chat session. | `/claudenew` |
| `/claudelatest` | Retrieve Claude's last response from the Desktop app. | `/claudelatest` |

### CLI & Context

| Command | Description | Example |
| :--- | :--- | :--- |
| `/claudecli [path-or-name] [optional prompt]` | If the first argument resolves to a folder, open Claude CLI there and optionally send the remaining text as the first prompt. Otherwise show a folder picker and treat all args as an optional prompt. | `/claudecli myrepo run tests` |
| `/claudeclisend <text>` | Send a prompt to an already-open Claude Code CLI session. | `/claudeclisend run the tests` |
| `/clauderepo` | Select the active repository for Claude context. | `/clauderepo` |
| `/claudebranch` | Switch the git branch for the active Claude session. | `/claudebranch` |
| `/claudeselect` | Switch between predefined desktop workspaces. | `/claudeselect` |
| `/claudemode` | Cycle Claude's agentic or conversational mode. | `/claudemode` |
| `/claudemodel` | Hot-swap the Claude model (Opus, Sonnet, Haiku). | `/claudemodel` |
| `/claudesearch <query>` | Search your Claude conversation history. | `/claudesearch python` |

---

## Antigravity Controller

Bridge the bot to VS Code via the Antigravity desktop extension.

| Command | Description | Example |
| :--- | :--- | :--- |
| `/openantigravity` | Launch or focus the Antigravity window. | `/openantigravity` |
| `/antigravitychat` | Focus the Antigravity chat input. | `/antigravitychat` |
| `/antigravitymode` | Toggle Antigravity context mode (agentic/chat). | `/antigravitymode` |
| `/antigravitymodel` | Switch the Antigravity AI model backend. | `/antigravitymodel` |
| `/antigravityclaudecodeopen` | Focus the Claude Code panel in VS Code. | `/antigravityclaudecodeopen` |
| `/openclaudeinvscode` | Run `Claude Code: Open` from the VS Code command palette. | `/openclaudeinvscode` |
| `/antigravityopenfolder [path-or-name]` | Open a project folder directly when an argument is provided, or show a picker when no argument is provided. | `/antigravityopenfolder myrepo` |

---

## Browser Automation

| Command | Description | Example |
| :--- | :--- | :--- |
| `/openbrowser [browser]` | Open `edge`, `chrome`, `firefox`, or `brave` directly, or show an inline picker with no argument. | `/openbrowser chrome` |

---

## Task Scheduling

Schedule one-shot or repeating automations, Claude prompts, and temporary permission watchers. Tasks persist across restarts.

> The scheduler checks for due tasks every **5 seconds**. The bot must be running when the scheduled time arrives.

| Command | Description | Example |
| :--- | :--- | :--- |
| `/schedule <HH:MM>` | Start recording an automation sequence to run at a specific time. | `/schedule 14:00` |
| `/scheduleshutdown <HH:MM>` | Schedule a one-shot system shutdown. Confirmation is required when creating the schedule; due-time execution runs without another prompt. | `/scheduleshutdown 23:45` |
| `/repeatschedule every <interval> for <duration>` | Record an automation sequence that starts immediately after `/done` and repeats for a limited time. | `/repeatschedule every 1m for 15m` |
| `/watchperm <claude\|antigravity> every <interval> for <duration> [labels=...]` | Repeatedly scan the Claude or Antigravity window for approval buttons like `Allow` or `Run` and click them when there is exactly one strong match. | `/watchperm claude every 1m for 15m` |
| `/watchscreen <text> every <interval> press <hotkey>` | Repeatedly scan the full screen or a target app for visible text and send a hotkey whenever it appears, until you stop the watcher. Optional suffixes: `in <screen\|claude\|antigravity>` and `cooldown <duration>`. | `/watchscreen Allow command every 1m press ctrl+enter in claude cooldown 30s` |
| `/stopscreenwatch [task_id\|all]` | Stop one active screen watcher by task ID or stop all active screen watchers for your account. | `/stopscreenwatch all` |
| `/claudeschedule <HH:MM> <text>` | Schedule a prompt to be sent to Claude at a specific time. | `/claudeschedule 02:00 run tests and summarize` |
| `/listschedules` | View all pending scheduled tasks with countdown timers. | `/listschedules` |
| `/cancelschedule <id>` | Cancel a pending scheduled task by its ID. | `/cancelschedule claude_123` |

**Time formats:**
- `HH:MM` — queues for later today, or tomorrow if the time has already passed (24-hour format)
- `YYYY-MM-DD HH:MM` — explicit future date and time

**Repeat formats:**
- `every 1m for 15m`
- `every 30s for 10m`
- `every 2h for 6h`

`/watchperm` and `/watchscreen` are Windows-only and require Tesseract OCR. `/watchperm` only clicks when the target app window has a single clear OCR match among the configured labels. `/watchscreen` can watch the whole screen or just Claude/Antigravity, and an optional cooldown can suppress repeated triggers while the same dialog stays visible.

---

## Workflow Builder

CI/CD commands for React Native Android build pipelines.

| Command | Description | Example |
| :--- | :--- | :--- |
| `/build` | Start the React Native / Android build workflow. | `/build` |
| `/getapk` | Retrieve the latest built APK and deliver it through Telegram or a large-file upload option. | `/getapk` |

See [BUILD_WORKFLOW.md](BUILD_WORKFLOW.md) for the full build guide.

---

## Access & Security Notes

- **Authorization:** Only Telegram user IDs in `AUTHORIZED_USER_IDS` (set via `pdagent configure` or `.env`) can use the bot. All others are silently rejected.
- **Directory sandboxing:** File operations (`/cat`, `/ls`, `/find`, etc.) are restricted to `APPROVED_DIRECTORIES` using strict path validation. Run `pdagent configure` and select **2) Approved Directories** to add or remove individual paths without re-entering all settings.
- **Implicit sandbox expansion:** `CLAUDE_DEFAULT_REPO_PATH` (the Default Projects Directory) is **always** appended to the approved sandbox at runtime by `FileManager`, even if it is not listed in `APPROVED_DIRECTORIES`. This ensures commands like `/clauderepo`, `/claudecli`, and `/build` can always reach your projects folder.
- **Rate limiting:** All commands are rate-limited per user. Dangerous commands (e.g., `/shutdown`) have much stricter limits.
- **OS requirements:** UI automation commands (`/screenshot`, `/hotkey`, `/smartclick`, `/findelements`, etc.) require Windows.
- **OCR requirement:** `/findtext` and `/smartclick` additionally require [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed on the host.
