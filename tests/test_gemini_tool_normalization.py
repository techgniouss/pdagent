from pocket_desk_agent.gemini_client import _normalize_tool_call


def test_alias_maps_to_remote_start_tool() -> None:
    tool_name, args = _normalize_tool_call("start-remote-session", {"unused": True})
    assert tool_name == "request_remote_session"
    assert args == {}


def test_start_screen_watch_argument_aliases_are_normalized() -> None:
    tool_name, args = _normalize_tool_call(
        "watch_screen",
        {
            "query": "Allow command",
            "every": "1m",
            "shortcut": "ctrl+enter",
            "window": "desktop",
            "throttle": "30s",
        },
    )
    assert tool_name == "start_screen_watch"
    assert args == {
        "text": "Allow command",
        "interval": "1m",
        "hotkey": "ctrl+enter",
        "scope": "screen",
        "cooldown": "30s",
    }


def test_stop_screen_watch_all_maps_to_empty_task_id() -> None:
    tool_name, args = _normalize_tool_call("stop_watch_screen", {"id": "all"})
    assert tool_name == "stop_screen_watch"
    assert args == {"task_id": ""}


def test_schedule_desktop_sequence_aliases_and_steps() -> None:
    tool_name, args = _normalize_tool_call(
        "schedule_command",
        {
            "when": "22:30",
            "title": "night_flow",
            "steps": [{"type": "hotkey", "args": ["ctrl+s"]}],
        },
    )
    assert tool_name == "schedule_desktop_sequence"
    assert args == {
        "execute_at": "22:30",
        "name": "night_flow",
        "actions": [{"type": "hotkey", "args": ["ctrl+s"]}],
    }


def test_open_browser_defaults_to_edge() -> None:
    tool_name, args = _normalize_tool_call("open_browser", {})
    assert tool_name == "open_browser"
    assert args == {"browser": "edge"}
