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
