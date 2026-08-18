import asyncio
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from pocket_desk_agent.file_manager import FileManager
from pocket_desk_agent.handlers import filesystem
from pocket_desk_agent.handlers._shared import getfile_retrieval_state


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.documents: list[dict[str, str | None]] = []
        self.text = ""

    async def reply_text(self, text: str, **kwargs) -> None:
        self.replies.append(text)

    async def reply_document(
        self,
        document,
        filename: str | None = None,
        caption: str | None = None,
        **kwargs,
    ) -> None:
        self.documents.append({"filename": filename, "caption": caption})


class DummyContext:
    def __init__(self, args: list[str]) -> None:
        self.args = args
        self.bot = SimpleNamespace()


def make_update(message: DummyMessage, user_id: int = 7):
    user = SimpleNamespace(id=user_id)
    chat = SimpleNamespace(id=99)
    return SimpleNamespace(
        message=message,
        effective_user=user,
        effective_chat=chat,
    )


def test_is_blocked_download_file_rejects_windows_executables() -> None:
    blocked = ["tool.exe", "setup.MSI", "run.cmd", "script.PS1", "screen.scr"]
    allowed = ["app.apk", "bundle.aab", "Main.java", "README", "archive.zip"]

    for name in blocked:
        assert FileManager.is_blocked_download_file(Path(name)) is True

    for name in allowed:
        assert FileManager.is_blocked_download_file(Path(name)) is False


def test_resolve_downloadable_file_rejects_paths_outside_approved_directories() -> None:
    with tempfile.TemporaryDirectory(dir="C:\\tmp") as temp_dir:
        root = Path(temp_dir)
        manager = FileManager()
        approved = root / "approved"
        approved.mkdir()
        outside = root / "outside.txt"
        outside.write_text("hello", encoding="utf-8")
        manager.approved_dirs = [approved]
        manager.current_dirs[7] = approved

        success, message = manager.resolve_downloadable_file(7, str(outside))

        assert success is False
        assert message == "Access denied: Path outside approved directory"


def test_getfile_command_rejects_blocked_path(monkeypatch) -> None:
    message = DummyMessage()
    update = make_update(message)
    context = DummyContext(args=["installer.exe"])

    monkeypatch.setattr(
        filesystem.file_manager,
        "resolve_downloadable_file",
        lambda user_id, path: (True, Path("C:/repo/installer.exe")),
    )

    asyncio.run(filesystem.getfile_command(update, context))

    assert "blocked" in message.replies[-1].lower()


def test_getfile_command_sends_allowed_file(monkeypatch) -> None:
    with tempfile.TemporaryDirectory(dir="C:\\tmp") as temp_dir:
        target = Path(temp_dir) / "app.apk"
        target.write_bytes(b"apk")
        message = DummyMessage()
        update = make_update(message)
        context = DummyContext(args=[str(target)])
        calls: list[Path] = []

        monkeypatch.setattr(
            filesystem.file_manager,
            "resolve_downloadable_file",
            lambda user_id, path: (True, target),
        )

        async def fake_send(update_arg, context_arg, file_path: Path) -> None:
            calls.append(file_path)

        monkeypatch.setattr(filesystem, "_send_requested_file", fake_send)

        asyncio.run(filesystem.getfile_command(update, context))

        assert calls == [target]


def test_getfile_command_without_args_starts_browser(monkeypatch) -> None:
    with tempfile.TemporaryDirectory(dir="C:\\tmp") as temp_dir:
        getfile_retrieval_state.clear()
        start_path = Path(temp_dir) / "repo"
        start_path.mkdir()
        message = DummyMessage()
        update = make_update(message)
        context = DummyContext(args=[])

        monkeypatch.setattr(filesystem.file_manager, "get_current_dir", lambda user_id: start_path)

        asyncio.run(filesystem.getfile_command(update, context))

        assert getfile_retrieval_state[7]["current_path"] == start_path
        assert str(start_path) in message.replies[-1]


def test_check_getfile_selection_cancel_clears_state() -> None:
    getfile_retrieval_state.clear()
    message = DummyMessage()
    message.text = "cancel"
    update = make_update(message)
    context = DummyContext(args=[])
    getfile_retrieval_state[7] = {
        "current_path": Path("C:/repo"),
        "timestamp": time.time(),
    }

    handled = asyncio.run(filesystem.check_getfile_selection(update, context))

    assert handled is True
    assert 7 not in getfile_retrieval_state
    assert "cancelled" in message.replies[-1].lower()
