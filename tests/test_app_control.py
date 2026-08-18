from pocket_desk_agent import app_control
from pocket_desk_agent.app_catalog import DesktopAppEntry


def test_force_close_fails_when_no_matching_processes(monkeypatch) -> None:
    entry = DesktopAppEntry(
        app_id="sample",
        display_name="Sample App",
        aliases=["sample"],
        launch_target=r"C:\Program Files\Sample\sample.exe",
        launch_type="exe",
    )

    terminate_calls: list[list[int]] = []

    monkeypatch.setattr(app_control.platform, "system", lambda: "Windows")
    monkeypatch.setattr(app_control, "_find_matching_process_ids", lambda _: [])
    monkeypatch.setattr(app_control, "_find_matching_window_handles", lambda _: [101])
    monkeypatch.setattr(
        app_control,
        "_terminate_process_ids",
        lambda process_ids: terminate_calls.append(process_ids) or [],
    )

    result = app_control.close_desktop_app(entry, force=True)

    assert not result.success
    assert "No matching processes found" in result.message
    assert terminate_calls == []
