"""Main bot entry point."""

import logging
import sys
import os
import atexit
from pathlib import Path
from telegram.error import InvalidToken
from telegram.request import HTTPXRequest
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from wakepy import keep

from pocket_desk_agent.async_utils import spawn_background_task
from pocket_desk_agent.process_utils import is_bot_process
from pocket_desk_agent.app_paths import app_path, ensure_app_dir, existing_app_path
from pocket_desk_agent.config import Config
from pocket_desk_agent.log_redaction import SecretRedactingFilter
from pocket_desk_agent.telegram_safe import MarkdownFallbackBot
from pocket_desk_agent.command_map import COMMAND_REGISTRY
from pocket_desk_agent.handlers import (
    button_callback,
    handle_message,
    handle_photo,
    handle_image_document,
    error_handler,
    get_bot_commands,
    cleanup_scheduled_task_artifacts,
    describe_task,
    execute_scheduled_task,
    safe_command,
    teardown_all_sessions,
    resume_if_enabled,
)
from pocket_desk_agent.scheduler_registry import get_scheduler_registry
from pocket_desk_agent.scheduling_utils import format_duration, get_task_due_at, local_now
from pocket_desk_agent.updater import (
    get_version_string,
    startup_update_check,
    update_checker_loop,
    format_update_notification,
)
import asyncio

# Ensure user config directory exists
ensure_app_dir()
PID_FILE = app_path("bot.pid")
LOG_FILE = app_path("bot.log")

# Configure logging to both console and file.
# RotatingFileHandler caps bot.log at 5 MB and keeps 3 backups (≤15 MB total).
from logging.handlers import RotatingFileHandler as _RotatingFileHandler
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, str(Config.LOG_LEVEL).strip().upper(), logging.INFO),
    handlers=[
        logging.StreamHandler(),
        _RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8',
        ),
    ]
)
# Library errors embed secrets (PTB's InvalidToken message contains the bot
# token; requests errors contain the request URL) — mask them on every handler.
for _handler in logging.getLogger().handlers:
    _handler.addFilter(SecretRedactingFilter())
logger = logging.getLogger(__name__)

# httpx logs every Telegram API request URL at INFO level, and those URLs
# embed the bot token — keep them out of bot.log.
logging.getLogger("httpx").setLevel(logging.WARNING)

SCHEDULER_POLL_INTERVAL_SECONDS = 5

# A one-shot task that is overdue by more than this was missed (bot or PC was
# off/asleep). Running it late is wrong and sometimes dangerous — a shutdown
# scheduled for last night must not fire at 09:00 when the bot starts — so it
# is skipped and reported instead. Shutdown gets a much tighter window.
MISSED_TASK_GRACE_SECONDS = 600
MISSED_SHUTDOWN_GRACE_SECONDS = 120


def missed_task_lateness(task, now=None) -> float | None:
    """Seconds a one-shot ``task`` is overdue beyond its grace window, else None.

    Repeating tasks are never "missed": they simply run at the next poll.
    """
    if task.interval_seconds:
        return None
    due_at = get_task_due_at(task.to_dict())
    if due_at is None:
        return None
    is_shutdown = task.task_type == "system_shutdown" or task.command == "system_shutdown"
    grace = MISSED_SHUTDOWN_GRACE_SECONDS if is_shutdown else MISSED_TASK_GRACE_SECONDS
    lateness = ((now or local_now()) - due_at).total_seconds()
    return lateness if lateness > grace else None

def _should_enable_reloader(project_root: Path) -> bool:
    """Enable live reload only for interactive dev sessions."""
    if not (project_root / ".git").exists():
        return False

    override = os.getenv("PDAGENT_ENABLE_RELOADER", "").strip().lower()
    if override in {"1", "true", "yes", "on"}:
        return True
    if override in {"0", "false", "no", "off"}:
        return False

    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except Exception:
        return False


def acquire_lock():
    """Ensure only one bot instance runs at a time."""
    existing_pid_file = existing_app_path("bot.pid")
    if existing_pid_file.exists():
        old_pid = existing_pid_file.read_text().strip()
        try:
            pid = int(old_pid)
            # A PID alone proves nothing: after a crash/reboot the OS may have
            # reused it for an unrelated program. Only a live *bot* process
            # counts as another instance.
            if is_bot_process(pid) and pid != os.getpid():
                logger.error(f"Another bot instance is already running (PID {pid}). Exiting.")
                sys.exit(1)
            raise ValueError("stale pid")
        except ValueError:
            # Process is dead, remove stale lock
            existing_pid_file.unlink(missing_ok=True)

    PID_FILE.write_text(str(os.getpid()))
    atexit.register(lambda: PID_FILE.unlink(missing_ok=True))


def _tesseract_available() -> bool:
    """Return True if the Tesseract binary is installed and reachable."""
    from pocket_desk_agent.cli import _tesseract_available as _check
    return _check()


async def post_init(application: Application):
    """Sync commands with Telegram on startup and launch background tasks."""
    try:
        await application.bot.set_my_commands(get_bot_commands())
        logger.info("Command menu sync completed.")
    except Exception as exc:
        logger.warning(f"[post_init] Failed to sync command menu: {exc}")

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

    # ── Update check (run in thread so the event loop is never blocked) ─────
    try:
        loop = asyncio.get_running_loop()
        update_info = await loop.run_in_executor(None, startup_update_check)
        if not update_info.up_to_date and not update_info.error:
            msg = format_update_notification(update_info)
            for user_id in Config.AUTHORIZED_USER_IDS:
                try:
                    await application.bot.send_message(
                        chat_id=user_id,
                        text=msg,
                        parse_mode="Markdown",
                    )
                except Exception:
                    pass
    except Exception as exc:
        logger.warning(f"[updater] Startup update check failed: {exc}")

    # ── Background tasks (running inside the Application's event loop) ────
    spawn_background_task(scheduler_loop(application))

    if Config.AUTO_UPDATE_ENABLED:
        async def _notify_update(info):
            msg = format_update_notification(info)
            for user_id in Config.AUTHORIZED_USER_IDS:
                try:
                    await application.bot.send_message(
                        chat_id=user_id,
                        text=msg,
                        parse_mode="Markdown",
                    )
                except Exception:
                    pass

        interval = Config.AUTO_UPDATE_INTERVAL_MINUTES * 60
        spawn_background_task(update_checker_loop(interval, _notify_update))

    # ── Auto battery manager (resumes if previously enabled) ────────────────
    try:
        await resume_if_enabled(application.bot)
    except Exception as exc:
        logger.warning("[autobattery] Failed to resume on startup: %s", exc)


async def post_shutdown(application: Application):
    """Tear down any active remote-desktop sessions cleanly on bot exit."""
    try:
        await teardown_all_sessions(application.bot)
    except Exception as exc:
        logger.warning(f"[remote] shutdown teardown raised: {exc}")


def start_reloader():
    """Restart the bot when a source ``.py`` file changes (dev only).

    Uses ``watchfiles`` for efficient, debounced filesystem watching instead of
    a 1.5s ``rglob`` poll loop. ``watchfiles`` is a ``[dev]`` optional
    dependency; when it is missing we log and skip the reloader rather than
    falling back to a CPU-hungry poll.
    """
    import threading

    try:
        from watchfiles import watch, PythonFilter
    except ImportError:
        logger.warning(
            "Live reloader requested but 'watchfiles' is not installed. "
            'Install dev extras (pip install -e ".[dev]") to enable it. Skipping reloader.'
        )
        return

    bot_dir = Path(__file__).parent.resolve()
    # Use `-m pocket_desk_agent.main` with the project root as cwd so that
    # `import pocket_desk_agent` resolves regardless of how it was first launched.
    project_root = bot_dir.parent.resolve()

    def reloader_thread():
        import subprocess
        import time

        # `watch` is a blocking generator that yields a set of changes (already
        # debounced). PythonFilter restricts events to .py files.
        for _changes in watch(str(bot_dir), watch_filter=PythonFilter(), debounce=400):
            logger.info("🔄 Source change detected. Live reloading...")

            # Remove the lock first so the replacement can acquire it.
            try:
                PID_FILE.unlink(missing_ok=True)
            except Exception:
                pass

            # Flush logs before replacing the process so nothing is lost.
            for handler in logging.getLogger().handlers:
                try:
                    handler.flush()
                except Exception:
                    pass

            subprocess.Popen(
                [sys.executable, "-m", "pocket_desk_agent.main"],
                cwd=str(project_root),
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            # Brief delay so the new process can start and see that PID_FILE is
            # gone before we exit; otherwise acquire_lock() may see a live PID.
            time.sleep(0.5)
            # os._exit() is intentional — sys.exit() only raises SystemExit in
            # this daemon thread; the main thread (run_polling) would keep going.
            os._exit(0)

    t = threading.Thread(target=reloader_thread, daemon=True)
    t.start()



async def _skip_missed_task(application: Application, registry, task, lateness: float) -> None:
    """Mark an overdue one-shot task failed (not run) and tell its owner."""
    late_for = format_duration(int(lateness))
    summary = describe_task(task)
    logger.warning(
        "Skipping scheduled task %s (%s): overdue by %s, missed while the bot was not running",
        task.id, task.command, late_for,
    )
    updated = registry.finalize_task_run(
        task.id,
        success=False,
        error=f"Missed its scheduled time by {late_for}; skipped instead of running late.",
    )
    if updated and updated.status in {"completed", "failed"}:
        cleanup_scheduled_task_artifacts(updated)
    try:
        await application.bot.send_message(
            chat_id=task.user_id,
            text=(
                f"⏭️ Skipped scheduled task (it was due {late_for} ago, while the bot "
                f"wasn't running): {summary}\nSchedule it again if you still want it."
            ),
        )
    except Exception:
        pass


async def scheduler_loop(application: Application):
    """Background task to check and execute scheduled tasks."""
    logger.info("🕒 Scheduler loop started.")
    _cleanup_counter = 0
    while True:
        try:
            registry = get_scheduler_registry()

            # Cleanup old completed/failed tasks once per hour.
            _cleanup_counter += 1
            if _cleanup_counter >= int(3600 / SCHEDULER_POLL_INTERVAL_SECONDS):
                _cleanup_counter = 0
                registry.cleanup_old_tasks(days=7)
                # Purge Gemini confirmation prompts the user never responded to.
                from pocket_desk_agent.gemini_actions import _purge_expired_pending_actions
                _purge_expired_pending_actions()

            due_tasks = registry.get_pending_tasks()
            
            for task in due_tasks:
                lateness = missed_task_lateness(task)
                if lateness is not None:
                    await _skip_missed_task(application, registry, task, lateness)
                    continue

                logger.info(f"🚀 Executing scheduled task {task.id}: {task.command}")
                
                # Execute the task. An exception must still finalize the run,
                # otherwise the task stays pending and re-fires every poll.
                try:
                    success, error = await execute_scheduled_task(task, application.bot)
                except Exception as task_exc:
                    logger.error(
                        "Scheduled task %s raised: %s", task.id, task_exc, exc_info=True
                    )
                    success, error = False, f"{type(task_exc).__name__}: {task_exc}"
                
                updated_task = registry.finalize_task_run(
                    task.id,
                    success=success,
                    error=error,
                )

                if updated_task and updated_task.status in {"completed", "failed"}:
                    cleanup_scheduled_task_artifacts(updated_task)

                if success:
                    if (
                        updated_task
                        and task.interval_seconds
                        and updated_task.status == "completed"
                    ):
                        try:
                            await application.bot.send_message(
                                chat_id=task.user_id,
                                text=(
                                    f"Repeating task finished: {describe_task(updated_task)}\n"
                                    f"Completed runs: {updated_task.run_count}"
                                ),
                            )
                        except Exception:
                            pass
                else:
                    summary = describe_task(task)
                    if updated_task and updated_task.status == "pending":
                        failure_note = (
                            f"⚠️ Scheduled task errored (will retry): {summary}\n"
                            f"Error: {error}\n"
                            f"Consecutive failures: {updated_task.consecutive_failures}"
                        )
                    else:
                        failure_note = (
                            f"❌ Scheduled task failed and stopped: {summary}\n"
                            f"Error: {error}"
                        )
                    try:
                        await application.bot.send_message(
                            chat_id=task.user_id,
                            text=failure_note,
                        )
                    except Exception:
                        pass
                
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}", exc_info=True)
        
        await asyncio.sleep(SCHEDULER_POLL_INTERVAL_SECONDS)


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
    # Generous network timeouts. Default PTB write/read timeouts (~5-20s) are
    # too short for large document uploads (e.g. APKs over a slow uplink): the
    # file finishes transferring but the client times out waiting for
    # Telegram's confirmation, surfacing a spurious "timed out" error even
    # though the file was delivered. Document sends additionally pass their own
    # per-call timeouts (see build.send_document_with_upload_fallback).
    # The bot is built explicitly (rather than via builder.token()) so it can be
    # the MarkdownFallbackBot; the builder's timeout setters aren't allowed
    # together with .bot(), so the same timeouts go on the HTTPXRequest.
    bot = MarkdownFallbackBot(
        token=Config.TELEGRAM_BOT_TOKEN,
        request=HTTPXRequest(
            connection_pool_size=256,
            connect_timeout=30.0,
            read_timeout=60.0,
            write_timeout=120.0,
            pool_timeout=30.0,
        ),
        get_updates_request=HTTPXRequest(connection_pool_size=1),
    )
    application = (
        Application.builder()
        .bot(bot)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
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
    application.add_handler(
        MessageHandler(filters.Document.IMAGE, safe_command(handle_image_document))
    )
    
    # Global error handler — catches anything that still slips through
    # (e.g. networking errors during polling, internal PTB errors)
    application.add_error_handler(error_handler)
    
    # Start the bot with keep-awake mode
    logger.info("Bot is running. Press Ctrl+C to stop.")
    logger.info("Keep-awake mode enabled - system will not sleep while bot is running")
    
    # Only start the live-reloader during development (running from a git
    # checkout).  When installed via pip the package lives in site-packages
    # and there is no .git directory — the reloader would just waste CPU
    # scanning files that never change.
    _project_root = Path(__file__).parent.parent.resolve()
    if _should_enable_reloader(_project_root):
        start_reloader()
        logger.info("Dev mode detected — live reloader enabled.")
    else:
        logger.debug("Production/background mode — live reloader disabled.")

    try:
        with keep.running():
            application.run_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True
            )
    except InvalidToken:
        # A wrong/revoked token is a configuration problem, not a crash: say so
        # plainly instead of letting a traceback (which echoes the token) escape.
        logger.error(
            "Telegram rejected the bot token (TELEGRAM_BOT_TOKEN). "
            "Run `pdagent configure` to enter a valid token from @BotFather."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
