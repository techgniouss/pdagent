"""PID-file helpers must never treat an unrelated process as the bot."""
import os
import subprocess
import sys

from pocket_desk_agent import process_utils


def test_unrelated_live_process_is_not_the_bot() -> None:
    # This pytest process is alive but its command line isn't the bot's.
    assert process_utils.is_bot_process(os.getpid()) is False


def test_nonexistent_pid_is_not_the_bot() -> None:
    assert process_utils.is_bot_process(2**22 + 12345) is False
    assert process_utils.is_bot_process(0) is False


def test_process_with_bot_cmdline_is_recognised_and_stoppable(tmp_path) -> None:
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)", "pocket_desk_agent.main"]
    )
    try:
        assert process_utils.is_bot_process(proc.pid) is True
        pid_file = tmp_path / "bot.pid"
        pid_file.write_text(str(proc.pid), encoding="utf-8")
        assert process_utils.running_bot_pid(pid_file) == proc.pid
        assert process_utils.stop_process(proc.pid) is True
        proc.wait(timeout=5)
        assert process_utils.running_bot_pid(pid_file) is None
    finally:
        if proc.poll() is None:
            proc.kill()


def test_read_pid_handles_garbage(tmp_path) -> None:
    pid_file = tmp_path / "bot.pid"
    assert process_utils.read_pid(pid_file) is None
    pid_file.write_text("not-a-pid", encoding="utf-8")
    assert process_utils.read_pid(pid_file) is None
    pid_file.write_text(" 42\n", encoding="utf-8")
    assert process_utils.read_pid(pid_file) == 42
