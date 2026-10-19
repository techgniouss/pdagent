"""
Process management utility for Pocket Desk Agent.
Handles stopping and status checking of the background bot.
"""

import os
import subprocess
import sys

from pocket_desk_agent.app_paths import app_path, existing_app_path
from pocket_desk_agent.process_utils import read_pid, running_bot_pid, stop_process


PID_FILE = app_path("bot.pid")


def safe_print(msg):
    try:
        print(msg)
    except Exception:
        pass


def _current_pid_file():
    """Return the canonical PID file, falling back to the legacy location."""
    if PID_FILE.exists():
        return PID_FILE
    return existing_app_path("bot.pid")


def stop_bot():
    """Terminate the bot process (only if the PID really is the bot)."""
    pid_file = _current_pid_file()
    if not pid_file.exists():
        safe_print("X No PID file found. Is the bot running?")
        return

    pid = running_bot_pid(pid_file)
    if pid is None:
        safe_print("Bot is not currently running. Cleaning stale PID file.")
        pid_file.unlink(missing_ok=True)
        return

    safe_print(f"Stopping bot (PID {pid})...")
    if stop_process(pid):
        safe_print("Bot stopped.")
        pid_file.unlink(missing_ok=True)
    else:
        safe_print(f"Error: could not stop bot (PID {pid}).")


def check_status():
    """Check and print bot status."""
    pid_file = _current_pid_file()
    if not pid_file.exists():
        safe_print("Status: NOT RUNNING")
        return

    pid = running_bot_pid(pid_file)
    if pid is not None:
        safe_print(f"Status: RUNNING (PID {pid})")
    elif read_pid(pid_file) is None:
        safe_print("Status: UNKNOWN (error reading PID file)")
    else:
        safe_print("Status: NOT RUNNING (stale PID file found)")


def restart_bot():
    """Restart the bot process."""
    pid_file = _current_pid_file()
    if pid_file.exists():
        pid = running_bot_pid(pid_file)
        if pid is not None:
            safe_print(f"Stopping existing bot (PID {pid})...")
            if not stop_process(pid):
                safe_print("Error: could not stop the existing bot; not starting another.")
                return
            safe_print("Bot stopped.")
        pid_file.unlink(missing_ok=True)

    safe_print("Starting Pocket Desk Agent in background...")
    python_exe = sys.executable
    if not python_exe or "python" not in python_exe.lower():
        python_exe = "python"
    child_env = dict(os.environ)
    child_env["PDAGENT_ENABLE_RELOADER"] = "0"

    subprocess.Popen(
        [python_exe, "-m", "pocket_desk_agent.main"],
        env=child_env,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    import time

    time.sleep(2)
    safe_print(f"Bot restarted in background. Check {app_path('bot.log')} for success.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        safe_print("Usage: python manage_service.py [stop|status|restart]")
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == "stop":
        stop_bot()
    elif command == "status":
        check_status()
    elif command == "restart":
        restart_bot()
    else:
        safe_print(f"Unknown command: {command}")
        sys.exit(1)
