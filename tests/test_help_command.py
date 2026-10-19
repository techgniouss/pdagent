"""/help must list every registered command and respect Telegram's size limit."""
import asyncio
from types import SimpleNamespace

from pocket_desk_agent.command_map import COMMAND_REGISTRY
from pocket_desk_agent.handlers import core


def test_help_lists_every_registered_command(monkeypatch) -> None:
    sent: list[str] = []

    class Msg:
        async def reply_text(self, text, **kwargs):
            sent.append(text)

    monkeypatch.setattr(core.auth_client, "is_authenticated", lambda user_id: True)
    update = SimpleNamespace(message=Msg(), effective_user=SimpleNamespace(id=1))
    asyncio.run(core.help_command(update, SimpleNamespace()))

    full_text = "\n".join(sent)
    missing = [name for name, _, _ in COMMAND_REGISTRY if f"/{name}" not in full_text]
    assert missing == []
    assert all(len(part) <= 4096 for part in sent), [len(part) for part in sent]
