"""Gemini AI client using Antigravity OAuth - matching the robust Agile AI Engineer implementation."""

import json
import uuid
import logging
import asyncio
import re
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

import requests

from pocket_desk_agent.config import Config
from pocket_desk_agent.antigravity_auth import AntigravityOAuth
from pocket_desk_agent.constants import (
    ANTIGRAVITY_ENDPOINT_DAILY,
    ANTIGRAVITY_ENDPOINT_AUTOPUSH,
    ANTIGRAVITY_ENDPOINT_PROD,
    GEMINI_API_BASE_URL,
    THINKING_TIER_BUDGETS,
    GEMINI_CLI_HEADERS,
    ANTIGRAVITY_HEADERS,
    MAX_HISTORY_TURNS,
)

logger = logging.getLogger(__name__)

# ============================================================================
# SYSTEM INSTRUCTION
# ============================================================================
DEFAULT_SYSTEM_INSTRUCTION = """You are a helpful AI assistant.
You are assisting a USER with various tasks, including coding, general questions, and system management.

You have access to comprehensive tools to interact with the user's file system:

**Exploration Tools**:
- get_tree_structure: Get complete project structure (use this first to understand the project!)
- list_directory: List files in a specific directory
- search_files: Find files by name pattern
- read_file: Read file contents
- get_file_info: Get file metadata

**Modification Tools**:
- write_file: Create or overwrite files
- append_file: Add content to existing files
- delete_file: Remove files
- create_directory: Create new directories

**Best Practices**:
1. Start with get_tree_structure to understand the project layout
2. Read files before modifying them
3. Explain what you're doing and why
4. Be careful with delete operations
5. All paths are relative to the current working directory

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
            thinking_budget = budget_family.get(tier, budget_family["medium"])

    return ResolvedModel(actual_model, is_thinking_model, thinking_budget, thinking_level, quota_preference)

def _get_headers(resolved: ResolvedModel, access_token: str) -> dict:
    if resolved.quota_preference == "gemini-cli":
        base = {
            **GEMINI_CLI_HEADERS,
            "Client-Metadata": "ideType=IDE_UNSPECIFIED,platform=PLATFORM_UNSPECIFIED,pluginType=GEMINI",
        }
    else:
        base = dict(ANTIGRAVITY_HEADERS)

    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        **base,
    }

def _get_endpoints(resolved: ResolvedModel) -> list:
    if resolved.quota_preference == "gemini-cli":
        return [ANTIGRAVITY_ENDPOINT_PROD, ANTIGRAVITY_ENDPOINT_DAILY, ANTIGRAVITY_ENDPOINT_AUTOPUSH]
    return [ANTIGRAVITY_ENDPOINT_DAILY, ANTIGRAVITY_ENDPOINT_AUTOPUSH, ANTIGRAVITY_ENDPOINT_PROD]

def _build_wrapped_body(project_id: str, model: str, history: list, message: str) -> Tuple[dict, ResolvedModel]:
    resolved = resolve_model(model)
    contents = list(history) + [{"role": "user", "parts": [{"text": message}]}]

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
        "project": project_id,
        "model": resolved.actual_model,
        "request": request_payload,
        "requestType": "agent",
        "userAgent": "antigravity",
        "requestId": f"agent-{uuid.uuid4()}",
    }

    return wrapped, resolved

def _get_api_tools() -> list:
    """Define tools available to the AI.

    SECURITY NOTE: ``execute_command`` is intentionally excluded.
    Allowing an LLM to invoke shell commands via prompt is a
    prompt-injection → RCE vector.
    """
    return [{
        "functionDeclarations": [
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
                "description": "Write content to a file. Creates new file or overwrites existing file.",
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
                "description": "Append content to an existing file.",
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
                "description": "Delete a file.",
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
                "description": "Create a new directory.",
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
    }]

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
})

def _build_wrapped_body_with_tools(project_id: str, model: str, history: list, message: str) -> Tuple[dict, ResolvedModel]:
    wrapped, resolved = _build_wrapped_body(project_id, model, history, message)
    wrapped["request"]["tools"] = _get_api_tools()
    return wrapped, resolved

def _parse_full_response(data: dict) -> str:
    candidates = data.get('candidates', [])
    if not candidates: return ""
    parts = candidates[0].get('content', {}).get('parts', [])
    return "".join(p['text'] for p in parts if 'text' in p)

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
        self._use_api_key = bool(Config.GOOGLE_API_KEY) and not Config.GOOGLE_OAUTH_ENABLED

        if self._use_api_key:
            logger.info("Using API key mode (standard Gemini API)")
            self._oauth = None
        else:
            self._oauth = AntigravityOAuth()
            if self._oauth.load_saved_tokens():
                self._oauth._fetch_project_id()
                self._oauth._save_tokens()
            else:
                logger.warning("No saved tokens.")

    def _get_token(self) -> str:
        if self._use_api_key:
            return ""
        self._oauth.ensure_valid_token()
        return self._oauth.access_token

    def _get_project(self) -> str:
        if self._use_api_key:
            return ""
        project = self._oauth.project_id
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

    async def send_message(self, user_id: int, message: str, file_manager: Any) -> str:
        try:
            history = self.get_or_create_session(user_id)
            current_dir = file_manager.get_current_dir(user_id)
            full_message = f"[Current Directory: {current_dir}]\n\n{message}"

            token = self._get_token()
            project = self._get_project()

            wrapped, resolved = _build_wrapped_body_with_tools(project, self.model, history, full_message)
            loop = asyncio.get_event_loop()

            for turn in range(5):
                response_data = await loop.run_in_executor(
                    None, self._call_api_raw, token, project, wrapped, resolved
                )

                candidates = response_data.get('candidates', [])
                if not candidates: break

                parts = candidates[0].get('content', {}).get('parts', [])
                tool_call = next((p.get('functionCall') for p in parts if p.get('functionCall')), None)

                if not tool_call:
                    response_text = _parse_full_response(response_data)
                    history.append({"role": "user", "parts": [{"text": full_message}]})
                    history.append({"role": "model", "parts": [{"text": response_text}]})
                    # Trim history to prevent unbounded growth
                    self.sessions[user_id] = _trim_history(history)
                    return response_text

                # Validate tool name against allowlist before executing
                func_name = tool_call.get('name')
                args = tool_call.get('args', {})

                if func_name not in _ALLOWED_TOOLS:
                    logger.warning(
                        f"AI requested disallowed tool '{func_name}' — "
                        f"ignoring (possible prompt injection)"
                    )
                    # Feed back an error so the model doesn't retry
                    history.append({"role": "user", "parts": [{"text": full_message}]})
                    history.append({"role": "model", "parts": [{"functionCall": tool_call}]})
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
                    wrapped, resolved = _build_wrapped_body_with_tools(project, self.model, history, "Continue based on tool result.")
                    continue

                logger.info(f"AI Turn {turn}: requested tool {func_name} with {args}")

                result_text = "Error: Tool not found"
                success = False

                if func_name == "list_directory":
                    success, result_text = await loop.run_in_executor(None, file_manager.list_directory, user_id, args.get('path'))
                elif func_name == "get_tree_structure":
                    success, result_text = await loop.run_in_executor(
                        None, file_manager.get_tree_structure,
                        user_id,
                        args.get('path'),
                        args.get('max_depth', 3),
                        args.get('max_files', 100)
                    )
                elif func_name == "read_file":
                    success, result_text = await loop.run_in_executor(None, file_manager.read_file, user_id, args.get('path'))
                elif func_name == "search_files":
                    success, result_text = await loop.run_in_executor(None, file_manager.search_files, user_id, args.get('pattern'))
                elif func_name == "write_file":
                    success, result_text = await loop.run_in_executor(None, file_manager.write_file, user_id, args.get('path'), args.get('content', ''))
                elif func_name == "append_file":
                    success, result_text = await loop.run_in_executor(None, file_manager.append_file, user_id, args.get('path'), args.get('content', ''))
                elif func_name == "delete_file":
                    success, result_text = await loop.run_in_executor(None, file_manager.delete_file, user_id, args.get('path'))
                elif func_name == "create_directory":
                    success, result_text = await loop.run_in_executor(None, file_manager.create_directory, user_id, args.get('path'))
                elif func_name == "get_file_info":
                    success, result_text = await loop.run_in_executor(None, file_manager.get_file_info, user_id, args.get('path'))

                logger.info(f"Tool {func_name} result: {result_text[:100]}")

                # Update history with call and response
                history.append({"role": "user", "parts": [{"text": full_message}]})
                history.append({"role": "model", "parts": [{"functionCall": tool_call}]})
                history.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": func_name,
                            "response": {"result": result_text, "success": success}
                        }
                    }]
                })
                wrapped, resolved = _build_wrapped_body_with_tools(project, self.model, history, "Continue based on tool result.")

            return "I couldn't complete the request after several turns."

        except Exception as e:
            logger.error(f"Error in send_message: {e}")
            return f"Error: {str(e)}"

    def _call_api_raw(self, token: str, project: str, wrapped: dict, resolved: ResolvedModel) -> dict:
        if self._use_api_key:
            return self._call_api_key_raw(wrapped, resolved)

        headers = _get_headers(resolved, token)
        headers["Accept"] = "application/json"

        endpoints = _get_endpoints(resolved)
        last_error = "Unknown error"

        for endpoint in endpoints:
            url = f"{endpoint}/v1internal:generateContent"
            try:
                resp = requests.post(url, headers=headers, json=wrapped, timeout=60)
                if resp.status_code == 200:
                    return resp.json().get('response', resp.json())
                last_error = f"HTTP {resp.status_code}: {resp.text[:100]}"
            except Exception as e:
                last_error = str(e)
                continue

        return {"error": f"Failed to connect: {last_error}"}

    def _call_api_key_raw(self, wrapped: dict, resolved: ResolvedModel) -> dict:
        """Call the standard Gemini API using an API key (fallback mode)."""
        model = resolved.actual_model
        url = f"{GEMINI_API_BASE_URL}/v1beta/models/{model}:generateContent?key={Config.GOOGLE_API_KEY}"
        # Standard API uses the inner request payload directly
        payload = wrapped.get("request", wrapped)
        try:
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"error": str(e)}

    async def send_message_with_image(self, user_id: int, message: str, image_bytes: bytes) -> str:
        """Send a message with an image to Gemini for vision analysis."""
        try:
            import base64
            history = self.get_or_create_session(user_id)

            token = self._get_token()
            project = self._get_project()

            # Build contents with inline image data
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            contents = list(history) + [{
                "role": "user",
                "parts": [
                    {"text": message},
                    {"inlineData": {"mimeType": "image/jpeg", "data": image_b64}},
                ],
            }]

            resolved = resolve_model(self.model)
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
                "project": project,
                "model": resolved.actual_model,
                "request": request_payload,
                "requestType": "agent",
                "userAgent": "antigravity",
                "requestId": f"vision-{uuid.uuid4()}",
            }

            loop = asyncio.get_event_loop()
            response_data = await loop.run_in_executor(
                None, self._call_api_raw, token, project, wrapped, resolved
            )

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
