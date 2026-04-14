"""
Command-line entry point for Pocket Desk Agent.

Installed as the `pdagent` console script via pyproject.toml's
[project.scripts] table. Provides subcommands for running, managing,
and authenticating the bot.

Usage:
    pdagent                   # run in foreground (default)
    pdagent run               # run in foreground
    pdagent start             # run in background
    pdagent stop              # stop the background bot
    pdagent status            # check bot status
    pdagent restart           # restart the bot
    pdagent configure         # interactive configuration wizard
    pdagent setup             # check and install system dependencies (e.g. Tesseract)
    pdagent startup status    # show automatic startup status
    pdagent startup enable    # enable automatic startup after Windows login
    pdagent startup disable   # disable automatic startup after Windows login
    pdagent startup configure # interactive autorun setup
    pdagent auth              # manage Gemini authentication
    pdagent version           # print the installed version
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _safe_print(message: str) -> None:
    """Print text without crashing on narrow Windows console encodings."""
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", errors="replace").decode("ascii"))


def _tesseract_available() -> bool:
    """Return True if the Tesseract binary is installed and reachable."""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _ensure_tesseract() -> None:
    """Check for Tesseract OCR and offer to install it via winget on Windows."""
    if _tesseract_available():
        return

    print("\nTesseract OCR is not installed.")
    print("It is required for OCR commands (/findtext, /smartclick, UI automation).")

    if sys.platform == "win32":
        answer = input("Install via winget now? [Y/n]: ").strip().lower()
        if answer in ("", "y", "yes"):
            print("Installing Tesseract OCR via winget...")
            result = subprocess.run(
                [
                    "winget", "install", "UB-Mannheim.TesseractOCR",
                    "--silent",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ],
                check=False,
            )
            if result.returncode == 0:
                print("Tesseract OCR installed successfully.")
                print("You may need to restart your terminal for PATH changes to take effect.")
            else:
                print("winget install failed. Install manually:")
                print("  https://github.com/UB-Mannheim/tesseract/wiki")
        else:
            print("Skipping. OCR features will be unavailable until Tesseract is installed.")
            print("  Install manually: winget install UB-Mannheim.TesseractOCR")
    elif sys.platform == "darwin":
        print("Install via Homebrew:  brew install tesseract")
    else:
        print("Install via apt:  sudo apt-get install tesseract-ocr")


def _run_foreground() -> int:
    """Run the bot attached to the current terminal."""
    _auto_configure()
    from pocket_desk_agent.main import main as bot_main
    bot_main()
    return 0


def _run_background() -> int:
    """Spawn the bot in the background and return immediately."""
    log_file = Path.cwd() / "bot.log"
    creationflags = 0
    child_env = dict(os.environ)
    child_env["PDAGENT_ENABLE_RELOADER"] = "0"
    if sys.platform == "win32":
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )

    _auto_configure()
    with open(log_file, "ab") as log:
        subprocess.Popen(
            [sys.executable, "-m", "pocket_desk_agent.main"],
            stdout=log,
            stderr=log,
            stdin=subprocess.DEVNULL,
            env=child_env,
            creationflags=creationflags,
            close_fds=True,
        )
    _safe_print(f"Pocket Desk Agent started in background. Logs: {log_file}")
    return 0


def _auto_configure() -> None:
    """Auto-trigger the setup wizard and system dependency check on first run."""
    from pocket_desk_agent.configure import has_config, run_configure_wizard
    _cwd_env = Path.cwd() / ".env"
    _home_env = Path.home() / ".pdagent" / ".env"
    if not has_config() and not _cwd_env.exists() and not _home_env.exists():
        run_configure_wizard(reconfigure=False)
        _ensure_tesseract()


def _configure() -> int:
    """Run the interactive configuration wizard."""
    from pocket_desk_agent.configure import run_configure_wizard
    run_configure_wizard(reconfigure=True)
    return 0


def _stop() -> int:
    """Stop the background bot via the PID file."""
    try:
        from scripts.manage_service import stop_bot  # type: ignore
    except ImportError:
        # When installed from PyPI the scripts/ dir isn't packaged, so
        # fall back to reading the PID file directly.
        return _stop_via_pidfile()
    stop_bot()
    return 0


def _stop_via_pidfile() -> int:
    """Fallback stop implementation that doesn't depend on scripts/."""
    import os
    import signal

    pid_file = Path.home() / ".pdagent" / "bot.pid"
    if not pid_file.exists():
        print("X No PID file found. Is the bot running?")
        return 1
    try:
        pid = int(pid_file.read_text().strip())
    except Exception as exc:
        print(f"❌ Could not read PID file: {exc}")
        return 1

    try:
        if sys.platform == "win32":
            import subprocess
            subprocess.run(
                ["taskkill", "/pid", str(pid), "/f"], check=False,
            )
        else:
            os.kill(pid, signal.SIGTERM)
        pid_file.unlink(missing_ok=True)
        print(f"✅ Bot stopped (PID {pid}).")
        return 0
    except Exception as exc:
        print(f"❌ Error stopping bot: {exc}")
        return 1


def _status() -> int:
    """Print whether the bot is currently running."""
    pid_file = Path.home() / ".pdagent" / "bot.pid"
    if not pid_file.exists():
        print("Status: 🛑 NOT RUNNING")
        return 0
    try:
        pid = int(pid_file.read_text().strip())
        print(f"Status: 🚀 RUNNING (PID {pid})")
    except Exception:
        print("Status: ❓ UNKNOWN (could not read PID file)")
    return 0


def _restart() -> int:
    """Stop then start the bot in the background."""
    _stop()
    return _run_background()


def _auth() -> int:
    """Run the interactive authentication manager."""
    try:
        from scripts.manage_auth import manage_auth  # type: ignore
        manage_auth()
        return 0
    except ImportError:
        pass

    # Fallback for PyPI installs — run the OAuth flow directly
    from pocket_desk_agent.config import Config
    from pocket_desk_agent.constants import AUTH_MODE_GEMINI_CLI, AUTH_MODE_APIKEY

    if Config.GEMINI_AUTH_MODE == AUTH_MODE_APIKEY:
        print("Bot is configured to use API Key. Authentication via OAuth is not needed.")
        return 0

    if Config.GEMINI_AUTH_MODE == AUTH_MODE_GEMINI_CLI:
        from pocket_desk_agent.gemini_cli_auth import GeminiCLIOAuth
        oauth = GeminiCLIOAuth()
        mode_name = "Gemini CLI OAuth"
    else:
        from pocket_desk_agent.antigravity_auth import AntigravityOAuth
        oauth = AntigravityOAuth()
        mode_name = "Antigravity OAuth"

    print("=" * 50)
    print(f"POCKET DESK AGENT — AUTHENTICATION ({mode_name})")
    print("=" * 50)
    print("\n1. Login (Authenticate)")
    print("2. Check Status")
    print("3. Logout")
    print("4. Exit")

    choice = input("\nEnter choice (1-4): ").strip()

    if choice == "1":
        print(f"\nThis will open your browser for {mode_name} authentication.")
        input("Press Enter to continue...")
        success = oauth.start_login_flow()
        if success and oauth.is_authenticated():
            print(f"\n✅ LOGIN SUCCESSFUL — {oauth.email}")
            if getattr(oauth, 'project_id', None):
                print(f"Project: {oauth.project_id}")
        else:
            print("\n❌ LOGIN FAILED — please try again.")
    elif choice == "2":
        if oauth.load_saved_tokens():
            print(f"\n✅ Authenticated as {oauth.email}")
            if getattr(oauth, 'project_id', None):
                print(f"Project: {oauth.project_id}")
        else:
            print("\n❌ Not authenticated. Run option 1 to login.")
    elif choice == "3":
        oauth.logout()
        print("\n✅ Logged out.")
    else:
        print("Goodbye!")
    return 0


def _startup_status() -> int:
    """Print automatic startup status."""
    from pocket_desk_agent.startup_manager import StartupManager

    manager = StartupManager()
    status = manager.get_status()
    print(status.message)
    if status.details:
        print()
        for detail in status.details:
            print(f"- {detail}")
    if status.supported:
        print()
        print(
            "Windows Service mode is not currently offered. Pocket Desk Agent's "
            "screenshot, OCR, Claude Desktop, and VS Code automation features "
            "require the logged-in desktop session."
        )
    return 1 if status.state == "broken" else 0


def _startup_enable() -> int:
    """Enable automatic startup after Windows login."""
    from pocket_desk_agent.startup_manager import StartupManager

    manager = StartupManager()
    success, message = manager.enable_startup()
    print(message)
    if success:
        print()
        print(
            "Pocket Desk Agent will start automatically in the background after "
            "you sign in to Windows. This is not a Windows Service."
        )
    return 0 if success else 1


def _startup_disable() -> int:
    """Disable automatic startup after Windows login."""
    from pocket_desk_agent.startup_manager import StartupManager

    manager = StartupManager()
    success, message = manager.disable_startup()
    print(message)
    return 0 if success else 1


def _startup_configure() -> int:
    """Interactively configure automatic startup."""
    from pocket_desk_agent.startup_manager import StartupManager

    manager = StartupManager()
    return manager.configure_interactive()


def _setup() -> int:
    """Check and install system dependencies (e.g. Tesseract OCR)."""
    _ensure_tesseract()
    return 0


def _version() -> int:
    """Print the installed version and check PyPI for a newer release."""
    from pocket_desk_agent import __version__
    print(f"pdagent {__version__}")
    try:
        from pocket_desk_agent.updater import check_for_updates
        info = check_for_updates()
        if not info.up_to_date and not info.error:
            if info.local_sha == "pypi-install":
                # PyPI install — remote_sha is a version string
                print(f"\nA newer version is available: v{info.remote_sha}")
                print("Upgrade with:  pip install --upgrade pocket-desk-agent")
                print("Then restart:  pdagent restart")
            else:
                # Git checkout — remote_sha is a commit hash
                print(f"\nA newer commit is available ({info.commits_behind} commit(s) behind).")
                print("Update with:   /update in Telegram, or git pull && pip install -e .")
    except Exception:
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point dispatched by the `pdagent` console script."""
    parser = argparse.ArgumentParser(
        prog="pdagent",
        description="Pocket Desk Agent — secure Telegram remote control for your PC.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("run", help="Run the bot attached to the current terminal (default)")
    sub.add_parser("start", help="Run the bot in the background")
    sub.add_parser("stop", help="Stop the background bot")
    sub.add_parser("status", help="Check whether the bot is running")
    sub.add_parser("restart", help="Restart the bot in the background")
    sub.add_parser("configure", help="Run the interactive configuration wizard")
    sub.add_parser("setup", help="Check and install system dependencies (e.g. Tesseract OCR)")
    startup = sub.add_parser(
        "startup",
        help="Manage automatic startup after Windows login",
    )
    startup_sub = startup.add_subparsers(dest="startup_command")
    startup_sub.add_parser("enable", help="Enable automatic startup after Windows login")
    startup_sub.add_parser("disable", help="Disable automatic startup after Windows login")
    startup_sub.add_parser("status", help="Show automatic startup status")
    startup_sub.add_parser("configure", help="Interactively configure automatic startup")
    sub.add_parser("auth", help="Manage Gemini authentication tokens")
    sub.add_parser("version", help="Print the installed version")

    args = parser.parse_args(argv)

    if args.command == "startup":
        startup_dispatch = {
            "enable": _startup_enable,
            "disable": _startup_disable,
            "status": _startup_status,
            "configure": _startup_configure,
            None: lambda: startup.print_help() or 0,
        }
        return startup_dispatch[args.startup_command]()

    dispatch = {
        None: _run_foreground,
        "run": _run_foreground,
        "start": _run_background,
        "stop": _stop,
        "status": _status,
        "restart": _restart,
        "configure": _configure,
        "setup": _setup,
        "auth": _auth,
        "version": _version,
    }

    return dispatch[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
