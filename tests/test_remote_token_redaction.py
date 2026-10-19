"""The viewer token is the session secret: it must never reach the AI provider."""
import asyncio

from pocket_desk_agent import gemini_actions as ga
from pocket_desk_agent.handlers import remote
from pocket_desk_agent.remote.session import ACTIVE_SESSIONS, RemoteSession

TOKEN = "S3CR3T-viewer-token-abcdefghijklmnopqrstuvwxyz123456"


def _session(user_id: int = 77) -> RemoteSession:
    session = RemoteSession.create(user_id=user_id, chat_id=1, port=1234, fps=10, quality=60, max_width=1280)
    session.token = TOKEN
    session.tunnel_url = remote._build_viewer_url("https://abc-def.trycloudflare.com", TOKEN)
    return session


def test_redact_viewer_url_strips_only_the_token() -> None:
    url = f"https://abc.trycloudflare.com/path?t={TOKEN}&x=1"
    redacted = remote.redact_viewer_url(url)
    assert TOKEN not in redacted and "x=1" in redacted
    assert remote.redact_viewer_url("https://abc.trycloudflare.com") == "https://abc.trycloudflare.com"


def test_sanitized_status_never_contains_the_token() -> None:
    session = _session()
    try:
        status = remote.sanitized_status(77)
        assert status["active"] is True
        assert TOKEN not in str(status)
    finally:
        ACTIVE_SESSIONS.pop(77, None)


def test_ai_tool_results_never_contain_the_token(monkeypatch) -> None:
    session = _session()
    monkeypatch.setattr(remote.Config, "REMOTE_ENABLED", True)
    monkeypatch.setattr(remote.Config, "REMOTE_AI_TOOLS_ENABLED", True)
    try:
        for tool in ("get_remote_session_status", "request_remote_session"):
            result = asyncio.run(ga.dispatch_gemini_tool(77, tool, {}, file_manager=None, tool_runtime={}))
            assert TOKEN not in result.result and TOKEN not in str(result.to_response())
    finally:
        ACTIVE_SESSIONS.pop(77, None)


def test_remoteinfo_still_shows_the_full_link_to_the_owner(monkeypatch) -> None:
    session = _session()
    sent: list[str] = []

    class Msg:
        async def reply_text(self, text, **kwargs):
            sent.append(text)

    from types import SimpleNamespace

    update = SimpleNamespace(message=Msg(), effective_user=SimpleNamespace(id=77))
    try:
        asyncio.run(remote.remoteinfo_command(update, SimpleNamespace()))
    finally:
        ACTIVE_SESSIONS.pop(77, None)
    assert TOKEN in sent[0]  # the human owner needs the working link
