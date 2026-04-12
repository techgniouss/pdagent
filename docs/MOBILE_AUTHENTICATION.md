# Mobile Authentication Guide

## Overview

You can authenticate Gemini AI access directly from your Telegram chat using an OAuth 2.0 PKCE flow with manual code entry. No server-side access or separate terminal session is required.

> **Note:** Authentication is only required for Gemini AI features (chat, image analysis, `/enhance`). All automation, file system, and Claude Desktop commands work without it. See [AUTHENTICATION_REQUIREMENTS.md](AUTHENTICATION_REQUIREMENTS.md) for the full breakdown.

---

## How It Works

1. Send `/login` in Telegram — the bot generates a unique OAuth URL.
2. Open the URL on any device (phone, desktop, etc.) and sign in with Google.
3. Google displays an authorization code on the screen.
4. Copy the code and send it back via `/authcode <code>`.
5. The bot exchanges the code for tokens and saves them securely.

The redirect URI (`http://localhost:51121`) only resolves on the host machine, so Google cannot redirect automatically when authenticating from a mobile device. Instead, you copy and paste the code — this is a standard OAuth "out-of-band" (OOB) flow.

---

## Commands

### `/login`

Generates an authentication link.

```
/login
```

- If already authenticated: shows current auth status.
- If not authenticated: returns a clickable OAuth URL with step-by-step instructions.

### `/authcode <code>`

Submits the authorization code to complete authentication.

```
/authcode 4/0AanRRrtT_abc123...
```

- Copy the **entire** code from the browser — it is typically a long string.
- Do not add spaces or line breaks.
- Each code is single-use and expires after 10 minutes.

### `/checkauth`

Verifies authentication status and token health.

```
/checkauth
```

Returns your authenticated email and project ID if valid, or prompts you to re-authenticate if tokens are missing or expired.

### `/logout`

Signs out and clears stored tokens.

```
/logout
```

Shows a confirmation dialog. On confirmation, all stored tokens are deleted.

### `/status`

Shows a summary of authentication and session state.

```
/status
```

---

## Token Storage

Tokens are stored per-user on the host machine at:

```
~/.pdagent/tokens.json
```

Permissions are set to `chmod 600` (Unix) or equivalent `icacls` restrictions (Windows) on creation. Tokens are automatically refreshed when they expire — you only need to re-run `/login` if you explicitly log out or if the refresh token is revoked.

---

## OAuth Configuration

- **Redirect URI**: `http://localhost:51121/oauth-callback`
- **Scopes**:
  - `https://www.googleapis.com/auth/cloud-platform`
  - `https://www.googleapis.com/auth/userinfo.email`
  - `https://www.googleapis.com/auth/userinfo.profile`
  - `https://www.googleapis.com/auth/cclog`
  - `https://www.googleapis.com/auth/experimentsandconfigs`

---

## Example Flow

```
User:  /login
Bot:   Authentication link:
       https://accounts.google.com/o/oauth2/v2/auth?...

       Instructions:
       1. Open the link on any device
       2. Sign in with your Google account
       3. Grant the requested permissions
       4. Copy the authorization code shown on screen
       5. Send it back: /authcode <code>

User:  /authcode 4/0AanRRrtT_abc123xyz...
Bot:   Processing authorization code...

       Authentication successful!
       Email: user@example.com
       Project: my-project-id

       You can now use all Gemini AI features.
       Try sending a message to chat with Gemini.
```

---

## Troubleshooting

**"No pending authentication found"**
- Use `/login` first to start a new session, then submit the code.
- The authentication session may have timed out — start over with `/login`.

**"Authentication failed" / "Invalid or expired authorization code"**
- Make sure you copied the full code with no extra spaces.
- Codes expire after 10 minutes — use `/login` to get a fresh one.
- Each code can only be used once.

**"Failed to generate authentication link"**
- Check that the bot has network connectivity.
- Review `bot.log` for detailed error messages.
- Try restarting the bot with `pdagent restart`.
