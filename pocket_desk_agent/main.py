"""Main bot entry point."""

import logging
import sys
import os
import atexit
from pathlib import Path
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from wakepy import keep

from pocket_desk_agent.config import Config
from pocket_desk_agent.command_map import COMMAND_REGISTRY
from pocket_desk_agent.handlers import (
    button_callback,
    handle_message,
    handle_photo,
    error_handler,
    get_bot_commands,
    execute_scheduled_task,
    safe_command,
)
from pocket_desk_agent.scheduler_registry import get_scheduler_registry
from pocket_desk_agent.updater import get_version_string
import asyncio

# Ensure user config directory exists
CONFIG_DIR = Path.home() / ".pdagent"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
PID_FILE = CONFIG_DIR / "bot.pid"
LOG_FILE = Path.cwd() / "bot.log"

# Configure logging to both console and file
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL),
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def acquire_lock():
    """Ensure only one bot instance runs at a time."""
    if PID_FILE.exists():
        old_pid = PID_FILE.read_text().strip()
        try:
            pid = int(old_pid)
            # Check if that process is still alive
            os.kill(pid, 0)
            logger.error(f"Another bot instance is already running (PID {pid}). Exiting.")
            sys.exit(1)
        except (OSError, ValueError):
            # Process is dead, remove stale lock
            PID_FILE.unlink(missing_ok=True)

    PID_FILE.write_text(str(os.getpid()))
    atexit.register(lambda: PID_FILE.unlink(missing_ok=True))


def _tesseract_available() -> bool:
    """Return True if the Tesseract binary is installed and reachable."""
    from pocket_desk_agent.cli import _tesseract_available as _check
    return _check()


async def post_init(application: Application):
    """Sync commands with Telegram on startup and launch background tasks."""
    # Use the helper that pulls from COMMAND_REGISTRY
    await application.bot.set_my_commands(get_bot_commands())
    logger.info("Self-sync completed: All commands in registry updated on Telegram.")

    # ── Tesseract OCR check ───────────────────────────────────────────────
    if not _tesseract_available():
        logger.warning(
            "Tesseract OCR binary not found — /findtext, /smartclick, "
            "and Claude/Antigravity UI automation will not work."
        )
        for user_id in Config.AUTHORIZED_USER_IDS:
            try:
                await application.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "⚠️ *Tesseract OCR is not installed.*\n\n"
                        "The following features will not work until it is installed:\n"
                        "• `/findtext`, `/smartclick` — OCR-based screen search\n"
                        "• Claude Desktop UI automation\n"
                        "• Antigravity model switching\n\n"
                        "*Install options:*\n"
                        "Windows (winget):\n"
                        "`winget install UB-Mannheim.TesseractOCR`\n\n"
                        "Or download the installer from:\n"
                        "https://github.com/UB-Mannheim/tesseract/wiki\n\n"
                        "Restart the bot after installing."
                    ),
                    parse_mode="Markdown",
                )
            except Exception:
                pass

    # ── Startup notification ──────────────────────────────────────────────
    for user_id in Config.AUTHORIZED_USER_IDS:
        try:
            await application.bot.send_message(
                chat_id=user_id,
                text=f"✅ Bot started — {get_version_string()}",
            )
        except Exception:
            pass

    # ── Background tasks (running inside the Application's event loop) ────
    asyncio.create_task(scheduler_loop(application))


def start_reloader():
    """Start a background thread to monitor file changes for live reloading."""
    import threading
    import time
    
    def reloader_thread():
        bot_dir = Path(__file__).parent.resolve()
        mtimes = {}
        
        # Initial scan
        for file_path in bot_dir.rglob("*.py"):
            try:
                mtimes[file_path] = file_path.stat().st_mtime
            except Exception:
                pass
                
        while True:
            time.sleep(1.5)
            changed = False
            for file_path in bot_dir.rglob("*.py"):
                try:
                    mtime = file_path.stat().st_mtime
                    if file_path not in mtimes:
                        mtimes[file_path] = mtime
                    elif mtimes[file_path] < mtime:
                        logger.info(f"🔄 File modified: {file_path.name}. Live reloading...")
                        changed = True
                        break
                except Exception:
                    pass
            
            if changed:
                try:
                    PID_FILE.unlink(missing_ok=True)
                except Exception:
                    pass
                # On Windows, os.execv doesn't work well for background apps. Use Popen.
                # Always use `-m pocket_desk_agent.main` with the project root as cwd so that
                # `import pocket_desk_agent` works correctly regardless of how the script was first launched.
                import subprocess
                project_root = Path(__file__).parent.parent.resolve()

                # Flush logs before killing the process so nothing is lost.
                for handler in logging.getLogger().handlers:
                    try:
                        handler.flush()
                    except Exception:
                        pass

                subprocess.Popen(
                    [sys.executable, "-m", "pocket_desk_agent.main"],
                    cwd=str(project_root),
                    creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0),
                )
                # Small delay so the new process can start and see that PID_FILE
                # is gone before we exit.  Without this the old process can linger
                # long enough for the new acquire_lock() to see a live PID via
                # os.kill(old_pid, 0) and refuse to start.
                time.sleep(0.5)
                # os._exit() is intentional — sys.exit() only raises SystemExit
                # in this daemon thread; the main thread (run_polling) keeps going.
                # PID file is already cleaned up above; atexit handlers are skipped
                # but that's acceptable since we've flushed logs and removed the lock.
                os._exit(0)
                
    t = threading.Thread(target=reloader_thread, daemon=True)
    t.start()



async def scheduler_loop(application: Application):
    """Background task to check and execute scheduled tasks."""
    logger.info("🕒 Scheduler loop started.")
    _cleanup_counter = 0
    while True:
        try:
            registry = get_scheduler_registry()

            # Cleanup old completed/failed tasks once per hour (every 60 iterations)
            _cleanup_counter += 1
            if _cleanup_counter >= 60:
                _cleanup_counter = 0
                registry.cleanup_old_tasks(days=7)

            due_tasks = registry.get_pending_tasks()
            
            for task in due_tasks:
                logger.info(f"🚀 Executing scheduled task {task.id}: {task.command}")
                
                # Execute the task
                success, error = await execute_scheduled_task(task, application.bot)
                
                if success:
                    registry.update_task_status(task.id, "completed")
                else:
                    registry.update_task_status(task.id, "failed", error=error)
                    try:
                        await application.bot.send_message(
                            chat_id=task.user_id,
                            text=f"❌ Scheduled task failed: {task.command}\nError: {error}"
                        )
                    except Exception:
                        pass
                
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}", exc_info=True)
        
        await asyncio.sleep(60) # Check every minute


def main():
    """Start the bot."""
    acquire_lock()

    # Validate configuration
    errors = Config.validate()
    if errors:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    logger.info(f"Starting Pocket Desk Agent {get_version_string()}...")
    
    # Create application with post_init hook
    application = (
        Application.builder()
        .token(Config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    
    # Register all commands dynamically from the centralized registry.
    # Every handler is wrapped with safe_command so that any unhandled exception
    # is caught, logged, and reported back to the user — the bot never crashes silently.
    for command_name, handler_func, _ in COMMAND_REGISTRY:
        application.add_handler(CommandHandler(command_name, safe_command(handler_func)))
    
    # Callback queries (inline buttons) — also protected
    application.add_handler(CallbackQueryHandler(safe_command(button_callback)))
    
    # Message handlers — also protected
    application.add_handler(MessageHandler(filters.TEXT, safe_command(handle_message)))
    application.add_handler(MessageHandler(filters.PHOTO, safe_command(handle_photo)))
    
    # Global error handler — catches anything that still slips through
    # (e.g. networking errors during polling, internal PTB errors)
    application.add_error_handler(error_handler)
    
    # Start the bot with keep-awake mode
    logger.info("Bot is running. Press Ctrl+C to stop.")
    logger.info("Keep-awake mode enabled - system will not sleep while bot is running")
    
    start_reloader()

    with keep.running():
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )


if __name__ == "__main__":
    main()
