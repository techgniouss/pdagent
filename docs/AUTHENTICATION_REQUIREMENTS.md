# Authentication Requirements

## Overview

The vast majority of commands work immediately after installation with **no authentication required**. Only Gemini AI features (chat and image analysis) need a Google account linked via OAuth.

---

## Commands That REQUIRE Authentication

### Gemini AI

- **Free-text messages** — sending any text to the bot to chat with Gemini
- **Photo messages** — sending images for Gemini Vision analysis
- `/enhance <text>` — rewrite a prompt using Gemini

If you use any of these without authenticating first, the bot will reply with a prompt to run `/login`. No action is taken and no error is logged — it is a clean, user-facing redirect.

**To authenticate:** Use `/login` in Telegram and follow the instructions. See [MOBILE_AUTHENTICATION.md](MOBILE_AUTHENTICATION.md).

---

## Commands That Work WITHOUT Authentication

### Core

- `/start`, `/help`, `/sync`, `/stopbot`, `/new`
- `/status` — works without auth but shows richer output (email, provider, token health) when authenticated

### Authentication Management

- `/login`, `/authcode`, `/checkauth`, `/logout`

### File System

- `/pwd`, `/cd`, `/ls`, `/cat`, `/find`, `/info`

### System Control

- `/screenshot`, `/hotkey`, `/clipboard`, `/viewclipboard`
- `/windows`, `/focuswindow`
- `/battery`, `/sleep`, `/wakeup`, `/shutdown`

### UI Automation

- `/clicktext`, `/findtext`, `/smartclick`
- `/findelements`, `/clickelement`
- `/typeenter`, `/pasteenter`
- `/scrollup`, `/scrolldown`

### Custom Commands

- `/savecommand`, `/done`, `/cancelrecord`, `/listcommands`, `/deletecommand`
- Any saved custom macro (e.g., `/deploy`)

### Claude Desktop & CLI

- `/openclaude`, `/stopclaude`, `/claudescreen`
- `/clauderemote`, `/claudeask`, `/claudechat`, `/claudenew`, `/claudelatest`
- `/claudecli`, `/claudeclisend`
- `/clauderepo`, `/claudebranch`, `/claudeselect`, `/claudemode`, `/claudemodel`, `/claudesearch`

### Antigravity / VS Code

- `/openantigravity`, `/antigravitychat`, `/antigravitymode`, `/antigravitymodel`
- `/antigravityclaudecodeopen`, `/antigravityopenfolder`
- `/openbrowser`

### Scheduling

- `/schedule`, `/scheduleshutdown`, `/claudeschedule`, `/listschedules`, `/cancelschedule`

### Build & APK

- `/build`, `/getapk`

---

## Why Does Only Gemini Need Auth?

**Gemini AI** calls Google's cloud API, which requires one of:
- OAuth login via `/login` using **Antigravity OAuth** or **Gemini CLI OAuth**
- Or an API key when the bot is configured in API-key mode

Provider notes:
- **Gemini CLI OAuth** uses the public Gemini API and does not need a project ID.
- **Antigravity OAuth** uses Google's internal code-assist API and may fetch a project automatically. If auto-detection fails, set `GOOGLE_PROJECT_ID`.

**All other commands** run locally on the host machine:
- Windows system APIs (`pyautogui`, `psutil`, `pyperclip`)
- Local file system operations
- Claude Desktop automation (controlling a local app via UI)
- Telegram inline keyboards and bot logic

---

## Quick Start

### Without Authentication (immediately available)

```
/start
/screenshot
/battery
/hotkey win+d
/ls
```

### Enabling Gemini AI

```
/login
[Open the link, sign in, copy the code]
/authcode <your-code>

[Now you can chat with Gemini:]
Hello, summarize my project status.
```

---

## Rate Limiting

Rate limiting applies to **all** commands regardless of authentication status. Each user has a per-command token bucket. Commands that are sensitive or resource-intensive (e.g., `/shutdown`, `/build`) have stricter per-user limits than routine commands (e.g., `/ls`, `/screenshot`). If you hit a rate limit, the bot will tell you how long to wait before retrying.

---

**Summary:** Most commands work without authentication. Only Gemini AI features require `/login` or API-key mode.
