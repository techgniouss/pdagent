"""Remote input: text typing must not drop non-ASCII characters; sizes are capped."""
import sys
import types

import pytest

from pocket_desk_agent.remote import input_bridge
from pocket_desk_agent.remote.session import RemoteSession, ACTIVE_SESSIONS


@pytest.fixture()
def dispatcher(monkeypatch):
    calls: list[tuple] = []
    gui = types.SimpleNamespace(
        FAILSAFE=True,
        FailSafeException=RuntimeError,
        write=lambda text, interval=0.0, _pause=True: calls.append(("write", text)),
        hotkey=lambda *keys, _pause=True: calls.append(("hotkey", keys)),
        scroll=lambda amount, _pause=True: calls.append(("scroll", amount)),
        size=lambda: (1920, 1080),
    )
    clip = {"value": "previous"}
    monkeypatch.setitem(sys.modules, "pyautogui", gui)
    monkeypatch.setitem(
        sys.modules,
        "pyperclip",
        types.SimpleNamespace(paste=lambda: clip["value"], copy=lambda v: clip.__setitem__("value", v)),
    )
    from pocket_desk_agent import automation_utils

    monkeypatch.setattr(automation_utils.time, "sleep", lambda _s: None)
    session = RemoteSession.create(user_id=55, chat_id=1, port=0, fps=5, quality=60, max_width=1280)
    yield input_bridge.InputDispatcher(session), calls
    ACTIVE_SESSIONS.pop(55, None)


def test_ascii_text_uses_the_fast_path(dispatcher) -> None:
    dispatch, calls = dispatcher
    dispatch.apply({"type": "text", "text": "hello"})
    assert calls == [("write", "hello")]


def test_non_ascii_text_is_pasted_not_dropped(dispatcher) -> None:
    dispatch, calls = dispatcher
    dispatch.apply({"type": "text", "text": "héllo Привіт ✓"})
    assert ("write", "héllo Привіт ✓") not in calls  # raw write would drop the accents
    assert ("hotkey", ("ctrl", "v")) in calls


def test_oversized_events_are_capped(dispatcher) -> None:
    dispatch, calls = dispatcher
    dispatch.apply({"type": "text", "text": "a" * 50_000})
    assert len(calls[0][1]) == input_bridge._MAX_TEXT_CHARS
    calls.clear()
    dispatch.apply({"type": "scroll", "dy": 10**9, "dx": 0})
    assert calls == [("scroll", input_bridge._MAX_SCROLL_UNITS)]
