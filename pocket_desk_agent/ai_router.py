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
