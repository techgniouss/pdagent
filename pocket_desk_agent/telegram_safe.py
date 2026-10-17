"""Telegram bot subclass that survives legacy-Markdown parse failures.

Many handlers send ``parse_mode="Markdown"`` text that embeds user data
(paths, command names, exception text). One stray ``_``, ``*`` or backtick
makes Telegram reject the whole message with "can't parse entities", which
surfaces as a handler crash even though the action itself succeeded.
``MarkdownFallbackBot`` retries such a call once as plain text, so the user
always gets the message.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Awaitable, Callable

from telegram.error import BadRequest
from telegram.ext import ExtBot

logger = logging.getLogger(__name__)

_MARKDOWN_MODES = frozenset({"Markdown", "MarkdownV2"})
_MARKUP_CHARS = re.compile(r"[*`]")
_TEXT_KEYS = ("text", "caption")


def is_entity_parse_error(exc: BaseException) -> bool:
    """True when Telegram rejected a message because its markup didn't parse."""
    return isinstance(exc, BadRequest) and "parse entities" in str(exc).lower()


def _plain_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Copy of ``kwargs`` without parse_mode and with Markdown markers removed."""
    plain = {k: v for k, v in kwargs.items() if k != "parse_mode"}
    for key in _TEXT_KEYS:
        value = plain.get(key)
        if isinstance(value, str):
            plain[key] = _MARKUP_CHARS.sub("", value)
    return plain


class MarkdownFallbackBot(ExtBot):
    """ExtBot that retries Markdown messages as plain text on entity-parse errors."""

    async def _retry_plain(
        self,
        method: Callable[..., Awaitable[Any]],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        try:
            return await method(*args, **kwargs)
        except BadRequest as exc:
            if kwargs.get("parse_mode") not in _MARKDOWN_MODES or not is_entity_parse_error(exc):
                raise
            logger.info("Markdown rejected by Telegram (%s); resending as plain text", exc)
            return await method(*args, **_plain_kwargs(kwargs))

    async def send_message(self, *args: Any, **kwargs: Any) -> Any:
        return await self._retry_plain(super().send_message, args, kwargs)

    async def edit_message_text(self, *args: Any, **kwargs: Any) -> Any:
        return await self._retry_plain(super().edit_message_text, args, kwargs)

    async def edit_message_caption(self, *args: Any, **kwargs: Any) -> Any:
        return await self._retry_plain(super().edit_message_caption, args, kwargs)

    async def send_photo(self, *args: Any, **kwargs: Any) -> Any:
        return await self._retry_plain(super().send_photo, args, kwargs)

    async def send_document(self, *args: Any, **kwargs: Any) -> Any:
        return await self._retry_plain(super().send_document, args, kwargs)
