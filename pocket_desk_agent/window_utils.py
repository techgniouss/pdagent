"""Helpers for listing and activating desktop windows on Windows."""

from __future__ import annotations

import ctypes
import logging
import platform
from dataclasses import dataclass
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

_IGNORED_WINDOW_TITLES = {
    "Program Manager",
    "Start",
    "Task Switching",
    "Task View",
    "Windows Input Experience",
}


@dataclass(frozen=True)
class WindowInfo:
    """Metadata for a switchable top-level window."""

    handle: int
    title: str
    is_active: bool
    is_minimized: bool


def list_open_windows() -> list[WindowInfo]:
    """Return visible top-level windows that can be selected by the user."""
    if platform.system() != "Windows":
        raise NotImplementedError("Window switching is currently only supported on Windows.")

    try:
        import pygetwindow as gw
    except ImportError as exc:
        raise ImportError("pygetwindow is required for window switching.") from exc

    active_window = gw.getActiveWindow()
    active_handle = _window_handle(active_window)
    return build_window_inventory(gw.getAllWindows(), active_handle)


def build_window_inventory(
    windows: Iterable[object],
    active_handle: Optional[int],
) -> list[WindowInfo]:
    """Normalize raw window objects into a sorted inventory."""
    inventory: list[WindowInfo] = []
    seen_handles: set[int] = set()

    for window in windows:
        handle = _window_handle(window)
        if handle is None or handle in seen_handles:
            continue

        title = str(getattr(window, "title", "") or "").strip()
        is_visible = bool(getattr(window, "visible", True))
        is_minimized = bool(getattr(window, "isMinimized", False))
        if not _is_switchable_window(title, is_visible, is_minimized):
            continue

        inventory.append(
            WindowInfo(
                handle=handle,
                title=title,
                is_active=handle == active_handle,
                is_minimized=is_minimized,
            )
        )
        seen_handles.add(handle)

    inventory.sort(key=lambda item: (not item.is_active, item.is_minimized))
    return inventory


def format_window_inventory(windows: list[WindowInfo]) -> str:
    """Build a readable numbered list for Telegram messages."""
    lines = []
    for index, window in enumerate(windows, start=1):
        flags = []
        if window.is_active:
            flags.append("active")
        if window.is_minimized:
            flags.append("minimized")
        suffix = f" ({', '.join(flags)})" if flags else ""
        lines.append(f"{index}. {window.title}{suffix}")
    return "\n".join(lines)


def activate_window(handle: int) -> bool:
    """Restore and focus a window by native handle."""
    if platform.system() != "Windows":
        raise NotImplementedError("Window switching is currently only supported on Windows.")

    user32 = ctypes.windll.user32
    if not user32.IsWindow(handle):
        return False

    sw_restore = 9
    sw_show = 5
    if user32.IsIconic(handle):
        user32.ShowWindow(handle, sw_restore)
    else:
        user32.ShowWindow(handle, sw_show)

    user32.BringWindowToTop(handle)
    user32.SetActiveWindow(handle)
    user32.SetForegroundWindow(handle)
    if user32.GetForegroundWindow() == handle:
        return True

    _nudge_foreground_lock(user32)
    user32.BringWindowToTop(handle)
    user32.SetForegroundWindow(handle)
    if user32.GetForegroundWindow() == handle:
        return True

    if not _activate_window_with_pygetwindow(handle):
        return False

    return user32.GetForegroundWindow() == handle


def _window_handle(window: object) -> Optional[int]:
    """Best-effort extraction of a platform window handle."""
    if window is None:
        return None
    handle = getattr(window, "_hWnd", None)
    if handle is None:
        handle = getattr(window, "hWnd", None)
    if handle is None:
        return None
    try:
        return int(handle)
    except (TypeError, ValueError):
        return None


def _is_switchable_window(title: str, is_visible: bool, is_minimized: bool) -> bool:
    """Filter out shell/tool windows that should not be shown to the user."""
    cleaned = title.strip()
    if not cleaned:
        return False
    if cleaned in _IGNORED_WINDOW_TITLES:
        return False
    if not is_visible and not is_minimized:
        return False
    return True


def _nudge_foreground_lock(user32) -> None:
    """Temporarily send ALT to satisfy Windows foreground rules."""
    vk_menu = 0x12
    keyeventf_keyup = 0x0002
    try:
        user32.keybd_event(vk_menu, 0, 0, 0)
        user32.keybd_event(vk_menu, 0, keyeventf_keyup, 0)
    except Exception:
        logger.debug("Failed to nudge Windows foreground lock", exc_info=True)


def _activate_window_with_pygetwindow(handle: int) -> bool:
    """Fallback activation path through pygetwindow helpers."""
    try:
        import pygetwindow as gw
    except ImportError:
        return False

    for window in gw.getAllWindows():
        if _window_handle(window) != handle:
            continue
        try:
            if getattr(window, "isMinimized", False):
                window.restore()
            window.activate()
            return True
        except Exception:
            logger.debug("pygetwindow activation fallback failed", exc_info=True)
            return False
    return False
