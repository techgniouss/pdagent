import asyncio

from pocket_desk_agent.ai_router import AIRouter
from pocket_desk_agent.ai_types import ProviderResult
from pocket_desk_agent.config import Config
from pocket_desk_agent.constants import AUTH_MODE_APIKEY


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
        self.commit_session_calls = 0

    def get_or_create_session(self, user_id: int) -> list:
        return self.sessions.setdefault(user_id, [])

    def commit_session(self, user_id: int, history: list) -> None:
        self.commit_session_calls += 1
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
    nvidia = _FakeNvidia(ProviderResult(text="unused"))
    router = AIRouter(gemini, nvidia, _FakeAuthClient({1}))

    result = asyncio.run(router.send_message(1, "hi", file_manager=None))

    assert result == "Gemini says hi"
    assert gemini.calls == 1
    assert nvidia.calls == 0


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
    assert gemini.commit_session_calls == 1


def test_send_message_returns_last_error_when_all_providers_fail(monkeypatch) -> None:
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    gemini = _FakeGemini(ProviderResult(text="gemini down", is_retryable_error=True))
    nvidia = _FakeNvidia(ProviderResult(text="nvidia down too", is_retryable_error=True))
    router = AIRouter(gemini, nvidia, _FakeAuthClient({1}))

    result = asyncio.run(router.send_message(1, "hi", file_manager=None))

    assert result == "nvidia down too"
    assert gemini.commit_session_calls == 1


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


def test_configured_providers_gemini_apikey_mode(monkeypatch) -> None:
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    monkeypatch.setattr(Config, "GEMINI_AUTH_MODE", AUTH_MODE_APIKEY)
    monkeypatch.setattr(Config, "GOOGLE_API_KEY", "sk-test-key-12345")
    router = AIRouter(
        _FakeGemini(ProviderResult(text="x")),
        _FakeNvidia(ProviderResult(text="x")),
        _FakeAuthClient(set()),
    )

    assert "gemini" in router.configured_providers(user_id=1)


def test_configured_providers_gemini_apikey_mode_without_key(monkeypatch) -> None:
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    monkeypatch.setattr(Config, "GEMINI_AUTH_MODE", AUTH_MODE_APIKEY)
    monkeypatch.setattr(Config, "GOOGLE_API_KEY", "")
    router = AIRouter(
        _FakeGemini(ProviderResult(text="x")),
        _FakeNvidia(ProviderResult(text="x")),
        _FakeAuthClient(set()),
    )

    assert "gemini" not in router.configured_providers(user_id=1)
