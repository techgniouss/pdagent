# Mobile Authentication Guide

## Overview

You can authenticate Gemini AI access directly from your Telegram chat using an OAuth 2.0 PKCE flow with manual code entry. The bot supports both **Antigravity OAuth** and **Gemini CLI OAuth**. No server-side access or separate terminal session is required.

> **Note:** Authentication is only required for Gemini AI features such as chat, image analysis, and `/enhance`. All automation, file system, and Claude Desktop commands work without it. See [AUTHENTICATION_REQUIREMENTS.md](AUTHENTICATION_REQUIREMENTS.md) for the full breakdown.

---

## How It Works

1. Send `/login` in Telegram.
2. Choose **Antigravity OAuth** or **Gemini CLI OAuth** from the inline buttons.
3. Open the generated URL on any device and sign in with Google.
4. After sign-in, your browser will try to open the localhost callback URL.
5. Copy the full callback URL or just the `code` value from it, then send it back via `/authcode <code_or_callback_url>`.
6. The bot exchanges the code for tokens and saves them securely.

The redirect URI (`http://localhost:51121/oauth-callback`) only resolves on the host machine, so mobile browsers cannot complete the redirect automatically. Instead, copy the full callback URL or just the embedded authorization code and send it to the bot with `/authcode`.

---

## Commands

### `/login`

Starts the authentication flow and lets you choose a provider.

```text
/login
```

- If already authenticated: shows current auth status.
- If not authenticated: shows inline buttons for **Antigravity OAuth** and **Gemini CLI OAuth**.

### `/authcode <code_or_callback_url>`

Submits the authorization code or callback URL to complete authentication.

```text
/authcode 4/0AanRRrtT_abc123...
/authcode http://localhost:51121/oauth-callback?code=4/0AanRRrtT_abc123...
```

- Copy either the **entire** code from the browser or the full callback URL.
- The full callback URL is preferred because it also includes the OAuth `state`, which helps the bot recover the correct provider reliably.
- Do not add spaces or line breaks.
- Each code is single-use and expires after about 10 minutes.

### `/checkauth`

Verifies authentication status and token health.

```text
/checkauth
```

Returns the active authentication mode and email if valid. In Antigravity mode it also shows the project ID when available.

### `/logout`

Signs out and clears stored tokens.

```text
/logout
```

Shows a confirmation dialog. On confirmation, stored tokens are deleted.

### `/status`

Shows a summary of authentication and session state.

```text
/status
```

---

## Token Storage

Tokens are stored on the host machine in a provider-specific location:

```text
~/.config/antigravity-chatbot/tokens.json
~/.config/pdagent-gemini/tokens.json
```

Antigravity tokens live in the first path. Gemini CLI tokens live in the second. Permissions are set to `chmod 600` on Unix or equivalent `icacls` restrictions on Windows. Tokens are automatically refreshed when they expire, so you only need to re-run `/login` if you explicitly log out or if the refresh token is revoked.

---

## Provider Notes

- **Shared redirect URI**: `http://localhost:51121/oauth-callback`
- **Gemini CLI OAuth**: Uses the public Gemini API and does not require a project ID.
- **Antigravity OAuth**: Uses Google's internal code-assist API and may auto-fetch a project ID. If it cannot, set `GOOGLE_PROJECT_ID`.

---

## Example Flow

```text
User:  /login
Bot:   Choose your authentication method:
       [Antigravity OAuth] [Gemini CLI OAuth]

User:  [taps Gemini CLI OAuth]
Bot:   Authentication link:
       https://accounts.google.com/o/oauth2/v2/auth?...

       Instructions:
       1. Open the link on any device
       2. Sign in with your Google account
       3. Grant the requested permissions
       4. Copy the full callback URL or the authorization code from it
       5. Send it back: /authcode <code_or_callback_url>

User:  /authcode 4/0AanRRrtT_abc123xyz...
Bot:   Processing authorization code...

       Authentication successful!
       Mode: Gemini CLI OAuth
       Email: user@example.com

       You can now use all Gemini AI features.
       Try sending a message to chat with Gemini.
```

---

## Troubleshooting

**"No pending authentication found"**
- Use `/login` first to start a new session, then submit the code.
- If you are pasting a full callback URL, include the full `state` value as well as the `code`.
- The authentication session may have timed out. Start over with `/login`.

**"Authentication failed" / "Invalid or expired authorization code"**
- Make sure you copied the full code with no extra spaces.
- Codes expire after about 10 minutes. Use `/login` to get a fresh one.
- Each code can only be used once.

**"Project ID not configured"**
- This applies to **Antigravity OAuth** only.
- Retry the login once in case automatic project lookup was temporary.
- If it persists, set `GOOGLE_PROJECT_ID` in your config or use **Gemini CLI OAuth** instead.

**"Failed to generate authentication link"**
- Check that the bot has network connectivity.
- Review `bot.log` for detailed error messages.
- Try restarting the bot with `pdagent restart`.
