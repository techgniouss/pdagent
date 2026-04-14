# Security Policy

## IMPORTANT

Pocket Desk Agent provides **system-level access** to your PC via Telegram. Read this document before deploying.

---

## Supported Versions

Security fixes are applied to the latest published release only. Always run the most recent version.

| Version | Supported |
| :--- | :---: |
| Latest (`pip install pocket-desk-agent`) | ✅ |
| Older pinned versions | ❌ |

---

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not open a public GitHub issue**.

Report privately via **GitHub's Security Advisory** feature:

1. Go to the [Security tab](../../security) of this repository
2. Click **"Report a vulnerability"**
3. Describe the issue, reproduction steps, and potential impact

You can expect an initial response within **72 hours** and a resolution or mitigation plan within **14 days** for confirmed issues.

---

## Security Model

### What the bot can access

Pocket Desk Agent has access to:
- Files and directories listed in `APPROVED_DIRECTORIES`
- The keyboard, mouse, and clipboard of the host PC
- Running applications visible on the desktop (for UI automation)
- The local network (to reach Telegram and optionally Google Gemini)

### Trust boundaries

| Boundary | Control |
| :--- | :--- |
| Who can send commands | `AUTHORIZED_USER_IDS` — only these Telegram user IDs are accepted |
| Which files can be read/written | `APPROVED_DIRECTORIES` — enforced with `Path.relative_to()`, not string matching |
| Which shell commands Gemini can run | None — Gemini has no shell access. All automation goes through typed UI interactions |
| Rate of commands | Per-user token-bucket rate limiter on every command |

### What leaves your machine

- **Telegram**: all commands and replies pass through Telegram's servers (end-to-end encrypted in Transit). Bot tokens and message content are visible to Telegram.
- **Google Gemini API** (optional): message text and attached images are sent to Google's API when you use AI chat or `/enhance`. No other data is sent.
- **TempFile.org / Dropbox** (optional): APK files are uploaded only when you explicitly choose these delivery options after a build.

Nothing else leaves the machine.

---

## Credential Security

| Credential | Storage location | Permissions |
| :--- | :--- | :--- |
| Bot config (`TELEGRAM_BOT_TOKEN`, etc.) | `~/.pdagent/config` | User-readable only |
| OAuth tokens (Antigravity / Gemini CLI) | `~/.config/antigravity-chatbot/tokens.json` or `~/.config/pdagent-gemini/tokens.json` | `chmod 600` (Unix) / `icacls` restricted (Windows) |
| Dropbox access token | `~/.pdagent/config` or `.env` | User-readable only |

**Never commit** `.env` files, `~/.pdagent/config`, or any OAuth token file to version control.

---

## Deployment Hardening Checklist

- [ ] `AUTHORIZED_USER_IDS` contains only your own Telegram user ID(s)
- [ ] `APPROVED_DIRECTORIES` is scoped to the minimum directories the bot needs
- [ ] Bot token is not committed to version control or shared publicly
- [ ] OAuth token files are not world-readable (`chmod 600` on Unix)
- [ ] Bot is running as a regular user account, not as Administrator or root
- [ ] If exposing the bot on a shared network, firewall port 51121 (OAuth callback) from external access — it only needs to be reachable by `localhost`
- [ ] Auto-update is enabled (`AUTO_UPDATE_ENABLED=true`) so security patches apply automatically

---

## Known Limitations

- **Telegram as the transport layer**: the security of commands depends on Telegram's platform security. Use a bot token that is not shared with anyone else.
- **No multi-factor auth for commands**: anyone who gains control of an authorized Telegram account can send commands. Keep your Telegram account secured with a strong password and 2FA.
- **UI automation scope**: OCR and element-clicking commands act on whatever is visible on the screen at the time — they are not restricted to specific applications.
