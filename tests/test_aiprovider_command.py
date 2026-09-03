import asyncio
from types import SimpleNamespace

from pocket_desk_agent import configure
from pocket_desk_agent.config import Config
from pocket_desk_agent.handlers import core as core_handlers


class _FakeMessage:
    def __init__(self):
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


def _make_update(args_text: str):
    message = _FakeMessage()
    update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=message)
    context = SimpleNamespace(args=args_text.split(",") if args_text else [])
    return update, context, message


def test_aiprovider_no_args_shows_current_order(monkeypatch) -> None:
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    update, context, message = _make_update("")

    asyncio.run(core_handlers.aiprovider_command(update, context))

    assert any("gemini" in r.lower() and "nvidia" in r.lower() for r in message.replies)


def test_aiprovider_rejects_unknown_token() -> None:
    update, context, message = _make_update("nvidia,bogus")

    asyncio.run(core_handlers.aiprovider_command(update, context))

    assert any("bogus" in r or "invalid" in r.lower() for r in message.replies)


def test_aiprovider_updates_order(tmp_path, monkeypatch) -> None:
    cfg_dir = tmp_path / ".pdagent"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(configure, "existing_app_path", lambda name: cfg_dir / name)
    monkeypatch.setattr(configure, "config_path", lambda: cfg_dir / "config")
    monkeypatch.setattr(configure, "ensure_app_dir", lambda: cfg_dir)

    update, context, message = _make_update("nvidia,gemini")

    asyncio.run(core_handlers.aiprovider_command(update, context))

    assert Config.AI_PROVIDER_ORDER == ["nvidia", "gemini"]
    assert any("updated" in r.lower() or "now" in r.lower() for r in message.replies)
