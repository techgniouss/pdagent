# Authentication Requirements

## Overview

The vast majority of commands work immediately after installation with **no authentication required**. Only Gemini AI features (chat and image analysis) need a Google account linked via OAuth.

---

## Commands That REQUIRE Authentication

### Gemini AI

- **Free-text messages** — sending any text to the bot to chat with Gemini
- **Photo messages** — sending images for Gemini Vision analysis
- `/new` — start a new Gemini conversation
- `/enhance <text>` — rewrite a prompt using Gemini

**To authenticate:** Use `/login` in Telegram and follow the instructions. See [MOBILE_AUTHENTICATION.md](MOBILE_AUTHENTICATION.md).

---

## Commands That Work WITHOUT Authentication

### Core

- `/start`, `/help`, `/status`, `/sync`, `/stopbot`

### Authentication Management

- `/login`, `/authcode`, `/checkauth`, `/logout`

### File System

- `/pwd`, `/cd`, `/ls`, `/cat`, `/find`, `/info`

### System Control

- `/screenshot`, `/hotkey`, `/clipboard`, `/viewclipboard`
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

- `/schedule`, `/claudeschedule`, `/listschedules`, `/cancelschedule`

### Build & APK

- `/build`, `/getapk`

---

## Why Does Only Gemini Need Auth?

**Gemini AI** calls Google's cloud API, which requires:
- A Google account with OAuth consent
- An access token scoped to the Gemini/Cloud Platform APIs
- A project ID returned during authentication

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

**Summary:** 90%+ of commands work without authentication. Only Gemini chat requires `/login`.
