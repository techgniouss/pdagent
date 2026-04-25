"""Helpers to auto-install the cloudflared binary on Windows via winget.

Used by the ``/remote`` flow: if cloudflared is missing, the bot prompts
the user for approval and then calls :func:`winget_install_cloudflared`.

After a successful install the winget-installed binary is written into
``Config.CLOUDFLARED_PATH`` for the current process, since the current
process's PATH is frozen at startup and will not pick up the new entry.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import shutil
from pathlib import Path
from typing import Optional

from pocket_desk_agent.config import Config

logger = logging.getLogger(__name__)

_WINGET_TIMEOUT_SECS = 300.0

_CANDIDATE_PATHS = (
    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
    r"C:\Program Files\cloudflared\cloudflared.exe",
)


def find_installed_binary() -> Optional[str]:
    """Probe known install locations for cloudflared.exe.

    Needed after a fresh ``winget install`` because the current Python
    process's PATH was resolved at startup and does not pick up the new
    install directory.
    """
    found = shutil.which("cloudflared")
    if found:
        return found

    local_appdata = os.environ.get("LOCALAPPDATA")
    search = list(_CANDIDATE_PATHS)
    if local_appdata:
        search.append(
            str(Path(local_appdata) / "Microsoft" / "WinGet" / "Links" / "cloudflared.exe")
        )
    for candidate in search:
        if Path(candidate).is_file():
            return candidate
    return None


def winget_available() -> bool:
    return shutil.which("winget") is not None


async def winget_install_cloudflared() -> tuple[bool, str]:
    """Run ``winget install Cloudflare.cloudflared`` and return (ok, msg).

    Sets ``Config.CLOUDFLARED_PATH`` on success so the already-running
    process can locate the new binary without a restart.
    """
    if platform.system() != "Windows":
        return False, "Auto-install via winget is only supported on Windows."

    already_installed = find_installed_binary()
    if already_installed:
        Config.CLOUDFLARED_PATH = already_installed
        logger.info("[remote] cloudflared already present at %s", already_installed)
        return True, already_installed

    if not winget_available():
        return (
            False,
            "winget is not available on this system. Install cloudflared manually "
            "from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/",
        )

    cmd = [
        "winget",
        "install",
        "--id",
        "Cloudflare.cloudflared",
        "-e",
        "--accept-source-agreements",
        "--accept-package-agreements",
        "--silent",
    ]

    logger.info("[remote] running winget install for cloudflared")
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except FileNotFoundError:
        return False, "winget binary disappeared before we could run it."
    except Exception as exc:
        logger.exception("[remote] winget spawn failed")
        return False, f"Could not launch winget: {exc}"

    try:
        stdout_bytes, _ = await asyncio.wait_for(
            proc.communicate(), timeout=_WINGET_TIMEOUT_SECS
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return False, "winget install timed out after 5 minutes. Try installing manually."

    output = (stdout_bytes or b"").decode("utf-8", errors="replace").strip()
    logger.debug("[remote][winget] exit=%s output=%s", proc.returncode, output)

    if proc.returncode != 0:
        # Some winget states return non-zero even when the package is present.
        resolved = find_installed_binary()
        if resolved:
            Config.CLOUDFLARED_PATH = resolved
            logger.info(
                "[remote] winget returned exit=%s but cloudflared exists at %s",
                proc.returncode,
                resolved,
            )
            return True, resolved
        tail = output[-400:] if output else "(no output captured)"
        return (
            False,
            f"winget install failed (exit {proc.returncode}). Output tail:\n{tail}",
        )

    resolved = find_installed_binary()
    if not resolved:
        return (
            False,
            "winget reported success but cloudflared.exe could not be located. "
            "Try restarting the bot, or set CLOUDFLARED_PATH manually.",
        )

    Config.CLOUDFLARED_PATH = resolved
    logger.info("[remote] cloudflared installed at %s", resolved)
    return True, resolved
