"""Authentication module with multi-provider support.

Supports three authentication modes:
  - antigravity : Internal Google OAuth (cloudcode-pa endpoints)
  - gemini-cli  : Public Gemini CLI OAuth (generativelanguage.googleapis.com)
  - apikey      : Google API key (no OAuth needed)
"""

import logging
from typing import Optional, Dict, Union
from telegram import Update

from pocket_desk_agent.config import Config
from pocket_desk_agent.constants import (
    AUTH_MODE_ANTIGRAVITY,
    AUTH_MODE_GEMINI_CLI,
    AUTH_MODE_APIKEY,
)
from pocket_desk_agent.antigravity_auth import AntigravityOAuth
from pocket_desk_agent.gemini_cli_auth import GeminiCLIOAuth

logger = logging.getLogger(__name__)

# Type alias for either OAuth provider
OAuthInstance = Union[AntigravityOAuth, GeminiCLIOAuth]


class AntigravityAuth:
    """Handles authentication for multiple users.

    Despite the legacy name, this class now serves as the multi-provider
    auth manager — it creates the right OAuth instance based on the
    configured (or per-login-request) auth mode.
    """

    def __init__(self):
        # Store OAuth instances per user
        self.user_oauth_instances: Dict[int, OAuthInstance] = {}
        # Pending verifiers from /login (keyed by user ID)
        self._pending_verifiers: Dict[int, str] = {}
        # Track which auth mode each user used for /login
        self._pending_auth_modes: Dict[int, str] = {}

    def _build_oauth_instance(self, user_id: int, mode: str) -> OAuthInstance:
        """Create a fresh OAuth instance for the requested provider."""
        def status_callback(msg: str):
            logger.info(f"[User {user_id}] {msg}")

        if mode == AUTH_MODE_GEMINI_CLI:
            return GeminiCLIOAuth(on_status_update=status_callback)
        return AntigravityOAuth(on_status_update=status_callback)

    def _get_oauth_instance(
        self, user_id: int, auth_mode: Optional[str] = None
    ) -> OAuthInstance:
        """Get or create OAuth instance for user.

        Args:
            user_id: Telegram user ID.
            auth_mode: Force a specific mode ("antigravity" or "gemini-cli").
                       If None, uses the globally configured mode.
        """
        mode = auth_mode or Config.GEMINI_AUTH_MODE

        # If user already has an instance of the right type, return it
        if user_id in self.user_oauth_instances:
            existing = self.user_oauth_instances[user_id]
            # Check type matches requested mode
            if mode == AUTH_MODE_GEMINI_CLI and isinstance(existing, GeminiCLIOAuth):
                return existing
            elif mode == AUTH_MODE_ANTIGRAVITY and isinstance(existing, AntigravityOAuth):
                return existing
            # Wrong type — recreate
            del self.user_oauth_instances[user_id]

        instance = self._build_oauth_instance(user_id, mode)
        self.user_oauth_instances[user_id] = instance
        return instance

    @staticmethod
    def _token_mtime(oauth: OAuthInstance) -> float:
        """Return the saved-token file mtime, or 0 when unavailable."""
        try:
            return oauth.storage.tokens_file.stat().st_mtime
        except Exception:
            return 0.0

    def _load_saved_instance(
        self, user_id: int, preferred_mode: Optional[str] = None
    ) -> Optional[OAuthInstance]:
        """Load the best saved OAuth instance for a user.

        If ``preferred_mode`` is explicitly requested, it wins when valid.
        Otherwise, prefer the most recently updated valid token store.
        """
        if preferred_mode and preferred_mode != AUTH_MODE_APIKEY:
            preferred = self._build_oauth_instance(user_id, preferred_mode)
            if preferred.load_saved_tokens():
                self.user_oauth_instances[user_id] = preferred
                return preferred

        candidates: list[tuple[float, OAuthInstance]] = []
        for mode in (AUTH_MODE_ANTIGRAVITY, AUTH_MODE_GEMINI_CLI):
            oauth = self._build_oauth_instance(user_id, mode)
            if oauth.load_saved_tokens():
                candidates.append((self._token_mtime(oauth), oauth))

        if not candidates:
            return None

        _, selected = max(candidates, key=lambda item: item[0])
        self.user_oauth_instances[user_id] = selected
        return selected

    def get_auth_mode(self, user_id: int, fallback: Optional[str] = None) -> str:
        """Return the active auth mode for a user."""
        existing = self.user_oauth_instances.get(user_id)
        if isinstance(existing, GeminiCLIOAuth):
            return AUTH_MODE_GEMINI_CLI
        if isinstance(existing, AntigravityOAuth):
            return AUTH_MODE_ANTIGRAVITY
        saved = self._load_saved_instance(user_id)
        if isinstance(saved, GeminiCLIOAuth):
            return AUTH_MODE_GEMINI_CLI
        if isinstance(saved, AntigravityOAuth):
            return AUTH_MODE_ANTIGRAVITY
        return fallback or Config.GEMINI_AUTH_MODE

    def is_authenticated(self, user_id: int) -> bool:
        """Check if user is authenticated."""
        if Config.GEMINI_AUTH_MODE == AUTH_MODE_APIKEY:
            return bool(Config.GOOGLE_API_KEY)

        if user_id in self.user_oauth_instances:
            oauth = self.user_oauth_instances[user_id]
            return oauth.is_authenticated() or oauth.load_saved_tokens()

        return self._load_saved_instance(user_id) is not None

    def get_user_info(self, user_id: int, auth_mode: Optional[str] = None) -> Optional[dict]:
        """Get authenticated user info."""
        if Config.GEMINI_AUTH_MODE == AUTH_MODE_APIKEY:
            return {
                "email": "(API key mode)",
                "project_id": None,
                "access_token": None,
                "auth_mode": AUTH_MODE_APIKEY,
            }

        if auth_mode is None and user_id in self.user_oauth_instances:
            oauth = self.user_oauth_instances[user_id]
            if oauth.is_authenticated() or oauth.load_saved_tokens():
                return {
                    "email": oauth.email,
                    "project_id": getattr(oauth, "project_id", None),
                    "access_token": oauth.access_token,
                    "auth_mode": AUTH_MODE_GEMINI_CLI
                    if isinstance(oauth, GeminiCLIOAuth)
                    else AUTH_MODE_ANTIGRAVITY,
                }

        oauth = self._load_saved_instance(user_id, preferred_mode=auth_mode)
        if oauth:
            return {
                "email": oauth.email,
                "project_id": getattr(oauth, "project_id", None),
                "access_token": oauth.access_token,
                "auth_mode": AUTH_MODE_GEMINI_CLI
                if isinstance(oauth, GeminiCLIOAuth)
                else AUTH_MODE_ANTIGRAVITY,
            }

        return None

    def logout_user(self, user_id: int):
        """Logout user and clear tokens for all OAuth modes."""
        if user_id in self.user_oauth_instances:
            self.user_oauth_instances[user_id].logout()
            del self.user_oauth_instances[user_id]

        # Ensure filesystem tokens from all providers are securely scrubbed
        AntigravityOAuth(on_status_update=lambda msg: None).logout()
        GeminiCLIOAuth(on_status_update=lambda msg: None).logout()
        logger.info(f"User {user_id} logged out (tokens cleared)")


def is_user_allowed(update: Update) -> bool:
    """Check if user is in allowed list."""
    if not update.effective_user:
        return False
    return update.effective_user.id in Config.AUTHORIZED_USER_IDS
