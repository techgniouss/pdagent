"""Shared helpers for scheduling and repeating automation tasks."""

from __future__ import annotations

import datetime as dt
import re
from typing import Mapping, Optional, Sequence


def local_now() -> dt.datetime:
    """Return the current local timezone-aware datetime."""
    return dt.datetime.now().astimezone()


def ensure_local_timezone(value: dt.datetime) -> dt.datetime:
    """Normalize naive or foreign datetimes to the local timezone."""
    local_tz = local_now().tzinfo
    if value.tzinfo is None:
        return value.replace(tzinfo=local_tz)
    return value.astimezone(local_tz)


def parse_iso_datetime(value: str | None) -> Optional[dt.datetime]:
    """Parse a stored ISO datetime and normalize it to local time."""
    if not value:
        return None

    try:
        return ensure_local_timezone(dt.datetime.fromisoformat(value))
    except (TypeError, ValueError):
        return None


def parse_schedule_time(time_str: str) -> Optional[dt.datetime]:
    """Parse HH:MM or YYYY-MM-DD HH:MM into a local timezone-aware datetime."""
    now = local_now()
    text = time_str.strip()
    try:
        if ":" in text and "-" not in text:
            parsed = dt.datetime.strptime(text, "%H:%M")
            candidate = now.replace(
                hour=parsed.hour,
                minute=parsed.minute,
                second=0,
                microsecond=0,
            )
            if candidate < now:
                candidate += dt.timedelta(days=1)
            return candidate

        parsed = dt.datetime.strptime(text, "%Y-%m-%d %H:%M")
        return parsed.replace(tzinfo=now.tzinfo)
    except ValueError:
        return None


_DURATION_UNITS = {
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
}


def parse_duration_spec(spec: str) -> Optional[dt.timedelta]:
    """Parse durations like 90s, 2 min, 15 minutes, or 1h."""
    normalized = " ".join(spec.strip().lower().split())
    match = re.fullmatch(r"(\d+)\s*([a-z]+)", normalized)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)
    multiplier = _DURATION_UNITS.get(unit)
    if multiplier is None or amount <= 0:
        return None

    return dt.timedelta(seconds=amount * multiplier)


def parse_repeat_expression(raw_args: Sequence[str] | str) -> Optional[tuple[int, dt.timedelta]]:
    """Parse repeating specs like ``every 1m for 15m``."""
    if isinstance(raw_args, str):
        text = raw_args.strip()
    else:
        text = " ".join(raw_args).strip()

    normalized = " ".join(text.split())
    match = re.fullmatch(
        r"every\s+(.+?)\s+(?:for|till|until)\s+(.+)",
        normalized,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    interval_delta = parse_duration_spec(match.group(1))
    duration_delta = parse_duration_spec(match.group(2))
    if not interval_delta or not duration_delta:
        return None

    return int(interval_delta.total_seconds()), duration_delta


def format_duration(total_seconds: int) -> str:
    """Render a short human-friendly duration."""
    if total_seconds <= 0:
        return "0s"

    remaining = int(total_seconds)
    hours, remaining = divmod(remaining, 3600)
    minutes, seconds = divmod(remaining, 60)

    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds and not hours:
        parts.append(f"{seconds}s")
    return " ".join(parts) or "0s"


def format_eta(target: dt.datetime, *, now: Optional[dt.datetime] = None) -> str:
    """Format a relative countdown such as ``in 2m`` or ``due now``."""
    reference = now or local_now()
    delta_seconds = int((target - reference).total_seconds())
    if delta_seconds <= 0:
        return "due now"
    return f"in {format_duration(delta_seconds)}"


def get_task_due_at(task: Mapping[str, object]) -> Optional[dt.datetime]:
    """Return the next scheduled run time for a stored task."""
    next_run_at = parse_iso_datetime(str(task.get("next_run_at") or ""))
    if next_run_at:
        return next_run_at
    return parse_iso_datetime(str(task.get("execute_at") or ""))
