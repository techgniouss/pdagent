from types import SimpleNamespace

from pocket_desk_agent.handlers import claude


def test_click_claude_input_prefers_type_slash_command_placeholder(monkeypatch) -> None:
    target_spec = {
        "title_re": r".*[Tt]ype\s*/\s*for\s*[Cc]ommand.*",
        "control_type": "Text",
    }
    seen_specs: list[dict[str, object]] = []
    clicked = {"value": False}

    class _Control:
        def click_input(self) -> None:
            clicked["value"] = True

    class _ClaudeWindow:
        def child_window(self, **spec):
            seen_specs.append(spec)
            if spec == target_spec:
                return _Control()
            raise RuntimeError("no control")

    class _App:
        def __init__(self, backend: str):
            assert backend == "uia"

        def connect(self, title_re: str):
            assert "Claude" in title_re
            return self

        def window(self, title_re: str):
            assert "Claude" in title_re
            return _ClaudeWindow()

    monkeypatch.setattr(claude, "PYWINAUTO_AVAILABLE", True)
    monkeypatch.setattr(claude, "_load_win_deps", lambda: None)
    monkeypatch.setattr(claude, "Application", _App)
    monkeypatch.setattr(claude, "_configure_tesseract", lambda: None)
    monkeypatch.setattr(claude.time, "sleep", lambda *_: None)

    window = SimpleNamespace(left=100, top=50, width=1200, height=900)
    pyautogui = SimpleNamespace(click=lambda *_: None)

    claude._click_claude_input(window, pyautogui)

    assert seen_specs
    assert seen_specs[0] == target_spec
    assert clicked["value"] is True


def test_click_claude_input_coordinate_fallback_targets_composer_area(monkeypatch) -> None:
    clicks: list[tuple[int, int]] = []

    monkeypatch.setattr(claude, "PYWINAUTO_AVAILABLE", False)
    monkeypatch.setattr(claude, "_configure_tesseract", lambda: None)
    monkeypatch.setattr(claude.time, "sleep", lambda *_: None)

    window = SimpleNamespace(left=100, top=50, width=1200, height=900)
    pyautogui = SimpleNamespace(click=lambda x, y: clicks.append((x, y)))

    claude._click_claude_input(window, pyautogui)

    assert clicks == [
        (700, 824),
        (700, 788),
        (700, 752),
    ]


def test_pick_claude_window_title_ignores_browsers_terminals_and_ides() -> None:
    from pocket_desk_agent.handlers.claude import pick_claude_window_title

    assert pick_claude_window_title(["Claude"]) == "Claude"
    assert pick_claude_window_title(["Claude - Google Chrome", "Claude CLI", "Claude"]) == "Claude"
    assert pick_claude_window_title(["Claude CLI", "Visual Studio Code - Claude Code"]) is None
    assert pick_claude_window_title(["Notes", "Inbox - Mail"]) is None
    assert pick_claude_window_title(["", "Claude (Beta)"]) == "Claude (Beta)"


def test_send_prompt_refuses_when_claude_is_not_foreground(monkeypatch) -> None:
    import sys
    import types

    import pytest

    from pocket_desk_agent.handlers import claude
    from pocket_desk_agent import window_utils

    keys: list[str] = []
    fake_gui = types.SimpleNamespace(
        hotkey=lambda *k: keys.append("+".join(k)), press=lambda k: keys.append(k)
    )
    fake_clip = types.SimpleNamespace(copy=lambda t: keys.append("copy"))
    monkeypatch.setitem(sys.modules, "pyautogui", fake_gui)
    monkeypatch.setitem(sys.modules, "pyperclip", fake_clip)
    monkeypatch.setattr(window_utils, "foreground_window_handle", lambda: 999)
    monkeypatch.setattr(window_utils, "activate_window", lambda handle: False)

    window = types.SimpleNamespace(_hWnd=123)
    with pytest.raises(RuntimeError, match="foreground"):
        claude.send_prompt_to_claude(window, "rm -rf /")
    assert keys == []  # nothing was pasted or submitted anywhere
