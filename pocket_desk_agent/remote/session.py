"""RemoteSession state container.

Holds the per-user live remote-desktop session: token, bound port, tunnel
URL, child process handles, WebSocket connections, and the fingerprint
used to lock the session to the first browser that loads it.

Keeping this in its own module (rather than ``handlers/_shared.py``)
makes the remote feature self-contained — no existing singleton changes.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

ACTIVE_SESSIONS: dict[int, "RemoteSession"] = {}


@dataclass
class RemoteSession:
    user_id: int
    chat_id: int
    token: str
    port: int
    tunnel_url: str = ""
    started_at: float = field(default_factory=time.time)
    last_input_at: float = field(default_factory=time.time)

    fps: int = 10
    quality: int = 60
    max_width: int = 1280

    server_runner: Any = None
    server_site: Any = None
    tunnel_proc: Any = None
    watchdog_task: Optional[asyncio.Task] = None
    capture_task_refs: set[asyncio.Task] = field(default_factory=set)

    bound_fingerprint: Optional[tuple[str, str]] = None
    active_ws: set[Any] = field(default_factory=set)

    torn_down: bool = False

    @classmethod
    def create(
        cls,
        user_id: int,
        chat_id: int,
        port: int,
        fps: int,
        quality: int,
        max_width: int,
    ) -> "RemoteSession":
        session = cls(
            user_id=user_id,
            chat_id=chat_id,
            token=secrets.token_urlsafe(32),
            port=port,
            fps=fps,
            quality=quality,
            max_width=max_width,
        )
        ACTIVE_SESSIONS[user_id] = session
        return session

    def touch(self) -> None:
        self.last_input_at = time.time()

    def idle_seconds(self) -> float:
        return time.time() - self.last_input_at

    def update_config(
        self,
        *,
        fps: Optional[int] = None,
        quality: Optional[int] = None,
        max_width: Optional[int] = None,
    ) -> None:
        if fps is not None:
            self.fps = max(2, min(20, int(fps)))
        if quality is not None:
            self.quality = max(30, min(85, int(quality)))
        if max_width is not None:
            self.max_width = max(640, min(1920, int(max_width)))


def get_for_user(user_id: int) -> Optional[RemoteSession]:
    session = ACTIVE_SESSIONS.get(user_id)
    if session and session.torn_down:
        ACTIVE_SESSIONS.pop(user_id, None)
        return None
    return session


async def teardown(session: RemoteSession) -> None:
    """Idempotent teardown: stop WS, server, tunnel; drop from registry.

    Each step is wrapped so a failure in one does not prevent the others
    from running — the goal is to leave no orphan process/port/state.
    """
    if session.torn_down:
        return
    session.torn_down = True

    for ws in list(session.active_ws):
        try:
            await ws.close()
        except Exception as exc:
            logger.debug("[remote] ws close failed: %s", exc)
    session.active_ws.clear()

    for task in list(session.capture_task_refs):
        try:
            task.cancel()
        except Exception:
            pass
    session.capture_task_refs.clear()

    if session.watchdog_task is not None:
        try:
            session.watchdog_task.cancel()
        except Exception:
            pass

    if session.server_site is not None:
        try:
            await session.server_site.stop()
        except Exception as exc:
            logger.debug("[remote] site stop failed: %s", exc)

    if session.server_runner is not None:
        try:
            await session.server_runner.cleanup()
        except Exception as exc:
            logger.debug("[remote] runner cleanup failed: %s", exc)

    if session.tunnel_proc is not None:
        try:
            from pocket_desk_agent.remote.tunnel import stop_tunnel

            await stop_tunnel(session.tunnel_proc)
        except Exception as exc:
            logger.debug("[remote] tunnel stop failed: %s", exc)

    ACTIVE_SESSIONS.pop(session.user_id, None)
    logger.info("[remote] session %s torn down", session.user_id)
