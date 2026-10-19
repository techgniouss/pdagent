"""AI scheduling tools must reject unusable times before asking for approval."""
import asyncio
import datetime as dt

from pocket_desk_agent import gemini_actions as ga


def _dispatch(name, args):
    return asyncio.run(ga.dispatch_gemini_tool(1, name, args, file_manager=None, tool_runtime={}))


def test_past_absolute_time_is_rejected_for_claude_prompt() -> None:
    result = _dispatch("schedule_claude_prompt", {"execute_at": "2001-01-01 10:00", "prompt": "hi"})
    assert result.success is False and "past" in result.result.lower()
    assert not ga.pending_gemini_actions


def test_garbage_time_is_rejected_for_sequence() -> None:
    result = _dispatch("schedule_desktop_sequence", {"execute_at": "tomorrow-ish", "name": "x", "actions": []})
    assert result.success is False and "invalid" in result.result.lower()


def test_empty_prompt_is_rejected() -> None:
    future = (dt.datetime.now() + dt.timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    result = _dispatch("schedule_claude_prompt", {"execute_at": future, "prompt": "   "})
    assert result.success is False and "prompt" in result.result.lower()


def test_future_time_proceeds_to_approval(monkeypatch) -> None:
    future = (dt.datetime.now() + dt.timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    seen = {}

    async def fake_queue(**kwargs):
        seen.update(kwargs)
        return ga.GeminiToolResult(True, "queued", awaiting_confirmation=True)

    monkeypatch.setattr(ga, "_queue_confirmation", fake_queue)
    result = _dispatch("schedule_claude_prompt", {"execute_at": future, "prompt": "run tests"})
    assert result.awaiting_confirmation is True and seen["action_type"] == "schedule_claude_prompt"


def test_file_write_approval_shows_what_will_be_written() -> None:
    summary = ga._summarize_file_action("write_file", {"path": "notes.txt", "content": "hello\nworld " * 40})
    assert "notes.txt" in summary and "hello world" in summary and "chars" in summary
    assert len(summary) < 400  # long content is truncated in the prompt
    assert "empty content" in ga._summarize_file_action("append_file", {"path": "a", "content": ""})
    assert ga._summarize_file_action("delete_file", {"path": "x"}) == "delete the file 'x'"
