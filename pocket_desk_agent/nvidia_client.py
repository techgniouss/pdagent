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
            # Snapshot the original history length as the very first thing
            # inside the try block so it is guaranteed to be defined no
            # matter where below an exception is raised — the outer except
            # uses it to roll back any half-built tool-call sequence.
            base_history_len = len(history)
            loop = asyncio.get_running_loop()
            current_dir = file_manager.get_current_dir(user_id)
            full_message = f"[Current Directory: {current_dir}]\n\n{message}"
            history.append({"role": "user", "parts": [{"text": full_message}]})

            tools = gemini_tools_to_openai(_get_api_tools()[0]["functionDeclarations"])
            system_prompt = Config.SYSTEM_PROMPT or DEFAULT_SYSTEM_INSTRUCTION

            max_turns = 10
            for turn in range(max_turns):
                messages = gemini_history_to_openai(history, system_prompt)
                payload = {
                    "model": Config.NVIDIA_MODEL,
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
            del history[base_history_len:]
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
            base_history_len = len(history)
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
                "model": Config.NVIDIA_MODEL,
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
            del history[base_history_len:]
            return ProviderResult(text=f"Error processing image: {exc}", is_retryable_error=True)
