"""Launch and close helpers for catalog-backed desktop applications."""

from __future__ import annotations

import ctypes
import os
import platform
import time
from dataclasses import dataclass, field

import psutil

from pocket_desk_agent.app_catalog import DesktopAppEntry, normalize_app_name

if hasattr(os, "startfile"):
    _startfile = os.startfile
else:
    def _startfile(_target: str) -> None:
        raise NotImplementedError("os.startfile is unavailable on this platform.")


@dataclass
class CloseAppResult:
    """Outcome of a graceful or force close attempt."""

    success: bool
    message: str
    requires_force: bool = False
    remaining_process_ids: list[int] = field(default_factory=list)


def launch_desktop_app(entry: DesktopAppEntry) -> tuple[bool, str]:
    """Launch one vetted desktop app entry."""
    if platform.system() != "Windows":
        return False, "Desktop app launching is currently only supported on Windows."

    try:
        _startfile(entry.launch_target)
        return True, f"Opening {entry.display_name}."
    except Exception as exc:
        return False, f"Failed to open {entry.display_name}: {exc}"


def close_desktop_app(entry: DesktopAppEntry, force: bool = False) -> CloseAppResult:
    """Close one desktop app, preferring graceful window close first."""
    if platform.system() != "Windows":
        return CloseAppResult(False, "Desktop app closing is currently only supported on Windows.")

    process_ids = _find_matching_process_ids(entry)
    window_handles = _find_matching_window_handles(entry)

    if not process_ids and not window_handles:
        return CloseAppResult(True, f"{entry.display_name} does not appear to be running.")

    if force:
        remaining = _terminate_process_ids(process_ids)
        if remaining:
            return CloseAppResult(
                False,
                f"Force-close attempted for {entry.display_name}, but some processes are still running.",
                requires_force=False,
                remaining_process_ids=remaining,
            )
        return CloseAppResult(True, f"Force-closed {entry.display_name}.")

    closed_windows = 0
    for handle in window_handles:
        if _close_window_handle(handle):
            closed_windows += 1

    if closed_windows:
        time.sleep(0.2)

    remaining = _find_matching_process_ids(entry)
    if remaining:
        if closed_windows == 0:
            message = (
                f"No closable window was found for {entry.display_name}, "
                "but matching processes are still running."
            )
        else:
            message = (
                f"Closed {closed_windows} window(s) for {entry.display_name}, "
                "but the app is still running."
            )
        return CloseAppResult(
            True,
            message,
            requires_force=True,
            remaining_process_ids=remaining,
        )
    return CloseAppResult(True, f"Closed {entry.display_name}.")


def _find_matching_window_handles(entry: DesktopAppEntry) -> list[int]:
    """Find visible windows whose titles likely belong to the app."""
    try:
        from pocket_desk_agent.window_utils import list_open_windows
    except Exception:
        return []

    try:
        windows = list_open_windows()
    except Exception:
        return []

    normalized_names = _candidate_names(entry)
    handles: list[int] = []
    for window in windows:
        window_title = normalize_app_name(window.title)
        if any(name in window_title for name in normalized_names):
            handles.append(window.handle)
    return handles


def _find_matching_process_ids(entry: DesktopAppEntry) -> list[int]:
    """Find process IDs that likely belong to the app."""
    normalized_names = _candidate_names(entry)
    process_ids: list[int] = []

    for process in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            fields = [
                process.info.get("name") or "",
                process.info.get("exe") or "",
                " ".join(process.info.get("cmdline") or []),
            ]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

        searchable = normalize_app_name(" ".join(fields))
        if any(name in searchable for name in normalized_names):
            process_ids.append(int(process.info["pid"]))

    return sorted(set(process_ids))


def _close_window_handle(handle: int) -> bool:
    """Send a polite close request to one top-level window."""
    try:
        user32 = ctypes.windll.user32
        wm_close = 0x0010
        if not user32.IsWindow(handle):
            return False
        user32.PostMessageW(handle, wm_close, 0, 0)
        return True
    except Exception:
        return False


def _terminate_process_ids(process_ids: list[int]) -> list[int]:
    """Terminate process IDs and return any that remain alive."""
    remaining: list[int] = []
    for pid in process_ids:
        try:
            process = psutil.Process(pid)
            process.terminate()
            try:
                process.wait(timeout=2)
            except psutil.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            try:
                if psutil.pid_exists(pid):
                    remaining.append(pid)
            except Exception:
                remaining.append(pid)
    return remaining


def _candidate_names(entry: DesktopAppEntry) -> list[str]:
    """Return normalized names used for process and window matching."""
    candidates = [normalize_app_name(entry.display_name)]
    candidates.extend(normalize_app_name(alias) for alias in entry.aliases)
    candidates.extend(normalize_app_name(hint) for hint in entry.process_hints)
    return [candidate for candidate in dict.fromkeys(candidates) if candidate]
