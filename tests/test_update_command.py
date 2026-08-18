from pocket_desk_agent import updater
from pathlib import Path
import tempfile


def test_apply_update_always_uses_pypi_flow(monkeypatch) -> None:
    monkeypatch.setattr(
        updater,
        "apply_pypi_update",
        lambda: (True, "updated from pypi"),
    )

    assert updater.apply_update() == (True, "updated from pypi")


def test_apply_update_uses_pypi_flow_even_in_git_repo(monkeypatch) -> None:
    monkeypatch.setattr(updater, "_is_git_repo", lambda: True)
    monkeypatch.setattr(
        updater,
        "apply_pypi_update",
        lambda: (True, "updated from pypi"),
    )

    assert updater.apply_update() == (True, "updated from pypi")


def test_is_git_repo_accepts_worktree_git_file(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / ".git").write_text("gitdir: C:/tmp/worktree-meta\n", encoding="utf-8")
        monkeypatch.setattr(updater, "PROJECT_ROOT", root)

        assert updater.is_git_repo() is True
