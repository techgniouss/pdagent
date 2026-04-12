"""
Interactive configuration wizard and INI-based config loader.

Stores configuration in two INI-format files under ~/.pdagent/:
  config       — non-sensitive settings (human-readable)
  credentials  — secrets only (chmod 600 on Unix)

This mirrors the AWS-CLI pattern: separate config and credentials files
in a dedicated app directory (~/.pdagent/).
"""

from __future__ import annotations

import configparser
import getpass
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def pdagent_dir() -> Path:
    """Return the Pocket Desk Agent configuration directory (~/.pdagent)."""
    return Path.home() / ".pdagent"


def config_path() -> Path:
    """Return the path to the non-sensitive config file."""
    return pdagent_dir() / "config"


def credentials_path() -> Path:
    """Return the path to the credentials (secrets) file."""
    return pdagent_dir() / "credentials"


def has_config() -> bool:
    """Return True if both config and credentials files exist."""
    return config_path().exists() and credentials_path().exists()


# ---------------------------------------------------------------------------
# INI → os.environ loader
# ---------------------------------------------------------------------------

# Maps (file_type, section, ini_key) → environment variable name
_INI_ENV_MAP: dict[tuple[str, str, str], str] = {
    # credentials file
    ("credentials", "default", "telegram_bot_token"):    "TELEGRAM_BOT_TOKEN",
    ("credentials", "default", "google_api_key"):        "GOOGLE_API_KEY",
    ("credentials", "default", "dropbox_access_token"):  "DROPBOX_ACCESS_TOKEN",
    ("credentials", "default", "google_oauth_client_id"):     "GOOGLE_OAUTH_CLIENT_ID",
    ("credentials", "default", "google_oauth_client_secret"):  "GOOGLE_OAUTH_CLIENT_SECRET",
    # config [bot] section
    ("config", "bot", "authorized_user_ids"):   "AUTHORIZED_USER_IDS",
    ("config", "bot", "telegram_bot_username"): "TELEGRAM_BOT_USERNAME",
    ("config", "bot", "approved_directories"):  "APPROVED_DIRECTORIES",
    ("config", "bot", "google_oauth_enabled"):  "GOOGLE_OAUTH_ENABLED",
    ("config", "bot", "gemini_model"):          "GEMINI_MODEL",
    ("config", "bot", "max_tokens_per_request"): "MAX_TOKENS_PER_REQUEST",
    ("config", "bot", "system_prompt"):         "SYSTEM_PROMPT",
    ("config", "bot", "google_project_id"):     "GOOGLE_PROJECT_ID",
    # config [features] section
    ("config", "features", "upload_expiry_time"):         "UPLOAD_EXPIRY_TIME",
    ("config", "features", "claude_default_repo_path"):   "CLAUDE_DEFAULT_REPO_PATH",
    ("config", "features", "auto_update_enabled"):        "AUTO_UPDATE_ENABLED",
    ("config", "features", "auto_update_interval_minutes"): "AUTO_UPDATE_INTERVAL_MINUTES",
    ("config", "features", "log_level"):                  "LOG_LEVEL",
}


def load_into_environ() -> None:
    """
    Read ~/.pdagent/config and ~/.pdagent/credentials and populate
    os.environ with their values using setdefault — never overwrites
    values already set by the shell or earlier in the process.

    Silent no-op if the files do not exist (backward compatibility
    for users who still rely on .env files).
    """
    _load_file("credentials", credentials_path())
    _load_file("config", config_path())


def _load_file(file_type: str, path: Path) -> None:
    if not path.exists():
        return
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    for (ftype, section, key), env_var in _INI_ENV_MAP.items():
        if ftype != file_type:
            continue
        if not parser.has_option(section, key):
            continue
        value = parser.get(section, key)
        if value:  # only inject non-empty values
            os.environ.setdefault(env_var, value)


# ---------------------------------------------------------------------------
# Private wizard helpers
# ---------------------------------------------------------------------------

def _prompt_required(label: str, hint: str | None = None, secret: bool = False) -> str:
    """Prompt until the user provides a non-empty value."""
    if hint:
        print(f"  Hint: {hint}")
    while True:
        prompt_text = f"  {label}: "
        value = (getpass.getpass(prompt_text) if secret else input(prompt_text)).strip()
        if value:
            return value
        print("  This field is required. Please enter a value.")


def _prompt_optional(
    label: str,
    hint: str | None = None,
    default: str = "",
    secret: bool = False,
) -> str:
    """Prompt for an optional value; returns default if user presses Enter."""
    display = f"  {label}"
    if default:
        display += f" [{default}]"
    display += " (optional, Enter to skip): "
    if hint:
        print(f"  Hint: {hint}")
    raw = (getpass.getpass(display) if secret else input(display)).strip()
    return raw if raw else default


def _validate_allowed_users(raw: str) -> str | None:
    """Return an error message if raw is not a valid comma-separated int list."""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return "At least one user ID is required."
    for part in parts:
        try:
            int(part)
        except ValueError:
            return f"'{part}' is not a valid integer. User IDs must be numeric."
    return None


def _mask(value: str) -> str:
    """Return a masked version showing only the last 4 characters."""
    if not value or len(value) <= 4:
        return "****"
    return "\u2022" * (len(value) - 4) + value[-4:]


def _show_current_config() -> None:
    """Display current configuration values (secrets masked)."""
    parser_cred = configparser.ConfigParser()
    parser_cfg = configparser.ConfigParser()
    if credentials_path().exists():
        parser_cred.read(credentials_path(), encoding="utf-8")
    if config_path().exists():
        parser_cfg.read(config_path(), encoding="utf-8")

    def cred(key: str) -> str:
        v = parser_cred.get("default", key, fallback="")
        return _mask(v) if v else "(not set)"

    def cfg(section: str, key: str) -> str:
        return parser_cfg.get(section, key, fallback="(not set)")

    print("\nCurrent configuration:")
    print(f"  Telegram Bot Token   : {cred('telegram_bot_token')}")
    print(f"  Authorized User IDs  : {cfg('bot', 'authorized_user_ids')}")
    print(f"  Google OAuth Enabled : {cfg('bot', 'google_oauth_enabled')}")
    print(f"  Google API Key       : {cred('google_api_key')}")
    print(f"  Gemini Model         : {cfg('bot', 'gemini_model')}")
    print(f"  Approved Directories : {cfg('bot', 'approved_directories')}")
    print(f"  Dropbox Token        : {cred('dropbox_access_token')}")
    print()


# ---------------------------------------------------------------------------
# Auto OAuth login (triggered at end of wizard)
# ---------------------------------------------------------------------------

def _auto_oauth_login() -> None:
    """Trigger browser-based OAuth login after configuration."""
    # Lazy import to avoid pulling in antigravity_auth during simple config reads
    from pocket_desk_agent.antigravity_auth import AntigravityOAuth

    oauth = AntigravityOAuth()
    if oauth.load_saved_tokens():
        print(f"\n  Already authenticated as {oauth.email}")
        return

    print("\n  Opening browser for Google authentication...")
    print("  (If the browser doesn't open, copy the URL from the terminal.)\n")

    success = oauth.start_login_flow()
    if success and oauth.is_authenticated():
        print(f"\n  ✅ Authenticated as {oauth.email}")
        if oauth.project_id:
            print(f"     Project: {oauth.project_id}")
    else:
        print("\n  ⚠️  Browser login didn't complete.")
        print("  You can authenticate later with: pdagent auth")
        print("  Or use /login in Telegram after starting the bot.")


# ---------------------------------------------------------------------------
# Public wizard entry point
# ---------------------------------------------------------------------------

def run_configure_wizard(reconfigure: bool = False) -> None:
    """
    Interactive setup wizard.

    Args:
        reconfigure: If False, exits silently when config already exists
                     (used for auto-detect on first run).
                     If True, shows current config and asks for confirmation
                     before overwriting (used by 'pdagent configure').
    """
    if not reconfigure and has_config():
        return

    print("\n=== Pocket Desk Agent — Configuration Setup ===\n")

    if reconfigure and has_config():
        _show_current_config()
        confirm = input("Reconfigure? (y/N): ").strip().lower()
        if confirm != "y":
            print("Configuration unchanged.")
            return

    pdagent_dir().mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # [1/3] Telegram Settings
    # ------------------------------------------------------------------
    print("\n[1/3] Telegram Settings")
    print("-" * 40)
    token = _prompt_required(
        "Telegram Bot Token",
        hint="Get from @BotFather on Telegram",
        secret=True,
    )

    while True:
        raw_ids = _prompt_required(
            "Authorized User IDs",
            hint="Your Telegram user ID(s), comma-separated. Find yours via @userinfobot",
        )
        error = _validate_allowed_users(raw_ids)
        if error:
            print(f"  Error: {error}")
        else:
            break

    # Normalize: strip whitespace around commas
    authorized_user_ids = ",".join(p.strip() for p in raw_ids.split(",") if p.strip())

    # ------------------------------------------------------------------
    # [2/3] Gemini AI Authentication
    # ------------------------------------------------------------------
    print("\n[2/3] Gemini AI Authentication")
    print("-" * 40)
    print("  How do you want to authenticate with Gemini AI?")
    print("    1) Google OAuth  (recommended — browser-based, tokens auto-refresh)")
    print("    2) Google API Key (paste a key directly)")

    google_oauth_enabled = "true"
    google_api_key = ""
    google_oauth_client_id = ""
    google_oauth_client_secret = ""
    while True:
        choice = input("  Choice [1]: ").strip() or "1"
        if choice == "1":
            google_oauth_enabled = "true"
            google_api_key = ""
            google_oauth_client_id = ""
            google_oauth_client_secret = ""
            print("  OAuth selected — uses built-in credentials (zero config).")
            print("  Start the bot and use /login in Telegram to authenticate.")
            break
        elif choice == "2":
            google_oauth_enabled = "false"
            google_api_key = _prompt_required(
                "Google API Key",
                hint="Get from Google AI Studio: aistudio.google.com",
                secret=True,
            )
            break
        else:
            print("  Please enter 1 or 2.")

    # ------------------------------------------------------------------
    # [3/3] Optional Settings
    # ------------------------------------------------------------------
    print("\n[3/3] Optional Settings")
    print("-" * 40)

    telegram_bot_username = _prompt_optional(
        "Telegram Bot Username",
        hint="Your bot's @username (without the @ symbol)",
    )
    approved_directories = _prompt_optional(
        "Approved Directories",
        hint="Comma-separated directories this bot may access",
        default=".",
    )
    dropbox_access_token = _prompt_optional(
        "Dropbox Access Token",
        hint="Only needed for large file uploads via Dropbox",
        secret=True,
    )

    # ------------------------------------------------------------------
    # Write credentials file
    # ------------------------------------------------------------------
    cred_parser = configparser.ConfigParser()
    cred_parser["default"] = {
        "telegram_bot_token": token,
        "google_api_key": google_api_key,
        "google_oauth_client_id": google_oauth_client_id,
        "google_oauth_client_secret": google_oauth_client_secret,
        "dropbox_access_token": dropbox_access_token,
    }
    with open(credentials_path(), "w", encoding="utf-8") as f:
        f.write("# Pocket Desk Agent — credentials\n")
        f.write("# Keep this file private. Do not share or commit it.\n\n")
        cred_parser.write(f)

    # Restrict permissions on Unix (no-op on Windows)
    if os.name != "nt":
        os.chmod(credentials_path(), 0o600)

    # ------------------------------------------------------------------
    # Write config file
    # ------------------------------------------------------------------
    cfg_parser = configparser.ConfigParser()
    cfg_parser["bot"] = {
        "authorized_user_ids": authorized_user_ids,
        "telegram_bot_username": telegram_bot_username,
        "approved_directories": approved_directories,
        "google_oauth_enabled": google_oauth_enabled,
        "gemini_model": "gemini-2.0-flash",
        "max_tokens_per_request": "8000",
        "system_prompt": "",
        "google_project_id": "",
    }
    cfg_parser["features"] = {
        "upload_expiry_time": "1h",
        "claude_default_repo_path": "",
        "auto_update_enabled": "true",
        "auto_update_interval_minutes": "60",
        "log_level": "INFO",
    }
    with open(config_path(), "w", encoding="utf-8") as f:
        f.write("# Pocket Desk Agent — configuration\n")
        f.write("# Edit values here and restart the bot to apply changes.\n\n")
        cfg_parser.write(f)

    # ------------------------------------------------------------------
    # Success message
    # ------------------------------------------------------------------
    print("\nConfiguration saved:")
    print(f"  {config_path()}")
    cred_perm = "permissions: 600" if os.name != "nt" else "created"
    print(f"  {credentials_path()}  ({cred_perm})")

    if google_oauth_enabled == "true":
        _auto_oauth_login()

    print("  Start the bot with: pdagent start\n")
