"""
Process management utility for Pocket Desk Agent.
Handles stopping and status checking of the background bot.
"""

import os
import sys
import subprocess
from pathlib import Path

# Paths must match main.py
CONFIG_DIR = Path.home() / ".pdagent"
PID_FILE = CONFIG_DIR / "bot.pid"


def safe_print(msg):
    try:
        print(msg)
    except Exception:
        pass


def is_running(pid: int) -> bool:
    """Check if process is running on Windows."""
    try:
        # Check if pid is in tasklist
        output = subprocess.check_output(["tasklist", "/fi", f"pid eq {pid}"]).decode()
        return str(pid) in output
    except Exception:
        return False


def stop_bot():
    """Terminate the bot process."""
    if not PID_FILE.exists():
        safe_print("X No PID file found. Is the bot running?")
        return

    try:
        pid = int(PID_FILE.read_text().strip())
        if is_running(pid):
            safe_print(f"Stopping bot (PID {pid})...")
            # Try taskkill first for clean exit
            subprocess.run(["taskkill", "/pid", str(pid), "/f"], check=True)
            safe_print("✅ Bot stopped.")
        else:
            safe_print("! Bot is not currently running. Cleaning stale PID file.")
        
        PID_FILE.unlink(missing_ok=True)
    except Exception as e:
        safe_print(f"❌ Error stopping bot: {e}")


def check_status():
    """Check and print bot status."""
    if not PID_FILE.exists():
        safe_print("Status: 🛑 NOT RUNNING")
        return

    try:
        pid = int(PID_FILE.read_text().strip())
        if is_running(pid):
            safe_print(f"Status: 🚀 RUNNING (PID {pid})")
        else:
            safe_print("Status: 🛑 NOT RUNNING (Stale PID file found)")
    except Exception:
        safe_print("Status: ❓ UNKNOWN (Error reading PID file)")


def restart_bot():
    """Restart the bot process."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if is_running(pid):
                safe_print(f"Stopping existing bot (PID {pid})...")
                subprocess.run(["taskkill", "/pid", str(pid), "/f"], check=True)
                safe_print("✅ Bot stopped.")
        except Exception:
            pass
        PID_FILE.unlink(missing_ok=True)
    
    safe_print("🚀 Starting Pocket Desk Agent in background...")
    # Get python path, favoring current venv if active
    python_exe = sys.executable
    if not python_exe or 'python' not in python_exe.lower():
        python_exe = 'python'
    child_env = dict(os.environ)
    child_env["PDAGENT_ENABLE_RELOADER"] = "0"

    # Run in background. Let python handle its own logging to bot.log
    subprocess.Popen(
        [python_exe, "-m", "pocket_desk_agent.main"],
        env=child_env,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    import time
    time.sleep(2)
    safe_print("✅ Bot is restarted in background. Check bot.log for success.")


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
