"""
Interactive configuration wizard and INI-based config loader.

Stores configuration in two INI-format files under ~/.pdagent/:
  config       — non-sensitive settings (human-readable)
  credentials  — secrets only (chmod 600 on Unix)

Legacy ~/.pd-agent/ files are still read for backward compatibility, but all
new writes go to the canonical app directory.
"""

from __future__ import annotations

import configparser
import getpass
import os
from pathlib import Path

from pocket_desk_agent.app_paths import (
    app_path,
    app_path_candidates,
    ensure_app_dir,
    existing_app_path,
)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def pdagent_dir() -> Path:
    """Return the canonical Pocket Desk Agent configuration directory."""
    return ensure_app_dir()


def config_path() -> Path:
    """Return the path to the non-sensitive config file."""
    return app_path("config")


def credentials_path() -> Path:
    """Return the path to the credentials (secrets) file."""
    return app_path("credentials")


def dotenv_path() -> Path:
    """Return the canonical legacy dotenv path."""
    return app_path(".env")


def config_path_candidates() -> tuple[Path, ...]:
    """Return canonical and legacy candidate config paths."""
    return app_path_candidates("config")


def credentials_path_candidates() -> tuple[Path, ...]:
    """Return canonical and legacy candidate credentials paths."""
    return app_path_candidates("credentials")


def dotenv_path_candidates() -> tuple[Path, ...]:
    """Return canonical and legacy candidate dotenv paths."""
    return app_path_candidates(".env")


def has_config() -> bool:
    """Return True if both config and credentials exist in supported locations."""
    return existing_app_path("config").exists() and existing_app_path("credentials").exists()


# ---------------------------------------------------------------------------
# INI -> os.environ loader
# ---------------------------------------------------------------------------

# Maps (file_type, section, ini_key) -> environment variable name
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
    ("config", "bot", "gemini_auth_mode"):       "GEMINI_AUTH_MODE",
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

    Legacy ~/.pd-agent files are read as fallbacks. Missing files are ignored.
    """
    for path in credentials_path_candidates():
        _load_file("credentials", path)
    for path in config_path_candidates():
        _load_file("config", path)


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


def _validate_directories(raw: str) -> tuple[list[Path], list[str]]:
    """
    Parse a comma-separated directory string.

    Returns (resolved_paths, warning_messages).
    Non-existent or non-directory paths produce warnings but are still
    included — the user may be configuring before a drive is mounted.
    An empty list produces an error warning without any paths.
    """
    warnings: list[str] = []
    paths: list[Path] = []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        warnings.append("At least one directory is required.")
        return paths, warnings
    for part in parts:
        try:
            p = Path(os.path.expandvars(part)).expanduser().resolve()
            if not p.exists():
                warnings.append(
                    f"  \u26a0  Does not exist (will be ignored at runtime): {p}"
                )
            elif not p.is_dir():
                warnings.append(
                    f"  \u26a0  Not a directory (will be rejected at runtime): {p}"
                )
            paths.append(p)
        except Exception as exc:
            warnings.append(f"  \u26a0  Could not resolve '{part}': {exc}")
    return paths, warnings


def _note_implicit_repo_path(cfg_parser: configparser.ConfigParser) -> None:
    """
    Print a note when CLAUDE_DEFAULT_REPO_PATH implicitly expands the sandbox.

    FileManager.__init__ always appends CLAUDE_DEFAULT_REPO_PATH to
    approved_dirs at runtime.  Users who set a Projects Directory without
    including it in Approved Directories would otherwise be surprised to
    find the bot can access that path.
    """
    repo = cfg_parser.get("features", "claude_default_repo_path", fallback="")
    if repo:
        print(
            f"  \u2139  Note: 'Default Projects Directory' ({repo}) is also\n"
            "     automatically added to the approved sandbox at runtime,\n"
            "     even if not listed above."
        )


def _show_current_config() -> None:
    """Display current configuration values (secrets masked)."""
    parser_cred = configparser.ConfigParser()
    parser_cfg = configparser.ConfigParser()
    current_credentials_path = existing_app_path("credentials")
    current_config_path = existing_app_path("config")
    if current_credentials_path.exists():
        parser_cred.read(current_credentials_path, encoding="utf-8")
    if current_config_path.exists():
        parser_cfg.read(current_config_path, encoding="utf-8")

    def cred(key: str) -> str:
        v = parser_cred.get("default", key, fallback="")
        return _mask(v) if v else "(not set)"

    def cfg(section: str, key: str) -> str:
        return parser_cfg.get(section, key, fallback="(not set)")

    print("\nCurrent configuration:")
    print(f"  Telegram Bot Token   : {cred('telegram_bot_token')}")
    print(f"  Authorized User IDs  : {cfg('bot', 'authorized_user_ids')}")
    print(f"  Gemini Auth Mode     : {cfg('bot', 'gemini_auth_mode')}")
    print(f"  Google OAuth Enabled : {cfg('bot', 'google_oauth_enabled')}")
    print(f"  Google API Key       : {cred('google_api_key')}")
    print(f"  Gemini Model         : {cfg('bot', 'gemini_model')}")
    print(f"  Approved Directories : {cfg('bot', 'approved_directories')}")
    print(f"  Dropbox Token        : {cred('dropbox_access_token')}")
    print()


# ---------------------------------------------------------------------------
# Auto OAuth login (triggered at end of wizard)
# ---------------------------------------------------------------------------

def _auto_oauth_login(auth_mode: str = "antigravity") -> None:
    """Trigger browser-based OAuth login after configuration."""
    if auth_mode == "gemini-cli":
        from pocket_desk_agent.gemini_cli_auth import GeminiCLIOAuth
        oauth = GeminiCLIOAuth()
    else:
        from pocket_desk_agent.antigravity_auth import AntigravityOAuth
        oauth = AntigravityOAuth()

    if oauth.load_saved_tokens():
        print(f"\n  Already authenticated as {oauth.email}")
        return

    print("\n  Opening browser for Google authentication...")
    print("  (If the browser doesn't open, copy the URL from the terminal.)\n")

    success = oauth.start_login_flow()
    if success and oauth.is_authenticated():
        print(f"\n  \u2705 Authenticated as {oauth.email}")
        if hasattr(oauth, 'project_id') and oauth.project_id:
            print(f"     Project: {oauth.project_id}")
    else:
        print("\n  \u26a0\ufe0f  Browser login didn't complete.")
        print("  You can authenticate later with: pdagent auth")
        print("  Or use /login in Telegram after starting the bot.")


def _configure_windows_startup(manager=None, input_func=input) -> None:
    """Offer interactive startup-at-logon setup on Windows."""
    if os.name != "nt":
        return

    if manager is None:
        from pocket_desk_agent.startup_manager import StartupManager

        manager = StartupManager()

    status = manager.get_status()
    if not status.supported:
        print("\nAutomatic background startup:")
        print(f"  {status.message}")
        return

    print("\n[Optional] Automatic Background Startup")
    print("-" * 40)
    print("Pocket Desk Agent can start automatically after you sign in to Windows.")
    print("This starts the bot in the background so you do not need to run `pdagent start` after reboot.")
    print("This is not a Windows Service.")
    print(
        "Startup-at-logon keeps screenshots, OCR, Claude Desktop control, and "
        "VS Code automation working because the bot runs in your logged-in desktop session."
    )

    if status.enabled:
        print("\n  Automatic startup is currently enabled.")
        answer = input_func("  Keep automatic startup enabled? [Y/n]: ").strip().lower()
        if answer in ("", "y", "yes"):
            print("  Automatic startup remains enabled.")
            return

        success, message = manager.disable_startup()
        print(f"  {message}")
        if not success:
            print("  You can try again later with: pdagent startup configure")
        return

    if status.details:
        print("\n  Existing startup task needs attention:")
        for detail in status.details:
            print(f"  - {detail}")

    answer = input_func("  Enable automatic startup after Windows login? [y/N]: ").strip().lower()
    if answer in ("y", "yes"):
        success, message = manager.enable_startup()
        print(f"  {message}")
        if not success:
            print("  You can try again later with: pdagent startup configure")
        return

    print("  Automatic startup left disabled.")
    print("  You can enable it later with: pdagent startup configure")


# ---------------------------------------------------------------------------
# Full first-time wizard
# ---------------------------------------------------------------------------

def _run_full_wizard() -> None:
    """Run the complete three-section configuration wizard from scratch."""
    ensure_app_dir()

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
    print("    1) Antigravity OAuth  (recommended — browser-based, internal Google API)")
    print("    2) Gemini CLI OAuth   (browser-based, public Gemini API — no GCP project needed)")
    print("    3) Google API Key     (paste a key directly)")
    print("    4) Setup Later        (skip — authenticate later via /login in Telegram)")

    gemini_auth_mode = "antigravity"
    google_oauth_enabled = "true"
    google_api_key = ""
    google_oauth_client_id = ""
    google_oauth_client_secret = ""
    do_oauth_later = False
    while True:
        choice = input("  Choice [1]: ").strip() or "1"
        if choice == "1":
            gemini_auth_mode = "antigravity"
            google_oauth_enabled = "true"
            google_api_key = ""
            google_oauth_client_id = ""
            google_oauth_client_secret = ""
            print("  Antigravity OAuth selected — uses built-in credentials (zero config).")
            break
        elif choice == "2":
            gemini_auth_mode = "gemini-cli"
            google_oauth_enabled = "true"
            google_api_key = ""
            google_oauth_client_id = ""
            google_oauth_client_secret = ""
            print("  Gemini CLI OAuth selected — uses public Gemini API, no GCP project needed.")
            break
        elif choice == "3":
            gemini_auth_mode = "apikey"
            google_oauth_enabled = "false"
            google_api_key = _prompt_required(
                "Google API Key",
                hint="Get from Google AI Studio: aistudio.google.com",
                secret=True,
            )
            break
        elif choice == "4":
            do_oauth_later = True
            gemini_auth_mode = "antigravity"
            google_oauth_enabled = "true"
            google_api_key = ""
            google_oauth_client_id = ""
            google_oauth_client_secret = ""
            print("  Skipping authentication setup.")
            print("  You can authenticate later using /login in Telegram after starting the bot.")
            break
        else:
            print("  Please enter 1, 2, 3, or 4.")

    # ------------------------------------------------------------------
    # [3/3] Optional Settings
    # ------------------------------------------------------------------
    print("\n[3/3] Optional Settings")
    print("-" * 40)

    telegram_bot_username = _prompt_optional(
        "Telegram Bot Username",
        hint="Your bot's @username (without the @ symbol)",
    )

    # Approved directories are the file-system security boundary.
    print("\n  Approved Directories — the bot's file-system SECURITY BOUNDARY.")
    print("  The bot can ONLY read, write, and browse inside these paths.")
    print("  Everything outside is blocked, regardless of the command used.")
    while True:
        approved_directories_raw = _prompt_optional(
            "Approved Directories",
            hint=(
                "Comma-separated absolute paths "
                "(e.g. C:\\Projects,C:\\Users\\you\\Downloads). "
                "Default: your entire home folder."
            ),
            default=str(Path.home()),
        )
        _, dir_warnings = _validate_directories(approved_directories_raw)
        for w in dir_warnings:
            print(w)
        # Only re-prompt if the list is completely empty
        if dir_warnings and dir_warnings[0].startswith("At least"):
            continue
        approved_directories = ",".join(
            p.strip() for p in approved_directories_raw.split(",") if p.strip()
        )
        break

    claude_default_repo_path = _prompt_optional(
        "Default Projects Directory",
        hint=(
            "Folder where your code repositories are located. "
            "This is also automatically added to the approved sandbox at runtime."
        ),
        default=str(Path.home() / "Documents"),
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
        "gemini_auth_mode": gemini_auth_mode,
        "google_oauth_enabled": google_oauth_enabled,
        "gemini_model": "gemini-2.0-flash",
        "max_tokens_per_request": "8000",
        "system_prompt": "",
        "google_project_id": "",
    }
    cfg_parser["features"] = {
        "upload_expiry_time": "1h",
        "claude_default_repo_path": claude_default_repo_path,
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
    _note_implicit_repo_path(cfg_parser)

    if google_oauth_enabled == "true" and not do_oauth_later:
        _auto_oauth_login(auth_mode=gemini_auth_mode)

    _configure_windows_startup()

    print("  Start the bot with: pdagent start\n")


# ---------------------------------------------------------------------------
# Selective update — patch individual fields in the existing config files
# ---------------------------------------------------------------------------

def _read_existing_parsers() -> tuple[configparser.ConfigParser, configparser.ConfigParser]:
    """Load the current credentials and config files into two ConfigParser objects."""
    cred_parser = configparser.ConfigParser()
    cfg_parser = configparser.ConfigParser()

    current_credentials_path = existing_app_path("credentials")
    current_config_path = existing_app_path("config")

    if current_credentials_path.exists():
        cred_parser.read(current_credentials_path, encoding="utf-8")
    if current_config_path.exists():
        cfg_parser.read(current_config_path, encoding="utf-8")

    # Ensure expected sections exist so setters never KeyError
    if not cred_parser.has_section("default"):
        cred_parser["default"] = {}
    for section in ("bot", "features"):
        if not cfg_parser.has_section(section):
            cfg_parser[section] = {}

    return cred_parser, cfg_parser


def _write_parsers(
    cred_parser: configparser.ConfigParser,
    cfg_parser: configparser.ConfigParser,
) -> None:
    """Write both parsers back to their canonical paths."""
    ensure_app_dir()

    with open(credentials_path(), "w", encoding="utf-8") as f:
        f.write("# Pocket Desk Agent — credentials\n")
        f.write("# Keep this file private. Do not share or commit it.\n\n")
        cred_parser.write(f)

    if os.name != "nt":
        os.chmod(credentials_path(), 0o600)

    with open(config_path(), "w", encoding="utf-8") as f:
        f.write("# Pocket Desk Agent — configuration\n")
        f.write("# Edit values here and restart the bot to apply changes.\n\n")
        cfg_parser.write(f)

    print("\nConfiguration updated:")
    print(f"  {config_path()}")
    cred_perm = "permissions: 600" if os.name != "nt" else "updated"
    print(f"  {credentials_path()}  ({cred_perm})")
    print("  Restart the bot with: pdagent restart\n")


def _update_authorized_user_ids(
    cred_parser: configparser.ConfigParser,
    cfg_parser: configparser.ConfigParser,
) -> None:
    """Prompt for and update the authorized user IDs."""
    current = cfg_parser.get("bot", "authorized_user_ids", fallback="")
    print(f"\n  Current value: {current or '(not set)'}")
    while True:
        raw_ids = _prompt_required(
            "New Authorized User IDs",
            hint="Comma-separated Telegram user IDs. Find yours via @userinfobot",
        )
        error = _validate_allowed_users(raw_ids)
        if error:
            print(f"  Error: {error}")
        else:
            break
    cfg_parser["bot"]["authorized_user_ids"] = ",".join(
        p.strip() for p in raw_ids.split(",") if p.strip()
    )
    _write_parsers(cred_parser, cfg_parser)


def _update_approved_directories(
    cred_parser: configparser.ConfigParser,
    cfg_parser: configparser.ConfigParser,
) -> None:
    """
    Interactive sub-menu to add, remove, or replace approved directories.

    Approved directories are the bot's complete file-system security boundary.
    Every read/write/browse operation is confined to these paths at runtime.
    FileManager also silently appends CLAUDE_DEFAULT_REPO_PATH to this list,
    which is surfaced as a note after saving.
    """
    current_raw = cfg_parser.get("bot", "approved_directories", fallback=str(Path.home()))
    current_paths = [p.strip() for p in current_raw.split(",") if p.strip()]
    changed = False

    while True:
        print("\n  Approved directories — the bot's file-system SECURITY BOUNDARY:")
        print("  The bot can ONLY read/write/browse files within these paths.\n")
        for i, p in enumerate(current_paths, 1):
            mark = "\u2713 exists" if Path(p).exists() else "\u2717 not found"
            print(f"    {i}. {p}  [{mark}]")
        print()
        print("    A) Add a directory")
        print("    R) Remove a directory")
        print("    S) Set all  (replace entire list at once)")
        print("    D) Done     (save changes)")
        print("    Q) Cancel   (discard changes)")
        print()

        sub = input("  Choice: ").strip().lower()

        if sub == "q":
            if changed:
                undo = input("  Discard unsaved changes? [y/N]: ").strip().lower()
                if undo in ("y", "yes"):
                    print("  Changes discarded.")
                    return
                continue
            print("  No changes made.")
            return

        elif sub == "d":
            if not changed:
                print("  No changes to save.")
                return
            break  # proceed to write

        elif sub == "a":
            new_dir = _prompt_required(
                "Path to add",
                hint="Absolute directory path to add to the approved sandbox",
            )
            try:
                p = Path(os.path.expandvars(new_dir)).expanduser().resolve()
                if not p.exists():
                    print(
                        f"  \u26a0  Warning: {p} does not exist — "
                        "it will be ignored at runtime."
                    )
                elif not p.is_dir():
                    print(
                        f"  \u26a0  Warning: {p} is not a directory — "
                        "it will be rejected at runtime."
                    )
                str_p = str(p)
                if str_p not in current_paths:
                    current_paths.append(str_p)
                    changed = True
                    print(f"  \u2713 Added: {p}")
                else:
                    print(f"  Already in list: {p}")
            except Exception as exc:
                print(f"  Error resolving path: {exc}")

        elif sub == "r":
            if not current_paths:
                print("  No directories in the list.")
                continue
            if len(current_paths) == 1:
                print(
                    "  Cannot remove the only directory — "
                    "at least one approved path is required."
                )
                continue
            idx_raw = input(
                f"  Remove which? (1-{len(current_paths)}, or Enter to cancel): "
            ).strip()
            if not idx_raw:
                continue
            if idx_raw.isdigit():
                idx = int(idx_raw) - 1
                if 0 <= idx < len(current_paths):
                    removed = current_paths.pop(idx)
                    changed = True
                    print(f"  \u2713 Removed: {removed}")
                else:
                    print(f"  Invalid number. Enter 1-{len(current_paths)}.")
            else:
                print("  Please enter a number.")

        elif sub == "s":
            new_raw = _prompt_required(
                "New directory list",
                hint=(
                    "Comma-separated absolute paths — this REPLACES the current list. "
                    "Example: C:\\Projects,C:\\Users\\you\\Downloads"
                ),
            )
            _, dir_warnings = _validate_directories(new_raw)
            for w in dir_warnings:
                print(w)
            if dir_warnings and dir_warnings[0].startswith("At least"):
                continue  # empty list — re-prompt
            current_paths = [p.strip() for p in new_raw.split(",") if p.strip()]
            changed = True
            print("  \u2713 List replaced.")

        else:
            print("  Please enter A, R, S, D, or Q.")

    cfg_parser["bot"]["approved_directories"] = ",".join(current_paths)
    _write_parsers(cred_parser, cfg_parser)
    _note_implicit_repo_path(cfg_parser)


def _update_bot_token(
    cred_parser: configparser.ConfigParser,
    cfg_parser: configparser.ConfigParser,
) -> None:
    """Prompt for and update the Telegram bot token."""
    current = cred_parser.get("default", "telegram_bot_token", fallback="")
    print(f"\n  Current value: {_mask(current) if current else '(not set)'}")
    new_token = _prompt_required(
        "New Telegram Bot Token",
        hint="Get from @BotFather on Telegram",
        secret=True,
    )
    cred_parser["default"]["telegram_bot_token"] = new_token
    _write_parsers(cred_parser, cfg_parser)


def _update_gemini_auth(
    cred_parser: configparser.ConfigParser,
    cfg_parser: configparser.ConfigParser,
) -> None:
    """Prompt for and update the Gemini authentication mode."""
    current_mode = cfg_parser.get("bot", "gemini_auth_mode", fallback="antigravity")
    print(f"\n  Current auth mode: {current_mode}")
    print("  How do you want to authenticate with Gemini AI?")
    print("    1) Antigravity OAuth  (recommended — browser-based, internal Google API)")
    print("    2) Gemini CLI OAuth   (browser-based, public Gemini API — no GCP project needed)")
    print("    3) Google API Key     (paste a key directly)")

    google_api_key = ""
    gemini_auth_mode = current_mode
    google_oauth_enabled = "true"

    while True:
        choice = input("  Choice (or Enter to cancel): ").strip()
        if not choice:
            print("  Auth mode unchanged.")
            return
        if choice == "1":
            gemini_auth_mode = "antigravity"
            google_oauth_enabled = "true"
            google_api_key = ""
            print("  Antigravity OAuth selected.")
            break
        elif choice == "2":
            gemini_auth_mode = "gemini-cli"
            google_oauth_enabled = "true"
            google_api_key = ""
            print("  Gemini CLI OAuth selected.")
            break
        elif choice == "3":
            gemini_auth_mode = "apikey"
            google_oauth_enabled = "false"
            google_api_key = _prompt_required(
                "Google API Key",
                hint="Get from Google AI Studio: aistudio.google.com",
                secret=True,
            )
            break
        else:
            print("  Please enter 1, 2, or 3 (or press Enter to cancel).")

    cfg_parser["bot"]["gemini_auth_mode"] = gemini_auth_mode
    cfg_parser["bot"]["google_oauth_enabled"] = google_oauth_enabled
    cred_parser["default"]["google_api_key"] = google_api_key
    _write_parsers(cred_parser, cfg_parser)

    if google_oauth_enabled == "true":
        redo_login = input("  Re-run browser OAuth login now? [y/N]: ").strip().lower()
        if redo_login in ("y", "yes"):
            _auto_oauth_login(auth_mode=gemini_auth_mode)


def _update_bot_username(
    cred_parser: configparser.ConfigParser,
    cfg_parser: configparser.ConfigParser,
) -> None:
    """Prompt for and update the Telegram bot username."""
    current = cfg_parser.get("bot", "telegram_bot_username", fallback="")
    print(f"\n  Current value: {current or '(not set)'}")
    new_val = _prompt_optional(
        "New Telegram Bot Username",
        hint="Your bot's @username (without the @ symbol)",
        default=current,
    )
    cfg_parser["bot"]["telegram_bot_username"] = new_val
    _write_parsers(cred_parser, cfg_parser)


def _update_projects_directory(
    cred_parser: configparser.ConfigParser,
    cfg_parser: configparser.ConfigParser,
) -> None:
    """Prompt for and update the default projects directory."""
    current = cfg_parser.get(
        "features", "claude_default_repo_path", fallback=str(Path.home() / "Documents")
    )
    print(f"\n  Current value: {current}")
    print(
        "  This path is also automatically added to the approved sandbox at runtime,\n"
        "  even if not listed in Approved Directories."
    )
    new_val = _prompt_optional(
        "New Default Projects Directory",
        hint="Folder where your code repositories are located",
        default=current,
    )
    cfg_parser["features"]["claude_default_repo_path"] = new_val
    _write_parsers(cred_parser, cfg_parser)
    _note_implicit_repo_path(cfg_parser)


def _update_dropbox_token(
    cred_parser: configparser.ConfigParser,
    cfg_parser: configparser.ConfigParser,
) -> None:
    """Prompt for and update the Dropbox access token."""
    current = cred_parser.get("default", "dropbox_access_token", fallback="")
    print(f"\n  Current value: {_mask(current) if current else '(not set)'}")
    new_val = _prompt_optional(
        "New Dropbox Access Token",
        hint="Only needed for large file uploads via Dropbox",
        default=current,
        secret=True,
    )
    cred_parser["default"]["dropbox_access_token"] = new_val
    _write_parsers(cred_parser, cfg_parser)


# Menu items: (label shown to user, handler function)
_SELECTIVE_MENU: list[tuple[str, object]] = [
    ("Authorized User IDs        — who can control this bot", _update_authorized_user_ids),
    ("Approved Directories       — file-system security sandbox", _update_approved_directories),
    ("Telegram Bot Token         — bot credential from @BotFather", _update_bot_token),
    ("Gemini Auth Mode           — OAuth vs API key", _update_gemini_auth),
    ("Telegram Bot Username      — your bot's @username", _update_bot_username),
    ("Default Projects Directory — used by /clauderepo and similar", _update_projects_directory),
    ("Dropbox Access Token       — for large file uploads", _update_dropbox_token),
]


def _run_selective_update() -> None:
    """
    Show a numbered menu of individual settings.

    The user picks the number of the field they want to update,
    enters the new value, and the wizard patches only that field in the
    existing config/credentials files and exits.
    Choosing 'F' runs the full reconfigure wizard.
    Pressing Enter (empty input) or 'Q' exits without changes.
    """
    print("What would you like to update?")
    print("-" * 50)
    for i, (label, _) in enumerate(_SELECTIVE_MENU, start=1):
        print(f"  {i}) {label}")
    print(f"  F) Full reconfigure (re-enter all settings from scratch)")
    print(f"  Q) Quit — no changes")
    print()

    while True:
        choice = input("  Choice: ").strip().lower()
        if not choice or choice == "q":
            print("No changes made.")
            return

        if choice == "f":
            confirm = input(
                "  This will overwrite ALL current settings. Continue? [y/N]: "
            ).strip().lower()
            if confirm in ("y", "yes"):
                _run_full_wizard()
            else:
                print("  Full reconfigure cancelled.")
            return

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(_SELECTIVE_MENU):
                _, handler = _SELECTIVE_MENU[idx]
                cred_parser, cfg_parser = _read_existing_parsers()
                handler(cred_parser, cfg_parser)  # type: ignore[operator]
                return

        print(f"  Please enter a number between 1 and {len(_SELECTIVE_MENU)}, F, or Q.")


# ---------------------------------------------------------------------------
# Public wizard entry point
# ---------------------------------------------------------------------------

def run_configure_wizard(reconfigure: bool = False) -> None:
    """
    Interactive setup wizard.

    Args:
        reconfigure: If False, exits silently when config already exists
                     (used for auto-detect on first run).
                     If True, shows current config and offers a selective
                     update menu or full reconfigure (used by 'pdagent configure').
    """
    if not reconfigure and has_config():
        return

    print("\n=== Pocket Desk Agent — Configuration Setup ===\n")

    if reconfigure and has_config():
        _show_current_config()
        _run_selective_update()
        return

    # Fresh install: run the full wizard
    _run_full_wizard()
