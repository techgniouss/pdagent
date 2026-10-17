"""Scheduled macro playback must match the live /hotkey semantics."""
import asyncio
import sys
import types

from pocket_desk_agent.command_registry import CommandAction
from pocket_desk_agent.handlers import scheduling


def test_hotkey_with_text_copies_before_pressing(monkeypatch) -> None:
    events: list[str] = []
    fake_gui = types.SimpleNamespace(FAILSAFE=True, FailSafeException=RuntimeError,
                                     hotkey=lambda *k: events.append("hotkey:" + "+".join(k)),
                                     press=lambda k: events.append("press:" + k))
    fake_clip = types.SimpleNamespace(copy=lambda t: events.append("copy:" + t), paste=lambda: "")
    monkeypatch.setitem(sys.modules, "pyautogui", fake_gui)
    monkeypatch.setitem(sys.modules, "pyperclip", fake_clip)

    async def no_sleep(_s):
        return None

    monkeypatch.setattr(scheduling.asyncio, "sleep", no_sleep)

    actions = [CommandAction(type="hotkey", args=["ctrl+v", "Hello"])]
    asyncio.run(scheduling.run_custom_actions(actions))

    assert events == ["copy:Hello", "hotkey:ctrl+v"]
