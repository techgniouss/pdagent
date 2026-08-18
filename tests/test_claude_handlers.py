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
