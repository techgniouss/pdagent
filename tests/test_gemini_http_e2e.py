"""End-to-end Gemini (API-key mode) test against a local fake Generative Language API."""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from pocket_desk_agent import gemini_client as gc


class _FakeGemini(BaseHTTPRequestHandler):
    seen: list[dict] = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        model = self.path.split("/models/")[1].split(":")[0]
        type(self).seen.append({"model": model, "path": self.path, "key": self.headers.get("x-goog-api-key"), "body": body})
        if model == "gemini-2.0-flash":
            self._reply(404, {"error": {"code": 404, "message": f"models/{model} is no longer available"}})
            return
        has_response = any(
            "functionResponse" in part
            for content in body["contents"] for part in content.get("parts", [])
        )
        if has_response:
            parts = [{"text": "You are in /work/project."}]
        else:
            parts = [{"functionCall": {"name": "get_current_directory", "args": {}}}]
        self._reply(200, {"candidates": [{"content": {"role": "model", "parts": parts}}]})

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
def gemini_server(monkeypatch):
    _FakeGemini.seen = []
    server = HTTPServer(("127.0.0.1", 0), _FakeGemini)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(gc, "GEMINI_API_BASE_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setattr(gc.Config, "GEMINI_AUTH_MODE", "apikey")
    monkeypatch.setattr(gc.Config, "GOOGLE_API_KEY", "AIzaSyFAKEfakeFAKEfakeFAKEfakeFAKEfake12")
    yield _FakeGemini
    server.shutdown()


def test_retired_model_404_falls_back_and_tool_loop_completes(gemini_server) -> None:
    client = gc.GeminiClient()
    client.model = "gemini-2.0-flash"  # as if pinned by an old config

    result = asyncio.run(client.send_message(1, "where am I?", _FileManager(), tool_runtime=None))

    assert result.is_retryable_error is False
    assert result.text == "You are in /work/project."

    models = [r["model"] for r in gemini_server.seen]
    assert models[0] == "gemini-2.0-flash"            # tried the pinned (retired) model first
    assert set(models[1:]) == {"gemini-2.5-flash"}    # then fell back and stayed on the working one

    for request in gemini_server.seen:
        assert "key=" not in request["path"]          # key never in the URL
        assert request["key"] == "AIzaSyFAKEfakeFAKEfakeFAKEfakeFAKEfake12"

    final = gemini_server.seen[-1]["body"]["contents"]
    assert [c["role"] for c in final] == ["user", "model", "user"]
    assert "functionResponse" in final[-1]["parts"][0]
    # Stored history is complete and clean for the next turn.
    assert [c["role"] for c in client.sessions[1]] == ["user", "model", "user", "model"]
