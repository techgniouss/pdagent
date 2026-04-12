# Pocket Desk Agent: Full Command Reference

Welcome to the definitive guide for interacting with your Pocket Desk Agent.
This document covers all commands organized by capability.

## Table of Contents

- [Core Bot Commands](#core-bot-commands)
- [Native AI Chat](#native-ai-chat-no-command-needed)
- [File System Operations](#file-system-operations)
- [System Settings & Controls](#system-settings--controls)
- [Vision & UI Automation](#vision--ui-automation)
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
| `/login` | Generate a Google OAuth link for Gemini authentication. | `/login` |
| `/authcode <code>` | Complete OAuth login with the authorization code from your browser. | `/authcode 4/1ABCDEF...` |
| `/checkauth` | Verify current authentication status and token health. | `/checkauth` |
| `/logout` | Sign out, revoke credentials, and clear the session. | `/logout` |
| `/new` | Purge current Gemini chat history and start a fresh session. | `/new` |
| `/enhance <text>` | Ask Gemini to rewrite or improve a prompt. | `/enhance write an email to my boss` |
| `/sync` | Force-sync the command list with Telegram's menu. | `/sync` |
| `/stopbot` | Shut down the bot service gracefully. | `/stopbot` |

---

## Native AI Chat (No Command Needed)

You do not need a slash command to talk to the AI.

- **Text**: Send any message directly to chat with Gemini 2.0 Flash.
- **Vision**: Attach a photo and ask a question — Gemini will analyze the image.

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
| `/clipboard <text>` | Overwrite the host clipboard with the given text. | `/clipboard https://example.com` |
| `/viewclipboard` | Read and return whatever is currently in the clipboard. | `/viewclipboard` |
| `/battery` | Check battery percentage and charging status. | `/battery` |
| `/sleep` | Put the host PC to sleep immediately. | `/sleep` |
| `/wakeup` | Show wake-up instructions and last wake time. | `/wakeup` |
| `/shutdown` | Shut down the host PC (requires confirmation). | `/shutdown` |

---

## Vision & UI Automation

Robotic Process Automation using OCR and computer vision.

| Command | Description | Example |
| :--- | :--- | :--- |
| `/clicktext <x> <y>` | Click at specific screen coordinates. | `/clicktext 500 800` |
| `/findtext <text>` | Locate text on screen using OCR and show its coordinates. | `/findtext Submit` |
| `/smartclick <text>` | Find all matches of text on screen and let you pick which to click. | `/smartclick Cancel` |
| `/findelements` | Scan the screen with computer vision and number all interactive icons/UI elements. | `/findelements` |
| `/clickelement <id>` | Click a numbered element from the last `/findelements` scan. | `/clickelement 4` |
| `/typeenter <text>` | Type text character-by-character and press Enter. | `/typeenter admin123` |
| `/pasteenter` | Paste the current clipboard contents and press Enter. | `/pasteenter` |
| `/scrollup [amount]` | Scroll up in the active window. | `/scrollup 500` |
| `/scrolldown [amount]` | Scroll down in the active window. | `/scrolldown 1200` |

> **Note:** OCR commands (`/findtext`, `/smartclick`) require Tesseract OCR installed on the host.
> `/findelements` uses computer vision (included in the standard installation).

---

## Custom Command Sequences

Record, save, and replay multi-step automation workflows.

**Recordable actions:** `/hotkey`, `/clipboard`, `/findtext`, `/smartclick`, `/clickelement`, `/pasteenter`, `/typeenter`, `/scrollup`, `/scrolldown`, `/openclaude`, and more.

| Command | Description | Example |
| :--- | :--- | :--- |
| `/savecommand <name>` | Start recording a new macro. Subsequent supported commands are recorded rather than executed. | `/savecommand deploy` |
| `/done` | Stop recording and save the macro. | `/done` |
| `/cancelrecord` | Abort recording without saving. | `/cancelrecord` |
| `/listcommands` | Show all saved macros. | `/listcommands` |
| `/deletecommand <name>` | Delete a saved macro. | `/deletecommand deploy` |

To run a saved macro, send `/<name>` — e.g., `/deploy`.

---

## Claude & CLI Integration

Control the Anthropic Claude Desktop app and Claude Code CLI from your phone.

### App Management

| Command | Description | Example |
| :--- | :--- | :--- |
| `/openclaude` | Launch or focus the Claude Desktop application. | `/openclaude` |
| `/stopclaude` | Terminate the Claude Desktop process. | `/stopclaude` |
| `/claudescreen` | Capture a screenshot of the Claude Desktop window. | `/claudescreen` |

### Interactions

| Command | Description | Example |
| :--- | :--- | :--- |
| `/clauderemote` | Open a cmd terminal at `CLAUDE_DEFAULT_REPO_PATH` and run `claude remote-control`. | `/clauderemote` |
| `/claudeask <prompt>` | Send a detailed multiline prompt to Claude Desktop. | `/claudeask optimize auth.py` |
| `/claudechat <msg>` | Append a message to the active Claude chat. | `/claudechat continue` |
| `/claudenew` | Open a new Claude Desktop chat session. | `/claudenew` |
| `/claudelatest` | Retrieve Claude's last response from the Desktop app. | `/claudelatest` |

### CLI & Context

| Command | Description | Example |
| :--- | :--- | :--- |
| `/claudecli [prompt]` | Open a Claude Code CLI session in a folder, with an optional initial prompt. | `/claudecli fix the login bug` |
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
| `/antigravityclaudecodeopen` | Open a Claude Code CLI terminal inside VS Code. | `/antigravityclaudecodeopen` |
| `/antigravityopenfolder` | Open a project folder in VS Code. | `/antigravityopenfolder` |

---

## Browser Automation

| Command | Description | Example |
| :--- | :--- | :--- |
| `/openbrowser` | Show an inline keyboard to select and open a browser full-screen. Supports Edge, Chrome, Firefox, and Brave. | `/openbrowser` |

---

## Task Scheduling

Schedule automation sequences or Claude prompts to run at a future time. Tasks persist across restarts.

| Command | Description | Example |
| :--- | :--- | :--- |
| `/schedule <HH:MM>` | Schedule a recorded macro to run at a specific time. | `/schedule 14:00` |
| `/claudeschedule <HH:MM> <text>` | Schedule a prompt to be sent to Claude at a specific time. | `/claudeschedule 02:00 run tests and summarize` |
| `/listschedules` | View all pending scheduled tasks with countdown timers. | `/listschedules` |
| `/cancelschedule <id>` | Cancel a pending scheduled task by its ID. | `/cancelschedule claude_123` |

**Time formats:**
- `HH:MM` — queues for later today, or tomorrow if the time has already passed
- `YYYY-MM-DD HH:MM` — explicit future date and time

---

## Workflow Builder

CI/CD commands for React Native Android build pipelines.

| Command | Description | Example |
| :--- | :--- | :--- |
| `/build` | Start the React Native / Android build workflow. | `/build` |
| `/getapk` | Retrieve the latest built APK and deliver it via Telegram. | `/getapk` |

See [docs/BUILD_WORKFLOW.md](BUILD_WORKFLOW.md) for the full build guide.

---

## Access & Security Notes

- **Authorization:** Only Telegram user IDs in `AUTHORIZED_USER_IDS` (set via `pdagent configure` or `.env`) can use the bot. All others are silently rejected.
- **Directory sandboxing:** File operations (`/cat`, `/ls`, `/find`, etc.) are restricted to `APPROVED_DIRECTORIES` using strict path validation.
- **Rate limiting:** All commands are rate-limited per user. Dangerous commands (e.g., `/shutdown`) have much stricter limits.
- **OS requirements:** UI automation commands (`/screenshot`, `/hotkey`, `/smartclick`, `/findelements`, etc.) require Windows.
- **OCR requirement:** `/findtext` and `/smartclick` additionally require [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed on the host.
