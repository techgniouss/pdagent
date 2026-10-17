"""safe_command: fail-closed auth, private-chat-only, and no double wrapping."""
import asyncio
from types import SimpleNamespace

import pytest

from pocket_desk_agent.config import Config
from pocket_desk_agent.handlers import _shared
from pocket_desk_agent.rate_limiter import rate_limiter


class _Bot:
    def __init__(self):
        self.sent: list[dict] = []

    async def send_message(self, **kwargs):
        self.sent.append(kwargs)


def _update(user_id=1, chat_type="private", with_user=True):
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id) if with_user else None,
        effective_chat=SimpleNamespace(id=500, type=chat_type),
        effective_message=None,
    )


@pytest.fixture()
def handler(monkeypatch):
    calls: list[int] = []

    async def sample_command(update, context):
        calls.append(1)

    monkeypatch.setattr(Config, "AUTHORIZED_USER_IDS", [1])
    monkeypatch.setattr(Config, "ALLOW_GROUP_CHATS", False)
    rate_limiter._hits.clear()
    return _shared.safe_command(sample_command), calls


def _run(wrapped, update):
    bot = _Bot()
    asyncio.run(wrapped(update, SimpleNamespace(bot=bot)))
    return bot


def test_authorized_private_chat_runs(handler) -> None:
    wrapped, calls = handler
    _run(wrapped, _update())
    assert calls == [1]


def test_unauthorized_user_is_ignored_silently(handler) -> None:
    wrapped, calls = handler
    bot = _run(wrapped, _update(user_id=2))
    assert calls == [] and bot.sent == []


def test_update_without_a_sender_is_rejected(handler) -> None:
    wrapped, calls = handler
    bot = _run(wrapped, _update(with_user=False))
    assert calls == [] and bot.sent == []


def test_group_chat_is_refused_by_default(handler) -> None:
    wrapped, calls = handler
    bot = _run(wrapped, _update(chat_type="supergroup"))
    assert calls == []
    assert bot.sent and "private chat" in bot.sent[0]["text"]


def test_group_chat_allowed_when_configured(handler, monkeypatch) -> None:
    wrapped, calls = handler
    monkeypatch.setattr(Config, "ALLOW_GROUP_CHATS", True)
    _run(wrapped, _update(chat_type="group"))
    assert calls == [1]


def test_unauthorized_group_message_gets_no_reply(handler) -> None:
    wrapped, calls = handler
    bot = _run(wrapped, _update(user_id=2, chat_type="group"))
    assert calls == [] and bot.sent == []


def test_registered_handlers_are_not_double_wrapped() -> None:
    """main.py wraps every handler; a decorator on the function itself would double-count rate limits."""
    from pocket_desk_agent.command_map import COMMAND_REGISTRY

    wrapped = [name for name, func, _ in COMMAND_REGISTRY if hasattr(func, "__wrapped__")]
    assert wrapped == [], f"handlers already wrapped with safe_command: {wrapped}"
