"""write_text must not silently drop non-ASCII characters."""
import sys
import types

from pocket_desk_agent import automation_utils as au


class _FakePyAutoGUI:
    FAILSAFE = True

    class FailSafeException(Exception):
        pass

    def __init__(self):
        self.written: list[str] = []
        self.hotkeys: list[tuple] = []

    def write(self, text, interval=0.0):
        self.written.append(text)

    def typewrite(self, text, interval=0.0):
        self.written.append(text)

    def hotkey(self, *keys):
        self.hotkeys.append(keys)


def _fake_pyperclip(monkeypatch):
    state = {"clip": "previous"}
    module = types.SimpleNamespace(
        paste=lambda: state["clip"],
        copy=lambda value: state.__setitem__("clip", value),
    )
    monkeypatch.setitem(sys.modules, "pyperclip", module)
    monkeypatch.setattr(au.time, "sleep", lambda _s: None)
    return state


def test_ascii_text_is_typed_directly(monkeypatch) -> None:
    _fake_pyperclip(monkeypatch)
    gui = _FakePyAutoGUI()
    au.write_text(gui, "hello world", interval=0.0)
    assert gui.written == ["hello world"]
    assert gui.hotkeys == []


def test_non_ascii_text_is_pasted_and_clipboard_restored(monkeypatch) -> None:
    state = _fake_pyperclip(monkeypatch)
    gui = _FakePyAutoGUI()
    au.write_text(gui, "Привіт, señor ✓", interval=0.0)
    assert gui.written == []
    assert gui.hotkeys == [("ctrl", "v")]
    assert state["clip"] == "previous"
