"""Configuration management.

Config values are loaded via the ``load()`` classmethod so that:
  1. Tests can call ``Config.load()`` after patching os.environ.
  2. The configure wizard can reload after writing new files.
  3. Import-time side-effects are limited to the initial load.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load INI-based config/credentials first (new format).
# Uses os.environ.setdefault — never overwrites shell env vars.
# Silent no-op for users who still use .env files.
from pocket_desk_agent.configure import dotenv_path_candidates, load_into_environ


def _load_config_files() -> None:
    """Load config values from canonical and legacy app directories."""
    load_into_environ()
    for dotenv_path in dotenv_path_candidates():
        load_dotenv(dotenv_path=dotenv_path, override=False)


def _resolve_user_path(raw_path: str, *, default: Path | None = None) -> Path:
    """Resolve user-configured paths without relying on the process cwd."""
    value = raw_path.strip()
    if not value:
        if default is None:
            raise ValueError("Path value is required when no default is supplied.")
        return default

    expanded = Path(os.path.expandvars(value)).expanduser()
    if expanded.is_absolute():
        return expanded

    return (Path.home() / expanded).resolve()


_load_config_files()


class Config:
    """Bot configuration.

    All values are read from ``os.environ`` when ``load()`` is called.
    The class is pre-loaded at import time for backward compatibility,
    but callers can re-invoke ``load()`` to pick up changes.
    """

    # These are set by load() — declared here for static analysis.
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""
    AUTHORIZED_USER_IDS: list[int] = []
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GOOGLE_OAUTH_ENABLED: bool = True
    GEMINI_AUTH_MODE: str = "antigravity"
    MAX_TOKENS_PER_REQUEST: int = 8000
    SYSTEM_PROMPT: str = ""
    GOOGLE_PROJECT_ID: str | None = None
    APPROVED_DIRECTORIES: list[Path] = []
    CLAUDE_DEFAULT_REPO_PATH: str = ""
    UPLOAD_EXPIRY_TIME: str = "1h"
    AUTO_UPDATE_ENABLED: bool = True
    AUTO_UPDATE_INTERVAL_MINUTES: int = 60
    LOG_LEVEL: str = "INFO"

    @classmethod
    def load(cls) -> None:
        """(Re-)read every config value from ``os.environ``."""
        _load_config_files()
        cls.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        cls.TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")

        cls.AUTHORIZED_USER_IDS = [
            int(uid.strip())
            for uid in (
                os.getenv("AUTHORIZED_USER_IDS")
                or os.getenv("ALLOWED_USERS", "")
            ).split(",")
            if uid.strip()
        ]

        cls.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

        cls.GEMINI_MODEL = (
            os.getenv("ANTIGRAVITY_MODEL")
            or os.getenv("GEMINI_MODEL")
            or "gemini-2.0-flash"
        )

        cls.GOOGLE_OAUTH_ENABLED = (
            os.getenv(
                "GOOGLE_OAUTH_ENABLED",
                os.getenv("ANTIGRAVITY_ENABLED", "true"),
            )
        ).lower() == "true"

        # Resolve auth mode: explicit GEMINI_AUTH_MODE takes priority,
        # otherwise derive from legacy GOOGLE_OAUTH_ENABLED / GOOGLE_API_KEY.
        explicit_mode = os.getenv("GEMINI_AUTH_MODE", "").strip().lower()
        if explicit_mode in ("antigravity", "gemini-cli", "apikey"):
            cls.GEMINI_AUTH_MODE = explicit_mode
        elif not cls.GOOGLE_OAUTH_ENABLED and cls.GOOGLE_API_KEY:
            cls.GEMINI_AUTH_MODE = "apikey"
        else:
            cls.GEMINI_AUTH_MODE = "antigravity"

        # Keep GOOGLE_OAUTH_ENABLED in sync for backward compat
        cls.GOOGLE_OAUTH_ENABLED = cls.GEMINI_AUTH_MODE != "apikey"

        cls.MAX_TOKENS_PER_REQUEST = int(
            os.getenv("MAX_TOKENS_PER_REQUEST", "8000")
        )

        cls.SYSTEM_PROMPT = (
            os.getenv("SYSTEM_PROMPT") or os.getenv("SYSTEM_INSTRUCTION", "")
        )

        cls.GOOGLE_PROJECT_ID = (
            os.getenv("GOOGLE_PROJECT_ID")
            or os.getenv("ANTIGRAVITY_PROJECT_ID")
        )

        approved_dirs_raw = (
            os.getenv("APPROVED_DIRECTORIES")
            or os.getenv("APPROVED_DIRECTORY")
            or str(Path.home())
        )
        cls.APPROVED_DIRECTORIES = [
            _resolve_user_path(path_value, default=Path.home())
            for path_value in approved_dirs_raw.split(",")
            if path_value.strip()
        ]

        default_repo_path = Path.home() / "Documents"
        cls.CLAUDE_DEFAULT_REPO_PATH = str(
            _resolve_user_path(
                os.getenv("CLAUDE_DEFAULT_REPO_PATH")
                or os.getenv("DEFAULT_REPO_PATH", str(default_repo_path)),
                default=default_repo_path,
            )
        )

        cls.UPLOAD_EXPIRY_TIME = os.getenv("UPLOAD_EXPIRY_TIME", "1h")

        cls.AUTO_UPDATE_ENABLED = (
            os.getenv(
                "AUTO_UPDATE_ENABLED",
                os.getenv("AUTO_UPDATE_CHECK", "true"),
            )
        ).lower() == "true"

        cls.AUTO_UPDATE_INTERVAL_MINUTES = int(
            os.getenv("AUTO_UPDATE_INTERVAL_MINUTES", "60")
        )

        cls.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration."""
        errors = []
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        if not cls.AUTHORIZED_USER_IDS:
            errors.append(
                "AUTHORIZED_USER_IDS is required — run 'pdagent configure' to set up"
            )
        return errors


# Auto-load at import time so existing code keeps working.
Config.load()
