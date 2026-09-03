# NVIDIA AI Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add NVIDIA NIM as a second AI provider that the bot automatically falls back to when Gemini's quota/session is exhausted, with full tool-calling parity, user-configurable provider order, and a chat command to set the NVIDIA key.

**Architecture:** A new `AIRouter` sits above the existing `GeminiClient` and a new `NvidiaClient`, both exposing the same `send_message`/`send_message_with_image` shape and returning a `ProviderResult` (text + retryable flag) instead of a bare string. Conversation history stays canonical in `GeminiClient.sessions` (Gemini's `contents`/`parts` shape); `NvidiaClient` converts it to OpenAI `messages` per call via pure converters in `ai_history.py`, so a mid-conversation fallback is seamless. A shared `ai_tool_loop.py` holds the tool allowlist and dispatch logic both clients call, so there's exactly one place that security-relevant logic can drift.

**Tech Stack:** Python 3.11+, `requests` (already a dependency), `pytest` + `monkeypatch` (existing test style — no new test dependencies).

**Spec:** [docs/superpowers/specs/2026-09-02-nvidia-ai-fallback-design.md](../specs/2026-09-02-nvidia-ai-fallback-design.md)

## Global Constraints

- NVIDIA endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`, OpenAI-compatible, `Authorization: Bearer <key>`.
- Default `NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"` (tool-calling capable). Re-verify current availability on build.nvidia.com before shipping — NVIDIA's catalog changes; swap the default in `config.py` if it's been retired.
- `AI_PROVIDER_ORDER` default: `["gemini", "nvidia"]`. Only `{"gemini", "nvidia"}` are valid tokens.
- No per-user provider preference — one global `Config` setting, same pattern as `GEMINI_AUTH_MODE`.
- Every new/modified Python file needs type hints on new functions (repo convention, `mypy` via `make lint`).
- Tests follow the existing style in `tests/`: plain `pytest` functions, `monkeypatch` for env vars / attribute patching, no `unittest.mock`. Run via `pytest tests/<file>.py -v`.
- `black pocket_desk_agent/ scripts/` before each commit (repo convention — `make format`).
- Secrets discipline: the NVIDIA key goes in `~/.pdagent/credentials` (chmod 600 pattern, same file as `google_api_key`), never in `~/.pdagent/config` or logs. Mask it in any status/print output the way `_mask()` already does for other credentials.

---

### Task 1: Gemini ⇄ OpenAI history and tool converters

**Files:**
- Create: `pocket_desk_agent/ai_history.py`
- Test: `tests/test_ai_history.py`

**Interfaces:**
- Produces: `gemini_tools_to_openai(function_declarations: list[dict]) -> list[dict]`, `gemini_history_to_openai(history: list[dict], system_prompt: str) -> list[dict]`, `openai_message_to_gemini_parts(message: dict) -> list[dict]`. These are the only three functions later tasks import from this module.

Gemini history shape (already used by `GeminiClient.sessions`): a list of `{"role": "user"|"model", "parts": [...]}`, where a part is `{"text": str}`, `{"functionCall": {"name": str, "args": dict}}`, or `{"functionResponse": {"name": str, "response": dict}}` (optionally followed by an `{"inlineData": {...}}` part in the same entry).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ai_history.py
from pocket_desk_agent.ai_history import (
    gemini_history_to_openai,
    gemini_tools_to_openai,
    openai_message_to_gemini_parts,
)


def test_gemini_tools_to_openai_wraps_function_declarations() -> None:
    declarations = [
        {
            "name": "read_file",
            "description": "Read a file.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        }
    ]

    tools = gemini_tools_to_openai(declarations)

    assert tools == [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file.",
                "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            },
        }
    ]


def test_gemini_tools_to_openai_defaults_missing_fields() -> None:
    tools = gemini_tools_to_openai([{"name": "ping"}])

    assert tools[0]["function"]["description"] == ""
    assert tools[0]["function"]["parameters"] == {"type": "object", "properties": {}}


def test_gemini_history_to_openai_converts_plain_turns() -> None:
    history = [
        {"role": "user", "parts": [{"text": "hello"}]},
        {"role": "model", "parts": [{"text": "hi there"}]},
    ]

    messages = gemini_history_to_openai(history, system_prompt="You are helpful.")

    assert messages == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


def test_gemini_history_to_openai_pairs_single_tool_call() -> None:
    history = [
        {"role": "user", "parts": [{"text": "list files"}]},
        {"role": "model", "parts": [{"functionCall": {"name": "list_directory", "args": {"path": "."}}}]},
        {"role": "user", "parts": [{"functionResponse": {"name": "list_directory", "response": {"result": "a.txt", "success": True}}}]},
    ]

    messages = gemini_history_to_openai(history, system_prompt="sys")

    assert messages[1] == {"role": "user", "content": "list files"}
    assistant_msg = messages[2]
    assert assistant_msg["role"] == "assistant"
    assert len(assistant_msg["tool_calls"]) == 1
    call_id = assistant_msg["tool_calls"][0]["id"]
    assert assistant_msg["tool_calls"][0]["function"]["name"] == "list_directory"
    import json
    assert json.loads(assistant_msg["tool_calls"][0]["function"]["arguments"]) == {"path": "."}

    tool_msg = messages[3]
    assert tool_msg == {
        "role": "tool",
        "tool_call_id": call_id,
        "content": tool_msg["content"],
    }
    assert json.loads(tool_msg["content"]) == {"result": "a.txt", "success": True}


def test_gemini_history_to_openai_pairs_multiple_tool_calls_in_order() -> None:
    history = [
        {"role": "user", "parts": [{"text": "do two things"}]},
        {
            "role": "model",
            "parts": [
                {"functionCall": {"name": "tool_a", "args": {}}},
                {"functionCall": {"name": "tool_b", "args": {}}},
            ],
        },
        {
            "role": "user",
            "parts": [
                {"functionResponse": {"name": "tool_a", "response": {"result": "A", "success": True}}},
                {"functionResponse": {"name": "tool_b", "response": {"result": "B", "success": True}}},
            ],
        },
    ]

    messages = gemini_history_to_openai(history, system_prompt="sys")

    assistant_msg = messages[2]
    ids = [tc["id"] for tc in assistant_msg["tool_calls"]]
    assert len(set(ids)) == 2  # distinct ids

    tool_msgs = [m for m in messages if m["role"] == "tool"]
    assert len(tool_msgs) == 2
    assert tool_msgs[0]["tool_call_id"] == ids[0]
    assert tool_msgs[1]["tool_call_id"] == ids[1]


def test_openai_message_to_gemini_parts_text_only() -> None:
    parts = openai_message_to_gemini_parts({"role": "assistant", "content": "hello"})
    assert parts == [{"text": "hello"}]


def test_openai_message_to_gemini_parts_with_tool_calls() -> None:
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "read_file", "arguments": '{"path": "a.txt"}'},
            }
        ],
    }

    parts = openai_message_to_gemini_parts(message)

    assert parts == [{"functionCall": {"name": "read_file", "args": {"path": "a.txt"}}}]


def test_openai_message_to_gemini_parts_handles_malformed_arguments() -> None:
    message = {
        "content": None,
        "tool_calls": [{"function": {"name": "broken", "arguments": "not json"}}],
    }

    parts = openai_message_to_gemini_parts(message)

    assert parts == [{"functionCall": {"name": "broken", "args": {}}}]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ai_history.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pocket_desk_agent.ai_history'`

- [ ] **Step 3: Implement `ai_history.py`**

```python
"""Pure converters between Gemini's `contents`/`parts` history shape and
OpenAI-compatible `messages`/`tools` shape.

The canonical conversation history for every AI provider lives in
GeminiClient.sessions, in Gemini's shape. NvidiaClient (OpenAI-compatible)
converts that shared history on every call via the functions here, and
converts its own responses back into Gemini's shape before they're
appended to history — so a conversation can move between providers
mid-stream without the history format ever diverging.
"""
from __future__ import annotations

import json
from typing import Any


def gemini_tools_to_openai(function_declarations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Wrap Gemini functionDeclarations as OpenAI-style `tools`."""
    return [
        {
            "type": "function",
            "function": {
                "name": decl["name"],
                "description": decl.get("description", ""),
                "parameters": decl.get("parameters") or {"type": "object", "properties": {}},
            },
        }
        for decl in function_declarations
    ]


def _stringify_function_response(function_response: dict[str, Any]) -> str:
    """Serialize a Gemini functionResponse's `response` payload for a tool message."""
    return json.dumps(function_response.get("response", {}))


def gemini_history_to_openai(history: list[dict[str, Any]], system_prompt: str) -> list[dict[str, Any]]:
    """Convert a Gemini-shaped history into an OpenAI-compatible `messages` list.

    A Gemini "model" turn with one or more `functionCall` parts becomes one
    assistant message with a `tool_calls` list; the *next* "user" turn's
    `functionResponse` parts are paired to those tool_calls by position
    (both sides are always produced in the same order by the callers that
    build this history — see ai_tool_loop.run_tool_turn).
    """
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    pending_tool_call_ids: list[str] = []
    call_index = 0

    for entry in history:
        role = entry.get("role")
        parts = entry.get("parts", [])

        if role == "user":
            function_responses = [p["functionResponse"] for p in parts if "functionResponse" in p]
            if function_responses:
                for i, resp in enumerate(function_responses):
                    call_id = (
                        pending_tool_call_ids[i]
                        if i < len(pending_tool_call_ids)
                        else f"call_{call_index}"
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": _stringify_function_response(resp),
                        }
                    )
                pending_tool_call_ids = []
                continue
            text = "".join(p.get("text", "") for p in parts if "text" in p)
            messages.append({"role": "user", "content": text})
            continue

        if role == "model":
            function_calls = [p["functionCall"] for p in parts if "functionCall" in p]
            text = "".join(p.get("text", "") for p in parts if "text" in p)
            if function_calls:
                tool_calls = []
                pending_tool_call_ids = []
                for fc in function_calls:
                    call_id = f"call_{call_index}"
                    call_index += 1
                    pending_tool_call_ids.append(call_id)
                    tool_calls.append(
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": fc.get("name", ""),
                                "arguments": json.dumps(fc.get("args") or {}),
                            },
                        }
                    )
                messages.append({"role": "assistant", "content": text or None, "tool_calls": tool_calls})
            else:
                messages.append({"role": "assistant", "content": text})
            continue

    return messages


def openai_message_to_gemini_parts(message: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert one OpenAI assistant message (text and/or tool_calls) to Gemini parts."""
    parts: list[dict[str, Any]] = []
    content = message.get("content")
    if isinstance(content, str) and content:
        parts.append({"text": content})

    for tool_call in message.get("tool_calls") or []:
        function = tool_call.get("function", {}) or {}
        try:
            args = json.loads(function.get("arguments") or "{}")
        except (ValueError, TypeError):
            args = {}
        parts.append({"functionCall": {"name": function.get("name", ""), "args": args}})

    return parts
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ai_history.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add pocket_desk_agent/ai_history.py tests/test_ai_history.py
git commit -m "feat: add Gemini<->OpenAI history/tool converters for AI fallback

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Shared provider result type and tool-call loop

**Files:**
- Create: `pocket_desk_agent/ai_types.py`
- Create: `pocket_desk_agent/ai_tool_loop.py`
- Test: `tests/test_ai_tool_loop.py`

**Interfaces:**
- Consumes: `pocket_desk_agent.gemini_actions.dispatch_gemini_tool` (existing, signature unchanged: `async def dispatch_gemini_tool(user_id, func_name, args, file_manager, tool_runtime=None) -> GeminiToolResult`, `GeminiToolResult.to_response() -> dict`, `.result: str`, `.image_bytes: Optional[bytes]`).
- Produces: `ai_types.ProviderResult(text: str, is_retryable_error: bool = False)`; `ai_tool_loop.ALLOWED_TOOLS: frozenset[str]`; `ai_tool_loop.normalize_tool_call(func_name, args) -> tuple[str, dict]`; `ai_tool_loop.ToolTurnResult(tool_result: dict, result_text: str, image_bytes: Optional[bytes], normalized_call: dict)`; `async def ai_tool_loop.run_tool_turn(*, user_id, raw_func_name, raw_args, file_manager, tool_runtime, loop, turn=0) -> ToolTurnResult`. Task 3 (GeminiClient) and Task 4 (NvidiaClient) both call `run_tool_turn` and both re-use `ALLOWED_TOOLS`.

This task **moves** (not duplicates) the tool-name-alias table, argument normalizer, and allowlist that currently live in `pocket_desk_agent/gemini_client.py` lines 37-110, 281-330, 332-438, and 659-712 — verbatim — plus adds the new `run_tool_turn` helper that lifts the tool-dispatch body currently inline in `GeminiClient.send_message` (lines 1148-1207). `gemini_client.py` itself is not touched until Task 3, so this task only adds new files.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ai_tool_loop.py
import asyncio

from pocket_desk_agent.ai_tool_loop import ALLOWED_TOOLS, normalize_tool_call, run_tool_turn
from pocket_desk_agent.ai_types import ProviderResult


def test_provider_result_defaults_not_retryable() -> None:
    result = ProviderResult(text="ok")
    assert result.is_retryable_error is False


def test_allowed_tools_include_canonical_app_tools() -> None:
    assert "open_desktop_app" in ALLOWED_TOOLS
    assert "close_desktop_app" in ALLOWED_TOOLS
    assert "list_directory" in ALLOWED_TOOLS


def test_normalize_tool_call_resolves_alias_and_args() -> None:
    name, args = normalize_tool_call("remote", {})
    assert name == "request_remote_session"
    assert args == {}

    name, args = normalize_tool_call("run_shell", {"cmd": "git status"})
    assert name == "execute_command"
    assert args == {"command": "git status"}


class _FakeFileManager:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def list_directory(self, user_id: int, path):
        self.calls.append(("list_directory", user_id, path))
        return True, "a.txt\nb.txt"


def test_run_tool_turn_dispatches_builtin_file_tool() -> None:
    fm = _FakeFileManager()

    async def _run():
        loop = asyncio.get_running_loop()
        return await run_tool_turn(
            user_id=1,
            raw_func_name="list_directory",
            raw_args={"path": "."},
            file_manager=fm,
            tool_runtime=None,
            loop=loop,
        )

    result = asyncio.run(_run())

    assert fm.calls == [("list_directory", 1, ".")]
    assert result.tool_result == {"result": "a.txt\nb.txt", "success": True}
    assert result.result_text == "a.txt\nb.txt"
    assert result.image_bytes is None
    assert result.normalized_call == {"name": "list_directory", "args": {"path": "."}}


def test_run_tool_turn_blocks_disallowed_tool() -> None:
    fm = _FakeFileManager()

    async def _run():
        loop = asyncio.get_running_loop()
        return await run_tool_turn(
            user_id=1,
            raw_func_name="execute_python_eval",  # not in ALLOWED_TOOLS, no alias
            raw_args={},
            file_manager=fm,
            tool_runtime=None,
            loop=loop,
        )

    result = asyncio.run(_run())

    assert result.tool_result["success"] is False
    assert "not available" in result.tool_result["result"]
    assert fm.calls == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ai_tool_loop.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pocket_desk_agent.ai_tool_loop'`

- [ ] **Step 3: Implement `ai_types.py`**

```python
"""Shared types exchanged between AI provider clients and AIRouter."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderResult:
    """Outcome of one AI provider's attempt to answer a message.

    ``text`` is the provider's answer, or — when ``is_retryable_error`` is
    True — an error message describing *this provider's* failure. AIRouter
    only shows that error text to the user if this was the last configured
    provider it tried; otherwise it moves on to the next provider and the
    text here is discarded (logged, not shown).
    """

    text: str
    is_retryable_error: bool = False
```

- [ ] **Step 4: Implement `ai_tool_loop.py`**

```python
"""Shared tool-call normalization, allowlist, and dispatch for AI providers.

GeminiClient and NvidiaClient both run a multi-turn tool-calling loop
against a different backend API, but the set of tools an AI is allowed to
invoke — and how each tool call gets dispatched to file_manager or
gemini_actions — must be identical and defined in exactly one place.  This
module is that place.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from pocket_desk_agent.gemini_actions import dispatch_gemini_tool

logger = logging.getLogger(__name__)

# Maps common natural-language / aliased tool names an AI might emit to the
# canonical tool name it actually corresponds to.
_TOOL_NAME_ALIASES: dict[str, str] = {
    "remote": "request_remote_session",
    "open_remote": "request_remote_session",
    "start_remote": "request_remote_session",
    "start_remote_session": "request_remote_session",
    "remote_desktop_start": "request_remote_session",
    "open_remote_session": "request_remote_session",
    "stop_remote": "request_stop_remote_session",
    "end_remote": "request_stop_remote_session",
    "close_remote": "request_stop_remote_session",
    "stop_remote_session": "request_stop_remote_session",
    "end_remote_session": "request_stop_remote_session",
    "remote_status": "get_remote_session_status",
    "get_remote_status": "get_remote_session_status",
    "remote_session_status": "get_remote_session_status",
    "check_remote_status": "get_remote_session_status",
    "build": "start_build_workflow",
    "start_build": "start_build_workflow",
    "build_workflow": "start_build_workflow",
    "build_project": "start_build_workflow",
    "run_build": "start_build_workflow",
    "get_apk": "start_apk_retrieval_workflow",
    "retrieve_apk": "start_apk_retrieval_workflow",
    "apk_retrieval": "start_apk_retrieval_workflow",
    "apk_workflow": "start_apk_retrieval_workflow",
    "watch_screen": "start_screen_watch",
    "screen_watch": "start_screen_watch",
    "start_watch_screen": "start_screen_watch",
    "stop_watch_screen": "stop_screen_watch",
    "end_screen_watch": "stop_screen_watch",
    "stop_screen_watcher": "stop_screen_watch",
    "schedule_claude": "schedule_claude_prompt",
    "claude_schedule": "schedule_claude_prompt",
    "schedule_macro": "schedule_desktop_sequence",
    "schedule_command": "schedule_desktop_sequence",
    "schedule_custom_command": "schedule_desktop_sequence",
    "schedule_actions": "schedule_desktop_sequence",
    "open_app": "open_desktop_app",
    "launch_app": "open_desktop_app",
    "start_app": "open_desktop_app",
    "close_app": "close_desktop_app",
    "stop_app": "close_desktop_app",
    "end_app": "close_desktop_app",
    "launch_browser": "open_browser",
    "open_folder_vscode": "open_vscode_folder",
    "vscode_open_folder": "open_vscode_folder",
    "launch_claude_cli": "open_claude_cli",
    "send_claude_cli_message": "claude_cli_send_message",
    "run_command": "execute_command",
    "shell_command": "execute_command",
    "run_shell": "execute_command",
    "exec_command": "execute_command",
    "run_in_folder": "execute_command",
    "click": "click_on_screen",
    "click_screen": "click_on_screen",
    "screen_click": "click_on_screen",
    "click_element": "click_on_screen",
    "click_button": "click_on_screen",
    "click_text": "click_on_screen",
    "click_at": "click_on_screen",
    "double_click": "double_click_on_screen",
    "dbl_click": "double_click_on_screen",
    "doubleclick": "double_click_on_screen",
    "double_click_screen": "double_click_on_screen",
    "right_click": "right_click_on_screen",
    "rightclick": "right_click_on_screen",
    "right_click_screen": "right_click_on_screen",
    "context_click": "right_click_on_screen",
    "scroll": "scroll_screen",
    "scroll_up": "scroll_screen",
    "scroll_down": "scroll_screen",
    "page_scroll": "scroll_screen",
    "screen_scroll": "scroll_screen",
}


def _normalize_tool_name(func_name: Any) -> str:
    """Normalize a tool name for alias resolution."""
    if not isinstance(func_name, str):
        return ""
    normalized = func_name.strip().lstrip("/").lower()
    normalized = re.sub(r"[\s\-]+", "_", normalized)
    return normalized


def _first_string(args: dict[str, Any], *keys: str, default: str = "") -> str:
    """Return the first non-empty string value from ``keys``."""
    for key in keys:
        value = args.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _first_value(args: dict[str, Any], *keys: str) -> Any:
    """Return the first present value for ``keys``."""
    for key in keys:
        if key in args:
            return args[key]
    return None


def _as_int(value: Any, default: int = 0) -> int:
    """Best-effort integer parsing used for tool arguments."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    """Best-effort boolean parsing for tool arguments."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on", "force"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _normalize_tool_args(func_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Normalize aliased argument keys to each tool's canonical schema."""
    if func_name in {
        "get_current_directory",
        "get_battery_status",
        "capture_screenshot",
        "list_open_windows",
        "view_clipboard",
        "shutdown_computer",
        "sleep_computer",
        "list_custom_commands",
        "list_schedules",
        "open_claude",
        "open_antigravity",
        "request_remote_session",
        "request_stop_remote_session",
        "get_remote_session_status",
    }:
        return {}
    if func_name == "change_directory":
        return {"path": _first_string(args, "path", "directory", "dir", "folder")}
    if func_name == "focus_window":
        selection = _first_value(args, "selection", "index", "window", "number")
        return {"selection": _as_int(selection, default=0)}
    if func_name == "set_privacy_mode":
        mode = _first_string(args, "mode", "action", "state", default="status").lower()
        return {"mode": mode}
    if func_name in {"start_build_workflow", "start_apk_retrieval_workflow"}:
        return {"project": _first_string(args, "project", "repo", "folder", "name", "target")}
    if func_name == "run_saved_command":
        return {"name": _first_string(args, "name", "command", "custom", "macro").lstrip("/")}
    if func_name in {"find_text_on_screen", "smart_click_text"}:
        return {"text": _first_string(args, "text", "query", "target", "search", "phrase")}
    if func_name == "set_clipboard":
        return {"text": _first_string(args, "text", "content", "value", "message")}
    if func_name == "press_hotkey":
        keys = _first_string(args, "keys", "hotkey", "shortcut", "key", "press")
        text = _first_string(args, "text", "content", "value", "message")
        return {"keys": keys, "text": text or None}
    if func_name == "click_coordinates":
        x = _as_int(_first_value(args, "x", "left", "column"), default=0)
        y = _as_int(_first_value(args, "y", "top", "row"), default=0)
        return {"x": x, "y": y}
    if func_name == "start_screen_watch":
        text = _first_string(args, "text", "query", "target", "search", "phrase")
        interval = _first_string(args, "interval", "every", "frequency")
        hotkey = _first_string(args, "hotkey", "shortcut", "key", "keys", "press")
        scope = _first_string(args, "scope", "app", "window", "context", "target", default="screen").lower()
        cooldown = _first_string(args, "cooldown", "throttle", "debounce")
        scope_aliases = {
            "desktop": "screen",
            "display": "screen",
            "fullscreen": "screen",
            "full": "screen",
            "claude_app": "claude",
            "claude desktop": "claude",
            "antigravity_app": "antigravity",
            "antigravity desktop": "antigravity",
        }
        scope = scope_aliases.get(scope, scope)
        return {
            "text": text,
            "interval": interval,
            "hotkey": hotkey,
            "scope": scope,
            "cooldown": cooldown,
        }
    if func_name == "stop_screen_watch":
        task_id = _first_string(args, "task_id", "id", "watch_id", "schedule_id", "target")
        if task_id.lower() in {"all", "*"}:
            task_id = ""
        return {"task_id": task_id}
    if func_name == "open_desktop_app":
        return {"name": _first_string(args, "name", "app", "application", "query", "target")}
    if func_name == "close_desktop_app":
        return {
            "name": _first_string(args, "name", "app", "application", "query", "target"),
            "force": _as_bool(_first_value(args, "force", "kill", "terminate"), default=False),
        }
    if func_name == "open_browser":
        browser = _first_string(args, "browser", "name", "app", "target", default="edge").lower()
        return {"browser": browser}
    if func_name == "execute_command":
        return {"command": _first_string(args, "command", "cmd", "shell", "run", "exec", "script")}
    if func_name in {"open_vscode_folder", "open_claude_cli"}:
        folder = _first_string(args, "folder", "path", "repo", "project", "name", "directory")
        normalized = {"folder": folder}
        if func_name == "open_claude_cli":
            normalized["prompt"] = _first_string(args, "prompt", "message", "text", "query")
        return normalized
    if func_name == "claude_cli_send_message":
        message = _first_string(args, "message", "prompt", "text", "query", "content")
        return {"message": message}
    if func_name == "schedule_claude_prompt":
        execute_at = _first_string(args, "execute_at", "time", "when", "at", "run_at")
        prompt = _first_string(args, "prompt", "message", "text", "query", "content")
        return {"execute_at": execute_at, "prompt": prompt}
    if func_name == "schedule_desktop_sequence":
        execute_at = _first_string(args, "execute_at", "time", "when", "at", "run_at")
        name = _first_string(args, "name", "title", "label", "command")
        actions = _first_value(args, "actions", "steps", "sequence", "commands")
        if isinstance(actions, dict):
            actions = [actions]
        if not isinstance(actions, list):
            actions = []
        return {"execute_at": execute_at, "name": name, "actions": actions}
    return args


def normalize_tool_call(func_name: Any, args: Any) -> tuple[str, dict[str, Any]]:
    """Normalize tool names and argument aliases before allowlist enforcement."""
    normalized_name = _normalize_tool_name(func_name)
    canonical_name = _TOOL_NAME_ALIASES.get(normalized_name, normalized_name)
    raw_args = args if isinstance(args, dict) else {}
    normalized_args = _normalize_tool_args(canonical_name, raw_args)
    return canonical_name, normalized_args


# Strict allowlist of tool names any AI provider is permitted to invoke.
# Any function call whose name is not in this set is silently ignored.
ALLOWED_TOOLS = frozenset({
    "list_directory",
    "get_tree_structure",
    "read_file",
    "search_files",
    "write_file",
    "append_file",
    "delete_file",
    "create_directory",
    "get_file_info",
    "execute_command",
    "get_current_directory",
    "change_directory",
    "get_battery_status",
    "capture_screenshot",
    "list_open_windows",
    "focus_window",
    "view_clipboard",
    "shutdown_computer",
    "sleep_computer",
    "set_privacy_mode",
    "list_custom_commands",
    "list_schedules",
    "start_screen_watch",
    "stop_screen_watch",
    "start_build_workflow",
    "start_apk_retrieval_workflow",
    "run_saved_command",
    "find_text_on_screen",
    "click_on_screen",
    "double_click_on_screen",
    "right_click_on_screen",
    "scroll_screen",
    "set_clipboard",
    "press_hotkey",
    "click_coordinates",
    "smart_click_text",
    "open_claude",
    "open_antigravity",
    "open_browser",
    "open_vscode_folder",
    "open_claude_cli",
    "claude_cli_send_message",
    "open_desktop_app",
    "close_desktop_app",
    "schedule_claude_prompt",
    "schedule_desktop_sequence",
    "request_remote_session",
    "request_stop_remote_session",
    "get_remote_session_status",
    "update_bot",
})


@dataclass
class ToolTurnResult:
    """Outcome of dispatching one normalized tool call."""

    tool_result: dict[str, Any]
    result_text: str
    image_bytes: Optional[bytes]
    normalized_call: dict[str, Any]


async def run_tool_turn(
    *,
    user_id: int,
    raw_func_name: Any,
    raw_args: Any,
    file_manager: Any,
    tool_runtime: Optional[dict[str, Any]],
    loop: asyncio.AbstractEventLoop,
    turn: int = 0,
) -> ToolTurnResult:
    """Normalize, allowlist-check, and dispatch one AI-requested tool call.

    Always returns a ToolTurnResult — callers append ``normalized_call`` as
    the model's functionCall part and ``tool_result``/``image_bytes`` as the
    matching functionResponse (+ optional inlineData) part, regardless of
    whether the call was allowed.
    """
    func_name, args = normalize_tool_call(raw_func_name, raw_args)
    if func_name != raw_func_name or args != raw_args:
        logger.info("Normalized tool call '%s' -> '%s' with args %s", raw_func_name, func_name, args)

    normalized_call = {"name": func_name, "args": args}

    if func_name not in ALLOWED_TOOLS:
        logger.warning(
            "AI requested disallowed tool '%s' — ignoring (possible prompt injection)", func_name
        )
        error_text = f"Error: tool '{func_name}' is not available."
        return ToolTurnResult(
            tool_result={"result": error_text, "success": False},
            result_text=error_text,
            image_bytes=None,
            normalized_call=normalized_call,
        )

    logger.info("AI Turn %d: requested tool %s with %s", turn, func_name, args)

    image_bytes: Optional[bytes] = None
    if func_name == "list_directory":
        success, result_text = await loop.run_in_executor(
            None, file_manager.list_directory, user_id, args.get("path")
        )
        tool_result = {"result": result_text, "success": success}
    elif func_name == "get_tree_structure":
        success, result_text = await loop.run_in_executor(
            None,
            file_manager.get_tree_structure,
            user_id,
            args.get("path"),
            args.get("max_depth", 3),
            args.get("max_files", 100),
        )
        tool_result = {"result": result_text, "success": success}
    elif func_name == "read_file":
        success, result_text = await loop.run_in_executor(
            None, file_manager.read_file, user_id, args.get("path")
        )
        tool_result = {"result": result_text, "success": success}
    elif func_name == "search_files":
        success, result_text = await loop.run_in_executor(
            None, file_manager.search_files, user_id, args.get("pattern")
        )
        tool_result = {"result": result_text, "success": success}
    elif func_name == "get_file_info":
        success, result_text = await loop.run_in_executor(
            None, file_manager.get_file_info, user_id, args.get("path")
        )
        tool_result = {"result": result_text, "success": success}
    elif func_name == "execute_command":
        success, result_text = await loop.run_in_executor(
            None, file_manager.execute_command, user_id, args.get("command", "")
        )
        tool_result = {"result": result_text, "success": success}
    else:
        dispatched = await dispatch_gemini_tool(
            user_id=user_id,
            func_name=func_name,
            args=args,
            file_manager=file_manager,
            tool_runtime=tool_runtime,
        )
        tool_result = dispatched.to_response()
        result_text = dispatched.result
        image_bytes = dispatched.image_bytes

    logger.info("Tool %s result: %s", func_name, str(result_text)[:100])

    return ToolTurnResult(
        tool_result=tool_result,
        result_text=result_text,
        image_bytes=image_bytes,
        normalized_call=normalized_call,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_ai_tool_loop.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add pocket_desk_agent/ai_types.py pocket_desk_agent/ai_tool_loop.py tests/test_ai_tool_loop.py
git commit -m "feat: extract shared tool-call loop and provider result type

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Refactor GeminiClient onto the shared tool loop + ProviderResult

**Files:**
- Modify: `pocket_desk_agent/gemini_client.py`
- Modify: `pocket_desk_agent/handlers/core.py:299-307,438-445,540-546`
- Modify: `tests/test_config_and_gemini.py:10-12`

**Interfaces:**
- Consumes: `ai_tool_loop.ALLOWED_TOOLS`, `ai_tool_loop.run_tool_turn`, `ai_types.ProviderResult` (Task 2).
- Produces: `GeminiClient.send_message(...) -> ProviderResult` (was `-> str`), `GeminiClient.send_message_with_image(...) -> ProviderResult` (was `-> str`), `GeminiClient.commit_session(user_id: int, history: list) -> None` (new — trims and stores a history list Task 6's AIRouter mutated externally). `gemini_client._ALLOWED_TOOLS` stays available as a re-export (existing test depends on it).

This is a mechanical move + return-type change, not new behavior — verify with the existing test suite rather than new behavior tests. `core.py`'s three call sites get a **temporary** `.text` unwrap here (`response = (await gemini_client.send_message(...)).text`) so the bot keeps working end-to-end with Gemini alone; Task 7 replaces these three lines with the final `ai_router` calls.

- [ ] **Step 1: Remove the moved code from `gemini_client.py` and import from `ai_tool_loop`**

Delete lines 37-110 (`_TOOL_NAME_ALIASES`), lines 281-330 (`_normalize_tool_name` through `_as_bool`), lines 332-438 (`_normalize_tool_args`), lines 441-447 (`_normalize_tool_call`), and lines 659-712 (`_ALLOWED_TOOLS` frozenset literal).

Add near the top, with the other local imports:

```python
from pocket_desk_agent.ai_tool_loop import ALLOWED_TOOLS as _ALLOWED_TOOLS
from pocket_desk_agent.ai_tool_loop import run_tool_turn
from pocket_desk_agent.ai_types import ProviderResult
```

Also change the existing `gemini_actions` import (line 15-18) — `dispatch_gemini_tool` is no longer called directly from this file (it's called from inside `ai_tool_loop.run_tool_turn` now); only `get_gemini_action_tools` (used by `_get_api_tools`) is still needed:

```python
from pocket_desk_agent.gemini_actions import get_gemini_action_tools
```

- [ ] **Step 2: Replace the inline tool-dispatch block in `send_message`**

Find the block starting at `raw_func_name = tool_call.get('name')` (originally line 1113) through the `history.append({"role": "user", "parts": _func_response_parts})` line (originally line 1207), and replace it with:

```python
                raw_func_name = tool_call.get('name')
                raw_args = tool_call.get('args', {}) or {}
                turn_result = await run_tool_turn(
                    user_id=user_id,
                    raw_func_name=raw_func_name,
                    raw_args=raw_args,
                    file_manager=file_manager,
                    tool_runtime=tool_runtime,
                    loop=loop,
                    turn=turn,
                )

                history.append({"role": "model", "parts": [{"functionCall": turn_result.normalized_call}]})

                func_response_parts: list[dict] = [{
                    "functionResponse": {
                        "name": turn_result.normalized_call["name"],
                        "response": turn_result.tool_result,
                    }
                }]
                if turn_result.image_bytes:
                    import base64 as _b64
                    func_response_parts.append({
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": _b64.b64encode(turn_result.image_bytes).decode("ascii"),
                        }
                    })
                history.append({"role": "user", "parts": func_response_parts})
```

(Drop the old `func_name not in _ALLOWED_TOOLS` branch and its `continue` entirely — `run_tool_turn` now handles both the allowed and disallowed cases uniformly, and falling through to the next `for turn` iteration is equivalent to the old `continue` since nothing follows this block in the loop body.)

- [ ] **Step 3: Wrap every `return "<str>"` in `send_message` as a `ProviderResult`**

In `send_message`, change:
- `return _SESSION_EXPIRED_MESSAGE` (both occurrences) → `return ProviderResult(text=_SESSION_EXPIRED_MESSAGE, is_retryable_error=True)`
- `return f"Error contacting Gemini: {err}"` → `return ProviderResult(text=f"Error contacting Gemini: {err}", is_retryable_error=True)`
- `return f"The model blocked this request (reason: {block_reason})."` → `return ProviderResult(text=f"The model blocked this request (reason: {block_reason}).", is_retryable_error=True)`
- `return "The model returned an empty response. Please try rephrasing."` → `return ProviderResult(text="The model returned an empty response. Please try rephrasing.", is_retryable_error=True)`
- `return response_text or "(The model returned an empty message.)"` → `return ProviderResult(text=response_text or "(The model returned an empty message.)")`
- the `max_turns` exceeded return → `return ProviderResult(text=(f"I couldn't complete the request after {max_turns} tool-call turns. Try asking in smaller steps."), is_retryable_error=True)`
- the outer `except Exception as e:` return → `return ProviderResult(text=f"Error: {str(e)}", is_retryable_error=True)`

- [ ] **Step 4: Wrap every `return "<str>"` in `send_message_with_image`**

- `return _SESSION_EXPIRED_MESSAGE` → `return ProviderResult(text=_SESSION_EXPIRED_MESSAGE, is_retryable_error=True)`
- `return f"Error contacting Gemini: {err}"` → `return ProviderResult(text=f"Error contacting Gemini: {err}", is_retryable_error=True)`
- the success/empty branch:
```python
            if response_text:
                history.append({"role": "user", "parts": [{"text": message}]})
                history.append({"role": "model", "parts": [{"text": response_text}]})
                self.sessions[user_id] = _trim_history(history)
                return ProviderResult(text=response_text)
            return ProviderResult(text="No response from Gemini Vision.", is_retryable_error=True)
```
- the outer `except Exception as e:` → `return ProviderResult(text=f"Error processing image: {e}", is_retryable_error=True)`

- [ ] **Step 5: Add `commit_session`**

Add next to `clear_session`:

```python
    def commit_session(self, user_id: int, history: list) -> None:
        """Store an externally-mutated history list, trimmed to the turn limit.

        Used by AIRouter after NvidiaClient runs a turn against the shared
        history it borrowed via ``get_or_create_session`` — GeminiClient
        remains the single owner of ``sessions`` and its trimming policy
        regardless of which provider answered.
        """
        self.sessions[user_id] = _trim_history(history)
```

- [ ] **Step 6: Update `core.py`'s three call sites with a temporary unwrap**

`handlers/core.py:301-307` (`enhance_command`):
```python
        response = (await gemini_client.send_message(
            user_id,
            enhancement_prompt,
            file_manager,
            auth_mode=auth_mode,
            oauth=oauth,
        )).text  # TODO(Task 7): replace with ai_router.send_message(...)
```

`handlers/core.py:438-445` (`handle_message`):
```python
    response = (await gemini_client.send_message(
        user_id,
        user_message,
        file_manager,
        tool_runtime={"bot": context.bot, "chat_id": update.effective_chat.id},
        auth_mode=auth_mode,
        oauth=oauth,
    )).text  # TODO(Task 7): replace with ai_router.send_message(...)
```

`handlers/core.py:540-546` (`_reply_with_gemini_image_analysis`):
```python
    response = (await gemini_client.send_message_with_image(
        user_id,
        caption,
        image_bytes,
        auth_mode=auth_mode,
        oauth=oauth,
    )).text  # TODO(Task 7): replace with ai_router.send_message_with_image(...)
```

- [ ] **Step 7: Update the existing allowlist test's import**

`tests/test_config_and_gemini.py:10-12` currently reads:
```python
def test_allowed_tools_include_canonical_app_tools() -> None:
    assert "open_desktop_app" in gemini_client._ALLOWED_TOOLS
    assert "close_desktop_app" in gemini_client._ALLOWED_TOOLS
```
No change needed to the test body — `gemini_client._ALLOWED_TOOLS` still resolves via the Step 1 re-export. Just confirm it still passes in Step 8.

- [ ] **Step 8: Run the full existing test suite to confirm no regressions**

Run: `pytest tests/ -v`
Expected: PASS — same tests that passed before this task still pass (in particular `tests/test_config_and_gemini.py` and `tests/test_ai_tool_loop.py`). This task changes no observable behavior for a Gemini-only setup; it only changes `GeminiClient`'s Python-level return type, and `core.py`'s three call sites were updated in Step 6 to match.

- [ ] **Step 9: Commit**

```bash
git add pocket_desk_agent/gemini_client.py pocket_desk_agent/handlers/core.py
git commit -m "refactor: move GeminiClient onto shared ai_tool_loop, return ProviderResult

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: NvidiaClient

**Files:**
- Create: `pocket_desk_agent/nvidia_client.py`
- Test: `tests/test_nvidia_client.py`

**Interfaces:**
- Consumes: `ai_history.{gemini_tools_to_openai, gemini_history_to_openai, openai_message_to_gemini_parts}` (Task 1), `ai_tool_loop.run_tool_turn` (Task 2), `ai_types.ProviderResult` (Task 2), `gemini_client.{DEFAULT_SYSTEM_INSTRUCTION, _get_api_tools}` (existing, unchanged), `Config.{NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL, MAX_TOKENS_PER_REQUEST, SYSTEM_PROMPT}` (`NVIDIA_*` land in Task 5 — this task can reference them now since Python resolves `Config.NVIDIA_*` at call time, not import time; **do Task 5 before running this task's tests**, or add the three attributes to `Config` as plain class attributes first — see Step 0).
- Produces: `NvidiaClient.is_configured() -> bool`, `NvidiaClient.send_message(user_id, message, file_manager, history, tool_runtime=None) -> ProviderResult`, `NvidiaClient.send_message_with_image(user_id, message, image_bytes, history) -> ProviderResult`. Task 6 (AIRouter) is the only caller.

**Note on ordering:** this task is written assuming Task 5 (Config additions) already landed. If executing tasks out of order, do Task 5 first — `NvidiaClient.__init__` reads `Config.NVIDIA_MODEL` at construction time.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_nvidia_client.py
import asyncio

from pocket_desk_agent.config import Config
from pocket_desk_agent.nvidia_client import NvidiaClient


class _FakeFileManager:
    def get_current_dir(self, user_id: int) -> str:
        return "/home/user"

    def list_directory(self, user_id: int, path):
        return True, "a.txt"


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict, headers=None):
        self.status_code = status_code
        self._json = json_data
        self.text = str(json_data)
        self.headers = headers or {}

    def json(self):
        return self._json


def _set_nvidia_config(monkeypatch, key: str = "nvapi-test-key") -> None:
    monkeypatch.setattr(Config, "NVIDIA_API_KEY", key)
    monkeypatch.setattr(Config, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setattr(Config, "NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
    monkeypatch.setattr(Config, "MAX_TOKENS_PER_REQUEST", 8000)
    monkeypatch.setattr(Config, "SYSTEM_PROMPT", "")


def test_is_configured_reflects_api_key(monkeypatch) -> None:
    monkeypatch.setattr(Config, "NVIDIA_API_KEY", "")
    assert NvidiaClient().is_configured() is False

    monkeypatch.setattr(Config, "NVIDIA_API_KEY", "nvapi-abc")
    assert NvidiaClient().is_configured() is True


def test_send_message_without_key_is_retryable(monkeypatch) -> None:
    monkeypatch.setattr(Config, "NVIDIA_API_KEY", "")
    client = NvidiaClient()

    result = asyncio.run(client.send_message(1, "hi", _FakeFileManager(), history=[]))

    assert result.is_retryable_error is True


def test_send_message_plain_text_reply(monkeypatch) -> None:
    _set_nvidia_config(monkeypatch)
    client = NvidiaClient()

    def fake_call_raw(self, payload):
        assert payload["model"] == "meta/llama-3.3-70b-instruct"
        return {"choices": [{"message": {"role": "assistant", "content": "Hello!"}}]}

    monkeypatch.setattr(NvidiaClient, "_call_raw", fake_call_raw)

    history: list = []
    result = asyncio.run(client.send_message(1, "hi", _FakeFileManager(), history=history))

    assert result.text == "Hello!"
    assert result.is_retryable_error is False
    assert history[-1] == {"role": "model", "parts": [{"text": "Hello!"}]}


def test_send_message_runs_one_tool_call_round_trip(monkeypatch) -> None:
    _set_nvidia_config(monkeypatch)
    client = NvidiaClient()

    calls = {"n": 0}

    def fake_call_raw(self, payload):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "list_directory", "arguments": "{}"},
                        }],
                    }
                }]
            }
        return {"choices": [{"message": {"role": "assistant", "content": "Here: a.txt"}}]}

    monkeypatch.setattr(NvidiaClient, "_call_raw", fake_call_raw)

    history: list = []
    result = asyncio.run(client.send_message(1, "list my files", _FakeFileManager(), history=history))

    assert calls["n"] == 2
    assert result.text == "Here: a.txt"
    assert result.is_retryable_error is False
    # history has: user msg, model(functionCall), user(functionResponse), model(final text)
    assert history[1]["parts"][0]["functionCall"]["name"] == "list_directory"
    assert "functionResponse" in history[2]["parts"][0]


def test_send_message_429_is_retryable(monkeypatch) -> None:
    _set_nvidia_config(monkeypatch)
    client = NvidiaClient()

    import pocket_desk_agent.nvidia_client as nvidia_client_module
    monkeypatch.setattr(nvidia_client_module.time, "sleep", lambda _seconds: None)

    def fake_post(url, headers, json, timeout):
        return _FakeResponse(429, {"error": "rate limited"})

    monkeypatch.setattr(nvidia_client_module.requests, "post", fake_post)

    result = asyncio.run(client.send_message(1, "hi", _FakeFileManager(), history=[]))

    assert result.is_retryable_error is True
    assert "429" in result.text or "rate" in result.text.lower() or "Error contacting NVIDIA" in result.text


def test_send_message_with_image_success(monkeypatch) -> None:
    _set_nvidia_config(monkeypatch)
    client = NvidiaClient()

    def fake_call_raw(self, payload):
        content_types = [c["type"] for c in payload["messages"][-1]["content"]]
        assert "image_url" in content_types
        return {"choices": [{"message": {"role": "assistant", "content": "A cat."}}]}

    monkeypatch.setattr(NvidiaClient, "_call_raw", fake_call_raw)

    history: list = []
    result = asyncio.run(
        client.send_message_with_image(1, "what is this?", b"fake-jpeg-bytes", history=history)
    )

    assert result.text == "A cat."
    assert result.is_retryable_error is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_nvidia_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pocket_desk_agent.nvidia_client'`

- [ ] **Step 3: Implement `nvidia_client.py`**

```python
"""NVIDIA NIM (build.nvidia.com) AI client — OpenAI-compatible fallback backend.

Mirrors GeminiClient's external send_message/send_message_with_image shape
so AIRouter can treat both providers uniformly. This client does NOT own
conversation history — the canonical history lives in GeminiClient.sessions
(Gemini's shape); AIRouter passes that shared list in via ``history`` on
every call, this client converts it to OpenAI ``messages`` via ai_history,
and converts its own response back into Gemini parts before appending —
so a fallback mid-conversation stays consistent regardless of which
provider answers next.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from typing import Any, Optional

import requests

from pocket_desk_agent.ai_history import (
    gemini_history_to_openai,
    gemini_tools_to_openai,
    openai_message_to_gemini_parts,
)
from pocket_desk_agent.ai_tool_loop import run_tool_turn
from pocket_desk_agent.ai_types import ProviderResult
from pocket_desk_agent.config import Config
from pocket_desk_agent.gemini_client import DEFAULT_SYSTEM_INSTRUCTION, _get_api_tools

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


def _retry_wait(resp: requests.Response, attempt: int) -> float:
    """Seconds to wait before retrying a 429 response. Respects Retry-After."""
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            pass
    return min(5 * (2 ** attempt), 60)


class NvidiaClient:
    """NVIDIA NIM chat-completions client with tool-calling support."""

    def __init__(self) -> None:
        self.model = Config.NVIDIA_MODEL

    def is_configured(self) -> bool:
        return bool(Config.NVIDIA_API_KEY)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {Config.NVIDIA_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _call_raw(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{Config.NVIDIA_BASE_URL.rstrip('/')}/chat/completions"
        last_error = "Unknown error"
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = requests.post(url, headers=self._headers(), json=payload, timeout=60)
                if resp.status_code == 200:
                    return resp.json()
                last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                if resp.status_code == 429 and attempt < _MAX_RETRIES:
                    wait = _retry_wait(resp, attempt)
                    logger.info(
                        "NVIDIA rate limited (429); retrying in %.0fs (attempt %d/%d)",
                        wait, attempt + 1, _MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue
                return {"error": last_error}
            except Exception as exc:
                last_error = str(exc)
                break
        return {"error": last_error}

    async def send_message(
        self,
        user_id: int,
        message: str,
        file_manager: Any,
        history: list,
        tool_runtime: Optional[dict[str, Any]] = None,
    ) -> ProviderResult:
        """Run a tool-calling turn loop against NVIDIA, mutating ``history`` in place."""
        if not self.is_configured():
            return ProviderResult(text="NVIDIA is not configured (no API key).", is_retryable_error=True)

        try:
            loop = asyncio.get_running_loop()
            current_dir = file_manager.get_current_dir(user_id)
            full_message = f"[Current Directory: {current_dir}]\n\n{message}"
            base_history_len = len(history)
            history.append({"role": "user", "parts": [{"text": full_message}]})

            tools = gemini_tools_to_openai(_get_api_tools()[0]["functionDeclarations"])
            system_prompt = Config.SYSTEM_PROMPT or DEFAULT_SYSTEM_INSTRUCTION

            max_turns = 10
            for turn in range(max_turns):
                messages = gemini_history_to_openai(history, system_prompt)
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "max_tokens": Config.MAX_TOKENS_PER_REQUEST,
                }
                data = await loop.run_in_executor(None, self._call_raw, payload)

                if data.get("error"):
                    logger.error("NVIDIA API error on turn %d: %s", turn, data["error"])
                    del history[base_history_len:]
                    return ProviderResult(
                        text=f"Error contacting NVIDIA: {data['error']}", is_retryable_error=True
                    )

                choices = data.get("choices", [])
                if not choices:
                    logger.warning("NVIDIA returned no choices on turn %d: %s", turn, str(data)[:400])
                    del history[base_history_len:]
                    return ProviderResult(text="NVIDIA returned an empty response.", is_retryable_error=True)

                assistant_message = choices[0].get("message", {}) or {}
                parts = openai_message_to_gemini_parts(assistant_message)
                tool_calls = assistant_message.get("tool_calls") or []

                if not tool_calls:
                    response_text = "".join(p.get("text", "") for p in parts if "text" in p)
                    history.append({"role": "model", "parts": parts or [{"text": ""}]})
                    return ProviderResult(text=response_text or "(NVIDIA returned an empty message.)")

                history.append({"role": "model", "parts": parts})

                # NVIDIA can request several tool calls in one turn; run them
                # in order and collect all responses into ONE user-role
                # history entry so roles keep strictly alternating (Gemini's
                # own history shape assumes exactly that).
                response_parts: list[dict] = []
                for tool_call in tool_calls:
                    function = tool_call.get("function", {}) or {}
                    try:
                        call_args = json.loads(function.get("arguments") or "{}")
                    except (ValueError, TypeError):
                        call_args = {}

                    turn_result = await run_tool_turn(
                        user_id=user_id,
                        raw_func_name=function.get("name"),
                        raw_args=call_args,
                        file_manager=file_manager,
                        tool_runtime=tool_runtime,
                        loop=loop,
                        turn=turn,
                    )

                    response_parts.append({
                        "functionResponse": {
                            "name": turn_result.normalized_call["name"],
                            "response": turn_result.tool_result,
                        }
                    })
                    if turn_result.image_bytes:
                        response_parts.append({
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": base64.b64encode(turn_result.image_bytes).decode("ascii"),
                            }
                        })

                history.append({"role": "user", "parts": response_parts})

            del history[base_history_len:]
            return ProviderResult(
                text=(
                    f"I couldn't complete the request after {max_turns} tool-call turns. "
                    "Try asking in smaller steps."
                ),
                is_retryable_error=True,
            )
        except Exception as exc:
            logger.exception("Error in NvidiaClient.send_message: %s", exc)
            return ProviderResult(text=f"Error: {exc}", is_retryable_error=True)

    async def send_message_with_image(
        self,
        user_id: int,
        message: str,
        image_bytes: bytes,
        history: list,
    ) -> ProviderResult:
        """Send a message with an image to NVIDIA for vision analysis (no tools).

        Not every NIM model supports vision — an unsupported model simply
        fails here like any other provider error, and AIRouter's normal
        fallback handles it.
        """
        if not self.is_configured():
            return ProviderResult(text="NVIDIA is not configured (no API key).", is_retryable_error=True)

        try:
            loop = asyncio.get_running_loop()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            system_prompt = Config.SYSTEM_PROMPT or DEFAULT_SYSTEM_INSTRUCTION
            messages = gemini_history_to_openai(history, system_prompt)
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            })
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "top_p": 0.95,
                "max_tokens": Config.MAX_TOKENS_PER_REQUEST,
            }
            data = await loop.run_in_executor(None, self._call_raw, payload)

            if data.get("error"):
                return ProviderResult(text=f"Error contacting NVIDIA: {data['error']}", is_retryable_error=True)

            choices = data.get("choices", [])
            if not choices:
                return ProviderResult(text="NVIDIA returned an empty response.", is_retryable_error=True)

            response_text = (choices[0].get("message", {}) or {}).get("content") or ""
            if response_text:
                history.append({"role": "user", "parts": [{"text": message}]})
                history.append({"role": "model", "parts": [{"text": response_text}]})
                return ProviderResult(text=response_text)
            return ProviderResult(text="No response from NVIDIA Vision.", is_retryable_error=True)
        except Exception as exc:
            logger.error("Error in NvidiaClient.send_message_with_image: %s", exc, exc_info=True)
            return ProviderResult(text=f"Error processing image: {exc}", is_retryable_error=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_nvidia_client.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add pocket_desk_agent/nvidia_client.py tests/test_nvidia_client.py
git commit -m "feat: add NvidiaClient (NVIDIA NIM OpenAI-compatible AI backend)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: NVIDIA + provider-order config

**Files:**
- Modify: `pocket_desk_agent/config.py`
- Modify: `pocket_desk_agent/configure.py:76-106` (`_INI_ENV_MAP`)
- Test: `tests/test_config_and_gemini.py`, `tests/test_configure_smartplug.py`-style new file `tests/test_config_nvidia.py`

**Interfaces:**
- Produces: `Config.NVIDIA_API_KEY: str`, `Config.NVIDIA_BASE_URL: str`, `Config.NVIDIA_MODEL: str`, `Config.AI_PROVIDER_ORDER: list[str]`. Tasks 4, 6, 8, 9, 10 all read these.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config_nvidia.py
from pocket_desk_agent import config, configure


def test_nvidia_defaults(monkeypatch) -> None:
    for var in ("NVIDIA_API_KEY", "NVIDIA_BASE_URL", "NVIDIA_MODEL", "AI_PROVIDER_ORDER"):
        monkeypatch.delenv(var, raising=False)

    config.Config.load()

    assert config.Config.NVIDIA_API_KEY == ""
    assert config.Config.NVIDIA_BASE_URL == "https://integrate.api.nvidia.com/v1"
    assert config.Config.NVIDIA_MODEL == "meta/llama-3.3-70b-instruct"
    assert config.Config.AI_PROVIDER_ORDER == ["gemini", "nvidia"]


def test_ai_provider_order_parses_valid_csv(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER_ORDER", "nvidia,gemini")
    config.Config.load()
    assert config.Config.AI_PROVIDER_ORDER == ["nvidia", "gemini"]


def test_ai_provider_order_drops_unknown_tokens(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER_ORDER", "nvidia,bogus,gemini")
    config.Config.load()
    assert config.Config.AI_PROVIDER_ORDER == ["nvidia", "gemini"]


def test_ai_provider_order_falls_back_when_empty_after_filtering(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER_ORDER", "bogus,also_bogus")
    config.Config.load()
    assert config.Config.AI_PROVIDER_ORDER == ["gemini", "nvidia"]


def test_ini_env_map_covers_nvidia_fields() -> None:
    env_map = configure._INI_ENV_MAP
    assert env_map[("credentials", "default", "nvidia_api_key")] == "NVIDIA_API_KEY"
    assert env_map[("config", "bot", "nvidia_model")] == "NVIDIA_MODEL"
    assert env_map[("config", "bot", "ai_provider_order")] == "AI_PROVIDER_ORDER"


def test_load_into_environ_reads_nvidia_ini_values(tmp_path, monkeypatch) -> None:
    cfg_dir = tmp_path / ".pdagent"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "credentials").write_text(
        "[default]\nnvidia_api_key = nvapi-test\n", encoding="utf-8"
    )
    (cfg_dir / "config").write_text(
        "[bot]\nnvidia_model = meta/llama-3.1-70b-instruct\nai_provider_order = nvidia,gemini\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(configure, "app_path_candidates", lambda name: (cfg_dir / name,))
    for var in ("NVIDIA_API_KEY", "NVIDIA_MODEL", "AI_PROVIDER_ORDER"):
        monkeypatch.delenv(var, raising=False)

    configure.load_into_environ()

    import os

    assert os.environ["NVIDIA_API_KEY"] == "nvapi-test"
    assert os.environ["NVIDIA_MODEL"] == "meta/llama-3.1-70b-instruct"
    assert os.environ["AI_PROVIDER_ORDER"] == "nvidia,gemini"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config_nvidia.py -v`
Expected: FAIL — `AttributeError: type object 'Config' has no attribute 'NVIDIA_API_KEY'`

- [ ] **Step 3: Add the fields and loader logic to `config.py`**

Add class attributes (near `GEMINI_MODEL`):

```python
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "meta/llama-3.3-70b-instruct"
    AI_PROVIDER_ORDER: list[str] = ["gemini", "nvidia"]
```

Add a module-level helper near `_parse_user_ids`:

```python
_VALID_AI_PROVIDERS = ("gemini", "nvidia")


def _parse_provider_order(raw_value: str) -> list[str]:
    """Parse a comma-separated AI provider order, dropping unknown tokens."""
    order = [p.strip().lower() for p in raw_value.split(",") if p.strip()]
    order = [p for p in order if p in _VALID_AI_PROVIDERS]
    return order or list(_VALID_AI_PROVIDERS)
```

Add to `Config.load()` (near `cls.GEMINI_MODEL`):

```python
        cls.NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
        cls.NVIDIA_BASE_URL = (
            os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip()
            or "https://integrate.api.nvidia.com/v1"
        )
        cls.NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct").strip() or "meta/llama-3.3-70b-instruct"
        cls.AI_PROVIDER_ORDER = _parse_provider_order(
            os.getenv("AI_PROVIDER_ORDER", ",".join(_VALID_AI_PROVIDERS))
        )
```

- [ ] **Step 4: Add the INI mapping in `configure.py`**

In `_INI_ENV_MAP`, add:

```python
    ("credentials", "default", "nvidia_api_key"):     "NVIDIA_API_KEY",
```
next to `google_api_key`, and:
```python
    ("config", "bot", "nvidia_model"):          "NVIDIA_MODEL",
    ("config", "bot", "ai_provider_order"):     "AI_PROVIDER_ORDER",
```
next to `gemini_model`. (`NVIDIA_BASE_URL` is intentionally env-var-only — no wizard/chat-command surface for it per the design spec; power users override it directly in `~/.pdagent/config` or the shell.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_config_nvidia.py tests/test_config_and_gemini.py tests/test_configure_smartplug.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pocket_desk_agent/config.py pocket_desk_agent/configure.py tests/test_config_nvidia.py
git commit -m "feat: add NVIDIA + AI_PROVIDER_ORDER config

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: AIRouter

**Files:**
- Create: `pocket_desk_agent/ai_router.py`
- Test: `tests/test_ai_router.py`

**Interfaces:**
- Consumes: `GeminiClient` (needs `.send_message`, `.send_message_with_image`, `.get_or_create_session`, `.commit_session`, `.clear_session`, `.sessions` — all present after Task 3), `NvidiaClient` (Task 4), `Config.AI_PROVIDER_ORDER` (Task 5), an `auth_client`-shaped object with `.is_authenticated(user_id) -> bool`.
- Produces: `AIRouter(gemini, nvidia, auth_client)`, `.configured_providers(user_id: int) -> list[str]`, `async .send_message(user_id, message, file_manager, tool_runtime=None, auth_mode=None, oauth=None) -> str`, `async .send_message_with_image(user_id, message, image_bytes, auth_mode=None, oauth=None) -> str`, `.clear_session(user_id)`, `.sessions` (property). Task 7 (`handlers/_shared.py`, `handlers/core.py`) is the sole caller of this class in production code.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ai_router.py
import asyncio

from pocket_desk_agent.ai_router import AIRouter
from pocket_desk_agent.ai_types import ProviderResult
from pocket_desk_agent.config import Config


class _FakeAuthClient:
    def __init__(self, authenticated_users: set[int] | None = None) -> None:
        self._authenticated = authenticated_users or set()

    def is_authenticated(self, user_id: int) -> bool:
        return user_id in self._authenticated


class _FakeGemini:
    def __init__(self, result: ProviderResult) -> None:
        self.result = result
        self.sessions: dict[int, list] = {}
        self.calls = 0

    def get_or_create_session(self, user_id: int) -> list:
        return self.sessions.setdefault(user_id, [])

    def commit_session(self, user_id: int, history: list) -> None:
        self.sessions[user_id] = history

    def clear_session(self, user_id: int) -> None:
        self.sessions[user_id] = []

    async def send_message(self, user_id, message, file_manager, tool_runtime=None, auth_mode=None, oauth=None):
        self.calls += 1
        return self.result

    async def send_message_with_image(self, user_id, message, image_bytes, auth_mode=None, oauth=None):
        self.calls += 1
        return self.result


class _FakeNvidia:
    def __init__(self, result: ProviderResult, configured: bool = True) -> None:
        self.result = result
        self._configured = configured
        self.calls = 0

    def is_configured(self) -> bool:
        return self._configured

    async def send_message(self, user_id, message, file_manager, history, tool_runtime=None):
        self.calls += 1
        return self.result

    async def send_message_with_image(self, user_id, message, image_bytes, history):
        self.calls += 1
        return self.result


def test_configured_providers_skips_unauthenticated_gemini(monkeypatch) -> None:
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    router = AIRouter(_FakeGemini(ProviderResult(text="x")), _FakeNvidia(ProviderResult(text="x")), _FakeAuthClient())

    assert router.configured_providers(user_id=1) == ["nvidia"]


def test_configured_providers_skips_unconfigured_nvidia(monkeypatch) -> None:
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    router = AIRouter(
        _FakeGemini(ProviderResult(text="x")),
        _FakeNvidia(ProviderResult(text="x"), configured=False),
        _FakeAuthClient({1}),
    )

    assert router.configured_providers(user_id=1) == ["gemini"]


def test_send_message_returns_gemini_answer_without_prefix(monkeypatch) -> None:
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    gemini = _FakeGemini(ProviderResult(text="Gemini says hi"))
    router = AIRouter(gemini, _FakeNvidia(ProviderResult(text="unused")), _FakeAuthClient({1}))

    result = asyncio.run(router.send_message(1, "hi", file_manager=None))

    assert result == "Gemini says hi"
    assert gemini.calls == 1


def test_send_message_falls_back_to_nvidia_on_retryable_gemini_error(monkeypatch) -> None:
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    gemini = _FakeGemini(ProviderResult(text="quota exhausted", is_retryable_error=True))
    nvidia = _FakeNvidia(ProviderResult(text="NVIDIA says hi"))
    router = AIRouter(gemini, nvidia, _FakeAuthClient({1}))

    result = asyncio.run(router.send_message(1, "hi", file_manager=None))

    assert "NVIDIA says hi" in result
    assert "fallback" in result.lower()
    assert gemini.calls == 1
    assert nvidia.calls == 1


def test_send_message_returns_last_error_when_all_providers_fail(monkeypatch) -> None:
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    gemini = _FakeGemini(ProviderResult(text="gemini down", is_retryable_error=True))
    nvidia = _FakeNvidia(ProviderResult(text="nvidia down too", is_retryable_error=True))
    router = AIRouter(gemini, nvidia, _FakeAuthClient({1}))

    result = asyncio.run(router.send_message(1, "hi", file_manager=None))

    assert result == "nvidia down too"


def test_send_message_no_provider_configured(monkeypatch) -> None:
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    router = AIRouter(
        _FakeGemini(ProviderResult(text="x")),
        _FakeNvidia(ProviderResult(text="x"), configured=False),
        _FakeAuthClient(set()),
    )

    result = asyncio.run(router.send_message(1, "hi", file_manager=None))

    assert "No AI provider is configured" in result


def test_send_message_with_image_falls_back_too(monkeypatch) -> None:
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    gemini = _FakeGemini(ProviderResult(text="down", is_retryable_error=True))
    nvidia = _FakeNvidia(ProviderResult(text="NVIDIA saw the image"))
    router = AIRouter(gemini, nvidia, _FakeAuthClient({1}))

    result = asyncio.run(router.send_message_with_image(1, "what is this", b"bytes"))

    assert "NVIDIA saw the image" in result


def test_clear_session_and_sessions_passthrough(monkeypatch) -> None:
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    gemini = _FakeGemini(ProviderResult(text="x"))
    gemini.sessions[1] = [{"role": "user", "parts": [{"text": "hi"}]}]
    router = AIRouter(gemini, _FakeNvidia(ProviderResult(text="x")), _FakeAuthClient({1}))

    assert 1 in router.sessions
    router.clear_session(1)
    assert router.sessions[1] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ai_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pocket_desk_agent.ai_router'`

- [ ] **Step 3: Implement `ai_router.py`**

```python
"""Routes AI chat/vision requests across configured providers, falling
back to the next one in ``Config.AI_PROVIDER_ORDER`` on a retryable error.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from pocket_desk_agent.ai_types import ProviderResult
from pocket_desk_agent.config import Config
from pocket_desk_agent.constants import AUTH_MODE_APIKEY

logger = logging.getLogger(__name__)

_PROVIDER_LABELS = {"gemini": "Gemini", "nvidia": "NVIDIA"}

_NO_PROVIDER_MESSAGE = (
    "No AI provider is configured. Use /login to sign in to Gemini, "
    "or /setnvidiakey <key> to configure the NVIDIA fallback."
)


class AIRouter:
    """Tries each configured AI provider in order, falling back on failure."""

    def __init__(self, gemini: Any, nvidia: Any, auth_client: Any) -> None:
        self.gemini = gemini
        self.nvidia = nvidia
        self._auth_client = auth_client

    def _provider_order(self) -> list[str]:
        order = [p for p in Config.AI_PROVIDER_ORDER if p in ("gemini", "nvidia")]
        return order or ["gemini", "nvidia"]

    def _is_provider_configured(self, provider: str, user_id: int) -> bool:
        if provider == "gemini":
            if Config.GEMINI_AUTH_MODE == AUTH_MODE_APIKEY:
                return bool(Config.GOOGLE_API_KEY)
            return bool(self._auth_client.is_authenticated(user_id))
        if provider == "nvidia":
            return bool(self.nvidia.is_configured())
        return False

    def configured_providers(self, user_id: int) -> list[str]:
        return [p for p in self._provider_order() if self._is_provider_configured(p, user_id)]

    def _prefix_if_fallback(self, primary: str, used: str, used_fallback: bool) -> str:
        if not used_fallback:
            return ""
        return (
            f"⚠️ {_PROVIDER_LABELS.get(primary, primary)} unavailable — "
            f"answered via {_PROVIDER_LABELS.get(used, used)} fallback.\n\n"
        )

    async def send_message(
        self,
        user_id: int,
        message: str,
        file_manager: Any,
        tool_runtime: Optional[dict[str, Any]] = None,
        auth_mode: Optional[str] = None,
        oauth: Optional[Any] = None,
    ) -> str:
        providers = self.configured_providers(user_id)
        if not providers:
            return _NO_PROVIDER_MESSAGE

        last_result: Optional[ProviderResult] = None
        used_fallback = False
        for index, provider in enumerate(providers):
            if provider == "gemini":
                result: ProviderResult = await self.gemini.send_message(
                    user_id, message, file_manager,
                    tool_runtime=tool_runtime, auth_mode=auth_mode, oauth=oauth,
                )
            else:
                history = self.gemini.get_or_create_session(user_id)
                result = await self.nvidia.send_message(
                    user_id, message, file_manager, history=history, tool_runtime=tool_runtime,
                )
                self.gemini.commit_session(user_id, history)

            if not result.is_retryable_error:
                return self._prefix_if_fallback(providers[0], provider, used_fallback) + result.text

            logger.warning(
                "AIRouter.send_message: provider '%s' failed retryably for user %d: %s",
                provider, user_id, result.text[:200],
            )
            last_result = result
            used_fallback = True

        return last_result.text if last_result else _NO_PROVIDER_MESSAGE

    async def send_message_with_image(
        self,
        user_id: int,
        message: str,
        image_bytes: bytes,
        auth_mode: Optional[str] = None,
        oauth: Optional[Any] = None,
    ) -> str:
        providers = self.configured_providers(user_id)
        if not providers:
            return _NO_PROVIDER_MESSAGE

        last_result: Optional[ProviderResult] = None
        used_fallback = False
        for provider in providers:
            if provider == "gemini":
                result: ProviderResult = await self.gemini.send_message_with_image(
                    user_id, message, image_bytes, auth_mode=auth_mode, oauth=oauth,
                )
            else:
                history = self.gemini.get_or_create_session(user_id)
                result = await self.nvidia.send_message_with_image(
                    user_id, message, image_bytes, history=history,
                )
                self.gemini.commit_session(user_id, history)

            if not result.is_retryable_error:
                return self._prefix_if_fallback(providers[0], provider, used_fallback) + result.text

            logger.warning(
                "AIRouter.send_message_with_image: provider '%s' failed retryably for user %d: %s",
                provider, user_id, result.text[:200],
            )
            last_result = result
            used_fallback = True

        return last_result.text if last_result else _NO_PROVIDER_MESSAGE

    def clear_session(self, user_id: int) -> None:
        self.gemini.clear_session(user_id)

    @property
    def sessions(self) -> dict:
        return self.gemini.sessions
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ai_router.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add pocket_desk_agent/ai_router.py tests/test_ai_router.py
git commit -m "feat: add AIRouter for cross-provider AI fallback

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Wire AIRouter into the bot, fix the auth-gate bug

**Files:**
- Modify: `pocket_desk_agent/handlers/_shared.py`
- Modify: `pocket_desk_agent/handlers/__init__.py`
- Modify: `pocket_desk_agent/handlers/core.py`
- Test: `tests/test_ai_router_wiring.py`

**Interfaces:**
- Consumes: `AIRouter`, `GeminiClient`, `NvidiaClient` (Tasks 3, 4, 6).
- Produces: `pocket_desk_agent.handlers._shared.ai_router` (module-level singleton, alongside the existing `gemini_client`/`auth_client`/`file_manager`).

This task removes the Task 3 `.text` shim and fixes the bug the design spec identified: `handle_message`, `handle_photo`, `handle_image_document`, and `enhance_command` currently gate on `auth_client.is_authenticated(user_id)` — meaning a message never even reaches Gemini's own quota/session-expiry handling if OAuth is logged out, even when NVIDIA is configured and would answer fine.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ai_router_wiring.py
from pocket_desk_agent.handlers import _shared
from pocket_desk_agent.ai_router import AIRouter


def test_shared_ai_router_is_wired_to_shared_clients() -> None:
    assert isinstance(_shared.ai_router, AIRouter)
    assert _shared.ai_router.gemini is _shared.gemini_client
    assert _shared.ai_router.nvidia is _shared.nvidia_client
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_router_wiring.py -v`
Expected: FAIL with `AttributeError: module 'pocket_desk_agent.handlers._shared' has no attribute 'ai_router'`

- [ ] **Step 3: Add the singletons to `_shared.py`**

In `handlers/_shared.py`, change:
```python
from pocket_desk_agent.gemini_client import GeminiClient
```
to:
```python
from pocket_desk_agent.ai_router import AIRouter
from pocket_desk_agent.gemini_client import GeminiClient
from pocket_desk_agent.nvidia_client import NvidiaClient
```
and change:
```python
auth_client = AntigravityAuth()
gemini_client = GeminiClient()
file_manager = FileManager()
```
to:
```python
auth_client = AntigravityAuth()
gemini_client = GeminiClient()
nvidia_client = NvidiaClient()
ai_router = AIRouter(gemini_client, nvidia_client, auth_client)
file_manager = FileManager()
```

- [ ] **Step 4: Export it from `handlers/__init__.py`**

In the `from pocket_desk_agent.handlers._shared import (...)` block, add `ai_router` and `nvidia_client` next to `gemini_client`:
```python
from pocket_desk_agent.handlers._shared import (  # noqa: F401
    safe_command,
    record_action_if_active,
    auth_client,
    gemini_client,
    nvidia_client,
    ai_router,
    file_manager,
    recording_sessions,
    build_monitor_state,
    build_screenshot_tasks,
    PYWINAUTO_AVAILABLE,
)
```

- [ ] **Step 5: Run the wiring test to verify it passes**

Run: `pytest tests/test_ai_router_wiring.py -v`
Expected: PASS

- [ ] **Step 6: Switch `core.py` to `ai_router` and fix the four auth gates**

Change the import block:
```python
from pocket_desk_agent.handlers._shared import (
    auth_client,
    ai_router,
    file_manager,
    record_action_if_active,
    register_media_group_item,
)
```
(`gemini_client` is no longer imported directly in `core.py`.)

`new_command` (was `gemini_client.clear_session(user_id)`):
```python
    ai_router.clear_session(user_id)
```

`status_command` (was `user_id in gemini_client.sessions`):
```python
    has_session = user_id in ai_router.sessions
```

`enhance_command` — replace the auth gate and the Task-3 shim:
```python
    # Check that at least one AI provider is usable
    if not ai_router.configured_providers(user_id):
        await update.message.reply_text(
            "No AI provider is configured. Use /login to sign in to Gemini, "
            "or /setnvidiakey <key> to configure the NVIDIA fallback."
        )
        return
```
and:
```python
        auth_mode, oauth = _get_gemini_auth_context(user_id)
        response = await ai_router.send_message(
            user_id,
            enhancement_prompt,
            file_manager,
            auth_mode=auth_mode,
            oauth=oauth,
        )
```

`handle_message` — replace:
```python
    # Check authentication only after non-Gemini reply workflows are handled.
    if not auth_client.is_authenticated(user_id):
        await update.message.reply_text(
            "🔓 Gemini AI requires authentication (session expired or signed out).\n\n"
            "Use /login to sign in again."
        )
        return
```
with:
```python
    # Check that at least one AI provider is usable — Gemini OAuth login
    # OR a configured NVIDIA key, not specifically "Gemini is logged in".
    if not ai_router.configured_providers(user_id):
        await update.message.reply_text(
            "🔓 No AI provider is available (Gemini session expired/signed out, "
            "and no NVIDIA fallback configured).\n\n"
            "Use /login to sign in to Gemini, or /setnvidiakey <key> for the NVIDIA fallback."
        )
        return
```
and:
```python
    auth_mode, oauth = _get_gemini_auth_context(user_id)

    response = await ai_router.send_message(
        user_id,
        user_message,
        file_manager,
        tool_runtime={"bot": context.bot, "chat_id": update.effective_chat.id},
        auth_mode=auth_mode,
        oauth=oauth,
    )
```

`handle_photo` and `handle_image_document` — both currently have this identical block; replace each occurrence:
```python
    if not auth_client.is_authenticated(user_id):
        await update.message.reply_text(
            "🔓 Gemini AI requires authentication (session expired or signed out).\n\n"
            "Use /login to sign in again."
        )
        return
```
with:
```python
    if not ai_router.configured_providers(user_id):
        await update.message.reply_text(
            "🔓 No AI provider is available (Gemini session expired/signed out, "
            "and no NVIDIA fallback configured).\n\n"
            "Use /login to sign in to Gemini, or /setnvidiakey <key> for the NVIDIA fallback."
        )
        return
```

`_reply_with_gemini_image_analysis`:
```python
    auth_mode, oauth = _get_gemini_auth_context(user_id)
    response = await ai_router.send_message_with_image(
        user_id,
        caption,
        image_bytes,
        auth_mode=auth_mode,
        oauth=oauth,
    )
    await update.message.reply_text(response)
```

- [ ] **Step 7: Run the full test suite**

Run: `pytest tests/ -v`
Expected: PASS — no regressions. `auth_client` is still imported in `core.py` (`start_command`, `status_command` still use `auth_client.is_authenticated`/`get_user_info` for the Gemini-specific parts of `/start` and `/status` — those are unchanged and correct, since they're reporting Gemini's *own* auth state, not gating whether AI chat works at all).

- [ ] **Step 8: Commit**

```bash
git add pocket_desk_agent/handlers/_shared.py pocket_desk_agent/handlers/__init__.py pocket_desk_agent/handlers/core.py tests/test_ai_router_wiring.py
git commit -m "feat: wire AIRouter into the bot, fix Gemini-only auth gate bug

handle_message/handle_photo/handle_image_document/enhance_command used to
refuse to even try NVIDIA fallback when Gemini OAuth was logged out.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: `/setnvidiakey` command

**Files:**
- Modify: `pocket_desk_agent/handlers/auth.py`
- Modify: `pocket_desk_agent/handlers/__init__.py`
- Modify: `pocket_desk_agent/command_map.py`
- Modify: `docs/COMMANDS.md`, `README.md`
- Test: `tests/test_setnvidiakey_command.py`

**Interfaces:**
- Produces: `handlers.auth.setnvidiakey_command(update, context)` registered as `/setnvidiakey`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_setnvidiakey_command.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_setnvidiakey_command.py -v`
Expected: FAIL with `AttributeError: module 'pocket_desk_agent.handlers.auth' has no attribute 'setnvidiakey_command'`

- [ ] **Step 3: Implement the handler in `auth.py`**

Add to `pocket_desk_agent/handlers/auth.py` (needs `configparser` and the `configure` module):

```python
async def setnvidiakey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setnvidiakey — save the NVIDIA NIM API key from chat.

    Writes to the same ~/.pdagent/credentials file `pdagent configure` uses,
    reloads Config immediately, and deletes the user's message afterward
    (best-effort) so the raw key doesn't sit in chat history.
    """
    if not update.effective_user or not update.message:
        return

    if not context.args:
        await update.message.reply_text(
            "ℹ️ *Usage:* `/setnvidiakey <key>`\n\n"
            "Get a key from build.nvidia.com (NVIDIA NIM). Keys start with `nvapi-`.\n\n"
            "This lets the bot fall back to NVIDIA when Gemini's quota runs out. "
            "See /aiprovider to control which provider is tried first.",
            parse_mode="Markdown",
        )
        return

    key = context.args[0].strip()
    if not key.startswith("nvapi-"):
        await update.message.reply_text(
            "❌ That doesn't look like an NVIDIA API key — keys start with `nvapi-`.\n\n"
            "Get one from build.nvidia.com and try again.",
            parse_mode="Markdown",
        )
        return

    import configparser
    import os

    from pocket_desk_agent import configure as configure_module
    from pocket_desk_agent.config import Config

    configure_module.ensure_app_dir()
    cred_parser = configparser.ConfigParser()
    cred_path = configure_module.credentials_path()
    if cred_path.exists():
        cred_parser.read(cred_path, encoding="utf-8")
    if not cred_parser.has_section("default"):
        cred_parser["default"] = {}
    cred_parser["default"]["nvidia_api_key"] = key

    with open(cred_path, "w", encoding="utf-8") as f:
        f.write("# Pocket Desk Agent — credentials\n")
        f.write("# Keep this file private. Do not share or commit it.\n\n")
        cred_parser.write(f)
    if os.name != "nt":
        os.chmod(cred_path, 0o600)

    os.environ["NVIDIA_API_KEY"] = key
    Config.load()

    await update.message.reply_text(
        "✅ NVIDIA API key saved. It's now available as a fallback provider — see /aiprovider."
    )

    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id, message_id=update.message.message_id
        )
    except Exception as exc:
        logger.info("Could not delete /setnvidiakey message (non-fatal): %s", exc)
```

- [ ] **Step 4: Export and register the command**

`handlers/__init__.py` — add `setnvidiakey_command` to the auth import block:
```python
from pocket_desk_agent.handlers.auth import (  # noqa: F401
    login_command,
    authcode_command,
    checkauth_command,
    logout_command,
    setnvidiakey_command,
)
```

`command_map.py` — add a row after `("logout", ...)`:
```python
    ("setnvidiakey", handlers.setnvidiakey_command, "Set NVIDIA NIM API key (AI fallback)"),
```

- [ ] **Step 5: Document it**

`docs/COMMANDS.md` — add a row to the "Core Bot Commands" table after `/logout`:
```markdown
| `/setnvidiakey <key>` | Configure the NVIDIA NIM fallback API key (used automatically when Gemini's quota is exhausted). | `/setnvidiakey nvapi-...` |
```

`README.md` — find the command quick-reference table (mirrors `docs/COMMANDS.md`'s core commands section) and add the same row in the same place.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_setnvidiakey_command.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add pocket_desk_agent/handlers/auth.py pocket_desk_agent/handlers/__init__.py pocket_desk_agent/command_map.py docs/COMMANDS.md README.md tests/test_setnvidiakey_command.py
git commit -m "feat: add /setnvidiakey command for NVIDIA fallback key

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: `/aiprovider` command

**Files:**
- Modify: `pocket_desk_agent/handlers/core.py`
- Modify: `pocket_desk_agent/handlers/__init__.py`
- Modify: `pocket_desk_agent/command_map.py`
- Modify: `docs/COMMANDS.md`, `README.md`
- Test: `tests/test_aiprovider_command.py`

**Interfaces:**
- Produces: `handlers.core.aiprovider_command(update, context)` registered as `/aiprovider`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_aiprovider_command.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_aiprovider_command.py -v`
Expected: FAIL with `AttributeError: module 'pocket_desk_agent.handlers.core' has no attribute 'aiprovider_command'`

- [ ] **Step 3: Implement the handler in `core.py`**

Add near `status_command`:

```python
_VALID_AI_PROVIDER_TOKENS = ("gemini", "nvidia")


async def aiprovider_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /aiprovider — view or set the AI fallback provider order."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if not context.args:
        order = Config.AI_PROVIDER_ORDER
        usable = ai_router.configured_providers(user_id)
        lines = [
            f"{i}. {p}{' ✅' if p in usable else ' ❌ not configured'}"
            for i, p in enumerate(order, start=1)
        ]
        await update.message.reply_text(
            "🤖 *Current AI provider order:*\n\n"
            + "\n".join(lines)
            + "\n\nTo change it: `/aiprovider nvidia,gemini`",
            parse_mode="Markdown",
        )
        return

    raw_tokens = [t.strip().lower() for chunk in context.args for t in chunk.split(",") if t.strip()]
    invalid = [t for t in raw_tokens if t not in _VALID_AI_PROVIDER_TOKENS]
    if invalid or not raw_tokens:
        await update.message.reply_text(
            f"❌ Invalid provider(s): {', '.join(invalid) or '(none given)'}.\n\n"
            f"Valid providers: {', '.join(_VALID_AI_PROVIDER_TOKENS)}.\n"
            "Example: `/aiprovider nvidia,gemini`",
            parse_mode="Markdown",
        )
        return

    new_order = list(dict.fromkeys(raw_tokens))  # de-dupe, keep order

    import configparser
    from pocket_desk_agent import configure as configure_module

    configure_module.ensure_app_dir()
    cfg_parser = configparser.ConfigParser()
    cfg_path = configure_module.config_path()
    if cfg_path.exists():
        cfg_parser.read(cfg_path, encoding="utf-8")
    if not cfg_parser.has_section("bot"):
        cfg_parser["bot"] = {}
    cfg_parser["bot"]["ai_provider_order"] = ",".join(new_order)

    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write("# Pocket Desk Agent — configuration\n")
        f.write("# Edit values here and restart the bot to apply changes.\n\n")
        cfg_parser.write(f)

    import os
    os.environ["AI_PROVIDER_ORDER"] = ",".join(new_order)
    Config.load()

    await update.message.reply_text(f"✅ AI provider order updated — now: {', '.join(new_order)}")
```

- [ ] **Step 4: Export and register the command**

`handlers/__init__.py` — add `aiprovider_command` to the core import block:
```python
from pocket_desk_agent.handlers.core import (  # noqa: F401
    start_command,
    help_command,
    new_command,
    status_command,
    enhance_command,
    aiprovider_command,
    update_command,
    handle_message,
    handle_photo,
    handle_image_document,
    error_handler,
    sync_commands_command,
    selftest_command,
    get_bot_commands,
)
```

`command_map.py` — add after `("status", ...)`:
```python
    ("aiprovider", handlers.aiprovider_command, "View or set AI provider fallback order"),
```

- [ ] **Step 5: Document it**

`docs/COMMANDS.md` — add a row to "Core Bot Commands" after `/status`:
```markdown
| `/aiprovider [order]` | View or set the AI provider fallback order (`gemini`, `nvidia`). | `/aiprovider nvidia,gemini` |
```
`README.md` — same row, same section.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_aiprovider_command.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add pocket_desk_agent/handlers/core.py pocket_desk_agent/handlers/__init__.py pocket_desk_agent/command_map.py docs/COMMANDS.md README.md tests/test_aiprovider_command.py
git commit -m "feat: add /aiprovider command to view/set fallback order

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 10: Setup wizard support for NVIDIA fallback

**Files:**
- Modify: `pocket_desk_agent/configure.py`
- Test: `tests/test_configure_nvidia.py`

**Interfaces:**
- Produces: `configure._validate_provider_order(raw: str) -> str | None` (pure validator, mirrors `_validate_allowed_users`), `configure._update_nvidia_fallback(cred_parser, cfg_parser) -> None` (new selective-menu handler), a new optional sub-step at the end of `_run_full_wizard`'s `[2/3]` section.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_configure_nvidia.py
from pocket_desk_agent import configure


def test_validate_provider_order_accepts_known_tokens() -> None:
    assert configure._validate_provider_order("nvidia,gemini") is None
    assert configure._validate_provider_order("gemini") is None


def test_validate_provider_order_rejects_unknown_token() -> None:
    error = configure._validate_provider_order("nvidia,bogus")
    assert error is not None
    assert "bogus" in error


def test_validate_provider_order_rejects_empty() -> None:
    error = configure._validate_provider_order("")
    assert error is not None


def test_selective_menu_includes_nvidia_fallback() -> None:
    labels = [label for label, _ in configure._SELECTIVE_MENU]
    assert any("NVIDIA" in label for label in labels)


def test_read_existing_parsers_does_not_break_on_missing_nvidia_fields(tmp_path, monkeypatch) -> None:
    """A config file written before this feature existed has no nvidia_* keys —
    the selective handler must not KeyError reading them with .get()-style fallbacks."""
    cfg_dir = tmp_path / ".pdagent"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "credentials").write_text("[default]\ntelegram_bot_token = x\n", encoding="utf-8")
    (cfg_dir / "config").write_text("[bot]\nauthorized_user_ids = 1\n", encoding="utf-8")

    monkeypatch.setattr(configure, "existing_app_path", lambda name: cfg_dir / name)

    cred_parser, cfg_parser = configure._read_existing_parsers()

    assert cred_parser.get("default", "nvidia_api_key", fallback="") == ""
    assert cfg_parser.get("bot", "nvidia_model", fallback="") == ""
    assert cfg_parser.get("bot", "ai_provider_order", fallback="") == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_configure_nvidia.py -v`
Expected: FAIL — `AttributeError: module 'pocket_desk_agent.configure' has no attribute '_validate_provider_order'` (the last test passes already, since `_read_existing_parsers` already uses `.get(..., fallback=...)` reads with no schema assumptions — that's fine, it's there to guard the *next* step doesn't accidentally introduce a hard key lookup).

- [ ] **Step 3: Add `_validate_provider_order`**

Add near `_validate_allowed_users`:

```python
_VALID_AI_PROVIDER_TOKENS = ("gemini", "nvidia")


def _validate_provider_order(raw: str) -> str | None:
    """Return an error message if raw is not a valid comma-separated provider list."""
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    if not parts:
        return "At least one provider is required."
    for part in parts:
        if part not in _VALID_AI_PROVIDER_TOKENS:
            return f"'{part}' is not a valid provider. Choose from: {', '.join(_VALID_AI_PROVIDER_TOKENS)}."
    return None
```

- [ ] **Step 4: Add the optional NVIDIA sub-step to the full wizard**

In `_run_full_wizard`, right after the Gemini `[2/3]` `while True:` choice block ends (after the line `print("  Please enter 1, 2, 3, or 4.")` / before `# [3/3] Optional Settings`), add:

```python
    print("\n  Optional: NVIDIA NIM AI Fallback")
    print("  Falls back to an NVIDIA-hosted model when Gemini's quota is exhausted.")
    nvidia_api_key = ""
    ai_provider_order = "gemini,nvidia"
    configure_nvidia = input("  Configure now? [y/N]: ").strip().lower()
    if configure_nvidia in ("y", "yes"):
        nvidia_api_key = _prompt_required(
            "NVIDIA API Key",
            hint="Get from build.nvidia.com (NIM). Keys start with nvapi-",
            secret=True,
        )
    else:
        print(
            "  Skipped. Configure later with 'pdagent configure', /setnvidiakey in "
            "Telegram, or the NVIDIA_API_KEY env var."
        )
```

Then in the credentials-writing block, add `"nvidia_api_key": nvidia_api_key,` to the `cred_parser["default"] = {...}` dict, and in the config-writing block add `"nvidia_model": "meta/llama-3.3-70b-instruct",` and `"ai_provider_order": ai_provider_order,` to the `cfg_parser["bot"] = {...}` dict.

- [ ] **Step 5: Add the selective-menu handler**

```python
def _update_nvidia_fallback(
    cred_parser: configparser.ConfigParser,
    cfg_parser: configparser.ConfigParser,
) -> None:
    """Prompt for and update the NVIDIA fallback key, model, and provider order."""
    current_key = cred_parser.get("default", "nvidia_api_key", fallback="")
    current_model = cfg_parser.get("bot", "nvidia_model", fallback="meta/llama-3.3-70b-instruct")
    current_order = cfg_parser.get("bot", "ai_provider_order", fallback="gemini,nvidia")

    print(f"\n  Current NVIDIA API Key : {_mask(current_key) if current_key else '(not set)'}")
    print(f"  Current NVIDIA Model   : {current_model}")
    print(f"  Current Provider Order : {current_order}")

    new_key = _prompt_optional(
        "New NVIDIA API Key",
        hint="Get from build.nvidia.com (NIM). Keys start with nvapi-. Enter to keep current.",
        default=current_key,
        secret=True,
    )
    new_model = _prompt_optional(
        "New NVIDIA Model",
        hint="e.g. meta/llama-3.3-70b-instruct",
        default=current_model,
    )
    while True:
        new_order_raw = _prompt_optional(
            "New Provider Order",
            hint="Comma-separated: gemini,nvidia or nvidia,gemini",
            default=current_order,
        )
        error = _validate_provider_order(new_order_raw)
        if error:
            print(f"  Error: {error}")
            continue
        break
    new_order = ",".join(p.strip().lower() for p in new_order_raw.split(",") if p.strip())

    cred_parser["default"]["nvidia_api_key"] = new_key
    cfg_parser["bot"]["nvidia_model"] = new_model
    cfg_parser["bot"]["ai_provider_order"] = new_order
    _write_parsers(cred_parser, cfg_parser)
```

Add it to `_SELECTIVE_MENU`, after the Gemini Auth Mode entry:

```python
    ("NVIDIA AI Fallback        — API key, model, and provider order", _update_nvidia_fallback),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_configure_nvidia.py tests/test_configure_smartplug.py -v`
Expected: PASS

- [ ] **Step 7: Run the full test suite one more time**

Run: `pytest tests/ -v`
Expected: PASS — every test added across all 10 tasks, plus every pre-existing test, green.

- [ ] **Step 8: Commit**

```bash
git add pocket_desk_agent/configure.py tests/test_configure_nvidia.py
git commit -m "feat: add NVIDIA fallback setup to the configure wizard

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Post-implementation checklist (not a task — do this once, after Task 10)

- [ ] Re-verify `meta/llama-3.3-70b-instruct` is still live on build.nvidia.com with tool-calling support; update the default in `config.py`, `configure.py`, and this plan's Global Constraints if it's been retired or renamed.
- [ ] Manually smoke-test end-to-end with a real NVIDIA key: `/setnvidiakey nvapi-...`, `/aiprovider nvidia,gemini`, then send a message that requires a tool call (e.g. "list my files") and confirm NVIDIA answers and the tool actually runs.
- [ ] Manually force a Gemini failure (e.g. temporarily set `GEMINI_MODEL` to a bogus value, or log out mid-session) with both providers configured and confirm the fallback note appears and the conversation continues coherently.
- [ ] Run `make lint` (flake8 + mypy) and `make format` (black) across all new/modified files.
