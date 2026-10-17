"""Small asyncio / Telegram helpers shared across modules."""

from __future__ import annotations

import asyncio
from typing import Any, Coroutine

# Telegram rejects messages longer than 4096 characters.
TELEGRAM_MAX_MESSAGE_CHARS = 4096

# asyncio only keeps weak references to tasks, so a fire-and-forget task can be
# garbage-collected mid-run. Hold strong references until each one finishes.
_background_tasks: set["asyncio.Task[Any]"] = set()


def spawn_background_task(coro: Coroutine[Any, Any, Any]) -> "asyncio.Task[Any]":
    """Start ``coro`` as a task that is kept alive until it finishes."""
    task = asyncio.get_running_loop().create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


def split_message(text: str, limit: int = TELEGRAM_MAX_MESSAGE_CHARS) -> list[str]:
    """Split ``text`` into chunks of at most ``limit`` characters.

    Prefers breaking at a newline, then a space, so words and lines stay
    intact; hard-splits only when a single token exceeds ``limit``.
    """
    if limit <= 0:
        raise ValueError("limit must be positive")
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        window = remaining[:limit]
        cut = window.rfind("\n")
        if cut <= 0:
            cut = window.rfind(" ")
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut].rstrip("\n"))
        remaining = remaining[cut:].lstrip("\n ") if cut < limit else remaining[cut:]
    if remaining:
        chunks.append(remaining)
    return [chunk for chunk in chunks if chunk]


async def reply_long_text(message: Any, text: str, **kwargs: Any) -> None:
    """``message.reply_text`` that splits replies over Telegram's size limit."""
    for chunk in split_message(text or "(empty response)"):
        await message.reply_text(chunk, **kwargs)
