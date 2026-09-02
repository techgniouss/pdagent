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
