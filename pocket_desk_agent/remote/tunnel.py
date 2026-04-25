"""Cloudflared quick-tunnel supervisor.

Spawns ``cloudflared tunnel --url http://127.0.0.1:<port> --no-autoupdate``
and captures the ``trycloudflare.com`` URL from its output. Free, no
account, HTTPS, supports WebSocket upgrades — ideal for /remote.

The binary itself is NOT bundled or downloaded. Users install it once
via ``winget install Cloudflare.cloudflared`` or point ``CLOUDFLARED_PATH``
at an existing install. See ``docs/REMOTE.md``.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from pocket_desk_agent.config import Config

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
_URL_WAIT_SECS = 25.0
_READY_WAIT_SECS = 8.0
_START_MAX_ATTEMPTS = 2
_START_RETRY_BACKOFF_SECS = 1.0
_READY_PATTERNS = (
    re.compile(r"registered tunnel connection", re.IGNORECASE),
    re.compile(r"connection .* registered", re.IGNORECASE),
    re.compile(r"connected to .*cloudflare", re.IGNORECASE),
)
_CANDIDATE_PATHS = (
    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
    r"C:\Program Files\cloudflared\cloudflared.exe",
)
_LOG_DRAIN_TASKS: dict[int, asyncio.Task[None]] = {}


class CloudflaredMissingError(RuntimeError):
    """Raised when the cloudflared binary cannot be found."""


def _discover_binary() -> Optional[str]:
    """Find cloudflared from PATH or common Windows install locations."""
    found = shutil.which("cloudflared")
    if found:
        return found

    search = list(_CANDIDATE_PATHS)
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        search.append(
            str(Path(local_appdata) / "Microsoft" / "WinGet" / "Links" / "cloudflared.exe")
        )

    for candidate in search:
        if Path(candidate).is_file():
            return candidate
    return None


def resolve_binary() -> str:
    """Return the path to the cloudflared binary or raise."""
    if Config.CLOUDFLARED_PATH:
        configured = Config.CLOUDFLARED_PATH
        if Path(configured).is_file():
            return configured
        if shutil.which(configured):
            return configured
        logger.warning(
            "[remote] CLOUDFLARED_PATH='%s' is not executable; trying PATH.",
            configured,
        )

    found = _discover_binary()
    if found:
        Config.CLOUDFLARED_PATH = found
        return found

    raise CloudflaredMissingError(
        "cloudflared binary not found. Install it with "
        "`winget install Cloudflare.cloudflared` or set CLOUDFLARED_PATH."
    )


async def start_quick_tunnel(port: int) -> tuple[asyncio.subprocess.Process, str]:
    """Spawn cloudflared and return (process, public_url).

    Caller is responsible for ``await stop_tunnel(proc)`` on teardown or
    on any failure further along the start path.
    """
    binary = resolve_binary()
    for attempt in range(1, _START_MAX_ATTEMPTS + 1):
        proc = await _spawn_tunnel_process(binary, port)
        try:
            url, ready = await _read_url_and_ready(proc, _URL_WAIT_SECS, _READY_WAIT_SECS)
        except Exception as exc:
            await stop_tunnel(proc)
            if attempt >= _START_MAX_ATTEMPTS:
                raise RuntimeError(
                    f"cloudflared failed to initialize quick tunnel: {exc}"
                ) from exc
            logger.warning(
                "[remote] cloudflared start attempt %d/%d failed (%s); retrying",
                attempt,
                _START_MAX_ATTEMPTS,
                exc,
            )
            await asyncio.sleep(_START_RETRY_BACKOFF_SECS * attempt)
            continue

        if proc.returncode is not None:
            await stop_tunnel(proc)
            if attempt >= _START_MAX_ATTEMPTS:
                raise RuntimeError("cloudflared exited before tunnel became stable.")
            logger.warning(
                "[remote] cloudflared exited early on attempt %d/%d; retrying",
                attempt,
                _START_MAX_ATTEMPTS,
            )
            await asyncio.sleep(_START_RETRY_BACKOFF_SECS * attempt)
            continue

        if not ready and attempt < _START_MAX_ATTEMPTS:
            logger.warning(
                "[remote] quick tunnel URL was created but edge readiness was not confirmed "
                "on attempt %d/%d; restarting tunnel",
                attempt,
                _START_MAX_ATTEMPTS,
            )
            await stop_tunnel(proc)
            await asyncio.sleep(_START_RETRY_BACKOFF_SECS * attempt)
            continue

        if not ready:
            logger.warning(
                "[remote] quick tunnel readiness signal missing on final attempt; "
                "continuing with URL anyway"
            )
        _start_log_drain(proc)
        return proc, url

    raise RuntimeError("cloudflared failed to initialize quick tunnel.")


async def _spawn_tunnel_process(binary: str, port: int) -> asyncio.subprocess.Process:
    """Spawn the cloudflared subprocess for a local HTTP target."""
    return await asyncio.create_subprocess_exec(
        binary,
        "tunnel",
        "--url",
        f"http://127.0.0.1:{port}",
        "--no-autoupdate",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )


def _line_has_ready_signal(line: str) -> bool:
    """Return True when a cloudflared output line indicates edge readiness."""
    return any(pattern.search(line) for pattern in _READY_PATTERNS)


async def _read_output_line(proc: asyncio.subprocess.Process, timeout_secs: float) -> Optional[str]:
    """Read and decode one cloudflared output line with timeout.

    Returns:
    - ``None`` on timeout
    - ``""`` on EOF
    - decoded line otherwise
    """
    assert proc.stdout is not None
    try:
        line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout_secs)
    except asyncio.TimeoutError:
        return None
    if not line_bytes:
        return ""
    line = line_bytes.decode("utf-8", errors="replace").strip()
    if line:
        logger.debug("[remote][cloudflared] %s", line)
    return line


async def _read_url_and_ready(
    proc: asyncio.subprocess.Process, url_timeout_secs: float, ready_timeout_secs: float
) -> tuple[str, bool]:
    """Read cloudflared output until URL is found, then wait briefly for readiness."""
    loop = asyncio.get_running_loop()
    url_deadline = loop.time() + url_timeout_secs
    url: Optional[str] = None
    ready = False

    while url is None:
        remaining = url_deadline - loop.time()
        if remaining <= 0:
            raise RuntimeError(
                f"cloudflared did not produce a tunnel URL within {url_timeout_secs:.0f}s."
            )
        line = await _read_output_line(proc, max(0.1, remaining))
        if line is None:
            continue
        if line == "":
            raise RuntimeError("cloudflared closed output without producing a URL.")

        if _line_has_ready_signal(line):
            ready = True
        match = _URL_PATTERN.search(line)
        if match:
            url = match.group(0)

    if ready:
        return url, True

    ready_deadline = loop.time() + ready_timeout_secs
    while loop.time() < ready_deadline:
        remaining = ready_deadline - loop.time()
        line = await _read_output_line(proc, max(0.1, remaining))
        if line is None:
            continue
        if line == "":
            break
        if _line_has_ready_signal(line):
            return url, True
        # cloudflared may print a newer URL line in rare retries; keep the latest one.
        match = _URL_PATTERN.search(line)
        if match:
            url = match.group(0)

    return url, False


def _start_log_drain(proc: asyncio.subprocess.Process) -> None:
    """Drain cloudflared stdout in the background after URL capture."""
    if proc.stdout is None:
        return
    key = id(proc)
    if key in _LOG_DRAIN_TASKS:
        return

    async def _drain() -> None:
        try:
            while True:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    return
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if line:
                    logger.debug("[remote][cloudflared] %s", line)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.debug("[remote] cloudflared log drain stopped: %s", exc)
        finally:
            _LOG_DRAIN_TASKS.pop(key, None)

    _LOG_DRAIN_TASKS[key] = asyncio.create_task(_drain())


async def _stop_log_drain(proc: asyncio.subprocess.Process) -> None:
    """Cancel and await the per-process log-drain task, if any."""
    task = _LOG_DRAIN_TASKS.pop(id(proc), None)
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


async def stop_tunnel(proc: asyncio.subprocess.Process) -> None:
    """Gracefully stop cloudflared. Force-kills after a timeout."""
    await _stop_log_drain(proc)
    if proc.returncode is not None:
        return
    try:
        proc.terminate()
    except ProcessLookupError:
        return
    except Exception as exc:
        logger.debug("[remote] terminate raised: %s", exc)

    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception as exc:
            logger.debug("[remote] kill raised: %s", exc)
        try:
            await asyncio.wait_for(proc.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            logger.warning("[remote] cloudflared did not exit after kill.")
