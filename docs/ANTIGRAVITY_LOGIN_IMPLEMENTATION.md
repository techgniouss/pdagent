# Antigravity OAuth Implementation Reference

## Overview

This document describes the architecture of the Google OAuth 2.0 PKCE authentication system used for Gemini AI access. The full implementation lives in `pocket_desk_agent/antigravity_auth.py`.

## Architecture

The authentication system has three components:

1. **`TokenStorage`** — Manages persistent token storage in `~/.pdagent/tokens.json`. Sets restrictive file permissions on creation (chmod 600 on Unix, icacls on Windows).

2. **`PKCEGenerator`** — Generates PKCE (Proof Key for Code Exchange) parameters: a cryptographically random `code_verifier` and its SHA-256-derived `code_challenge`. Prevents authorization code interception attacks.

3. **`AntigravityAuth`** — Orchestrates the complete OAuth 2.0 PKCE flow:
   - Generates the authorization URL
   - Exchanges the authorization code for access/refresh tokens
   - Automatically refreshes expired access tokens using the stored refresh token
   - Exposes `get_valid_token()` for all API callers

## OAuth Configuration

- **Redirect URI**: `http://localhost:51121/oauth-callback`
- **Flow**: Authorization Code with PKCE (out-of-band — user manually copies the code)

### Required Scopes

```python
ANTIGRAVITY_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
]
```

### API Endpoints

```python
ANTIGRAVITY_ENDPOINT_DAILY = "https://daily-cloudcode-pa.sandbox.googleapis.com"
ANTIGRAVITY_ENDPOINT_PROD  = "https://cloudcode-pa.googleapis.com"
```

## Credentials

OAuth client credentials (`GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`) are configured via environment variable or `~/.pdagent/config.ini`. They are **never** hardcoded in the application. See [README.md](../README.md#configuration) for configuration details.

## Dependencies

```
requests>=2.31.0
```

All other dependencies are from the Python standard library (`hashlib`, `base64`, `secrets`, `json`, `pathlib`).

## User Flow

See [MOBILE_AUTHENTICATION.md](MOBILE_AUTHENTICATION.md) for the end-user authentication flow and Telegram commands.
