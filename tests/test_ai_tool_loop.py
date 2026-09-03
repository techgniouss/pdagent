import asyncio

from pocket_desk_agent.ai_tool_loop import ALLOWED_TOOLS, normalize_tool_call, run_tool_turn
from pocket_desk_agent.ai_types import ProviderResult


def test_provider_result_defaults_not_retryable() -> None:
    result = ProviderResult(text="ok")
    assert result.is_retryable_error is False


def test_allowed_tools_include_canonical_app_tools() -> None:
    assert "open_desktop_app" in ALLOWED_TOOLS
    assert "close_desktop_app" in ALLOWED_TOOLS
    assert "list_directory" in ALLOWED_TOOLS


def test_normalize_tool_call_resolves_alias_and_args() -> None:
    name, args = normalize_tool_call("remote", {})
    assert name == "request_remote_session"
    assert args == {}


def test_execute_command_is_not_ai_reachable() -> None:
    # SECURITY: execute_command must never be callable by the AI — no direct
    # name, no alias, and it must not appear in the allowlist. See CLAUDE.md:
    # "Never expose execute_command or raw shell access to the AI."
    assert "execute_command" not in ALLOWED_TOOLS

    for alias in ("run_command", "shell_command", "run_shell", "exec_command", "run_in_folder"):
        name, _ = normalize_tool_call(alias, {"cmd": "git status"})
        assert name != "execute_command"


class _FakeFileManager:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def list_directory(self, user_id: int, path):
        self.calls.append(("list_directory", user_id, path))
        return True, "a.txt\nb.txt"


def test_run_tool_turn_dispatches_builtin_file_tool() -> None:
    fm = _FakeFileManager()

    async def _run():
        loop = asyncio.get_running_loop()
        return await run_tool_turn(
            user_id=1,
            raw_func_name="list_directory",
            raw_args={"path": "."},
            file_manager=fm,
            tool_runtime=None,
            loop=loop,
        )

    result = asyncio.run(_run())

    assert fm.calls == [("list_directory", 1, ".")]
    assert result.tool_result == {"result": "a.txt\nb.txt", "success": True}
    assert result.result_text == "a.txt\nb.txt"
    assert result.image_bytes is None
    assert result.normalized_call == {"name": "list_directory", "args": {"path": "."}}


def test_run_tool_turn_blocks_disallowed_tool() -> None:
    fm = _FakeFileManager()

    async def _run():
        loop = asyncio.get_running_loop()
        return await run_tool_turn(
            user_id=1,
            raw_func_name="execute_python_eval",  # not in ALLOWED_TOOLS, no alias
            raw_args={},
            file_manager=fm,
            tool_runtime=None,
            loop=loop,
        )

    result = asyncio.run(_run())

    assert result.tool_result["success"] is False
    assert "not available" in result.tool_result["result"]
    assert fm.calls == []


def test_run_tool_turn_blocks_execute_command() -> None:
    """SECURITY: a direct AI call to execute_command must be rejected, not
    dispatched to file_manager.execute_command (shell access)."""
    fm = _FakeFileManager()

    async def _run():
        loop = asyncio.get_running_loop()
        return await run_tool_turn(
            user_id=1,
            raw_func_name="execute_command",
            raw_args={"command": "git status"},
            file_manager=fm,
            tool_runtime=None,
            loop=loop,
        )

    result = asyncio.run(_run())

    assert result.tool_result["success"] is False
    assert "not available" in result.tool_result["result"]
    assert fm.calls == []
