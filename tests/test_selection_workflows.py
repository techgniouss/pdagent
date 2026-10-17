"""Starting one number-reply workflow must cancel the others (no hijacked replies)."""
import time

from pocket_desk_agent.handlers import _shared


def _seed(user_id: int) -> None:
    for state in (_shared.build_state, _shared.apk_retrieval_state, _shared.getfile_retrieval_state):
        state[user_id] = {"timestamp": time.time()}


def test_reset_keeps_only_the_requested_workflow() -> None:
    _seed(42)
    _shared.reset_selection_workflows(42, keep="getfile")
    assert 42 not in _shared.build_state
    assert 42 not in _shared.apk_retrieval_state
    assert 42 in _shared.getfile_retrieval_state
    _shared.getfile_retrieval_state.pop(42, None)


def test_reset_only_touches_the_given_user() -> None:
    _seed(1)
    _seed(2)
    _shared.reset_selection_workflows(1)
    assert 1 not in _shared.build_state and 2 in _shared.build_state
    for state in (_shared.build_state, _shared.apk_retrieval_state, _shared.getfile_retrieval_state):
        state.pop(2, None)


def test_starting_getfile_cancels_a_pending_build(monkeypatch, tmp_path) -> None:
    import asyncio
    from types import SimpleNamespace

    from pocket_desk_agent.handlers import filesystem

    _seed(7)
    sent: list[str] = []

    class Msg:
        async def reply_text(self, text, **kwargs):
            sent.append(text)

    update = SimpleNamespace(message=Msg(), effective_user=SimpleNamespace(id=7), effective_chat=SimpleNamespace(id=1))
    monkeypatch.setattr(filesystem.file_manager, "get_current_dir", lambda uid: tmp_path)
    asyncio.run(filesystem.getfile_command(update, SimpleNamespace(args=[], bot=None)))

    assert 7 not in _shared.build_state and 7 not in _shared.apk_retrieval_state
    assert 7 in _shared.getfile_retrieval_state
    _shared.getfile_retrieval_state.pop(7, None)
