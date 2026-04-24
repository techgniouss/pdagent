from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pocket_desk_agent.remote import tunnel


class _DummyProc:
    def __init__(self, name: str) -> None:
        self.name = name
        self.returncode = None
        self.stdout = None

    def terminate(self) -> None:
        self.returncode = 0

    def kill(self) -> None:
        self.returncode = 0

    async def wait(self) -> int:
        self.returncode = 0
        return 0


@pytest.mark.asyncio
async def test_start_quick_tunnel_retries_until_ready(monkeypatch):
    procs = [_DummyProc("first"), _DummyProc("second")]
    stopped: list[str] = []

    async def fake_spawn(binary: str, port: int):
        assert binary == "cloudflared"
        assert port == 48500
        return procs.pop(0)

    async def fake_read(proc, url_timeout: float, ready_timeout: float):
        assert url_timeout > 0
        assert ready_timeout > 0
        if proc.name == "first":
            return "https://first.trycloudflare.com", False
        return "https://second.trycloudflare.com", True

    async def fake_stop(proc) -> None:
        stopped.append(proc.name)
        proc.returncode = 0

    monkeypatch.setattr(tunnel, "resolve_binary", lambda: "cloudflared")
    monkeypatch.setattr(tunnel, "_spawn_tunnel_process", fake_spawn)
    monkeypatch.setattr(tunnel, "_read_url_and_ready", fake_read)
    monkeypatch.setattr(tunnel, "stop_tunnel", fake_stop)
    monkeypatch.setattr(tunnel, "_start_log_drain", lambda proc: None)
    monkeypatch.setattr(tunnel, "_START_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(tunnel, "_START_RETRY_BACKOFF_SECS", 0.0)

    proc, url = await tunnel.start_quick_tunnel(48500)

    assert proc.name == "second"
    assert url == "https://second.trycloudflare.com"
    assert stopped == ["first"]


@pytest.mark.asyncio
async def test_start_quick_tunnel_last_attempt_returns_when_ready_signal_missing(monkeypatch):
    procs = [_DummyProc("first"), _DummyProc("second")]
    stopped: list[str] = []

    async def fake_spawn(binary: str, port: int):
        return procs.pop(0)

    async def fake_read(proc, url_timeout: float, ready_timeout: float):
        return f"https://{proc.name}.trycloudflare.com", False

    async def fake_stop(proc) -> None:
        stopped.append(proc.name)
        proc.returncode = 0

    monkeypatch.setattr(tunnel, "resolve_binary", lambda: "cloudflared")
    monkeypatch.setattr(tunnel, "_spawn_tunnel_process", fake_spawn)
    monkeypatch.setattr(tunnel, "_read_url_and_ready", fake_read)
    monkeypatch.setattr(tunnel, "stop_tunnel", fake_stop)
    monkeypatch.setattr(tunnel, "_start_log_drain", lambda proc: None)
    monkeypatch.setattr(tunnel, "_START_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(tunnel, "_START_RETRY_BACKOFF_SECS", 0.0)

    proc, url = await tunnel.start_quick_tunnel(48500)

    assert proc.name == "second"
    assert url == "https://second.trycloudflare.com"
    assert stopped == ["first"]


def test_line_has_ready_signal_matches_registered_connection():
    assert tunnel._line_has_ready_signal("INF Registered tunnel connection connIndex=0")
    assert tunnel._line_has_ready_signal("Connection 84f1 registered")
    assert not tunnel._line_has_ready_signal("Your quick Tunnel has been created")
