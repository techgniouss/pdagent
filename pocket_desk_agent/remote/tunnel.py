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
import re
import shutil
from typing import Optional

from pocket_desk_agent.config import Config

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
_URL_WAIT_SECS = 25.0


class CloudflaredMissingError(RuntimeError):
    """Raised when the cloudflared binary cannot be found."""


def resolve_binary() -> str:
    """Return the path to the cloudflared binary or raise."""
    if Config.CLOUDFLARED_PATH:
        configured = Config.CLOUDFLARED_PATH
        if shutil.which(configured):
            return configured
        logger.warning(
            "[remote] CLOUDFLARED_PATH='%s' is not executable; trying PATH.",
            configured,
        )

    found = shutil.which("cloudflared")
    if found:
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

    proc = await asyncio.create_subprocess_exec(
        binary,
        "tunnel",
        "--url",
        f"http://127.0.0.1:{port}",
        "--no-autoupdate",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    url: Optional[str] = None
    try:
        url = await asyncio.wait_for(_read_url(proc), timeout=_URL_WAIT_SECS)
    except asyncio.TimeoutError:
        await stop_tunnel(proc)
        raise RuntimeError(
            "cloudflared did not produce a tunnel URL within 25s. "
            "Check outbound network access."
        )

    if proc.returncode is not None and not url:
        await stop_tunnel(proc)
        raise RuntimeError("cloudflared exited before reporting a URL.")

    return proc, url


async def _read_url(proc: asyncio.subprocess.Process) -> str:
    """Read cloudflared stdout line-by-line until a trycloudflare URL appears."""
    assert proc.stdout is not None
    while True:
        line_bytes = await proc.stdout.readline()
        if not line_bytes:
            raise RuntimeError("cloudflared closed output without producing a URL.")
        line = line_bytes.decode("utf-8", errors="replace").strip()
        if line:
            logger.debug("[remote][cloudflared] %s", line)
        match = _URL_PATTERN.search(line)
        if match:
            return match.group(0)


async def stop_tunnel(proc: asyncio.subprocess.Process) -> None:
    """Gracefully stop cloudflared. Force-kills after a timeout."""
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
