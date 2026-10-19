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


class _FakeProc:
    def __init__(self, pid, name, exe):
        self.info = {"pid": pid, "name": name, "exe": exe}


def _entry(name, hints):
    from pocket_desk_agent.app_catalog import DesktopAppEntry

    return DesktopAppEntry(
        app_id="t", display_name=name, aliases=[name], launch_target="",
        launch_type="lnk", process_hints=hints,
    )


def test_generic_first_word_does_not_match_system_processes(monkeypatch) -> None:
    procs = [
        _FakeProc(100, "svchost.exe", r"C:\Windows\System32\svchost.exe"),
        _FakeProc(101, "WindowsTerminal.exe", r"C:\Program Files\WindowsApps\WindowsTerminal.exe"),
        _FakeProc(102, "explorer.exe", r"C:\Windows\explorer.exe"),
    ]
    monkeypatch.setattr(app_control.psutil, "process_iter", lambda attrs: iter(procs))
    monkeypatch.setattr(app_control, "_protected_process_ids", lambda: set())

    entry = _entry("Windows Terminal", ["windowsterminal", "windows"])
    assert app_control._find_matching_process_ids(entry) == [101]


def test_bot_process_and_ancestors_are_never_matched(monkeypatch) -> None:
    procs = [
        _FakeProc(200, "python.exe", r"C:\Python\python.exe"),
        _FakeProc(201, "python.exe", r"C:\Python\python.exe"),
    ]
    monkeypatch.setattr(app_control.psutil, "process_iter", lambda attrs: iter(procs))
    monkeypatch.setattr(app_control, "_protected_process_ids", lambda: {200})

    entry = _entry("Python", ["python"])
    # "python" is generic -> dropped, so nothing matches at all.
    assert app_control._find_matching_process_ids(entry) == []

    entry = _entry("Python Tool", ["python.exe"])
    assert app_control._find_matching_process_ids(entry) == [201]
