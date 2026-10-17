"""MarkdownFallbackBot retries Markdown parse failures as plain text."""
import asyncio

import pytest
from telegram.error import BadRequest, NetworkError
from telegram.ext import ExtBot

from pocket_desk_agent.telegram_safe import MarkdownFallbackBot, is_entity_parse_error


def _bot() -> MarkdownFallbackBot:
    return MarkdownFallbackBot(token="123:abc")


def test_entity_error_detection() -> None:
    assert is_entity_parse_error(BadRequest("Can't parse entities: can't find end of the entity"))
    assert not is_entity_parse_error(BadRequest("Chat not found"))
    assert not is_entity_parse_error(NetworkError("Can't parse entities"))


def test_markdown_failure_is_retried_as_plain_text(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_send(self, *args, **kwargs):
        calls.append(kwargs)
        if kwargs.get("parse_mode") == "Markdown":
            raise BadRequest("Can't parse entities: Can't find end of the entity starting at byte offset 4")
        return "sent"

    monkeypatch.setattr(ExtBot, "send_message", fake_send)
    result = asyncio.run(_bot().send_message(chat_id=1, text="Use: /quick_reply *now* `x`", parse_mode="Markdown"))

    assert result == "sent"
    assert len(calls) == 2
    assert "parse_mode" not in calls[1]
    assert calls[1]["text"] == "Use: /quick_reply now x"


def test_other_bad_requests_are_not_swallowed(monkeypatch) -> None:
    async def fake_send(self, *args, **kwargs):
        raise BadRequest("Chat not found")

    monkeypatch.setattr(ExtBot, "send_message", fake_send)
    with pytest.raises(BadRequest):
        asyncio.run(_bot().send_message(chat_id=1, text="hi", parse_mode="Markdown"))


def test_plain_messages_are_passed_through_once(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_edit(self, *args, **kwargs):
        calls.append(kwargs)
        return "ok"

    monkeypatch.setattr(ExtBot, "edit_message_text", fake_edit)
    assert asyncio.run(_bot().edit_message_text(text="hello", chat_id=1, message_id=2)) == "ok"
    assert len(calls) == 1
