"""Shared constants for Pocket Desk Agent.

Single source of truth for API endpoints, headers, scopes, and other
values that were previously duplicated across antigravity_auth.py and
gemini_client.py.
"""

# ── Default OAuth Credentials ───────────────────────────────────────────────
# Gemini CLI public OAuth client (installed app — not treated as secret).
# Source: https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/code_assist/oauth2.ts
# Google's own comment: "It's ok to save this in git because this is an
# installed application" — the client secret is not treated as a secret
# for desktop/CLI apps (RFC 8252).  PKCE is the real security boundary.
#
# Users can override these by setting GOOGLE_OAUTH_CLIENT_ID and
# GOOGLE_OAUTH_CLIENT_SECRET environment variables (or in ~/.pdagent/credentials).
DEFAULT_OAUTH_CLIENT_ID = (
    "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
)
DEFAULT_OAUTH_CLIENT_SECRET = "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"

# ── OAuth Configuration ──────────────────────────────────────────────────────
OAUTH_REDIRECT_URI = "http://localhost:51121/oauth-callback"

ANTIGRAVITY_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
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

ANTIGRAVITY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Antigravity/1.15.8 Chrome/138.0.7204.235 "
        "Electron/37.3.1 Safari/537.36"
    ),
    "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
    "Client-Metadata": (
        '{"ideType":"IDE_UNSPECIFIED","platform":"PLATFORM_UNSPECIFIED",'
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
