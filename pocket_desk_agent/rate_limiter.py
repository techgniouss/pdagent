"""Per-user, per-command rate limiter.

Prevents abuse by limiting how frequently each user can invoke each
command.  Designed to be used as a decorator or a direct check.
"""

import time
import threading
from typing import Dict, Tuple


class RateLimiter:
    """Token-bucket style rate limiter keyed by (user_id, command)."""

    def __init__(self, default_calls: int = 10, default_window: int = 60):
        """
        Args:
            default_calls:  Max invocations per window (default: 10).
            default_window: Window size in seconds (default: 60).
        """
        self._default_calls = default_calls
        self._default_window = default_window
        # {(user_id, command): [timestamp, ...]}
        self._hits: Dict[Tuple[int, str], list] = {}
        self._lock = threading.Lock()
        # Per-command overrides: {command: (calls, window)}
        self._overrides: Dict[str, Tuple[int, int]] = {}

    def set_limit(self, command: str, calls: int, window: int) -> None:
        """Override the rate limit for a specific command."""
        self._overrides[command] = (calls, window)

    def check(self, user_id: int, command: str) -> bool:
        """
        Return True if the request is allowed, False if rate-limited.

        Automatically prunes expired timestamps.
        """
        calls, window = self._overrides.get(
            command, (self._default_calls, self._default_window)
        )
        now = time.monotonic()
        key = (user_id, command)

        with self._lock:
            timestamps = self._hits.get(key, [])
            # Prune old entries
            cutoff = now - window
            timestamps = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= calls:
                self._hits[key] = timestamps
                return False

            timestamps.append(now)
            self._hits[key] = timestamps
            return True

    def remaining(self, user_id: int, command: str) -> int:
        """Return how many calls remain in the current window."""
        calls, window = self._overrides.get(
            command, (self._default_calls, self._default_window)
        )
        now = time.monotonic()
        key = (user_id, command)

        with self._lock:
            timestamps = self._hits.get(key, [])
            cutoff = now - window
            active = [t for t in timestamps if t > cutoff]
            return max(0, calls - len(active))


# ── Global instance ──────────────────────────────────────────────────────────
rate_limiter = RateLimiter(default_calls=10, default_window=60)

# Stricter limits for expensive / dangerous commands
rate_limiter.set_limit("screenshot", calls=5, window=60)
rate_limiter.set_limit("shutdown", calls=1, window=300)
rate_limiter.set_limit("sleep", calls=2, window=120)
rate_limiter.set_limit("stopbot", calls=2, window=120)
rate_limiter.set_limit("restart", calls=2, window=120)
rate_limiter.set_limit("update", calls=1, window=300)
rate_limiter.set_limit("hotkey", calls=25, window=60)
rate_limiter.set_limit("clipboard", calls=25, window=60)
rate_limiter.set_limit("enhance", calls=5, window=60)
# AI messages — allow reasonable usage but prevent runaway billing.
# "handle_message" and "handle_photo" are the handler function names
# after stripping "_command" suffix in safe_command().
rate_limiter.set_limit("handle_message", calls=15, window=60)
rate_limiter.set_limit("handle_photo", calls=10, window=60)
# Callback queries — generous limit since buttons generate many callbacks
rate_limiter.set_limit("button_callback", calls=30, window=60)
