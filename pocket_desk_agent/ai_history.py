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

    Malformed/unpaired history is tolerated rather than passed through:
    OpenAI-compatible APIs reject a lone "tool" message with no preceding
    tool_calls, and reject an assistant tool_calls message with no
    following tool response. Two real (not hypothetical) sources of such
    unpaired history: GeminiClient._trim_history can slice starting
    mid-pair, and an unhandled exception mid-tool-loop can leave a
    dangling functionCall with its response never appended.
    """
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    pending_tool_call_ids: list[str] = []
    call_index = 0

    for i, entry in enumerate(history):
        role = entry.get("role")
        parts = entry.get("parts", [])

        if role == "user":
            function_responses = [p["functionResponse"] for p in parts if "functionResponse" in p]
            if function_responses:
                if not pending_tool_call_ids:
                    # Orphaned tool response(s) with no preceding assistant
                    # tool_calls in this (possibly trimmed) history — drop
                    # rather than emit an invalid lone "tool" message.
                    continue
                for j, resp in enumerate(function_responses):
                    call_id = (
                        pending_tool_call_ids[j]
                        if j < len(pending_tool_call_ids)
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
                # Only emit as a tool_calls message if the very next
                # history entry actually carries the matching
                # functionResponse(s) — otherwise (a dangling call left by
                # an unhandled exception, or simply the end of history) an
                # OpenAI-compatible API will reject an assistant message
                # with unanswered tool_calls.
                next_entry = history[i + 1] if i + 1 < len(history) else None
                next_has_response = bool(
                    next_entry
                    and next_entry.get("role") == "user"
                    and any("functionResponse" in p for p in next_entry.get("parts", []))
                )
                if next_has_response:
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
                    # Dangling tool call with no response anywhere in this
                    # history — surface only the text, if any; drop the
                    # unanswerable tool_calls rather than emit an invalid
                    # message.
                    pending_tool_call_ids = []
                    if text:
                        messages.append({"role": "assistant", "content": text})
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
