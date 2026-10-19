"""Safe helpers for finding and stopping the background bot process.

The PID file can outlive the bot (crash, power loss, ``os._exit``) and the
OS may then hand that PID to an unrelated program, so a PID alone is never
enough to decide "the bot is running" or "kill this process".
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import psutil

logger = logging.getLogger(__name__)

# Substrings that identify a Pocket Desk Agent process in its command line:
# `python -m pocket_desk_agent.main` and the `pdagent` console script.
_BOT_CMDLINE_MARKERS = ("pocket_desk_agent", "pdagent")


def read_pid(pid_file: Path) -> Optional[int]:
    """Parse the PID file; None when missing or malformed."""
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def is_bot_process(pid: int) -> bool:
    """True only when ``pid`` is alive AND its command line looks like the bot."""
    if pid <= 0:
        return False
    try:
        proc = psutil.Process(pid)
        if proc.status() == psutil.STATUS_ZOMBIE:
            return False
        cmdline = " ".join(proc.cmdline()).lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
        return False
    return any(marker in cmdline for marker in _BOT_CMDLINE_MARKERS)


def running_bot_pid(pid_file: Path) -> Optional[int]:
    """PID of the running bot recorded in ``pid_file``, or None if stale/absent."""
    pid = read_pid(pid_file)
    if pid is not None and is_bot_process(pid):
        return pid
    return None


def stop_process(pid: int, timeout: float = 10.0) -> bool:
    """Terminate ``pid`` (gracefully, then forcibly) and wait until it is gone."""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=timeout)
        except psutil.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    except psutil.NoSuchProcess:
        return True
    except (psutil.AccessDenied, psutil.TimeoutExpired, OSError) as exc:
        logger.warning("Could not stop PID %s: %s", pid, exc)
        return False
    return not psutil.pid_exists(pid)


def wait_until_gone(pid: int, timeout: float = 10.0) -> bool:
    """Poll until ``pid`` no longer exists; True if it exited within ``timeout``."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not psutil.pid_exists(pid):
            return True
        time.sleep(0.1)
    return not psutil.pid_exists(pid)
