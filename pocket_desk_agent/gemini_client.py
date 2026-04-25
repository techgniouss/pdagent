"""Gemini AI client with multi-auth support (Antigravity OAuth, Gemini CLI OAuth, API Key)."""

import json
import uuid
import logging
import asyncio
import re
from typing import Optional, Tuple, Dict, Any, Callable

import requests

from pocket_desk_agent.config import Config
from pocket_desk_agent.antigravity_auth import AntigravityOAuth
from pocket_desk_agent.gemini_cli_auth import GeminiCLIOAuth
from pocket_desk_agent.gemini_actions import (
    dispatch_gemini_tool,
    get_gemini_action_tools,
)
from pocket_desk_agent.constants import (
    ANTIGRAVITY_ENDPOINT_PROD,
    GEMINI_API_BASE_URL,
    THINKING_TIER_BUDGETS,
    GEMINI_CLI_HEADERS,
    MAX_HISTORY_TURNS,
    AUTH_MODE_GEMINI_CLI,
    AUTH_MODE_APIKEY,
)

logger = logging.getLogger(__name__)

OAuthProvider = AntigravityOAuth | GeminiCLIOAuth

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
    "launch_browser": "open_browser",
    "open_folder_vscode": "open_vscode_folder",
    "vscode_open_folder": "open_vscode_folder",
    "launch_claude_cli": "open_claude_cli",
    "send_claude_cli_message": "claude_cli_send_message",
}

# ============================================================================
# SYSTEM INSTRUCTION
# ============================================================================
DEFAULT_SYSTEM_INSTRUCTION = """You are a helpful AI assistant.
You are assisting a USER with various tasks, including coding, general questions, and system management.

You have access to comprehensive tools for files, desktop context, and automation.

**Exploration Tools**:
- get_current_directory / change_directory: Handle requests like /pwd and /cd
- list_directory / search_files / read_file / get_file_info: Handle requests like /ls, /find, /cat, and /info
- get_tree_structure: Get complete project structure (use this first to understand the project!)

**Desktop Tools**:
- capture_screenshot: Capture the current screen and send it back to the chat
- list_open_windows / focus_window: Inspect and switch application windows
- find_text_on_screen / scan_ui_elements: Understand what's visible before clicking
- view_clipboard / get_battery_status: Inspect host state
- start_screen_watch / stop_screen_watch: Start or stop recurring screen watchers that look for text and send a hotkey
- start_build_workflow: Prepare the existing build flow so the user can choose a project/script
- start_apk_retrieval_workflow: Prepare the existing APK retrieval flow so the user can choose a project or browse build outputs
- set_privacy_mode: Check or control display privacy mode
- open_browser: Open a supported browser in a maximized window
- open_vscode_folder: Open a specific approved folder in VS Code
- open_claude_cli / claude_cli_send_message: Launch Claude CLI in a folder or send it a follow-up prompt
- get_remote_session_status: Read-only status of the live remote-desktop session (URL, fps, idle time)

**Confirmed Action Tools**:
- write_file / append_file / delete_file / create_directory
- set_clipboard / press_hotkey / click_coordinates / smart_click_text / click_ui_element
- run_saved_command / shutdown_computer / sleep_computer
- open_claude / claude_new_chat / claude_send_message
- open_antigravity / focus_antigravity_chat
- schedule_claude_prompt / schedule_desktop_sequence
- request_remote_session / request_stop_remote_session (confirmation-gated live remote-desktop)

These tools send an approval prompt to the user before any risky action happens.

**Best Practices**:
1. Start with get_tree_structure to understand the project layout
2. Read files and inspect the current UI before modifying things
3. Explain what you're doing and why
4. For risky actions, tell the user an approval prompt has been sent
5. All file paths are relative to the current working directory unless the tool says otherwise
6. Prefer existing workflows for slash-command-style requests. Examples:
   - "build emploi project" -> start_build_workflow
   - "get apk from emploi" -> start_apk_retrieval_workflow
   - "watch Claude every minute for Allow and press enter with 30s cooldown" -> start_screen_watch
   - "stop watching my screen" -> stop_screen_watch
   - "open chrome" -> open_browser
   - "open emploi folder in vscode" -> open_vscode_folder
   - "open claude cli in emploi and ask it to run tests" -> open_claude_cli
   - "open remote" / "control my pc from my phone" / "share my screen" -> request_remote_session
   - "stop remote" / "end remote session" -> request_stop_remote_session
   - "show current folder" -> get_current_directory or list_directory
   - "open/read/find file" -> use the filesystem tools above
7. Users may phrase commands naturally (aliases like "start remote", "get apk", "watch screen", "at 22:30", "every 1m"). Map those to the canonical tool names and expected arguments.

Use these tools proactively to understand context and complete tasks efficiently!
"""

class ResolvedModel:
    """Resolved model with thinking configuration - ported from Agile AI Engineer."""
    def __init__(self, actual_model: str, is_thinking_model: bool = False, thinking_budget: Optional[int] = None,
                 thinking_level: Optional[str] = None, quota_preference: str = "gemini-cli"):
        self.actual_model = actual_model
        self.is_thinking_model = is_thinking_model
        self.thinking_budget = thinking_budget
        self.thinking_level = thinking_level
        self.quota_preference = quota_preference

def resolve_model(requested_model: str) -> ResolvedModel:
    """Resolve model name and thinking config."""
    lower = requested_model.lower()

    # Strip prefixes
    base_name = re.sub(r"^antigravity-", "", requested_model, flags=re.IGNORECASE)

    # Extract tier
    tier_match = re.search(r"-(minimal|low|medium|high)$", base_name, re.IGNORECASE)
    tier = tier_match.group(1).lower() if tier_match else None
    if tier:
        base_name = re.sub(r"-(minimal|low|medium|high)$", "", base_name, re.IGNORECASE)

    is_gemini3 = "gemini-3" in lower and "-preview" not in lower
    is_gemini25 = "gemini-2.5" in lower

    quota_preference = "gemini-cli" if is_gemini25 else "antigravity"

    actual_model = base_name
    if is_gemini3 and "gemini-3-pro" in lower:
        actual_model = f"{base_name}-{tier or 'low'}"

    # Thinking
    is_thinking_model = "thinking" in lower or is_gemini3 or is_gemini25
    thinking_budget = None
    thinking_level = None

    if is_thinking_model:
        if is_gemini3:
            thinking_level = tier or "low"
        elif is_gemini25:
            budget_family = THINKING_TIER_BUDGETS.get("gemini-2.5-pro" if "pro" in lower else "gemini-2.5-flash", THINKING_TIER_BUDGETS["default"])
            thinking_budget = budget_family.get(tier) or budget_family.get("medium", 12288)

    return ResolvedModel(actual_model, is_thinking_model, thinking_budget, thinking_level, quota_preference)


def _candidate_model_names(requested_model: str) -> list[str]:
    """Return ordered fallback candidates for backend model lookup."""
    candidates: list[str] = []

    def add(name: str) -> None:
        normalized = name.strip()
        if normalized and normalized not in candidates:
            candidates.append(normalized)

    add(requested_model)

    base_name = re.sub(r"^antigravity-", "", requested_model.strip(), flags=re.IGNORECASE)
    add(base_name)

    tierless_name = re.sub(r"-(minimal|low|medium|high)$", "", base_name, flags=re.IGNORECASE)
    add(tierless_name)

    lower = tierless_name.lower()
    if "gemini-2.5" in lower and "pro" in lower:
        add("gemini-2.5-pro")
        add("gemini-2.5-flash")
    elif "gemini-2.5" in lower and "flash" in lower:
        add("gemini-2.5-flash")
    else:
        add("gemini-2.5-flash")

    if "gemini-3" in lower and "pro" in lower:
        add("gemini-3-pro")
        add("gemini-2.5-flash")

    add("gemini-2.0-flash")
    return candidates


def _is_model_not_found_error(response_data: dict) -> bool:
    """Return True when the backend rejected the requested model lookup."""
    error_text = response_data.get("error", "")
    if not isinstance(error_text, str):
        return False
    return "HTTP 404" in error_text and "Requested entity was not found" in error_text


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
        "scan_ui_elements",
        "open_claude",
        "open_antigravity",
        "focus_antigravity_chat",
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
    if func_name == "click_ui_element":
        selection = _first_value(args, "selection", "index", "number", "element", "id")
        return {"selection": _as_int(selection, default=0)}
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
    if func_name == "open_browser":
        browser = _first_string(args, "browser", "name", "app", "target", default="edge").lower()
        return {"browser": browser}
    if func_name in {"open_vscode_folder", "open_claude_cli"}:
        folder = _first_string(args, "folder", "path", "repo", "project", "name", "directory")
        normalized = {"folder": folder}
        if func_name == "open_claude_cli":
            normalized["prompt"] = _first_string(args, "prompt", "message", "text", "query")
        return normalized
    if func_name in {"claude_send_message", "claude_cli_send_message", "claude_new_chat"}:
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


def _normalize_tool_call(func_name: Any, args: Any) -> tuple[str, dict[str, Any]]:
    """Normalize tool names and argument aliases before allowlist enforcement."""
    normalized_name = _normalize_tool_name(func_name)
    canonical_name = _TOOL_NAME_ALIASES.get(normalized_name, normalized_name)
    raw_args = args if isinstance(args, dict) else {}
    normalized_args = _normalize_tool_args(canonical_name, raw_args)
    return canonical_name, normalized_args

def _get_code_assist_headers(_auth_mode: str, access_token: str) -> dict:
    """Build headers for the shared internal Code Assist backend."""
    base = dict(GEMINI_CLI_HEADERS)
    base["User-Agent"] = "GeminiCLI/1.0.0 google-api-nodejs-client/10.3.0"

    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        **base,
    }

def _get_code_assist_endpoints(_auth_mode: str) -> list[str]:
    """Return the stable endpoint order for the Code Assist backend."""
    return [ANTIGRAVITY_ENDPOINT_PROD]

def _build_wrapped_body(project_id: str, model: str, history: list, message: Optional[str] = None) -> Tuple[dict, ResolvedModel]:
    resolved = resolve_model(model)
    contents = list(history)
    if message is not None:
        contents.append({"role": "user", "parts": [{"text": message}]})

    gen_config = {
        "temperature": 0.7,
        "topP": 0.95,
        "maxOutputTokens": Config.MAX_TOKENS_PER_REQUEST,
    }

    if resolved.is_thinking_model:
        thinking_config = {"includeThoughts": True}
        if resolved.thinking_level:
            thinking_config["thinkingLevel"] = resolved.thinking_level
        gen_config["thinkingConfig"] = thinking_config

    request_payload = {
        "contents": contents,
        "generationConfig": gen_config,
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_LOW_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_LOW_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_LOW_AND_ABOVE"},
        ],
        "sessionId": f"pdagent-{uuid.uuid4()}",
        "systemInstruction": {
            "role": "user",
            "parts": [{"text": Config.SYSTEM_PROMPT or DEFAULT_SYSTEM_INSTRUCTION}]
        },
    }

    wrapped = {
        "model": resolved.actual_model,
        "request": request_payload,
        "requestType": "agent",
        "userAgent": "antigravity",
        "requestId": f"agent-{uuid.uuid4()}",
    }
    if project_id:
        wrapped["project"] = project_id

    return wrapped, resolved

def _get_api_tools() -> list:
    """Define tools available to the AI.

    SECURITY NOTE: ``execute_command`` is intentionally excluded.
    Allowing an LLM to invoke shell commands via prompt is a
    prompt-injection → RCE vector.
    """
    declarations = [
            {
                "name": "list_directory",
                "description": "List files and subdirectories in the current or specified path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Optional relative path to list. Leave empty for current directory."}
                    }
                }
            },
            {
                "name": "get_tree_structure",
                "description": "Get a tree view of the entire directory structure. Perfect for understanding project layout and contents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Optional relative path. Leave empty for current directory."},
                        "max_depth": {"type": "integer", "description": "Maximum depth to traverse (default: 3)"},
                        "max_files": {"type": "integer", "description": "Maximum files to show (default: 100)"}
                    }
                }
            },
            {
                "name": "read_file",
                "description": "Read the content of a specific file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path to the file to read."}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "search_files",
                "description": "Recursively search for files matching a pattern in all subfolders.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Substring to search for in filenames."}
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "write_file",
                "description": "Ask the user to approve writing content to a file. Creates new files or overwrites existing ones after approval.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path to the file to write."},
                        "content": {"type": "string", "description": "Content to write to the file."}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "append_file",
                "description": "Ask the user to approve appending content to an existing file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path to the file to append to."},
                        "content": {"type": "string", "description": "Content to append to the file."}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "delete_file",
                "description": "Ask the user to approve deleting a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path to the file to delete."}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "create_directory",
                "description": "Ask the user to approve creating a new directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path to the directory to create."}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "get_file_info",
                "description": "Get detailed information about a file or directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path to the file or directory."}
                    },
                    "required": ["path"]
                }
            },
        ]
    declarations.extend(get_gemini_action_tools())
    return [{"functionDeclarations": declarations}]

# Strict allowlist of tool names the AI is permitted to invoke.
# Any function call whose name is not in this set is silently ignored.
_ALLOWED_TOOLS = frozenset({
    "list_directory",
    "get_tree_structure",
    "read_file",
    "search_files",
    "write_file",
    "append_file",
    "delete_file",
    "create_directory",
    "get_file_info",
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
    "scan_ui_elements",
    "set_clipboard",
    "press_hotkey",
    "click_coordinates",
    "smart_click_text",
    "click_ui_element",
    "open_claude",
    "claude_new_chat",
    "claude_send_message",
    "open_antigravity",
    "focus_antigravity_chat",
    "open_browser",
    "open_vscode_folder",
    "open_claude_cli",
    "claude_cli_send_message",
    "schedule_claude_prompt",
    "schedule_desktop_sequence",
    "request_remote_session",
    "request_stop_remote_session",
    "get_remote_session_status",
})

def _build_wrapped_body_with_tools(project_id: str, model: str, history: list, message: Optional[str] = None) -> Tuple[dict, ResolvedModel]:
    wrapped, resolved = _build_wrapped_body(project_id, model, history, message)
    wrapped["request"]["tools"] = _get_api_tools()
    return wrapped, resolved

def _parse_full_response(data: dict) -> str:
    candidates = data.get('candidates', [])
    if not candidates:
        return ""
    parts = candidates[0].get('content', {}).get('parts', [])
    return "".join(
        part["text"]
        for part in parts
        if "text" in part and not part.get("thought")
    )

def _trim_history(history: list) -> list:
    """Keep only the most recent MAX_HISTORY_TURNS pairs of messages."""
    max_items = MAX_HISTORY_TURNS * 2  # each turn = user + model
    if len(history) > max_items:
        return history[-max_items:]
    return history

class GeminiClient:
    """Telegram bot Gemini client with Tool support."""

    def __init__(self):
        self.model = Config.GEMINI_MODEL
        self.sessions: Dict[int, list] = {}
        self._working_model_cache: Dict[str, str] = {}
        self._auth_mode = Config.GEMINI_AUTH_MODE

        if self._auth_mode == AUTH_MODE_APIKEY:
            logger.info("Using API key mode (standard Gemini API)")
            self._oauth = None
        elif self._auth_mode == AUTH_MODE_GEMINI_CLI:
            logger.info("Using Gemini CLI OAuth mode (Code Assist backend)")
            self._oauth = GeminiCLIOAuth()
            if not self._oauth.load_saved_tokens():
                logger.warning("No saved Gemini CLI tokens.")
        else:
            logger.info("Using Antigravity OAuth mode (internal API)")
            self._oauth = AntigravityOAuth()
            if self._oauth.load_saved_tokens():
                self._oauth._fetch_project_id()
                self._oauth._save_tokens()
            else:
                logger.warning("No saved tokens.")

    def _get_token(self) -> str:
        if self._auth_mode == AUTH_MODE_APIKEY:
            return ""
        self._oauth.ensure_valid_token()
        return self._oauth.access_token

    def _resolve_auth_context(
        self,
        auth_mode: Optional[str] = None,
        oauth: Optional[OAuthProvider] = None,
    ) -> tuple[str, Optional[OAuthProvider]]:
        """Resolve the auth mode and OAuth instance for the current request."""
        resolved_mode = auth_mode or self._auth_mode

        if resolved_mode == AUTH_MODE_APIKEY:
            return resolved_mode, None

        if oauth is not None:
            return resolved_mode, oauth

        if resolved_mode == self._auth_mode and self._oauth is not None:
            return resolved_mode, self._oauth

        if resolved_mode == AUTH_MODE_GEMINI_CLI:
            resolved_oauth: OAuthProvider = GeminiCLIOAuth()
            resolved_oauth.load_saved_tokens()
            return resolved_mode, resolved_oauth

        resolved_oauth = AntigravityOAuth()
        if resolved_oauth.load_saved_tokens():
            resolved_oauth._fetch_project_id()
            resolved_oauth._save_tokens()
        return resolved_mode, resolved_oauth

    def _get_request_token(
        self,
        auth_mode: Optional[str] = None,
        oauth: Optional[OAuthProvider] = None,
    ) -> str:
        """Return the access token for the resolved auth context."""
        resolved_mode, resolved_oauth = self._resolve_auth_context(auth_mode, oauth)
        if resolved_mode == AUTH_MODE_APIKEY:
            return ""
        if resolved_oauth is None:
            raise RuntimeError("Google authentication is not configured.")
        resolved_oauth.ensure_valid_token()
        return resolved_oauth.access_token or ""

    def _get_project(
        self,
        auth_mode: Optional[str] = None,
        oauth: Optional[OAuthProvider] = None,
    ) -> str:
        resolved_mode, resolved_oauth = self._resolve_auth_context(auth_mode, oauth)
        if resolved_mode == AUTH_MODE_APIKEY:
            return ""  # Public API — no project needed
        if resolved_oauth is None:
            raise RuntimeError("Google authentication is not configured.")

        if resolved_mode == AUTH_MODE_GEMINI_CLI:
            if isinstance(resolved_oauth, GeminiCLIOAuth):
                resolved_oauth.ensure_code_assist_ready()
                return resolved_oauth.project_id or ""
            return ""

        project = resolved_oauth.project_id
        if not project and isinstance(resolved_oauth, AntigravityOAuth):
            if resolved_oauth.load_saved_tokens():
                resolved_oauth._fetch_project_id()
                resolved_oauth._save_tokens()
                project = resolved_oauth.project_id
        if not project:
            raise RuntimeError(
                "Google Cloud project ID not configured. "
                "Set GOOGLE_PROJECT_ID in your config or run 'pdagent configure'."
            )
        return project

    def get_or_create_session(self, user_id: int) -> list:
        if user_id not in self.sessions:
            self.sessions[user_id] = []
        return self.sessions[user_id]

    def _get_request_model_candidates(self) -> list[str]:
        """Return the configured model plus safe fallbacks, preferring known-good cache."""
        candidates = _candidate_model_names(self.model)
        cached = self._working_model_cache.get(self.model)
        if cached and cached in candidates:
            candidates.remove(cached)
            candidates.insert(0, cached)
        return candidates

    async def _request_with_model_fallbacks(
        self,
        loop: asyncio.AbstractEventLoop,
        auth_mode: str,
        token: str,
        project: str,
        build_request: Callable[[str], Tuple[dict, ResolvedModel]],
    ) -> dict:
        """Send a request, retrying when the backend rejects the selected model."""
        last_response = {"error": "Failed to connect: no model candidates available"}
        attempted_actual_models: set[str] = set()

        for requested_model in self._get_request_model_candidates():
            wrapped, resolved = build_request(requested_model)
            if resolved.actual_model in attempted_actual_models:
                continue
            attempted_actual_models.add(resolved.actual_model)
            response_data = await loop.run_in_executor(
                None,
                self._call_api_raw,
                auth_mode,
                token,
                project,
                wrapped,
                resolved,
            )

            if _is_model_not_found_error(response_data):
                logger.warning(
                    "Model lookup failed for '%s' (resolved as '%s'); trying fallback.",
                    requested_model,
                    resolved.actual_model,
                )
                last_response = response_data
                continue

            if not response_data.get("error"):
                self._working_model_cache[self.model] = requested_model
            return response_data

        return last_response

    async def send_message(
        self,
        user_id: int,
        message: str,
        file_manager: Any,
        tool_runtime: Optional[dict[str, Any]] = None,
        auth_mode: Optional[str] = None,
        oauth: Optional[OAuthProvider] = None,
    ) -> str:
        try:
            history = self.get_or_create_session(user_id)
            current_dir = file_manager.get_current_dir(user_id)
            full_message = f"[Current Directory: {current_dir}]\n\n{message}"

            resolved_auth_mode, resolved_oauth = self._resolve_auth_context(auth_mode, oauth)
            token = self._get_request_token(resolved_auth_mode, resolved_oauth)
            project = self._get_project(resolved_auth_mode, resolved_oauth)
            loop = asyncio.get_event_loop()

            # Snapshot the original history so we can roll back on failure
            # without leaking a half-built tool-call sequence into future turns.
            base_history_len = len(history)
            history.append({"role": "user", "parts": [{"text": full_message}]})

            max_turns = 10
            for turn in range(max_turns):
                response_data = await self._request_with_model_fallbacks(
                    loop,
                    resolved_auth_mode,
                    token,
                    project,
                    lambda requested_model: _build_wrapped_body_with_tools(
                        project,
                        requested_model,
                        history,
                    ),
                )

                if isinstance(response_data, dict) and response_data.get('error'):
                    err = response_data['error']
                    logger.error(f"Gemini API error on turn {turn}: {err}")
                    # Roll back the pending turn so the session stays clean.
                    del history[base_history_len:]
                    self.sessions[user_id] = _trim_history(history)
                    return f"Error contacting Gemini: {err}"

                candidates = response_data.get('candidates', [])
                if not candidates:
                    logger.warning(f"Empty candidates on turn {turn}: {str(response_data)[:400]}")
                    del history[base_history_len:]
                    self.sessions[user_id] = _trim_history(history)
                    prompt_feedback = response_data.get('promptFeedback') or {}
                    block_reason = prompt_feedback.get('blockReason')
                    if block_reason:
                        return f"The model blocked this request (reason: {block_reason})."
                    return "The model returned an empty response. Please try rephrasing."

                parts = candidates[0].get('content', {}).get('parts', [])
                tool_call = next((p.get('functionCall') for p in parts if p.get('functionCall')), None)

                if not tool_call:
                    response_text = _parse_full_response(response_data)
                    history.append({"role": "model", "parts": [{"text": response_text}]})
                    self.sessions[user_id] = _trim_history(history)
                    return response_text or "(The model returned an empty message.)"

                raw_func_name = tool_call.get('name')
                raw_args = tool_call.get('args', {}) or {}
                func_name, args = _normalize_tool_call(raw_func_name, raw_args)
                normalized_tool_call = {"name": func_name, "args": args}
                if func_name != raw_func_name or args != raw_args:
                    logger.info(
                        "Normalized tool call '%s' -> '%s' with args %s",
                        raw_func_name,
                        func_name,
                        args,
                    )

                if func_name not in _ALLOWED_TOOLS:
                    logger.warning(
                        f"AI requested disallowed tool '{func_name}' — "
                        f"ignoring (possible prompt injection)"
                    )
                    history.append({"role": "model", "parts": [{"functionCall": normalized_tool_call}]})
                    history.append({
                        "role": "user",
                        "parts": [{
                            "functionResponse": {
                                "name": func_name,
                                "response": {
                                    "result": f"Error: tool '{func_name}' is not available.",
                                    "success": False,
                                }
                            }
                        }]
                    })
                    continue

                logger.info(f"AI Turn {turn}: requested tool {func_name} with {args}")

                if func_name == "list_directory":
                    success, result_text = await loop.run_in_executor(None, file_manager.list_directory, user_id, args.get('path'))
                    tool_result = {"result": result_text, "success": success}
                elif func_name == "get_tree_structure":
                    success, result_text = await loop.run_in_executor(
                        None, file_manager.get_tree_structure,
                        user_id,
                        args.get('path'),
                        args.get('max_depth', 3),
                        args.get('max_files', 100)
                    )
                    tool_result = {"result": result_text, "success": success}
                elif func_name == "read_file":
                    success, result_text = await loop.run_in_executor(None, file_manager.read_file, user_id, args.get('path'))
                    tool_result = {"result": result_text, "success": success}
                elif func_name == "search_files":
                    success, result_text = await loop.run_in_executor(None, file_manager.search_files, user_id, args.get('pattern'))
                    tool_result = {"result": result_text, "success": success}
                elif func_name == "get_file_info":
                    success, result_text = await loop.run_in_executor(None, file_manager.get_file_info, user_id, args.get('path'))
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

                logger.info(f"Tool {func_name} result: {str(result_text)[:100]}")

                history.append({"role": "model", "parts": [{"functionCall": normalized_tool_call}]})
                history.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": func_name,
                            "response": tool_result
                        }
                    }]
                })

            logger.warning(f"send_message hit max_turns={max_turns} without final answer")
            del history[base_history_len:]
            self.sessions[user_id] = _trim_history(history)
            return (
                f"I couldn't complete the request after {max_turns} tool-call turns. "
                "Try asking in smaller steps."
            )

        except Exception as e:
            logger.exception(f"Error in send_message: {e}")
            return f"Error: {str(e)}"

    def _call_api_raw(
        self,
        auth_mode: str,
        token: str,
        project: str,
        wrapped: dict,
        resolved: ResolvedModel,
    ) -> dict:
        if auth_mode == AUTH_MODE_APIKEY:
            return self._call_api_key_raw(wrapped, resolved)

        if auth_mode == AUTH_MODE_GEMINI_CLI:
            return self._call_code_assist_raw(auth_mode, token, wrapped)

        # Antigravity mode uses the same Code Assist transport.
        headers = _get_code_assist_headers(auth_mode, token)
        headers["Accept"] = "application/json"

        endpoints = _get_code_assist_endpoints(auth_mode)
        last_error = "Unknown error"

        # The correct URL format is /v1internal:generateContent
        # The model is passed in the wrapped body (not the URL path).
        for endpoint in endpoints:
            url = f"{endpoint}/v1internal:generateContent"
            try:
                resp = requests.post(url, headers=headers, json=wrapped, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get('response', data)
                last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                logger.warning(f"Endpoint {url} returned {resp.status_code}: {resp.text[:300]}")
                if resp.status_code in (400, 401, 403, 429):
                    return {"error": last_error}
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Endpoint {url} error: {e}")
                continue

        return {"error": f"Failed to connect: {last_error}"}

    def _call_code_assist_raw(self, auth_mode: str, token: str, wrapped: dict) -> dict:
        """Call Google's internal Code Assist backend for OAuth auth modes."""
        headers = _get_code_assist_headers(auth_mode, token)
        headers["Accept"] = "application/json"
        last_error = "Unknown error"

        for endpoint in _get_code_assist_endpoints(auth_mode):
            url = f"{endpoint}/v1internal:generateContent"
            try:
                resp = requests.post(url, headers=headers, json=wrapped, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get('response', data)
                last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                logger.warning(f"Endpoint {url} returned {resp.status_code}: {resp.text[:300]}")
                if resp.status_code in (400, 401, 403, 429):
                    return {"error": last_error}
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Endpoint {url} error: {e}")
                continue

        return {"error": f"Failed to connect: {last_error}"}

    def _call_api_key_raw(self, wrapped: dict, resolved: ResolvedModel) -> dict:
        """Call the standard Gemini API using an API key (fallback mode)."""
        model = resolved.actual_model
        url = f"{GEMINI_API_BASE_URL}/v1beta/models/{model}:generateContent?key={Config.GOOGLE_API_KEY}"
        # Standard API uses the inner request payload directly
        payload = wrapped.get("request", wrapped)
        # Remove internal-only fields that the public API does not accept
        payload = {k: v for k, v in payload.items() if k not in ("sessionId",)}
        try:
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        except Exception as e:
            return {"error": str(e)}

    async def send_message_with_image(
        self,
        user_id: int,
        message: str,
        image_bytes: bytes,
        auth_mode: Optional[str] = None,
        oauth: Optional[OAuthProvider] = None,
    ) -> str:
        """Send a message with an image to Gemini for vision analysis."""
        try:
            import base64
            history = self.get_or_create_session(user_id)

            resolved_auth_mode, resolved_oauth = self._resolve_auth_context(auth_mode, oauth)
            token = self._get_request_token(resolved_auth_mode, resolved_oauth)
            project = self._get_project(resolved_auth_mode, resolved_oauth)

            # Build contents with inline image data
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            contents = list(history) + [{
                "role": "user",
                "parts": [
                    {"text": message},
                    {"inlineData": {"mimeType": "image/jpeg", "data": image_b64}},
                ],
            }]

            loop = asyncio.get_event_loop()
            def _build_vision_request(requested_model: str) -> Tuple[dict, ResolvedModel]:
                resolved = resolve_model(requested_model)
                gen_config = {
                    "temperature": 0.7,
                    "topP": 0.95,
                    "maxOutputTokens": Config.MAX_TOKENS_PER_REQUEST,
                }
                if resolved.is_thinking_model:
                    thinking_config = {"includeThoughts": True}
                    if resolved.thinking_level:
                        thinking_config["thinkingLevel"] = resolved.thinking_level
                    gen_config["thinkingConfig"] = thinking_config

                request_payload = {
                    "contents": contents,
                    "generationConfig": gen_config,
                    "safetySettings": [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_LOW_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_LOW_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_LOW_AND_ABOVE"},
                    ],
                    "systemInstruction": {
                        "role": "user",
                        "parts": [{"text": Config.SYSTEM_PROMPT or DEFAULT_SYSTEM_INSTRUCTION}],
                    },
                }

                wrapped = {
                    "model": resolved.actual_model,
                    "request": request_payload,
                    "requestType": "agent",
                    "userAgent": "antigravity",
                    "requestId": f"vision-{uuid.uuid4()}",
                }
                if project:
                    wrapped["project"] = project
                return wrapped, resolved

            response_data = await self._request_with_model_fallbacks(
                loop,
                resolved_auth_mode,
                token,
                project,
                _build_vision_request,
            )
            if isinstance(response_data, dict) and response_data.get("error"):
                return f"Error contacting Gemini: {response_data['error']}"

            response_text = _parse_full_response(response_data)
            if response_text:
                history.append({"role": "user", "parts": [{"text": message}]})
                history.append({"role": "model", "parts": [{"text": response_text}]})
                # Trim history to prevent unbounded growth
                self.sessions[user_id] = _trim_history(history)
            return response_text or "No response from Gemini Vision."

        except Exception as e:
            logger.error(f"Error in send_message_with_image: {e}", exc_info=True)
            return f"Error processing image: {e}"

    def clear_session(self, user_id: int):
        if user_id in self.sessions:
            self.sessions[user_id] = []
