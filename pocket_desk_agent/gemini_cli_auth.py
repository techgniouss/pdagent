"""Gemini CLI-style OAuth authentication implementation.

Performs the same browser-based OAuth flow as the official Gemini CLI
using its installed-app client credentials. Requests are sent through
Google's internal Code Assist backend rather than the public
``generativelanguage.googleapis.com`` OAuth surface.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional, Callable, Tuple, Any
from urllib.parse import urlencode

import requests

from pocket_desk_agent.constants import (
    OAUTH_REDIRECT_URI,
    GEMINI_CLI_SCOPES,
    GEMINI_CLI_OAUTH_CLIENT_ID,
    GEMINI_CLI_OAUTH_CLIENT_SECRET,
    ANTIGRAVITY_ENDPOINT_PROD,
    AUTH_MODE_GEMINI_CLI,
)

# Reuse the PKCE and callback machinery from the Antigravity module.
from pocket_desk_agent.antigravity_auth import (
    TokenStorage,
    PKCEGenerator,
    OAuthCallbackHandler,
)

logger = logging.getLogger(__name__)

_CLIENT_ID = (
    os.getenv("GEMINI_CLI_OAUTH_CLIENT_ID") or GEMINI_CLI_OAUTH_CLIENT_ID
)
_CLIENT_SECRET = (
    os.getenv("GEMINI_CLI_OAUTH_CLIENT_SECRET") or GEMINI_CLI_OAUTH_CLIENT_SECRET
)

# Gemini CLI stores its own creds at ~/.gemini/oauth_creds.json.
_GEMINI_CLI_CREDS_PATH = Path.home() / ".gemini" / "oauth_creds.json"
_CLI_PROJECT_ENV_VARS = (
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_PROJECT_ID",
)


class GeminiCLIOAuth:
    """OAuth flow compatible with Gemini CLI's Google login."""

    def __init__(self, on_status_update: Optional[Callable[[str], None]] = None):
        self.storage = TokenStorage(app_name="pdagent-gemini")
        self.on_status_update = on_status_update or logger.info
        self.server = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.email: Optional[str] = None
        self.project_id: Optional[str] = None
        self.expires_at: float = 0
        self._code_assist_ready = False

    def _update_status(self, message: str) -> None:
        self.on_status_update(message)

    @staticmethod
    def _request_headers() -> dict[str, str]:
        """Headers that match Gemini CLI's Code Assist transport."""
        return {
            "User-Agent": "GeminiCLI/1.0.0 google-api-nodejs-client/10.3.0",
            "X-Goog-Api-Client": "gl-node/22.18.0",
        }

    def _configured_project_id(self) -> Optional[str]:
        """Return an explicitly configured Gemini CLI project, if set."""
        for env_var in _CLI_PROJECT_ENV_VARS:
            value = os.getenv(env_var, "").strip()
            if value:
                return value
        return None

    @staticmethod
    def _extract_project_id(value: Any) -> Optional[str]:
        """Normalize project IDs returned as strings or nested objects."""
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            project_id = value.get("id") or value.get("projectId")
            if isinstance(project_id, str) and project_id.strip():
                return project_id.strip()
        return None

    def _load_code_assist_profile(self) -> None:
        """Initialize project selection for the Code Assist backend."""
        project_id = self._configured_project_id() or self.project_id
        client_metadata = {
            "ideType": "IDE_UNSPECIFIED",
            "platform": "PLATFORM_UNSPECIFIED",
            "pluginType": "GEMINI",
            "duetProject": project_id,
        }

        load_response = requests.post(
            f"{ANTIGRAVITY_ENDPOINT_PROD}/v1internal:loadCodeAssist",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                **self._request_headers(),
            },
            json={
                "cloudaicompanionProject": project_id,
                "metadata": client_metadata,
            },
            timeout=30,
        )

        if not load_response.ok:
            raise RuntimeError(
                f"Gemini CLI setup failed: HTTP {load_response.status_code}: "
                f"{load_response.text[:300]}"
            )

        load_data = load_response.json()
        if not project_id:
            project_id = self._extract_project_id(
                load_data.get("cloudaicompanionProject")
            )

        current_tier = load_data.get("currentTier") or {}
        if not current_tier:
            for tier in load_data.get("allowedTiers") or []:
                if tier.get("isDefault"):
                    current_tier = tier
                    break
        if not current_tier:
            current_tier = {
                "id": "legacy-tier",
                "userDefinedCloudaicompanionProject": True,
            }

        if current_tier.get("userDefinedCloudaicompanionProject") and not project_id:
            raise RuntimeError(
                "This Gemini CLI login requires a Google Cloud project. "
                "Set GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_PROJECT_ID and try again."
            )

        onboard_payload = {
            "tierId": current_tier.get("id"),
            "cloudaicompanionProject": project_id,
            "metadata": client_metadata,
        }
        onboard_response = requests.post(
            f"{ANTIGRAVITY_ENDPOINT_PROD}/v1internal:onboardUser",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                **self._request_headers(),
            },
            json=onboard_payload,
            timeout=30,
        )

        if not onboard_response.ok:
            raise RuntimeError(
                f"Gemini CLI onboarding failed: HTTP {onboard_response.status_code}: "
                f"{onboard_response.text[:300]}"
            )

        onboard_data = onboard_response.json()
        attempts = 0
        while not onboard_data.get("done", False):
            attempts += 1
            if attempts >= 12:
                raise RuntimeError("Gemini CLI onboarding did not finish in time.")
            time.sleep(1)
            onboard_response = requests.post(
                f"{ANTIGRAVITY_ENDPOINT_PROD}/v1internal:onboardUser",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    **self._request_headers(),
                },
                json=onboard_payload,
                timeout=30,
            )
            if not onboard_response.ok:
                raise RuntimeError(
                    f"Gemini CLI onboarding failed: HTTP {onboard_response.status_code}: "
                    f"{onboard_response.text[:300]}"
                )
            onboard_data = onboard_response.json()

        onboard_project = self._extract_project_id(
            (onboard_data.get("response") or {}).get("cloudaicompanionProject")
        )
        self.project_id = onboard_project or project_id

    def ensure_code_assist_ready(self) -> bool:
        """Ensure CLI tokens are ready for Code Assist requests."""
        if self._code_assist_ready:
            return True
        if not self.access_token:
            return False

        self._load_code_assist_profile()
        self._code_assist_ready = True
        return True

    def build_authorization_url(self) -> Tuple[str, str]:
        """Build the OAuth authorization URL with PKCE."""
        import base64 as _b64

        verifier, challenge = PKCEGenerator.generate()
        payload = json.dumps(
            {
                "verifier": verifier,
                "projectId": "",
                "authMode": AUTH_MODE_GEMINI_CLI,
            }
        )
        state = _b64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

        params = {
            "client_id": _CLIENT_ID,
            "response_type": "code",
            "redirect_uri": OAUTH_REDIRECT_URI,
            "scope": " ".join(GEMINI_CLI_SCOPES),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        return auth_url, verifier

    def start_callback_server(self) -> None:
        from http.server import HTTPServer
        import threading

        OAuthCallbackHandler.reset()
        self.server = HTTPServer(("localhost", 51121), OAuthCallbackHandler)

        def serve() -> None:
            while not OAuthCallbackHandler.callback_received.is_set():
                self.server.handle_request()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()

    def stop_callback_server(self) -> None:
        if self.server:
            self.server.server_close()
            self.server = None

    def exchange_code(self, code: str, verifier: str) -> bool:
        """Exchange authorization code for access and refresh tokens."""
        self._update_status("Exchanging authorization code...")

        try:
            response = requests.post(
                "https://oauth2.googleapis.com/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "Accept": "*/*",
                },
                data={
                    "client_id": _CLIENT_ID,
                    "client_secret": _CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": OAUTH_REDIRECT_URI,
                    "code_verifier": verifier,
                },
                timeout=30,
            )

            if not response.ok:
                self._update_status(f"Token exchange failed: {response.text}")
                return False

            data = response.json()
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.expires_at = time.time() + data.get("expires_in", 3600)

            self._fetch_user_info()
            self.ensure_code_assist_ready()
            self._save_tokens()

            self._update_status(
                f"Authenticated as {self.email or 'Unknown'} (Gemini CLI mode)"
            )
            return True

        except Exception as exc:
            self._update_status(f"Token exchange error: {exc}")
            return False

    def _fetch_user_info(self) -> None:
        try:
            response = requests.get(
                "https://www.googleapis.com/oauth2/v1/userinfo?alt=json",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )
            if response.ok:
                self.email = response.json().get("email")
        except Exception:
            pass

    def _save_tokens(self) -> None:
        self.storage.save_tokens(
            {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_at": self.expires_at,
                "email": self.email,
                "project_id": self.project_id,
            }
        )

    def load_saved_tokens(self) -> bool:
        """Load tokens, first from our own store and then Gemini CLI's."""
        tokens = self.storage.load_tokens()
        if tokens:
            return self._apply_tokens(tokens)

        if _GEMINI_CLI_CREDS_PATH.exists():
            try:
                with open(_GEMINI_CLI_CREDS_PATH, "r", encoding="utf-8") as handle:
                    cli_tokens = json.load(handle)
                mapped = {
                    "access_token": cli_tokens.get("access_token"),
                    "refresh_token": cli_tokens.get("refresh_token"),
                    "expires_at": cli_tokens.get("expiry_date", 0) / 1000.0
                    if cli_tokens.get("expiry_date")
                    else 0,
                }
                if mapped["access_token"] or mapped["refresh_token"]:
                    self._update_status(
                        "Loaded credentials from existing Gemini CLI login"
                    )
                    return self._apply_tokens(mapped)
            except Exception as exc:
                logger.debug(f"Failed to load Gemini CLI creds: {exc}")

        return False

    def _apply_tokens(self, tokens: dict) -> bool:
        self.access_token = tokens.get("access_token")
        self.refresh_token = tokens.get("refresh_token")
        self.expires_at = tokens.get("expires_at", 0)
        self.email = tokens.get("email")
        self.project_id = tokens.get("project_id") or self._configured_project_id()
        self._code_assist_ready = bool(self.project_id)

        if time.time() >= self.expires_at - 60:
            return self.refresh_access_token()

        return bool(self.access_token)

    def refresh_access_token(self) -> bool:
        if not self.refresh_token:
            return False

        self._update_status("Refreshing access token...")
        try:
            response = requests.post(
                "https://oauth2.googleapis.com/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                },
                data={
                    "client_id": _CLIENT_ID,
                    "client_secret": _CLIENT_SECRET,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=30,
            )

            if response.ok:
                data = response.json()
                self.access_token = data.get("access_token")
                self.expires_at = time.time() + data.get("expires_in", 3600)
                self._code_assist_ready = False
                self.ensure_code_assist_ready()
                self._save_tokens()
                self._update_status("Token refreshed successfully")
                return True

            self._update_status(f"Token refresh failed: {response.text}")
            return False

        except Exception as exc:
            self._update_status(f"Token refresh error: {exc}")
            return False

    def ensure_valid_token(self) -> bool:
        if time.time() >= self.expires_at - 60:
            return self.refresh_access_token()
        return bool(self.access_token)

    def is_authenticated(self) -> bool:
        return bool(self.access_token) and time.time() < self.expires_at

    def logout(self) -> None:
        self.storage.clear_tokens()
        self.access_token = None
        self.refresh_token = None
        self.email = None
        self.project_id = None
        self.expires_at = 0
        self._code_assist_ready = False

    def start_login_flow(self) -> bool:
        """Start the complete OAuth login flow (local browser)."""
        self._update_status("Starting Gemini CLI OAuth authentication...")
        try:
            import webbrowser

            auth_url, verifier = self.build_authorization_url()
            self.start_callback_server()

            self._update_status("Opening browser for authentication...")
            webbrowser.open(auth_url)

            OAuthCallbackHandler.callback_received.wait(timeout=300)

            if OAuthCallbackHandler.auth_code:
                return self.exchange_code(OAuthCallbackHandler.auth_code, verifier)

            self._update_status("Authentication timed out or was cancelled")
            return False
        finally:
            self.stop_callback_server()
