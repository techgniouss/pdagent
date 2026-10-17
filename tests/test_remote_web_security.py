"""Access control of the remote viewer server (real aiohttp app, test client)."""
import asyncio

import pytest

pytest.importorskip("aiohttp")

from aiohttp import WSMsgType  # noqa: E402
from aiohttp.test_utils import TestClient, TestServer  # noqa: E402

from pocket_desk_agent.remote import capture, input_bridge, web_server  # noqa: E402
from pocket_desk_agent.remote.session import RemoteSession, ACTIVE_SESSIONS  # noqa: E402


class _RecordingDispatcher:
    events: list = []
    last_failsafe_at = 0.0

    def __init__(self, session):
        self.session = session

    def apply(self, event):
        type(self).events.append(event)

    def cursor_norm(self):
        return {"x": 0.5, "y": 0.5}


async def _frames(session):
    while not session.torn_down:
        yield b"\xff\xd8fake-jpeg\xff\xd9"
        await asyncio.sleep(0.05)


def _run(coro):
    return asyncio.run(coro)


def _make_session() -> RemoteSession:
    session = RemoteSession.create(user_id=99, chat_id=1, port=0, fps=5, quality=60, max_width=1280)
    session.token = "t" * 43
    return session


async def _with_client(test):
    session = _make_session()
    server = TestServer(web_server.build_app(session))
    async with TestClient(server) as client:
        try:
            await test(client, session)
        finally:
            session.torn_down = True
            ACTIVE_SESSIONS.pop(99, None)


@pytest.fixture(autouse=True)
def _stubs(monkeypatch):
    _RecordingDispatcher.events = []
    monkeypatch.setattr(capture, "frame_iter", _frames)
    monkeypatch.setattr(input_bridge, "InputDispatcher", _RecordingDispatcher)


def test_root_requires_the_session_token() -> None:
    async def scenario(client, session):
        assert (await client.get("/")).status == 404
        assert (await client.get("/?t=wrong")).status == 404
        good = await client.get(f"/?t={session.token}")
        assert good.status == 200
        assert "pdremote" in good.headers.get("Set-Cookie", "")
        assert "HttpOnly" in good.headers["Set-Cookie"]

    _run(_with_client(scenario))


def test_websockets_reject_requests_without_the_session_cookie() -> None:
    async def scenario(client, session):
        for path in ("/ws/video", "/ws/input"):
            response = await client.get(path)
            assert response.status == 401

    _run(_with_client(scenario))


def test_websocket_rejects_a_foreign_origin_even_with_a_valid_cookie() -> None:
    async def scenario(client, session):
        client.session.cookie_jar.update_cookies({"pdremote": session.token})
        response = await client.get("/ws/input", headers={"Origin": "https://evil.example"})
        assert response.status == 401

    _run(_with_client(scenario))


def test_same_origin_websocket_delivers_input_and_video() -> None:
    async def scenario(client, session):
        client.session.cookie_jar.update_cookies({"pdremote": session.token})
        origin = f"http://{client.host}:{client.port}"

        async with client.ws_connect("/ws/input", headers={"Origin": origin}) as ws:
            await ws.send_json({"type": "click", "x": 0.5, "y": 0.5})
            reply = await ws.receive(timeout=2)
            assert reply.type == WSMsgType.TEXT  # cursor echo
        assert _RecordingDispatcher.events == [{"type": "click", "x": 0.5, "y": 0.5}]

        async with client.ws_connect("/ws/video", headers={"Origin": origin}) as ws:
            frame = await ws.receive(timeout=2)
            assert frame.type == WSMsgType.BINARY and frame.data.startswith(b"\xff\xd8")

    _run(_with_client(scenario))


def test_favicon_does_not_404() -> None:
    async def scenario(client, session):
        assert (await client.get("/favicon.ico")).status == 204

    _run(_with_client(scenario))


def test_video_loop_stops_promptly_when_the_viewer_disconnects() -> None:
    async def scenario(client, session):
        client.session.cookie_jar.update_cookies({"pdremote": session.token})
        origin = f"http://{client.host}:{client.port}"

        async with client.ws_connect("/ws/video", headers={"Origin": origin}) as ws:
            await ws.receive(timeout=2)
            assert len(session.active_ws) == 1

        # Without a concurrent reader the server only noticed after the
        # ~30s heartbeat timeout, leaving a zombie capture loop running.
        for _ in range(40):
            if not session.active_ws:
                break
            await asyncio.sleep(0.05)
        assert not session.active_ws

    _run(_with_client(scenario))
