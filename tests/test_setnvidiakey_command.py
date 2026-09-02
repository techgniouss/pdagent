import asyncio
from types import SimpleNamespace

from pocket_desk_agent import configure
from pocket_desk_agent.handlers import auth as auth_handlers


class _FakeMessage:
    def __init__(self, message_id: int = 1):
        self.message_id = message_id
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class _FakeBot:
    def __init__(self):
        self.deleted: list[tuple[int, int]] = []

    async def delete_message(self, chat_id, message_id):
        self.deleted.append((chat_id, message_id))


def _make_update(args_text: str, message_id: int = 42):
    message = _FakeMessage(message_id)
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=1),
        effective_chat=SimpleNamespace(id=99),
        message=message,
    )
    context = SimpleNamespace(args=args_text.split() if args_text else [], bot=_FakeBot())
    return update, context, message


def test_setnvidiakey_requires_args() -> None:
    update, context, message = _make_update("")

    asyncio.run(auth_handlers.setnvidiakey_command(update, context))

    assert any("Usage" in r for r in message.replies)


def test_setnvidiakey_rejects_malformed_key() -> None:
    update, context, message = _make_update("not-an-nvidia-key")

    asyncio.run(auth_handlers.setnvidiakey_command(update, context))

    assert any("nvapi-" in r for r in message.replies)


def test_setnvidiakey_saves_and_deletes_message(tmp_path, monkeypatch) -> None:
    cfg_dir = tmp_path / ".pdagent"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(configure, "existing_app_path", lambda name: cfg_dir / name)
    monkeypatch.setattr(configure, "credentials_path", lambda: cfg_dir / "credentials")
    monkeypatch.setattr(configure, "config_path", lambda: cfg_dir / "config")
    monkeypatch.setattr(configure, "ensure_app_dir", lambda: cfg_dir)

    update, context, message = _make_update("nvapi-abc123")

    asyncio.run(auth_handlers.setnvidiakey_command(update, context))

    from pocket_desk_agent.config import Config
    assert Config.NVIDIA_API_KEY == "nvapi-abc123"
    assert any("saved" in r.lower() or "success" in r.lower() for r in message.replies)
    assert context.bot.deleted == [(99, 42)]
