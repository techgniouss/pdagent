from pathlib import Path

from pocket_desk_agent import app_catalog


def test_is_safe_launch_target_rejects_shortcuts_to_unsafe_targets(monkeypatch) -> None:
    monkeypatch.setattr(
        app_catalog,
        "resolve_shortcut_target",
        lambda target: r"C:\Temp\unsafe-script.bat",
        raising=False,
    )

    assert not app_catalog.is_safe_launch_target(r"C:\Users\dell\Desktop\Unsafe App.lnk")


def test_builtin_catalog_skips_unresolved_bare_executables(monkeypatch) -> None:
    monkeypatch.setattr(app_catalog.os.path, "exists", lambda path: False)

    catalog = app_catalog.build_builtin_app_catalog()

    assert all(
        Path(entry.launch_target).is_absolute()
        or entry.launch_target.lower().startswith(("shell:appsfolder\\", "ms-settings:"))
        for entry in catalog
    )
