"""Translate remote browser events into pyautogui input on the host.

Events are JSON dicts emitted by the viewer on ``/ws/input``. Coordinates
arrive normalized (0..1); we multiply by the live screen size so window
resolution changes mid-session are handled.

Exceptions are swallowed: a bad event must never kill the input loop. A
rate limiter caps at 200 events/sec to defeat a spammy client. pyautogui
fail-safe (cursor in corner) is caught and surfaced via ``last_failsafe``
so the handler can notify the user once without flooding chat.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from pocket_desk_agent.remote.session import RemoteSession

logger = logging.getLogger(__name__)

_RATE_LIMIT_PER_SEC = 200

_MOUSE_BUTTONS = {"left", "right", "middle"}


class InputDispatcher:
    """Per-session input dispatcher with rate limit and fail-safe tracking."""

    def __init__(self, session: RemoteSession) -> None:
        self.session = session
        self._window_start = time.time()
        self._count = 0
        self._screen_size: Optional[tuple[int, int]] = None
        self.last_failsafe_at: float = 0.0

    def _check_rate(self) -> bool:
        now = time.time()
        if now - self._window_start >= 1.0:
            self._window_start = now
            self._count = 0
        if self._count >= _RATE_LIMIT_PER_SEC:
            return False
        self._count += 1
        return True

    def _screen(self) -> tuple[int, int]:
        if self._screen_size is None:
            try:
                import pyautogui  # type: ignore

                self._screen_size = pyautogui.size()
            except Exception:
                self._screen_size = (1920, 1080)
        return self._screen_size

    def apply(self, event: dict[str, Any]) -> Optional[str]:
        """Apply a single event. Returns an optional status string."""
        if not isinstance(event, dict):
            return None
        if not self._check_rate():
            return None

        etype = str(event.get("type", "")).lower()

        try:
            import pyautogui  # type: ignore
        except Exception as exc:
            logger.warning("[remote] pyautogui import failed: %s", exc)
            return "pyautogui unavailable"

        try:
            if etype == "config":
                self.session.update_config(
                    fps=event.get("fps"),
                    quality=event.get("quality"),
                    max_width=event.get("width"),
                )
                self.session.touch()
                return None

            if etype == "move":
                x, y = self._coords(event)
                pyautogui.moveTo(x, y, _pause=False)
            elif etype == "down":
                x, y = self._coords(event)
                button = self._button(event)
                pyautogui.mouseDown(x, y, button=button, _pause=False)
            elif etype == "up":
                x, y = self._coords(event)
                button = self._button(event)
                pyautogui.mouseUp(x, y, button=button, _pause=False)
            elif etype == "click":
                x, y = self._coords(event)
                button = self._button(event)
                pyautogui.click(x, y, button=button, _pause=False)
            elif etype == "scroll":
                delta = int(event.get("dy", 0))
                pyautogui.scroll(delta)
            elif etype == "key":
                key = str(event.get("key", "")).strip()
                if not key:
                    return None
                pyautogui.press(key, _pause=False)
            elif etype == "hotkey":
                keys = event.get("keys") or []
                if not isinstance(keys, list) or not keys:
                    return None
                pyautogui.hotkey(*[str(k) for k in keys], _pause=False)
            elif etype == "text":
                text = str(event.get("text", ""))
                if text:
                    pyautogui.write(text, interval=0.0, _pause=False)
            else:
                return None

            self.session.touch()
            return None

        except getattr(__import__("pyautogui"), "FailSafeException", Exception) as exc:  # noqa: BLE001
            self.last_failsafe_at = time.time()
            logger.info("[remote] pyautogui fail-safe triggered: %s", exc)
            return "failsafe"
        except Exception as exc:
            logger.debug("[remote] input event %s failed: %s", etype, exc)
            return None

    def _coords(self, event: dict[str, Any]) -> tuple[int, int]:
        width, height = self._screen()
        x_norm = float(event.get("x", 0.0))
        y_norm = float(event.get("y", 0.0))
        x = int(max(0.0, min(1.0, x_norm)) * (width - 1))
        y = int(max(0.0, min(1.0, y_norm)) * (height - 1))
        return x, y

    def _button(self, event: dict[str, Any]) -> str:
        button = str(event.get("button", "left")).lower()
        return button if button in _MOUSE_BUTTONS else "left"
