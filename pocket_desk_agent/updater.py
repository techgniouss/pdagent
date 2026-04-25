"""
Auto-update manager for Pocket Desk Agent.

Compares the local git HEAD against the upstream GitHub repo.
If a newer commit exists, it can pull the changes, re-install
dependencies, and signal the bot process to restart.

Public API
----------
VERSION               -> str          (semantic version of this release)
check_for_updates()   -> UpdateInfo
apply_update()        -> (success: bool, message: str)
get_version_string()  -> str          (formatted for display)
startup_update_check()-> UpdateInfo   (logs result, returns info)
update_checker_loop() -> coroutine    (periodic background checker)
"""

import asyncio
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

import requests

from pocket_desk_agent import __version__ as _PACKAGE_VERSION

logger = logging.getLogger(__name__)

# ── Version ───────────────────────────────────────────────────────────────────
# Single source of truth: pyproject.toml [project].version. Bumping it there
# propagates automatically via importlib.metadata. The git SHA is appended at
# runtime so users see both the human-readable version and exact commit.
VERSION = _PACKAGE_VERSION

# ── Repo coordinates ─────────────────────────────────────────────────────────
GITHUB_REPO = "techgniouss/pocket-desk-agent"
GITHUB_BRANCH = "main"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/commits/{GITHUB_BRANCH}"
GITHUB_COMPARE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/compare"

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"

PYPI_JSON_URL = "https://pypi.org/pypi/pocket-desk-agent/json"


def _is_git_repo() -> bool:
    """Return True if the project root is a git repository (source checkout)."""
    return (PROJECT_ROOT / ".git").is_dir()


def is_git_repo() -> bool:
    """Public alias for _is_git_repo."""
    return _is_git_repo()


def _parse_version(v: str) -> tuple:
    """Parse a semver string into a comparable tuple (major, minor, patch)."""
    try:
        return tuple(int(x) for x in v.split(".")[:3])
    except Exception:
        return (0, 0, 0)


# ── Cached state (module-level, survives across calls) ────────────────────────
_last_check_result: Optional["UpdateInfo"] = None
_last_check_time: Optional[datetime] = None


@dataclass
class UpdateInfo:
    """Result of a check-for-updates query."""
    up_to_date: bool
    local_sha: str
    remote_sha: str
    remote_message: str          # commit message of the latest remote commit
    remote_author: str
    remote_date: str
    commits_behind: int          # 0 if up-to-date or unknown
    changelog: List[str] = field(default_factory=list)   # recent commit summaries
    error: Optional[str] = None  # set when the check itself failed


# ── Git helpers ───────────────────────────────────────────────────────────────

def _run_git(*args, cwd: Path = PROJECT_ROOT) -> subprocess.CompletedProcess:
    """Run a git sub-command and return the completed process."""
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )


def get_local_sha() -> str:
    """Return the current local HEAD commit SHA (full)."""
    try:
        result = _run_git("rev-parse", "HEAD")
        return result.stdout.strip()
    except Exception as exc:
        logger.warning(f"[updater] Could not read local SHA: {exc}")
        return "unknown"


def get_local_short_sha() -> str:
    """Return the current local HEAD commit SHA (short 7-char)."""
    sha = get_local_sha()
    return sha[:7] if sha != "unknown" else sha


def get_version_string() -> str:
    """Human-readable version string: v1.0.0 (abc1234) for git, v1.0.0 for PyPI."""
    if not _is_git_repo():
        return f"v{VERSION}"
    short_sha = get_local_short_sha()
    return f"v{VERSION} ({short_sha})"


def get_local_commit_date() -> str:
    """Return the date of the local HEAD commit."""
    try:
        result = _run_git("log", "-1", "--format=%ci")
        return result.stdout.strip()
    except Exception:
        return "unknown"


# ── Update check ──────────────────────────────────────────────────────────────

def check_pypi_version() -> UpdateInfo:
    """
    Query PyPI for the latest published version of pocket-desk-agent.

    Returns an UpdateInfo where:
      - local_sha = "pypi-install"
      - remote_sha = latest version string on PyPI
      - up_to_date = True if installed version >= PyPI latest
    """
    global _last_check_result, _last_check_time

    try:
        response = requests.get(PYPI_JSON_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        latest = data["info"]["version"]
        current = VERSION

        up_to_date = _parse_version(current) >= _parse_version(latest)

        result = UpdateInfo(
            up_to_date=up_to_date,
            local_sha="pypi-install",
            remote_sha=latest,
            remote_message=f"v{latest} available on PyPI",
            remote_author="",
            remote_date="",
            commits_behind=0 if up_to_date else 1,
        )
    except requests.exceptions.ConnectionError:
        result = UpdateInfo(
            up_to_date=True,
            local_sha="pypi-install",
            remote_sha="unknown",
            remote_message="",
            remote_author="",
            remote_date="",
            commits_behind=0,
            error="No network connection — PyPI version check skipped.",
        )
    except Exception as exc:
        result = UpdateInfo(
            up_to_date=True,
            local_sha="pypi-install",
            remote_sha="unknown",
            remote_message="",
            remote_author="",
            remote_date="",
            commits_behind=0,
            error=str(exc),
        )

    _last_check_result = result
    _last_check_time = datetime.now(timezone.utc)
    return result


def check_for_updates() -> UpdateInfo:
    """
    Check PyPI for the latest published version of pocket-desk-agent.

    Always uses PyPI regardless of install type — tracks releases, not commits.
    Returns an UpdateInfo. On network errors, up_to_date=True (safe default)
    and a non-None .error field.
    """
    return check_pypi_version()


def get_last_check() -> tuple[Optional["UpdateInfo"], Optional[datetime]]:
    """Return the cached result and timestamp of the last update check."""
    return _last_check_result, _last_check_time


# ── Apply update ──────────────────────────────────────────────────────────────

def apply_update() -> tuple[bool, str]:
    """
    Pull latest changes from GitHub and re-install requirements.

    Returns (success, message).  On success the calling code should restart
    the bot (the existing reloader in main.py will handle that automatically
    once a .py file changes on disk after the pull).
    """
    if not _is_git_repo():
        return False, (
            "Cannot apply updates — installed from PyPI (no git repo).\n"
            "Use `pip install --upgrade pocket-desk-agent` to update."
        )
    try:
        # 1. Stash any local changes to avoid merge conflicts
        logger.info("[updater] Stashing local changes...")
        _run_git("stash", "--include-untracked")

        # 2. Fetch + pull
        logger.info("[updater] Running git pull…")
        pull = _run_git("pull", "origin", GITHUB_BRANCH)
        if pull.returncode != 0:
            err = pull.stderr.strip() or pull.stdout.strip()
            # Try to pop stash on failure
            _run_git("stash", "pop")
            return False, f"git pull failed:\n{err}"

        pull_output = pull.stdout.strip()
        logger.info(f"[updater] git pull output: {pull_output}")

        # Nothing changed (already up to date)
        if "Already up to date" in pull_output:
            _run_git("stash", "pop")
            return True, "✅ Already up to date — no changes were pulled."

        # 3. Re-apply stashed local changes (if any were stashed)
        logger.info("[updater] Re-applying stashed changes...")
        stash_pop = _run_git("stash", "pop")
        if stash_pop.returncode != 0:
            pop_err = stash_pop.stderr.strip()
            # "No stash entries found" is fine — means stash was a no-op
            if "No stash entries" not in pop_err:
                logger.warning(f"[updater] stash pop had issues: {pop_err}")

        # 4. Re-install dependencies (non-interactive, upgrade)
        if REQUIREMENTS_FILE.exists():
            logger.info("[updater] Re-installing dependencies…")
            pip = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r",
                 str(REQUIREMENTS_FILE), "--quiet", "--upgrade"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if pip.returncode != 0:
                logger.warning(f"[updater] pip install had warnings: {pip.stderr[:300]}")
                # Not fatal — continue

        new_sha = get_local_short_sha()
        new_version = get_version_string()

        # Count files changed
        files_changed = ""
        try:
            stat_lines = [l for l in pull_output.split("\n") if l.strip()]
            files_changed = f"\n📄 {len(stat_lines)} lines of output"
        except Exception:
            pass

        return True, (
            f"✅ Update applied successfully!\n\n"
            f"📦 New version: `{new_version}`\n"
            f"{files_changed}\n\n"
            f"🔄 The bot will restart automatically in a moment…"
        )

    except subprocess.TimeoutExpired:
        return False, "❌ Update timed out. Please try again or update manually."
    except Exception as exc:
        logger.error(f"[updater] apply_update crashed: {exc}", exc_info=True)
        return False, f"❌ Unexpected error during update: {exc}"


# ── PyPI update ───────────────────────────────────────────────────────────────

def apply_pypi_update() -> tuple[bool, str]:
    """
    Upgrade the installed package from PyPI.

    Checks PyPI first — returns (False, msg) without restarting if already
    at the latest version.  Returns (True, msg) only when a real upgrade ran.
    """
    info = check_pypi_version()
    if info.error:
        return False, f"❌ Could not reach PyPI: {info.error}"
    if info.up_to_date:
        return False, f"✅ Already on latest version `v{VERSION}`."

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pocket-desk-agent",
             "--quiet"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout).strip()[:400]
            return False, f"❌ pip upgrade failed:\n`{err}`"
        return True, f"✅ Upgraded to `v{info.remote_sha}` successfully!"
    except subprocess.TimeoutExpired:
        return False, "❌ Upgrade timed out. Run `pip install --upgrade pocket-desk-agent` manually."
    except Exception as exc:
        return False, f"❌ Unexpected error: {exc}"


# ── Startup check ─────────────────────────────────────────────────────────────

def startup_update_check() -> UpdateInfo:
    """
    Run an update check at startup and log the result.

    This is meant to be called once from main.py during bot initialization.
    """
    logger.info(f"[updater] Bot version: {get_version_string()}")
    logger.info(f"[updater] Checking for updates at startup...")

    info = check_for_updates()

    if info.error:
        logger.warning(f"[updater] Startup check failed: {info.error}")
    elif info.up_to_date:
        logger.info("[updater] ✅ Bot is up to date.")
    else:
        by = f" by {info.remote_author}" if info.remote_author else ""
        logger.info(
            f"[updater] ⚠️  Update available! "
            f"Latest: {info.remote_message}{by}"
        )

    return info


# ── Periodic background checker ──────────────────────────────────────────────

async def update_checker_loop(
    interval_seconds: int = 3600,
    notify_callback=None,
):
    """
    Background coroutine that periodically checks for updates.

    Args:
        interval_seconds: How often to check (default: 1 hour).
        notify_callback:  async callable(UpdateInfo) called when a new update
                          is detected.  Receives the UpdateInfo so the caller
                          can send Telegram notifications.
    """
    logger.info(
        f"[updater] Periodic update checker started "
        f"(interval: {interval_seconds}s / {interval_seconds // 60}min)"
    )

    _last_notified_version: Optional[str] = None

    while True:
        await asyncio.sleep(interval_seconds)

        try:
            info = check_for_updates()

            if info.error:
                logger.debug(f"[updater] Periodic check error: {info.error}")
                continue

            if not info.up_to_date:
                if info.remote_sha == _last_notified_version:
                    logger.debug(f"[updater] Already notified for v{info.remote_sha}, skipping.")
                    continue
                logger.info(f"[updater] 🔔 New update available: v{info.remote_sha}")
                _last_notified_version = info.remote_sha
                if notify_callback:
                    try:
                        await notify_callback(info)
                    except Exception as cb_err:
                        logger.error(f"[updater] Notify callback error: {cb_err}")
            else:
                _last_notified_version = None  # reset so re-notify if version bumps again
                logger.debug("[updater] Periodic check: still up to date.")

        except Exception as exc:
            logger.error(f"[updater] Periodic check crashed: {exc}", exc_info=True)


def format_update_notification(info: UpdateInfo) -> str:
    """Format an UpdateInfo into a user-friendly Telegram message."""
    msg = (
        f"🔔 *Update Available!*\n\n"
        f"📦 Installed: `v{VERSION}`\n"
        f"🆕 Latest: `v{info.remote_sha}`\n\n"
    )
    if info.remote_message:
        msg += f"💬 _{info.remote_message}_\n\n"
    msg += "⬆️ Use /update to upgrade and restart the bot."
    return msg
