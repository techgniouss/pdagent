from pocket_desk_agent.handlers import system


def test_build_app_picker_keyboard_includes_request_id() -> None:
    keyboard = system._build_app_picker_keyboard(
        "open",
        "req-123",
        {1: "chrome"},
    )

    button = keyboard.inline_keyboard[0][0]
    assert button.callback_data == "appselect_req-123_open_1"


def test_vscode_window_finder_does_not_accept_arbitrary_code_titles(monkeypatch) -> None:
    import sys
    import types

    from pocket_desk_agent.handlers import antigravity

    class Win:
        def __init__(self, title):
            self.title, self.visible, self.width = title, True, 800

    fake_gw = types.SimpleNamespace(
        getAllWindows=lambda: [Win("Barcode scanner"), Win("notes.txt - source code - Notepad"), Win("Code review - Google Chrome")]
    )
    monkeypatch.setitem(sys.modules, "pygetwindow", fake_gw)
    assert antigravity._find_vscode_window() is None

    fake_gw.getAllWindows = lambda: [Win("Barcode scanner"), Win("main.py - proj - Visual Studio Code")]
    assert antigravity._find_vscode_window().title.endswith("Visual Studio Code")


def test_claude_cli_window_match_excludes_browser_tabs() -> None:
    import types

    from pocket_desk_agent.handlers import antigravity

    def win(title, visible=True):
        return types.SimpleNamespace(title=title, visible=visible)

    assert antigravity._is_claude_cli_window(win("Claude CLI"))
    assert not antigravity._is_claude_cli_window(win("Claude CLI docs - Google Chrome"))
    assert not antigravity._is_claude_cli_window(win("Claude CLI", visible=False))
    assert not antigravity._is_claude_cli_window(win("Notes"))
