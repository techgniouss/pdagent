"""Gemini action tools, confirmation flows, and reusable action helpers."""

from __future__ import annotations

import asyncio
import datetime as dt
import io
import logging
import time
import uuid
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from pocket_desk_agent.command_registry import CommandAction, get_registry
from pocket_desk_agent.rate_limiter import RateLimiter
from pocket_desk_agent.scheduler_registry import ScheduledTask, get_scheduler_registry

logger = logging.getLogger(__name__)

_CONFIRM_PREFIX = "geminicf_"
_CANCEL_PREFIX = "geminix_"
_MAX_TEXT_PREVIEW = 180
_SCHEDULABLE_ACTIONS = frozenset({
    "hotkey",
    "clipboard",
    "findtext",
    "smartclick",
    "pasteenter",
    "typeenter",
})


@dataclass
class GeminiToolResult:
    """Structured tool execution result returned to Gemini."""

    success: bool
    result: str
    awaiting_confirmation: bool = False
    confirmation_id: Optional[str] = None
    media_sent: bool = False

    def to_response(self) -> dict[str, Any]:
        """Convert the result to a functionResponse payload."""
        payload: dict[str, Any] = {
            "result": self.result,
            "success": self.success,
        }
        if self.awaiting_confirmation:
            payload["awaiting_confirmation"] = True
        if self.confirmation_id:
            payload["confirmation_id"] = self.confirmation_id
        if self.media_sent:
            payload["media_sent"] = True
        return payload


@dataclass
class PendingGeminiAction:
    """A side-effecting action waiting for the user's approval."""

    action_id: str
    user_id: int
    action_type: str
    args: dict[str, Any]
    summary: str
    created_at: float
    chat_id: int


pending_gemini_actions: dict[str, PendingGeminiAction] = {}
_GEMINI_TOOL_RATE_LIMITER = RateLimiter(default_calls=20, default_window=60)
_RATE_LIMIT_LABELS = {
    "capture_screenshot": "screenshot captures",
    "find_text_on_screen": "OCR screen searches",
    "scan_ui_elements": "UI scans",
    "list_open_windows": "window listings",
    "focus_window": "window focus actions",
    "smart_click_text": "smart-click requests",
    "open_claude": "Claude app actions",
    "claude_new_chat": "Claude new-chat actions",
    "claude_send_message": "Claude message actions",
    "open_antigravity": "Antigravity app actions",
    "focus_antigravity_chat": "Antigravity chat focus actions",
    "open_browser": "browser launch actions",
    "open_vscode_folder": "VS Code folder opens",
    "open_claude_cli": "Claude CLI launches",
    "claude_cli_send_message": "Claude CLI message actions",
    "start_screen_watch": "screen watcher starts",
    "stop_screen_watch": "screen watcher stops",
    "schedule_claude_prompt": "Claude scheduling requests",
    "schedule_desktop_sequence": "desktop scheduling requests",
    "request_remote_session": "remote-desktop start requests",
    "request_stop_remote_session": "remote-desktop stop requests",
    "get_remote_session_status": "remote-desktop status checks",
    "gemini_confirmation_request": "Gemini approval requests",
}
_RATE_LIMITED_TOOLS = frozenset(_RATE_LIMIT_LABELS) - {"gemini_confirmation_request"}

_GEMINI_TOOL_RATE_LIMITER.set_limit("capture_screenshot", calls=5, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("find_text_on_screen", calls=6, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("scan_ui_elements", calls=4, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("list_open_windows", calls=10, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("focus_window", calls=12, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("smart_click_text", calls=6, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("open_claude", calls=6, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("claude_new_chat", calls=4, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("claude_send_message", calls=6, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("open_antigravity", calls=6, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("focus_antigravity_chat", calls=6, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("open_browser", calls=6, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("open_vscode_folder", calls=6, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("open_claude_cli", calls=5, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("claude_cli_send_message", calls=6, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("start_screen_watch", calls=4, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("stop_screen_watch", calls=8, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("schedule_claude_prompt", calls=6, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("schedule_desktop_sequence", calls=4, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("request_remote_session", calls=3, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("request_stop_remote_session", calls=3, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("get_remote_session_status", calls=10, window=60)
_GEMINI_TOOL_RATE_LIMITER.set_limit("gemini_confirmation_request", calls=8, window=60)


def _check_tool_rate_limit(user_id: int, limit_key: str) -> Optional[GeminiToolResult]:
    """Return a GeminiToolResult when a tool-specific rate limit is exceeded."""
    if _GEMINI_TOOL_RATE_LIMITER.check(user_id, limit_key):
        return None

    label = _RATE_LIMIT_LABELS.get(limit_key, limit_key.replace("_", " "))
    return GeminiToolResult(
        False,
        f"Rate limit reached for {label}. Please wait a bit before asking Gemini to do that again.",
    )


def get_gemini_action_tools() -> list[dict[str, Any]]:
    """Return additional Gemini tool declarations for desktop actions."""
    return [
        {
            "name": "get_current_directory",
            "description": "Return the user's current working directory inside the approved file sandbox.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "change_directory",
            "description": "Change the current working directory inside the approved file sandbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative or approved absolute path to switch into."}
                },
                "required": ["path"],
            },
        },
        {
            "name": "get_battery_status",
            "description": "Check the device battery percentage, charging state, and time remaining when available.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "capture_screenshot",
            "description": "Capture the current screen and send the screenshot back to the Telegram chat.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "list_open_windows",
            "description": "List visible top-level application windows and assign selection numbers for later focus_window calls.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "focus_window",
            "description": "Activate one of the windows previously returned by list_open_windows using its selection number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selection": {"type": "integer", "description": "Window number from the latest list_open_windows result."}
                },
                "required": ["selection"],
            },
        },
        {
            "name": "view_clipboard",
            "description": "Read the current clipboard contents from the host machine.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "shutdown_computer",
            "description": "Ask for confirmation before shutting down the computer.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "sleep_computer",
            "description": "Ask for confirmation before putting the computer to sleep.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "set_privacy_mode",
            "description": "Check privacy mode status, or ask for confirmation before turning privacy mode on or off.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "description": "One of status, on, or off."}
                },
                "required": ["mode"],
            },
        },
        {
            "name": "list_custom_commands",
            "description": "List saved custom automation commands and their action counts.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "list_schedules",
            "description": "List the current user's pending scheduled tasks.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "start_screen_watch",
            "description": "Ask for confirmation before starting a recurring screen watcher that looks for visible text and sends a hotkey until the user stops it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Visible screen text to watch for, such as Allow command."},
                    "interval": {"type": "string", "description": "Repeat interval such as 1m, 30s, or 2m."},
                    "hotkey": {"type": "string", "description": "Hotkey to send when the text appears, such as enter or ctrl+enter."},
                    "scope": {"type": "string", "description": "Optional scope: screen, claude, or antigravity."},
                    "cooldown": {"type": "string", "description": "Optional cooldown such as 30s or 1m to avoid repeated triggers."},
                },
                "required": ["text", "interval", "hotkey"],
            },
        },
        {
            "name": "stop_screen_watch",
            "description": "Stop one active screen watcher by task ID, or stop all active screen watchers for the current user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Optional task ID from list_schedules. Leave empty to stop all screen watchers."}
                },
            },
        },
        {
            "name": "start_build_workflow",
            "description": "Prepare the React Native build workflow and optionally narrow it to a project name so the user can choose which npm script to run.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Optional project name hint such as emploi."}
                },
            },
        },
        {
            "name": "start_apk_retrieval_workflow",
            "description": "Prepare the existing APK retrieval workflow and optionally narrow it to an Android project so the user can browse build outputs or pick an APK.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Optional Android project name hint such as emploi."}
                },
            },
        },
        {
            "name": "run_saved_command",
            "description": "Ask for confirmation before running one of the user's saved custom commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Saved command name without the leading slash."}
                },
                "required": ["name"],
            },
        },
        {
            "name": "find_text_on_screen",
            "description": "Use OCR to locate visible text on screen, send an annotated screenshot, and return coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Visible text to search for on the current screen."}
                },
                "required": ["text"],
            },
        },
        {
            "name": "scan_ui_elements",
            "description": "Use computer vision to label potential clickable UI elements, send an annotated screenshot, and store numbered selections.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "set_clipboard",
            "description": "Ask for confirmation to replace the host clipboard with new text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to place on the clipboard after approval."}
                },
                "required": ["text"],
            },
        },
        {
            "name": "press_hotkey",
            "description": "Ask for confirmation before sending a keyboard shortcut or typing text on the host machine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {"type": "string", "description": "Shortcut string such as ctrl+shift+esc or type."},
                    "text": {"type": "string", "description": "Optional text used with the hotkey or with the special 'type' mode."},
                },
                "required": ["keys"],
            },
        },
        {
            "name": "click_coordinates",
            "description": "Ask for confirmation before clicking a specific screen coordinate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Screen X coordinate."},
                    "y": {"type": "integer", "description": "Screen Y coordinate."},
                },
                "required": ["x", "y"],
            },
        },
        {
            "name": "smart_click_text",
            "description": "Ask for confirmation before OCR-searching for text and clicking the strongest matching on-screen result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Visible text to search for and click."}
                },
                "required": ["text"],
            },
        },
        {
            "name": "click_ui_element",
            "description": "Ask for confirmation before clicking one of the numbered UI elements returned by scan_ui_elements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selection": {"type": "integer", "description": "Element number from the latest scan_ui_elements result."}
                },
                "required": ["selection"],
            },
        },
        {
            "name": "open_claude",
            "description": "Ask for confirmation before opening or focusing the Claude desktop app.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "claude_new_chat",
            "description": "Ask for confirmation before opening a new Claude chat, with an optional first message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Optional first message to send in the new Claude chat."}
                },
            },
        },
        {
            "name": "claude_send_message",
            "description": "Ask for confirmation before sending a message to the active Claude desktop chat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message to send to Claude desktop."}
                },
                "required": ["message"],
            },
        },
        {
            "name": "open_antigravity",
            "description": "Ask for confirmation before opening or focusing the Antigravity desktop app.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "focus_antigravity_chat",
            "description": "Ask for confirmation before focusing Antigravity's agent chat input.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "open_browser",
            "description": "Ask for confirmation before opening a supported browser in a maximized window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "browser": {"type": "string", "description": "Browser name such as edge, chrome, firefox, or brave."}
                },
                "required": ["browser"],
            },
        },
        {
            "name": "open_vscode_folder",
            "description": "Ask for confirmation before opening a specific approved folder in VS Code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Folder path or folder name to resolve inside approved workspaces."}
                },
                "required": ["folder"],
            },
        },
        {
            "name": "open_claude_cli",
            "description": "Ask for confirmation before opening Claude CLI in a specific approved folder, with an optional first prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Folder path or folder name to resolve inside approved workspaces."},
                    "prompt": {"type": "string", "description": "Optional first prompt to send after Claude CLI opens."},
                },
                "required": ["folder"],
            },
        },
        {
            "name": "claude_cli_send_message",
            "description": "Ask for confirmation before sending a follow-up message to the active Claude CLI window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Prompt to send to the active Claude CLI window."}
                },
                "required": ["message"],
            },
        },
        {
            "name": "schedule_claude_prompt",
            "description": "Ask for confirmation before scheduling a prompt to be sent to Claude later. Use HH:MM or YYYY-MM-DD HH:MM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "execute_at": {"type": "string", "description": "Local execution time in HH:MM or YYYY-MM-DD HH:MM format."},
                    "prompt": {"type": "string", "description": "Prompt to send to Claude at that time."},
                },
                "required": ["execute_at", "prompt"],
            },
        },
        {
            "name": "request_remote_session",
            "description": (
                "Request a live remote-desktop session. This does NOT start the session directly — "
                "it asks the user to confirm via an inline button, and only then opens the tunnel. "
                "Use when the user says things like 'open remote', 'let me control my pc from phone', "
                "or 'share my screen'."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "request_stop_remote_session",
            "description": (
                "Request to stop the active remote-desktop session. Does not stop directly — "
                "asks the user to confirm via an inline button."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "get_remote_session_status",
            "description": (
                "Read-only status of the current user's remote-desktop session. Returns active/inactive, "
                "the tunnel URL if active, idle seconds, and current fps/quality. Does not leak the session token."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "schedule_desktop_sequence",
            "description": "Ask for confirmation before scheduling a short sequence of supported desktop automation actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "execute_at": {"type": "string", "description": "Local execution time in HH:MM or YYYY-MM-DD HH:MM format."},
                    "name": {"type": "string", "description": "Optional friendly name for the scheduled sequence."},
                    "actions": {
                        "type": "array",
                        "description": "Ordered actions to run at the scheduled time.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "description": "One of hotkey, clipboard, findtext, smartclick, pasteenter, or typeenter."},
                                "args": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "String arguments for that action type.",
                                },
                            },
                            "required": ["type", "args"],
                        },
                    },
                },
                "required": ["execute_at", "actions"],
            },
        },
    ]


def is_gemini_confirmation_callback(callback_data: str) -> bool:
    """Return True when the callback belongs to the Gemini confirmation flow."""
    return callback_data.startswith(_CONFIRM_PREFIX) or callback_data.startswith(_CANCEL_PREFIX)


async def handle_gemini_confirmation_callback(update, context) -> bool:
    """Execute or cancel a pending Gemini action from an inline keyboard callback."""
    query = update.callback_query
    if not query or not query.data or not is_gemini_confirmation_callback(query.data):
        return False

    if query.data.startswith(_CONFIRM_PREFIX):
        action_id = query.data[len(_CONFIRM_PREFIX):]
    else:
        action_id = query.data[len(_CANCEL_PREFIX):]
    pending = pending_gemini_actions.get(action_id)
    if not pending:
        await query.edit_message_text("This Gemini action is no longer available. Ask again if you still want to run it.")
        return True

    if update.effective_user and pending.user_id != update.effective_user.id:
        await query.answer("This approval request belongs to a different user.", show_alert=True)
        return True

    if query.data.startswith(_CANCEL_PREFIX):
        pending_gemini_actions.pop(action_id, None)
        await query.edit_message_text(f"Cancelled: {pending.summary}")
        return True

    await query.edit_message_text(f"Running: {pending.summary}")
    try:
        result = await _execute_confirmed_action(pending, context.bot)
    except Exception as exc:
        logger.error("Gemini confirmed action failed: %s", exc, exc_info=True)
        pending_gemini_actions.pop(action_id, None)
        await context.bot.send_message(
            chat_id=pending.chat_id,
            text=f"Action failed: {type(exc).__name__}: {exc}",
        )
        return True

    pending_gemini_actions.pop(action_id, None)
    await context.bot.send_message(chat_id=pending.chat_id, text=result.result)
    return True


async def dispatch_gemini_tool(
    user_id: int,
    func_name: str,
    args: dict[str, Any],
    file_manager: Any,
    tool_runtime: Optional[dict[str, Any]] = None,
) -> GeminiToolResult:
    """Dispatch a Gemini tool call to an immediate or confirmation-gated action."""
    tool_runtime = tool_runtime or {}
    if func_name in _RATE_LIMITED_TOOLS:
        rate_limited = _check_tool_rate_limit(user_id, func_name)
        if rate_limited is not None:
            return rate_limited

    if func_name == "get_current_directory":
        return GeminiToolResult(True, f"Current directory: {file_manager.get_current_dir(user_id)}")

    if func_name == "change_directory":
        success, message = file_manager.set_current_dir(user_id, str(args.get("path", "")))
        return GeminiToolResult(success, message)

    if func_name == "get_battery_status":
        return GeminiToolResult(True, _get_battery_status_text())

    if func_name == "capture_screenshot":
        return await _capture_screenshot(tool_runtime)

    if func_name == "list_open_windows":
        return GeminiToolResult(True, _list_open_windows(user_id))

    if func_name == "focus_window":
        selection = int(args.get("selection", 0))
        return GeminiToolResult(*_focus_window(user_id, selection))

    if func_name == "view_clipboard":
        return GeminiToolResult(True, _read_clipboard_text())

    if func_name == "shutdown_computer":
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={},
            summary="shutdown the computer",
            tool_runtime=tool_runtime,
        )

    if func_name == "sleep_computer":
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={},
            summary="put the computer to sleep",
            tool_runtime=tool_runtime,
        )

    if func_name == "set_privacy_mode":
        import platform
        from pocket_desk_agent.handlers.system import _build_privacy_mode_status_text, _normalize_privacy_mode_action

        mode = _normalize_privacy_mode_action([str(args.get("mode", ""))])
        if mode == "invalid":
            return GeminiToolResult(False, "Invalid privacy mode. Use status, on, or off.")
        if mode == "status":
            return GeminiToolResult(True, _build_privacy_mode_status_text())
        if platform.system() != "Windows":
            return GeminiToolResult(False, "Privacy mode is currently only supported on Windows.")
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"mode": mode},
            summary=f"turn privacy mode {mode}",
            tool_runtime=tool_runtime,
        )

    if func_name == "list_custom_commands":
        return GeminiToolResult(True, _list_custom_commands_text())

    if func_name == "list_schedules":
        return GeminiToolResult(True, _list_schedules_text(user_id))

    if func_name == "start_screen_watch":
        search_text = str(args.get("text", "")).strip()
        interval = str(args.get("interval", "")).strip()
        hotkey = str(args.get("hotkey", "")).strip()
        scope = str(args.get("scope", "screen")).strip().lower() or "screen"
        cooldown = str(args.get("cooldown", "")).strip()
        if not search_text or not interval or not hotkey:
            return GeminiToolResult(False, "Please provide text, interval, and hotkey for the screen watcher.")
        if scope not in {"screen", "claude", "antigravity"}:
            return GeminiToolResult(False, "Screen watch scope must be screen, claude, or antigravity.")
        summary = f"watch {scope} every {interval} for '{search_text}' and send hotkey '{hotkey}' until stopped"
        if cooldown:
            summary += f" with a cooldown of {cooldown}"
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"text": search_text, "interval": interval, "hotkey": hotkey, "scope": scope, "cooldown": cooldown},
            summary=summary,
            tool_runtime=tool_runtime,
        )

    if func_name == "stop_screen_watch":
        from pocket_desk_agent.handlers.scheduling import stop_screen_watch_tasks

        task_id = str(args.get("task_id", "")).strip() or None
        success, message = stop_screen_watch_tasks(user_id=user_id, task_id=task_id)
        return GeminiToolResult(success, message)

    if func_name == "start_build_workflow":
        from pocket_desk_agent.handlers.build import prepare_build_workflow

        current_dir = str(file_manager.get_current_dir(user_id))
        success, message = prepare_build_workflow(
            user_id=user_id,
            current_dir=current_dir,
            project_query=str(args.get("project", "")).strip() or None,
        )
        return GeminiToolResult(success, message)

    if func_name == "start_apk_retrieval_workflow":
        from pocket_desk_agent.handlers.build import prepare_apk_retrieval_workflow

        current_dir = str(file_manager.get_current_dir(user_id))
        success, message = prepare_apk_retrieval_workflow(
            user_id=user_id,
            current_dir=current_dir,
            project_query=str(args.get("project", "")).strip() or None,
        )
        return GeminiToolResult(success, message)

    if func_name == "run_saved_command":
        command_name = str(args.get("name", "")).strip().lstrip("/")
        if not command_name:
            return GeminiToolResult(False, "Please provide the saved command name to run.")
        if not get_registry().command_exists(command_name):
            return GeminiToolResult(False, f"No saved command named '{command_name}' exists.")
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"name": command_name},
            summary=f"run the saved command '/{command_name}'",
            tool_runtime=tool_runtime,
        )

    if func_name == "find_text_on_screen":
        return await _find_text_on_screen(tool_runtime, str(args.get("text", "")))

    if func_name == "scan_ui_elements":
        return await _scan_ui_elements(user_id, tool_runtime)

    if func_name in {"write_file", "append_file", "delete_file", "create_directory"}:
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args=args,
            summary=_summarize_file_action(func_name, args),
            tool_runtime=tool_runtime,
        )

    if func_name == "set_clipboard":
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"text": str(args.get("text", ""))},
            summary=f"replace the clipboard with {_shorten(str(args.get('text', '')))}",
            tool_runtime=tool_runtime,
        )

    if func_name == "press_hotkey":
        text = args.get("text")
        summary = f"send hotkey '{args.get('keys', '')}'"
        if text:
            summary += f" with text {_shorten(str(text))}"
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"keys": str(args.get("keys", "")), "text": text if text is None else str(text)},
            summary=summary,
            tool_runtime=tool_runtime,
        )

    if func_name == "click_coordinates":
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"x": int(args.get("x", 0)), "y": int(args.get("y", 0))},
            summary=f"click screen coordinates ({int(args.get('x', 0))}, {int(args.get('y', 0))})",
            tool_runtime=tool_runtime,
        )

    if func_name == "smart_click_text":
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"text": str(args.get("text", ""))},
            summary=f"search the screen for '{args.get('text', '')}' and click the best match",
            tool_runtime=tool_runtime,
        )

    if func_name == "click_ui_element":
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"selection": int(args.get("selection", 0))},
            summary=f"click UI element #{int(args.get('selection', 0))} from the latest scan",
            tool_runtime=tool_runtime,
        )

    if func_name == "open_claude":
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={},
            summary="open or focus the Claude desktop app",
            tool_runtime=tool_runtime,
        )

    if func_name == "claude_new_chat":
        message = args.get("message")
        summary = "open a new Claude chat"
        if message:
            summary += f" and send {_shorten(str(message))}"
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"message": None if message is None else str(message)},
            summary=summary,
            tool_runtime=tool_runtime,
        )

    if func_name == "claude_send_message":
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"message": str(args.get("message", ""))},
            summary=f"send a message to Claude: {_shorten(str(args.get('message', '')))}",
            tool_runtime=tool_runtime,
        )

    if func_name == "open_antigravity":
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={},
            summary="open or focus the Antigravity app",
            tool_runtime=tool_runtime,
        )

    if func_name == "focus_antigravity_chat":
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={},
            summary="focus the Antigravity agent chat input",
            tool_runtime=tool_runtime,
        )

    if func_name == "open_browser":
        browser = str(args.get("browser", "")).strip().lower()
        if not browser:
            return GeminiToolResult(False, "Please provide a browser name such as chrome, edge, firefox, or brave.")
        if browser not in {"edge", "chrome", "firefox", "brave"}:
            return GeminiToolResult(False, "Unsupported browser. Choose edge, chrome, firefox, or brave.")
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"browser": browser},
            summary=f"open {browser} in a maximized window",
            tool_runtime=tool_runtime,
        )

    if func_name == "open_vscode_folder":
        from pocket_desk_agent.handlers.antigravity import resolve_workspace_folder

        folder = str(args.get("folder", "")).strip()
        if not folder:
            return GeminiToolResult(False, "Please provide the folder path or folder name to open in VS Code.")
        resolved, folder_or_error = resolve_workspace_folder(folder)
        if not resolved:
            return GeminiToolResult(False, folder_or_error)
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"folder": folder_or_error},
            summary=f"open the folder {_shorten(folder_or_error)} in VS Code",
            tool_runtime=tool_runtime,
        )

    if func_name == "open_claude_cli":
        from pocket_desk_agent.handlers.antigravity import resolve_workspace_folder

        folder = str(args.get("folder", "")).strip()
        prompt = str(args.get("prompt", "")).strip()
        if not folder:
            return GeminiToolResult(False, "Please provide the folder path or folder name for Claude CLI.")
        resolved, folder_or_error = resolve_workspace_folder(folder)
        if not resolved:
            return GeminiToolResult(False, folder_or_error)
        summary = f"open Claude CLI in {_shorten(folder_or_error)}"
        if prompt:
            summary += f" and send {_shorten(prompt)}"
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"folder": folder_or_error, "prompt": prompt},
            summary=summary,
            tool_runtime=tool_runtime,
        )

    if func_name == "claude_cli_send_message":
        message = str(args.get("message", "")).strip()
        if not message:
            return GeminiToolResult(False, "Please provide the Claude CLI message to send.")
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"message": message},
            summary=f"send a message to Claude CLI: {_shorten(message)}",
            tool_runtime=tool_runtime,
        )

    if func_name == "schedule_claude_prompt":
        execute_at = str(args.get("execute_at", ""))
        prompt = str(args.get("prompt", ""))
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"execute_at": execute_at, "prompt": prompt},
            summary=f"schedule a Claude prompt for {execute_at}: {_shorten(prompt)}",
            tool_runtime=tool_runtime,
        )

    if func_name == "schedule_desktop_sequence":
        execute_at = str(args.get("execute_at", ""))
        name = str(args.get("name", "")).strip()
        actions = args.get("actions", [])
        return await _queue_confirmation(
            user_id=user_id,
            action_type=func_name,
            args={"execute_at": execute_at, "name": name, "actions": actions},
            summary=_summarize_scheduled_sequence(execute_at, name, actions),
            tool_runtime=tool_runtime,
        )

    if func_name == "request_remote_session":
        from pocket_desk_agent.config import Config as _Config
        from pocket_desk_agent.remote.session import get_for_user as _get_for_user

        if not _Config.REMOTE_ENABLED:
            return GeminiToolResult(False, "Remote desktop feature is disabled in configuration.")
        if not _Config.REMOTE_AI_TOOLS_ENABLED:
            return GeminiToolResult(
                False,
                "AI-initiated remote-desktop requests are disabled. The user can run /remote manually.",
            )
        existing = _get_for_user(user_id)
        if existing:
            return GeminiToolResult(
                True,
                f"A remote session is already active. Open: {existing.tunnel_url}",
            )
        return await _queue_confirmation(
            user_id=user_id,
            action_type="start_remote_session_ai",
            args={},
            summary="start a live remote-desktop session (opens a public tunnel)",
            tool_runtime=tool_runtime,
        )

    if func_name == "request_stop_remote_session":
        from pocket_desk_agent.config import Config as _Config
        from pocket_desk_agent.remote.session import get_for_user as _get_for_user

        if not _Config.REMOTE_AI_TOOLS_ENABLED:
            return GeminiToolResult(
                False,
                "AI-initiated remote-desktop requests are disabled. The user can run /stopremote manually.",
            )
        existing = _get_for_user(user_id)
        if not existing:
            return GeminiToolResult(True, "No remote-desktop session is currently active.")
        return await _queue_confirmation(
            user_id=user_id,
            action_type="stop_remote_session_ai",
            args={},
            summary="stop the active remote-desktop session",
            tool_runtime=tool_runtime,
        )

    if func_name == "get_remote_session_status":
        from pocket_desk_agent.config import Config as _Config
        from pocket_desk_agent.handlers.remote import sanitized_status

        if not _Config.REMOTE_ENABLED:
            return GeminiToolResult(True, "Remote desktop feature is disabled in configuration.")
        status = sanitized_status(user_id)
        if not status.get("active"):
            return GeminiToolResult(True, "Remote desktop session: inactive.")
        return GeminiToolResult(
            True,
            (
                f"Remote desktop session: active.\n"
                f"URL: {status.get('url', '')}\n"
                f"Idle: {status.get('idle_seconds', 0)}s\n"
                f"Settings: {status.get('fps')} fps, quality {status.get('quality')}, "
                f"max width {status.get('max_width')}."
            ),
        )

    return GeminiToolResult(False, f"Tool '{func_name}' is not implemented.")


async def _queue_confirmation(
    user_id: int,
    action_type: str,
    args: dict[str, Any],
    summary: str,
    tool_runtime: dict[str, Any],
) -> GeminiToolResult:
    """Send an inline confirmation prompt and store the pending action."""
    bot = tool_runtime.get("bot")
    chat_id = tool_runtime.get("chat_id")
    if not bot or chat_id is None:
        return GeminiToolResult(False, "This action requires a Telegram chat context, but none was available.")

    rate_limited = _check_tool_rate_limit(user_id, "gemini_confirmation_request")
    if rate_limited is not None:
        return rate_limited

    action_id = uuid.uuid4().hex[:10]
    pending_gemini_actions[action_id] = PendingGeminiAction(
        action_id=action_id,
        user_id=user_id,
        action_type=action_type,
        args=args,
        summary=summary,
        created_at=time.time(),
        chat_id=int(chat_id),
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Approve", callback_data=f"{_CONFIRM_PREFIX}{action_id}"),
                InlineKeyboardButton("Cancel", callback_data=f"{_CANCEL_PREFIX}{action_id}"),
            ]
        ]
    )
    await bot.send_message(
        chat_id=chat_id,
        text=f"Gemini wants to {summary}. Approve this action?",
        reply_markup=keyboard,
    )
    return GeminiToolResult(
        success=True,
        result=f"Approval requested for: {summary}",
        awaiting_confirmation=True,
        confirmation_id=action_id,
    )


async def _capture_screenshot(tool_runtime: dict[str, Any]) -> GeminiToolResult:
    """Capture the current screen and optionally send it to the chat."""
    def _build_screenshot_bytes() -> io.BytesIO:
        import pyautogui

        image = pyautogui.screenshot()
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        image_bytes.seek(0)
        return image_bytes

    image_bytes = await asyncio.to_thread(_build_screenshot_bytes)

    bot = tool_runtime.get("bot")
    chat_id = tool_runtime.get("chat_id")
    if bot and chat_id is not None:
        await bot.send_photo(chat_id=chat_id, photo=image_bytes, caption="Current screen capture")
        return GeminiToolResult(True, "Captured the current screen and sent the screenshot to the chat.", media_sent=True)

    return GeminiToolResult(True, "Captured the current screen, but no Telegram chat context was available to send the image.")


async def _find_text_on_screen(tool_runtime: dict[str, Any], search_text: str) -> GeminiToolResult:
    """Run OCR on the current screen, send an annotated screenshot, and return matches."""
    if not search_text.strip():
        return GeminiToolResult(False, "Please provide text to search for on the screen.")

    def _scan() -> tuple[list[Any], io.BytesIO]:
        import pyautogui
        from pocket_desk_agent.automation_utils import annotate_screenshot_with_markers, find_text_in_image

        screenshot = pyautogui.screenshot()
        matches = find_text_in_image(screenshot, search_text)
        annotated_bytes = io.BytesIO()
        if matches:
            annotated = annotate_screenshot_with_markers(screenshot, matches)
            annotated.save(annotated_bytes, format="PNG")
            annotated_bytes.seek(0)
        return matches, annotated_bytes

    matches, image_bytes = await asyncio.to_thread(_scan)
    if not matches:
        return GeminiToolResult(True, f"No on-screen matches found for '{search_text}'.")

    bot = tool_runtime.get("bot")
    chat_id = tool_runtime.get("chat_id")
    if bot and chat_id is not None:
        await bot.send_photo(
            chat_id=chat_id,
            photo=image_bytes,
            caption=f"OCR results for '{search_text}'",
        )

    lines = [
        f"{index}. '{match.text}' at ({match.x}, {match.y})"
        for index, match in enumerate(matches[:15], start=1)
    ]
    summary = f"Found {len(matches)} match(es) for '{search_text}':\n" + "\n".join(lines)
    return GeminiToolResult(True, summary, media_sent=bool(bot and chat_id is not None))


async def _scan_ui_elements(user_id: int, tool_runtime: dict[str, Any]) -> GeminiToolResult:
    """Detect and label UI elements on screen, then send the annotated image."""
    from pocket_desk_agent.handlers._shared import findui_options

    def _scan() -> tuple[list[Any], io.BytesIO]:
        import pyautogui
        from pocket_desk_agent.automation_utils import annotate_screenshot_with_markers, find_ui_elements

        screenshot = pyautogui.screenshot()
        matches = find_ui_elements(screenshot)
        annotated_bytes = io.BytesIO()
        if matches:
            annotated = annotate_screenshot_with_markers(screenshot, matches)
            annotated.save(annotated_bytes, format="PNG")
            annotated_bytes.seek(0)
        return matches, annotated_bytes

    matches, image_bytes = await asyncio.to_thread(_scan)
    if not matches:
        return GeminiToolResult(True, "No clickable UI elements were detected on the current screen.")

    findui_options[user_id] = {
        index: (match.x, match.y)
        for index, match in enumerate(matches, start=1)
    }
    bot = tool_runtime.get("bot")
    chat_id = tool_runtime.get("chat_id")
    if bot and chat_id is not None:
        await bot.send_photo(
            chat_id=chat_id,
            photo=image_bytes,
            caption="Numbered UI element scan",
        )

    return GeminiToolResult(
        True,
        f"Found {len(matches)} numbered UI elements. Use click_ui_element with the saved selection number to click one after approval.",
        media_sent=bool(bot and chat_id is not None),
    )


def _get_battery_status_text() -> str:
    """Return the current battery status in the same spirit as /battery."""
    import psutil

    battery = psutil.sensors_battery()
    if battery is None:
        return "No battery detected. This may be a desktop or battery reporting may be unavailable."

    if battery.secsleft == psutil.POWER_TIME_UNLIMITED:
        time_remaining = "Unlimited (plugged in)"
    elif battery.secsleft == psutil.POWER_TIME_UNKNOWN:
        time_remaining = "Unknown"
    else:
        hours = battery.secsleft // 3600
        minutes = (battery.secsleft % 3600) // 60
        time_remaining = f"{hours}h {minutes}m"

    status = "Charging" if battery.power_plugged else "Not charging"
    return (
        f"Battery level: {battery.percent}%\n"
        f"Status: {status}\n"
        f"Time remaining: {time_remaining}"
    )


def _list_open_windows(user_id: int) -> str:
    """Return the current window inventory and cache the selection numbers."""
    from pocket_desk_agent.handlers._shared import window_switch_options
    from pocket_desk_agent.window_utils import format_window_inventory, list_open_windows

    windows = list_open_windows()
    if not windows:
        return "No open application windows were found."

    window_switch_options[user_id] = {
        index: {"handle": window.handle, "title": window.title}
        for index, window in enumerate(windows, start=1)
    }
    return format_window_inventory(windows)


def _focus_window(user_id: int, selection: int) -> tuple[bool, str]:
    """Activate a cached window selection."""
    from pocket_desk_agent.handlers._shared import window_switch_options
    from pocket_desk_agent.window_utils import activate_window

    selected = window_switch_options.get(user_id, {}).get(selection)
    if not selected:
        return False, "No saved window list was found for that selection. Run list_open_windows first."

    if activate_window(selected["handle"]):
        return True, f"Activated window {selection}: {selected['title']}"
    return False, "That window could not be activated. It may have been closed. Run list_open_windows again."


def _read_clipboard_text() -> str:
    """Read the current clipboard, truncating very large values."""
    import pyperclip

    content = pyperclip.paste()
    if not content:
        return "The clipboard is currently empty."
    if len(content) > 3900:
        content = content[:3900] + "\n...(truncated)"
    return f"Clipboard contents:\n\n{content}"


def _list_custom_commands_text() -> str:
    """Return a readable list of saved custom commands."""
    commands = get_registry().list_commands()
    if not commands:
        return "No saved custom commands exist yet."
    lines = [f"/{name} ({count} actions)" for name, count in commands.items()]
    return "Saved custom commands:\n" + "\n".join(lines)


def _list_schedules_text(user_id: int) -> str:
    """Return the current user's pending schedules."""
    from pocket_desk_agent.handlers.scheduling import describe_task
    from pocket_desk_agent.scheduling_utils import format_eta, get_task_due_at

    tasks = [t for t in get_scheduler_registry().get_all_pending() if t.get("user_id") == user_id]
    if not tasks:
        return "There are no pending scheduled tasks for this user."

    now = dt.datetime.now().astimezone()
    lines = []
    for index, task in enumerate(tasks, start=1):
        due_at = get_task_due_at(task)
        try:
            when = due_at.strftime("%Y-%m-%d %H:%M:%S") if due_at else str(task.get("execute_at", "")).strip()
            eta = format_eta(due_at, now=now) if due_at else "unknown ETA"
        except Exception:
            when = str(task.get("execute_at", "")).strip()
            eta = "unknown ETA"
        try:
            description = describe_task(ScheduledTask.from_dict(task))
        except Exception:
            description = str(task.get("command", "")).strip() or "task"
        lines.append(f"{index}. {task.get('id', '?')} at {when} ({eta}) -> {description}")
    return "Pending scheduled tasks:\n" + "\n".join(lines)


async def _execute_confirmed_action(pending: PendingGeminiAction, bot: Any) -> GeminiToolResult:
    """Execute an already-approved side-effecting action."""
    action_type = pending.action_type
    args = pending.args

    if action_type in {"write_file", "append_file", "delete_file", "create_directory"}:
        from pocket_desk_agent.handlers._shared import file_manager

        method = getattr(file_manager, action_type)
        if action_type in {"delete_file", "create_directory"}:
            success, message = method(pending.user_id, str(args.get("path", "")))
        else:
            success, message = method(
                pending.user_id,
                str(args.get("path", "")),
                str(args.get("content", "")),
            )
        return GeminiToolResult(success, message)

    if action_type == "shutdown_computer":
        from pocket_desk_agent.handlers.system import perform_system_shutdown

        perform_system_shutdown()
        return GeminiToolResult(True, "Shutdown requested. The computer should power off shortly.")

    if action_type == "sleep_computer":
        from pocket_desk_agent.handlers.system import perform_system_sleep

        return GeminiToolResult(True, perform_system_sleep())

    if action_type == "set_privacy_mode":
        from pocket_desk_agent.handlers.system import _set_privacy_mode_windows

        mode = str(args.get("mode", "status")).strip().lower()
        if mode not in {"on", "off"}:
            return GeminiToolResult(False, "Privacy mode confirmations only support on or off.")
        success, message = _set_privacy_mode_windows(mode == "on")
        return GeminiToolResult(success, message)

    if action_type == "run_saved_command":
        command_name = str(args.get("name", "")).strip().lstrip("/")
        if not command_name:
            return GeminiToolResult(False, "No saved command name was provided.")
        return await _run_saved_command(bot=bot, chat_id=pending.chat_id, user_id=pending.user_id, command_name=command_name)

    if action_type == "start_screen_watch":
        from pocket_desk_agent.handlers.scheduling import start_screen_watch_task
        from pocket_desk_agent.scheduling_utils import parse_duration_spec

        interval_text = str(args.get("interval", "")).strip()
        interval_delta = parse_duration_spec(interval_text)
        if not interval_delta:
            return GeminiToolResult(False, "Invalid screen watch interval. Use values like 30s, 1m, or 2m.")
        cooldown_text = str(args.get("cooldown", "")).strip()
        cooldown_seconds = 0
        if cooldown_text:
            cooldown_delta = parse_duration_spec(cooldown_text)
            if not cooldown_delta:
                return GeminiToolResult(False, "Invalid screen watch cooldown. Use values like 30s or 1m.")
            cooldown_seconds = int(cooldown_delta.total_seconds())
        success, message = start_screen_watch_task(
            user_id=pending.user_id,
            search_text=str(args.get("text", "")),
            interval_seconds=int(interval_delta.total_seconds()),
            hotkey=str(args.get("hotkey", "")),
            scope=str(args.get("scope", "screen")),
            cooldown_seconds=cooldown_seconds,
        )
        return GeminiToolResult(success, message)

    if action_type == "set_clipboard":
        import pyperclip

        text = str(args.get("text", ""))
        pyperclip.copy(text)
        return GeminiToolResult(True, f"Clipboard updated with {_shorten(text)}")

    if action_type == "press_hotkey":
        import pyautogui
        from pocket_desk_agent.automation_utils import (
            map_keys_to_pyautogui,
            press_key,
            send_hotkey,
            write_text,
        )

        keys = str(args.get("keys", ""))
        text = args.get("text")
        if keys.lower() == "type":
            if not text:
                return GeminiToolResult(False, "The special 'type' mode requires text.")
            write_text(pyautogui, str(text), interval=0.05)
            return GeminiToolResult(True, f"Typed {_shorten(str(text))}")

        mapped_keys = map_keys_to_pyautogui(keys)
        if not mapped_keys:
            return GeminiToolResult(False, f"Unsupported hotkey string: {keys}")
        if len(mapped_keys) == 1:
            press_key(pyautogui, mapped_keys[0])
        else:
            send_hotkey(pyautogui, *mapped_keys)
        if text:
            await asyncio.sleep(0.4)
            write_text(pyautogui, str(text), interval=0.05)
            return GeminiToolResult(True, f"Sent hotkey '{keys}' and typed {_shorten(str(text))}")
        return GeminiToolResult(True, f"Sent hotkey '{keys}'")

    if action_type == "click_coordinates":
        import pyautogui

        x = int(args.get("x", 0))
        y = int(args.get("y", 0))
        pyautogui.click(x, y)
        return GeminiToolResult(True, f"Clicked coordinates ({x}, {y})")

    if action_type == "smart_click_text":
        search_text = str(args.get("text", ""))
        def _find_match() -> Optional[tuple[str, int, int]]:
            import pyautogui
            from pocket_desk_agent.automation_utils import find_text_in_image

            screenshot = pyautogui.screenshot()
            matches = find_text_in_image(screenshot, search_text)
            if not matches:
                return None
            best = matches[0]
            return best.text, best.x, best.y

        best_match = await asyncio.to_thread(_find_match)
        if not best_match:
            return GeminiToolResult(False, f"No on-screen match found for '{search_text}'.")

        import pyautogui

        best_text, best_x, best_y = best_match
        pyautogui.click(best_x, best_y)
        return GeminiToolResult(True, f"Clicked '{best_text}' at ({best_x}, {best_y})")

    if action_type == "click_ui_element":
        import pyautogui
        from pocket_desk_agent.handlers._shared import findui_options

        selection = int(args.get("selection", 0))
        coords = findui_options.get(pending.user_id, {}).get(selection)
        if not coords:
            return GeminiToolResult(False, "No saved UI element scan was found for that selection. Run scan_ui_elements first.")
        pyautogui.click(coords[0], coords[1])
        return GeminiToolResult(True, f"Clicked UI element #{selection} at ({coords[0]}, {coords[1]})")

    if action_type == "open_claude":
        return await _run_handler_action(
            user_id=pending.user_id,
            chat_id=pending.chat_id,
            bot=bot,
            handler_path="pocket_desk_agent.handlers.claude",
            handler_name="openclaude_command",
            args=[],
        )

    if action_type == "claude_new_chat":
        message = args.get("message")
        handler_args = [str(message)] if message else []
        return await _run_handler_action(
            user_id=pending.user_id,
            chat_id=pending.chat_id,
            bot=bot,
            handler_path="pocket_desk_agent.handlers.claude",
            handler_name="claudenew_command",
            args=handler_args,
        )

    if action_type == "claude_send_message":
        return await _run_handler_action(
            user_id=pending.user_id,
            chat_id=pending.chat_id,
            bot=bot,
            handler_path="pocket_desk_agent.handlers.claude",
            handler_name="claudechat_command",
            args=[str(args.get("message", ""))],
        )

    if action_type == "open_antigravity":
        return await _run_handler_action(
            user_id=pending.user_id,
            chat_id=pending.chat_id,
            bot=bot,
            handler_path="pocket_desk_agent.handlers.antigravity",
            handler_name="openantigravity_command",
            args=[],
        )

    if action_type == "focus_antigravity_chat":
        return await _run_handler_action(
            user_id=pending.user_id,
            chat_id=pending.chat_id,
            bot=bot,
            handler_path="pocket_desk_agent.handlers.antigravity",
            handler_name="antigravitychat_command",
            args=[],
        )

    if action_type == "open_browser":
        from pocket_desk_agent.handlers.antigravity import launch_browser

        success, message = launch_browser(str(args.get("browser", "")))
        return GeminiToolResult(success, message)

    if action_type == "open_vscode_folder":
        from pocket_desk_agent.handlers.antigravity import open_folder_in_vscode, resolve_workspace_folder

        resolved, folder_or_error = resolve_workspace_folder(str(args.get("folder", "")))
        if not resolved:
            return GeminiToolResult(False, folder_or_error)
        success, message = open_folder_in_vscode(folder_or_error)
        return GeminiToolResult(success, message)

    if action_type == "open_claude_cli":
        from pocket_desk_agent.handlers.antigravity import launch_claude_cli, resolve_workspace_folder

        resolved, folder_or_error = resolve_workspace_folder(str(args.get("folder", "")))
        if not resolved:
            return GeminiToolResult(False, folder_or_error)
        success, message = launch_claude_cli(folder_or_error, str(args.get("prompt", "")))
        return GeminiToolResult(success, message)

    if action_type == "claude_cli_send_message":
        from pocket_desk_agent.handlers.antigravity import send_prompt_to_claude_cli

        success, message = send_prompt_to_claude_cli(str(args.get("message", "")))
        return GeminiToolResult(success, message)

    if action_type == "schedule_claude_prompt":
        execute_at = _parse_schedule_time(str(args.get("execute_at", "")))
        if not execute_at:
            return GeminiToolResult(False, "Invalid schedule time. Use HH:MM or YYYY-MM-DD HH:MM.")
        prompt = str(args.get("prompt", ""))
        task = ScheduledTask(
            id=f"claude_{int(time.time())}",
            user_id=pending.user_id,
            command=f"claude_msg:{prompt}",
            execute_at=execute_at.isoformat(),
            task_type="claude_prompt",
        )
        get_scheduler_registry().add_task(task)
        return GeminiToolResult(True, f"Scheduled the Claude prompt for {execute_at.strftime('%Y-%m-%d %H:%M')}.")

    if action_type == "start_remote_session_ai":
        from pocket_desk_agent.handlers.remote import start_remote_session

        success, message = await start_remote_session(
            user_id=pending.user_id,
            chat_id=pending.chat_id,
            bot=bot,
        )
        return GeminiToolResult(success, message)

    if action_type == "stop_remote_session_ai":
        from pocket_desk_agent.handlers.remote import stop_remote_session

        success, message = await stop_remote_session(
            user_id=pending.user_id,
            bot=bot,
            reason="stopped",
        )
        return GeminiToolResult(success, message)

    if action_type == "schedule_desktop_sequence":
        execute_at = _parse_schedule_time(str(args.get("execute_at", "")))
        if not execute_at:
            return GeminiToolResult(False, "Invalid schedule time. Use HH:MM or YYYY-MM-DD HH:MM.")

        actions = _coerce_scheduled_actions(args.get("actions", []))
        if not actions:
            return GeminiToolResult(False, "No valid schedulable actions were provided.")

        name = str(args.get("name", "")).strip() or f"gemini_schedule_{int(time.time())}"
        registry = get_registry()
        if hasattr(registry, "command_exists"):
            base_name = name
            suffix = 1
            while registry.command_exists(name):
                suffix += 1
                name = f"{base_name}_{suffix}"
        if not registry.add_command(name, actions):
            return GeminiToolResult(False, "Failed to persist the scheduled automation sequence.")

        task = ScheduledTask(
            id=f"sched_{int(time.time())}",
            user_id=pending.user_id,
            command=f"custom_cmd:{name}",
            execute_at=execute_at.isoformat(),
            task_type="custom_command",
            temporary_command=True,
        )
        get_scheduler_registry().add_task(task)
        return GeminiToolResult(True, f"Scheduled '{name}' for {execute_at.strftime('%Y-%m-%d %H:%M')} with {len(actions)} action(s).")

    return GeminiToolResult(False, f"Unsupported approved action '{action_type}'.")


def _parse_schedule_time(time_str: str) -> Optional[dt.datetime]:
    """Parse schedule strings using the same formats as /schedule."""
    now = dt.datetime.now().astimezone()
    try:
        if ":" in time_str and "-" not in time_str:
            parsed = dt.datetime.strptime(time_str, "%H:%M")
            candidate = now.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
            if candidate < now:
                candidate += dt.timedelta(days=1)
            return candidate

        parsed = dt.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        return parsed.replace(tzinfo=now.tzinfo)
    except Exception:
        return None


def _coerce_scheduled_actions(raw_actions: Any) -> list[CommandAction]:
    """Validate and normalize scheduled automation actions."""
    if not isinstance(raw_actions, list):
        return []

    actions: list[CommandAction] = []
    for raw_action in raw_actions:
        if not isinstance(raw_action, dict):
            continue
        action_type = str(raw_action.get("type", "")).strip().lower()
        if action_type not in _SCHEDULABLE_ACTIONS:
            continue
        raw_args = raw_action.get("args", [])
        if not isinstance(raw_args, list):
            continue
        args = [str(item) for item in raw_args]
        actions.append(CommandAction(type=action_type, args=args))
    return actions


async def _run_handler_action(
    user_id: int,
    chat_id: int,
    bot: Any,
    handler_path: str,
    handler_name: str,
    args: list[str],
) -> GeminiToolResult:
    """Run an existing handler with a lightweight proxy update/context."""
    module = __import__(handler_path, fromlist=[handler_name])
    handler = getattr(module, handler_name)
    collector = _MessageCollector(bot, chat_id)
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id),
        message=collector,
    )
    context = SimpleNamespace(bot=bot, args=args)
    await handler(update, context)
    if collector.messages:
        return GeminiToolResult(True, "\n".join(collector.messages[-3:]))
    return GeminiToolResult(True, f"Completed action via {handler_name}.")


async def _run_saved_command(bot: Any, chat_id: int, user_id: int, command_name: str) -> GeminiToolResult:
    """Execute a saved custom command through the existing command runner."""
    from pocket_desk_agent.handlers.custom_commands import execute_custom_command

    collector = _MessageCollector(bot, chat_id)
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id),
        message=collector,
    )
    context = SimpleNamespace(bot=bot, args=[])
    await execute_custom_command(update, context, command_name)
    if collector.messages:
        final_message = collector.messages[-1]
        return GeminiToolResult(not final_message.startswith("❌"), "\n".join(collector.messages[-3:]))
    return GeminiToolResult(True, f"Completed saved command '/{command_name}'.")


class _MessageCollector:
    """Minimal Telegram message proxy for reusing existing handlers."""

    def __init__(self, bot: Any, chat_id: int):
        self._bot = bot
        self._chat_id = chat_id
        self.messages: list[str] = []

    async def reply_text(self, text: str, **kwargs):
        """Forward reply_text calls to the real bot while collecting the text."""
        self.messages.append(text)
        return SimpleNamespace(text=text, kwargs=kwargs)

    async def reply_photo(self, photo: Any, caption: Optional[str] = None, **kwargs):
        """Forward reply_photo calls to the real bot and remember the caption."""
        if caption:
            self.messages.append(caption)
        return await self._bot.send_photo(chat_id=self._chat_id, photo=photo, caption=caption, **kwargs)


def _summarize_file_action(func_name: str, args: dict[str, Any]) -> str:
    """Build a readable confirmation summary for file mutations."""
    path = str(args.get("path", ""))
    if func_name == "write_file":
        return f"overwrite or create the file '{path}'"
    if func_name == "append_file":
        return f"append content to the file '{path}'"
    if func_name == "delete_file":
        return f"delete the file '{path}'"
    return f"create the directory '{path}'"


def _summarize_scheduled_sequence(execute_at: str, name: str, actions: Any) -> str:
    """Build a compact confirmation summary for a scheduled action list."""
    count = len(actions) if isinstance(actions, list) else 0
    label = name or "desktop sequence"
    return f"schedule '{label}' for {execute_at} with {count} action(s)"


def _shorten(text: str, limit: int = _MAX_TEXT_PREVIEW) -> str:
    """Return a single-line preview string suitable for confirmations."""
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return f"'{cleaned}'"
    return f"'{cleaned[: limit - 3]}...'"

