"""Credential stores are off limits even when the home folder is approved."""
from pathlib import Path

import pytest

from pocket_desk_agent.file_manager import FileManager


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    for sub in (".pdagent", ".ssh", ".aws", ".config/gcloud", ".config/pdagent-gemini", "projects"):
        (tmp_path / sub).mkdir(parents=True)
    (tmp_path / ".pdagent" / "credentials").write_text("telegram_bot_token = secret", encoding="utf-8")
    (tmp_path / ".ssh" / "id_rsa").write_text("PRIVATE KEY", encoding="utf-8")
    (tmp_path / "projects" / "app.py").write_text("print('hi')", encoding="utf-8")
    return tmp_path


def _manager(home: Path) -> FileManager:
    manager = FileManager()
    manager.approved_dirs = [home]  # the default: the whole home folder
    manager.current_dirs[1] = home
    return manager


@pytest.mark.parametrize(
    "relative",
    [".pdagent/credentials", ".ssh/id_rsa", ".aws", ".config/gcloud", ".config/pdagent-gemini"],
)
def test_credential_locations_are_denied(home, relative) -> None:
    assert _manager(home)._is_safe_path(home / relative) is False


def test_ordinary_project_files_are_still_allowed(home) -> None:
    manager = _manager(home)
    assert manager._is_safe_path(home / "projects" / "app.py") is True
    ok, content = manager.read_file(1, "projects/app.py")
    assert ok and "print('hi')" in content


def test_every_file_tool_refuses_the_credentials_file(home) -> None:
    manager = _manager(home)
    for call in (
        lambda: manager.read_file(1, ".pdagent/credentials"),
        lambda: manager.get_file_info(1, ".pdagent/credentials"),
        lambda: manager.write_file(1, ".ssh/authorized_keys", "ssh-rsa attacker"),
        lambda: manager.delete_file(1, ".ssh/id_rsa"),
        lambda: manager.list_directory(1, ".pdagent"),
        lambda: manager.set_current_dir(1, ".ssh"),
        lambda: manager.resolve_downloadable_file(1, ".pdagent/credentials"),
    ):
        ok, message = call()
        assert ok is False and "denied" in str(message).lower()
    assert not (home / ".ssh" / "authorized_keys").exists()
    assert (home / ".ssh" / "id_rsa").exists()


def test_symlink_into_a_protected_dir_is_denied(home) -> None:
    link = home / "projects" / "innocent.txt"
    try:
        link.symlink_to(home / ".pdagent" / "credentials")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert _manager(home)._is_safe_path(link) is False
