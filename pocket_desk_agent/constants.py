"""Shared constants for Pocket Desk Agent.

Single source of truth for API endpoints, headers, scopes, and other
values that were previously duplicated across antigravity_auth.py and
gemini_client.py.
"""

# ── Auth Mode Constants ─────────────────────────────────────────────────────
AUTH_MODE_ANTIGRAVITY = "antigravity"
AUTH_MODE_GEMINI_CLI = "gemini-cli"
AUTH_MODE_APIKEY = "apikey"

# ── Default OAuth Credentials (Antigravity) ─────────────────────────────────
# These are **public installed-app (native) OAuth credentials** — not secrets.
#
# RFC 8252 §8.4 explicitly states that client secrets for native/desktop apps
# "are not treated as secret" because they cannot be kept confidential when
# shipped in distributed software.  PKCE (RFC 7636) is the actual security
# boundary that prevents authorization-code interception.
#
# ┌─ What this means ─────────────────────────────────────────────────────────┐
# │  • Committing these values to a public repo is SAFE and CORRECT.          │
# │  • Including them in a PyPI wheel is SAFE and CORRECT.                    │
# │  • There is NO need to inject them from CI secrets at build time.         │
# └───────────────────────────────────────────────────────────────────────────┘
#
# To use a *different* OAuth app (e.g., your own registered client), set the
# following env vars in ~/.pdagent/config or as shell environment variables:
#
#   GOOGLE_OAUTH_CLIENT_ID      – overrides DEFAULT_OAUTH_CLIENT_ID
#   GOOGLE_OAUTH_CLIENT_SECRET  – overrides DEFAULT_OAUTH_CLIENT_SECRET
#
# The runtime lookup in antigravity_auth.py always checks env vars first.
DEFAULT_OAUTH_CLIENT_ID = (
    "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
)
DEFAULT_OAUTH_CLIENT_SECRET = "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"

# ── Gemini CLI OAuth Credentials ────────────────────────────────────────────
# Public OAuth client from the official Gemini CLI (google-gemini/gemini-cli).
# Source: packages/core/src/code_assist/oauth2.ts (open-source, Apache-2.0).
#
# Google themselves commit these values to their public GitHub repository —
# they are public installed-app credentials (RFC 8252) and are NOT secrets.
# PKCE is the security boundary; the client secret has no confidentiality
# requirement for installed applications per RFC 8252 §8.4.
#
# To use a different Gemini CLI OAuth app, override at runtime via:
#
#   GEMINI_CLI_OAUTH_CLIENT_ID      – overrides GEMINI_CLI_OAUTH_CLIENT_ID
#   GEMINI_CLI_OAUTH_CLIENT_SECRET  – overrides GEMINI_CLI_OAUTH_CLIENT_SECRET
GEMINI_CLI_OAUTH_CLIENT_ID = (
    "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
)
GEMINI_CLI_OAUTH_CLIENT_SECRET = "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"

# ── OAuth Configuration ──────────────────────────────────────────────────────
OAUTH_REDIRECT_URI = "http://localhost:51121/oauth-callback"

ANTIGRAVITY_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
]

GEMINI_CLI_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# ── API Endpoints ────────────────────────────────────────────────────────────
ANTIGRAVITY_ENDPOINT_DAILY = "https://daily-cloudcode-pa.sandbox.googleapis.com"
ANTIGRAVITY_ENDPOINT_AUTOPUSH = "https://autopush-cloudcode-pa.sandbox.googleapis.com"
ANTIGRAVITY_ENDPOINT_PROD = "https://cloudcode-pa.googleapis.com"

# ── User-Agent Headers ───────────────────────────────────────────────────────
GEMINI_CLI_HEADERS = {
    "User-Agent": "google-api-nodejs-client/10.3.0",
    "X-Goog-Api-Client": "gl-node/22.18.0",
}

# Since Google's 2026-06-18 shutdown of Code Assist for individuals, the
# tier-eligibility check keys off the *client identity* in the User-Agent /
# Client-Metadata. ideType MUST be "ANTIGRAVITY" (not "IDE_UNSPECIFIED") and
# the User-Agent must be the Antigravity Electron string below — anything
# else (e.g. the plain gemini-cli UA) gets free-tier refused with
# reasonCode UNSUPPORTED_CLIENT and no project can be resolved.
# Verified live 2026-08-04 against all three Code Assist endpoints.
ANTIGRAVITY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Antigravity/1.19.4 Chrome/138.0.7204.235 "
        "Electron/37.3.1 Safari/537.36"
    ),
    "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
    "Client-Metadata": (
        '{"ideType":"ANTIGRAVITY","platform":"PLATFORM_UNSPECIFIED",'
        '"pluginType":"GEMINI"}'
    ),
}

# ── Thinking Tier Budgets (for Gemini model resolution) ─────────────────────
THINKING_TIER_BUDGETS = {
    "claude": {"low": 8192, "medium": 16384, "high": 32768},
    "gemini-2.5-pro": {"low": 8192, "medium": 16384, "high": 32768},
    "gemini-2.5-flash": {"low": 6144, "medium": 12288, "high": 24576},
    "default": {"low": 4096, "medium": 8192, "high": 16384},
}

# ── Standard Gemini API (API key mode fallback) ─────────────────────────────
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com"

# ── History Limits ───────────────────────────────────────────────────────────
MAX_HISTORY_TURNS = 40  # Maximum conversation turns to keep in memory
