# Antigravity OAuth Implementation Reference

## Overview

This document describes the Antigravity-specific portion of the Google OAuth 2.0 PKCE system used for Gemini AI access. The provider implementation lives in `pocket_desk_agent/antigravity_auth.py`, while provider selection and Telegram command handling live in `pocket_desk_agent/auth.py` and `pocket_desk_agent/handlers/auth.py`.

## Architecture

The Antigravity provider has three main components:

1. **`TokenStorage`**  
   Manages persistent token storage in `~/.config/antigravity-chatbot/tokens.json` and applies restrictive file permissions on creation.

2. **`PKCEGenerator`**  
   Generates a cryptographically random `code_verifier` and its SHA-256-derived `code_challenge` for PKCE.

3. **`AntigravityOAuth`**  
   Orchestrates the provider-specific OAuth flow:
   - Generates the authorization URL
   - Exchanges the authorization code for access and refresh tokens
   - Automatically refreshes expired access tokens
   - Fetches the signed-in email and active project ID

## OAuth Configuration

- **Redirect URI**: `http://localhost:51121/oauth-callback`
- **Flow**: Authorization Code with PKCE and a local callback server on `localhost:51121`
- **Telegram compatibility**: The `/login` plus `/authcode` flow accepts a copied callback URL or raw code manually
- **Project resolution**: After OAuth succeeds, Antigravity tries to fetch the active project ID from the internal API. If that fails, users can set `GOOGLE_PROJECT_ID`.

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

The application ships with built-in Antigravity plugin OAuth credentials as defaults in `constants.py` (`DEFAULT_OAUTH_CLIENT_ID` and `DEFAULT_OAUTH_CLIENT_SECRET`). These are public installed-app credentials with the registered redirect URI `http://localhost:51121/oauth-callback`. PKCE is the real security boundary.

Users can override the built-in credentials by setting `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` via environment variable or `~/.pdagent/credentials`. If overriding, register `http://localhost:51121/oauth-callback` as an authorized redirect URI in your OAuth client.

## Dependencies

```text
requests>=2.31.0
```

All other dependencies are from the Python standard library.

## User Flow

See [MOBILE_AUTHENTICATION.md](MOBILE_AUTHENTICATION.md) for the end-user authentication flow and Telegram commands.
