"""Desktop app adapter helpers for UI automation features.

This module centralizes "how do we find and activate app X?" logic so
watchers and workflow recipes can reuse consistent behavior.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DesktopAdapter:
    """Represents one desktop app target used by automation commands."""

    key: str
    title: str
    find_window: Callable[[], object | None]


def _find_claude_window() -> object | None:
    from pocket_desk_agent.handlers.claude import find_claude_window

    return find_claude_window()


def _find_antigravity_window() -> object | None:
    from pocket_desk_agent.handlers.antigravity import find_antigravity_window

    return find_antigravity_window()


_ADAPTERS: dict[str, DesktopAdapter] = {
    "claude": DesktopAdapter(
        key="claude",
        title="Claude Desktop",
        find_window=_find_claude_window,
    ),
    "antigravity": DesktopAdapter(
        key="antigravity",
        title="Antigravity",
        find_window=_find_antigravity_window,
    ),
}


def get_desktop_adapter(key: str) -> Optional[DesktopAdapter]:
    """Return a desktop adapter by key."""
    return _ADAPTERS.get((key or "").strip().lower())


def list_desktop_adapters() -> list[str]:
    """Return sorted adapter keys."""
    return sorted(_ADAPTERS.keys())


def find_adapter_window(key: str) -> object | None:
    """Locate the target window for the requested adapter."""
    adapter = get_desktop_adapter(key)
    if not adapter:
        return None
    try:
        return adapter.find_window()
    except Exception as exc:
        logger.debug("Window lookup failed for adapter %s: %s", key, exc)
        return None


async def activate_adapter_window(window: object) -> bool:
    """Best-effort restore+activate helper for pygetwindow-like objects."""
    try:
        if getattr(window, "isMinimized", False):
            window.restore()
            await asyncio.sleep(0.4)
        window.activate()
        await asyncio.sleep(0.3)
        return True
    except Exception as exc:
        logger.debug("Window activation skipped: %s", exc)
        return False


def window_region(window: object) -> Optional[tuple[int, int, int, int]]:
    """Return (left, top, width, height) for a window object."""
    try:
        left = max(0, int(getattr(window, "left")))
        top = max(0, int(getattr(window, "top")))
        width = max(1, int(getattr(window, "width")))
        height = max(1, int(getattr(window, "height")))
    except Exception:
        return None
    return left, top, width, height
