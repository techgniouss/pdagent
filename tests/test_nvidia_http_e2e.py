"""End-to-end NVIDIA client test against a local fake NIM server (real HTTP)."""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from pocket_desk_agent.config import Config
from pocket_desk_agent.nvidia_client import NvidiaClient


class _FakeNim(BaseHTTPRequestHandler):
    requests_seen: list[dict] = []
    headers_seen: list[dict] = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests_seen.append(body)
        type(self).headers_seen.append(dict(self.headers))
        if body["model"] == "retired/model":
            self._reply(410, {"status": 410, "detail": "model reached end of life"})
            return
        tool_turns = [m for m in body["messages"] if m["role"] == "tool"]
        if not tool_turns:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_abc", "type": "function",
                    "function": {"name": "get_current_directory", "arguments": "{}"},
                }],
            }
        else:
            message = {"role": "assistant", "content": "You are in the project folder."}
        self._reply(200, {"choices": [{"message": message}]})

    def _reply(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class _FileManager:
    def get_current_dir(self, user_id):
        return Path("/work/project")


@pytest.fixture()
def nim_server(monkeypatch):
    _FakeNim.requests_seen = []
    _FakeNim.headers_seen = []
    server = HTTPServer(("127.0.0.1", 0), _FakeNim)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(Config, "NVIDIA_API_KEY", "nvapi-test-key-1234567890")
    monkeypatch.setattr(Config, "NVIDIA_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setattr(Config, "NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    yield _FakeNim
    server.shutdown()


def test_tool_call_round_trip_over_real_http(nim_server) -> None:
    history: list = []
    result = asyncio.run(
        NvidiaClient().send_message(1, "where am I?", _FileManager(), history=history)
    )

    assert result.is_retryable_error is False
    assert result.text == "You are in the project folder."

    first, second = nim_server.requests_seen
    assert first["model"] == "nvidia/nemotron-3-super-120b-a12b"
    assert first["tool_choice"] == "auto" and len(first["tools"]) > 40
    assert first["messages"][0]["role"] == "system"
    assert nim_server.headers_seen[0]["Authorization"] == "Bearer nvapi-test-key-1234567890"

    # Second request must carry the assistant tool_calls AND a matching tool reply.
    roles = [m["role"] for m in second["messages"]]
    assert roles[-2:] == ["assistant", "tool"]
    assistant, tool = second["messages"][-2:]
    assert assistant["tool_calls"][0]["id"] == tool["tool_call_id"] == "call_0"
    assert "Current directory" in tool["content"]

    # History ends in the canonical Gemini shape: user, model(call), user(response), model(text).
    assert [h["role"] for h in history] == ["user", "model", "user", "model"]


def test_retired_model_is_reported_as_retryable_error(nim_server, monkeypatch) -> None:
    monkeypatch.setattr(Config, "NVIDIA_MODEL", "retired/model")
    history: list = []
    result = asyncio.run(NvidiaClient().send_message(1, "hi", _FileManager(), history=history))

    assert result.is_retryable_error is True
    assert "410" in result.text
    assert history == []  # the failed turn is rolled back


def test_empty_nvidia_reply_is_not_stored_in_the_shared_history(nim_server, monkeypatch) -> None:
    class EmptyNim(_FakeNim):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self._reply(200, {"choices": [{"message": {"role": "assistant", "content": ""}, "finish_reason": "stop"}]})

    server = HTTPServer(("127.0.0.1", 0), EmptyNim)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(Config, "NVIDIA_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    try:
        history: list = []
        result = asyncio.run(NvidiaClient().send_message(1, "hi", _FileManager(), history=history))
    finally:
        server.shutdown()

    assert result.is_retryable_error is True and "empty response" in result.text
    assert history == []  # an empty text part here would make Gemini reject every later request
