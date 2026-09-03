import asyncio

from pocket_desk_agent.ai_router import AIRouter
from pocket_desk_agent.config import Config
from pocket_desk_agent.gemini_client import GeminiClient
from pocket_desk_agent.nvidia_client import NvidiaClient


class _FakeFileManager:
    def get_current_dir(self, user_id: int) -> str:
        return "/home/user"


class _FailingGemini:
    """Stands in for GeminiClient but always fails retryably — forces the
    router to fall back to the real NvidiaClient with a realistic history
    that GeminiClient itself already built."""

    def __init__(self, gemini_for_session: GeminiClient):
        self._gemini = gemini_for_session

    def get_or_create_session(self, user_id: int) -> list:
        return self._gemini.get_or_create_session(user_id)

    def commit_session(self, user_id: int, history: list) -> None:
        self._gemini.commit_session(user_id, history)

    def clear_session(self, user_id: int) -> None:
        self._gemini.clear_session(user_id)

    @property
    def sessions(self):
        return self._gemini.sessions

    async def send_message(self, user_id, message, file_manager, tool_runtime=None, auth_mode=None, oauth=None):
        from pocket_desk_agent.ai_types import ProviderResult
        return ProviderResult(text="gemini quota exhausted", is_retryable_error=True)

    async def send_message_with_image(self, *args, **kwargs):
        from pocket_desk_agent.ai_types import ProviderResult
        return ProviderResult(text="gemini quota exhausted", is_retryable_error=True)


class _FakeAuthClient:
    def is_authenticated(self, user_id: int) -> bool:
        return True


def test_fallback_with_realistic_pregenerated_history_produces_well_formed_payload(monkeypatch) -> None:
    """Seed a Gemini-shaped session with a COMPLETED tool round-trip (the
    kind GeminiClient itself builds), then force a fallback to a real
    NvidiaClient and assert the OpenAI-shaped payload it builds from that
    history is well-formed (every 'tool' message pairs to a preceding
    assistant tool_calls id; no assistant tool_calls message is left
    unanswered)."""
    monkeypatch.setattr(Config, "AI_PROVIDER_ORDER", ["gemini", "nvidia"])
    monkeypatch.setattr(Config, "NVIDIA_API_KEY", "nvapi-test")
    monkeypatch.setattr(Config, "NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
    monkeypatch.setattr(Config, "MAX_TOKENS_PER_REQUEST", 8000)
    monkeypatch.setattr(Config, "SYSTEM_PROMPT", "")

    real_gemini_for_storage = GeminiClient.__new__(GeminiClient)
    real_gemini_for_storage.sessions = {
        42: [
            {"role": "user", "parts": [{"text": "[Current Directory: /home/user]\n\nlist my files"}]},
            {"role": "model", "parts": [{"functionCall": {"name": "list_directory", "args": {"path": "."}}}]},
            {"role": "user", "parts": [{"functionResponse": {"name": "list_directory", "response": {"result": "a.txt\nb.txt", "success": True}}}]},
            {"role": "model", "parts": [{"text": "You have a.txt and b.txt."}]},
        ]
    }
    real_gemini_for_storage.commit_session = lambda user_id, history: real_gemini_for_storage.sessions.__setitem__(user_id, history)
    real_gemini_for_storage.get_or_create_session = lambda user_id: real_gemini_for_storage.sessions.setdefault(user_id, [])
    real_gemini_for_storage.clear_session = lambda user_id: real_gemini_for_storage.sessions.__setitem__(user_id, [])

    nvidia = NvidiaClient()
    captured_payloads = []

    def fake_call_raw(self, payload):
        captured_payloads.append(payload)
        return {"choices": [{"message": {"role": "assistant", "content": "Fallback answer."}}]}

    monkeypatch.setattr(NvidiaClient, "_call_raw", fake_call_raw)

    router = AIRouter(_FailingGemini(real_gemini_for_storage), nvidia, _FakeAuthClient())

    result = asyncio.run(router.send_message(42, "what files do I have?", _FakeFileManager()))

    assert "Fallback answer." in result
    assert len(captured_payloads) == 1
    messages = captured_payloads[0]["messages"]

    # Well-formedness: every assistant message with tool_calls must be
    # immediately followed (possibly after other tool messages for the
    # same turn) by at least one 'tool' message referencing one of its ids;
    # every 'tool' message's tool_call_id must reference SOME preceding
    # assistant tool_calls id.
    seen_call_ids: set[str] = set()
    for i, msg in enumerate(messages):
        if msg["role"] == "assistant" and msg.get("tool_calls"):
            ids = {tc["id"] for tc in msg["tool_calls"]}
            seen_call_ids |= ids
            following_tool_ids = {
                m["tool_call_id"] for m in messages[i + 1:] if m["role"] == "tool"
            }
            assert ids & following_tool_ids, f"assistant tool_calls {ids} never answered"
        if msg["role"] == "tool":
            assert msg["tool_call_id"] in seen_call_ids, "tool message references unknown call id"
