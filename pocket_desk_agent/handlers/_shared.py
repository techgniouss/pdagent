"""Shared state, clients, and utilities for all handler modules."""

import logging
import os
import sys
import platform
import subprocess
import asyncio
import psutil
import time
import io
import json
import requests
import datetime
import functools
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ContextTypes

from pocket_desk_agent.auth import is_user_allowed, AntigravityAuth
from pocket_desk_agent.gemini_client import GeminiClient
from pocket_desk_agent.file_manager import FileManager
from pocket_desk_agent.scheduler_registry import get_scheduler_registry, ScheduledTask
from pocket_desk_agent.updater import (
    check_for_updates, apply_update, get_version_string,
    get_last_check, format_update_notification,
    get_local_short_sha, VERSION,
)

# Import pywinauto only on Windows
if platform.system() == "Windows":
    try:
        from pywinauto import Application as PywinautoApp
        from pywinauto.keyboard import send_keys
        import pygetwindow as gw
        from PIL import ImageGrab
        PYWINAUTO_AVAILABLE = True
    except ImportError:
        PYWINAUTO_AVAILABLE = False
else:
    PYWINAUTO_AVAILABLE = False

logger = logging.getLogger(__name__)

# ── Shared client instances ─────────────────────────────────────────────────
auth_client = AntigravityAuth()
gemini_client = GeminiClient()
file_manager = FileManager()

# ── Recording state for custom command saver AND scheduler ──────────────────
# Structure: {user_id: {"command_name": str, "actions": [...], "started_at": float, "scheduled_at": str|None}}
recording_sessions = {}
RECORDING_TIMEOUT_SECS = 600  # 10 minutes

# ── Per-domain state dicts ──────────────────────────────────────────────────
openfolder_options = {}          # {user_id: {index: path}}
claudecli_options = {}           # {user_id: {"paths": {index: path}, "prompt": str}}
findui_options = {}              # {user_id: {num: (x, y)}}
search_results = {}              # Claude search results
repo_lists = {}                  # Claude repo listings
repo_selection_state = {}        # Claude repo selection flow
build_state = {}                 # Build workflow state
large_file_upload_state = {}     # Upload choice state
apk_retrieval_state = {}         # APK retrieval flow

# Default repository base path
from pocket_desk_agent.config import Config
DEFAULT_REPO_PATH = Config.CLAUDE_DEFAULT_REPO_PATH

def safe_command(func):
    """
    Decorator that wraps every command/message/callback handler to:
      1. Enforce authorization — silently reject unauthorized users
      2. Enforce per-user rate limits — politely reject if over quota
      3. Catch any Exception that escapes the wrapped handler
      4. Send a sanitized error message to the user's chat
      5. Never re-raise, so the bot process never crashes
    """
    from pocket_desk_agent.rate_limiter import rate_limiter

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # ── Centralized auth check ──────────────────────────────────
        # Replaces 60+ per-handler is_user_allowed() calls.
        if update and update.effective_user and not is_user_allowed(update):
            logger.debug(f"Unauthorized access attempt by user {update.effective_user.id}")
            return

        # ── Rate limiting ───────────────────────────────────────────
        # The command name is derived from the handler function name
        # (e.g. "screenshot_command" → "screenshot").  For message
        # handlers that don't follow the pattern, fall back to the
        # raw function name so they still get the default limit.
        user_id = update.effective_user.id if update and update.effective_user else 0
        cmd_key = func.__name__.replace("_command", "")
        if not rate_limiter.check(user_id, cmd_key):
            chat_id = None
            try:
                if update and update.effective_chat:
                    chat_id = update.effective_chat.id
            except Exception:
                pass
            if chat_id:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"⏳ Rate limited — please wait before using /{cmd_key} again.",
                    )
                except Exception:
                    pass
            return

        try:
            await func(update, context)
        except Exception as exc:
            import traceback as _tb
            logger.error(
                f"[safe_command] Unhandled error in {func.__name__}: {exc}",
                exc_info=True,
            )
            # Determine where to send the reply
            chat_id = None
            try:
                if update and update.effective_chat:
                    chat_id = update.effective_chat.id
                elif update and update.effective_message:
                    chat_id = update.effective_message.chat_id
            except Exception:
                pass

            if chat_id is None:
                return  # No way to reply, just log

            short = f"{type(exc).__name__}: {str(exc)[:400]}"
            cmd_label = func.__name__.replace("_command", "").replace("_", " ")

            # Try Markdown first, fall back to plain text
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"\u2620\ufe0f *Error in* `{cmd_label}`\n\n"
                        f"`{short}`\n\n"
                        f"_The bot is still running. Try again or check /help._"
                    ),
                    parse_mode="Markdown",
                )
            except Exception:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"\u2620\ufe0f Error in [{cmd_label}]: {short}\n\n"
                            f"The bot is still running. Try again or check /help."
                        ),
                    )
                except Exception as send_err:
                    logger.error(f"[safe_command] Could not send error reply: {send_err}")

    return wrapper


def record_action_if_active(user_id: int, action_type: str, args: list) -> bool:
    """
    Record an action if user has an active recording session.
    Returns True if recorded (caller should NOT execute the action).
    Returns False if no session (caller should execute normally).
    Also auto-cancels sessions that have exceeded RECORDING_TIMEOUT_SECS.
    """
    if user_id not in recording_sessions:
        return False

    session = recording_sessions[user_id]

    # Check timeout
    elapsed = time.time() - session.get("started_at", time.time())
    if elapsed > RECORDING_TIMEOUT_SECS:
        del recording_sessions[user_id]
        logger.info(f"Auto-cancelled recording session for user {user_id} (timeout after {elapsed:.0f}s)")
        return False  # Session expired — execute normally

    from pocket_desk_agent.command_registry import CommandAction
    action = CommandAction(type=action_type, args=args)
    session["actions"].append(action)
    logger.info(f"Recorded action for user {user_id}: {action_type} {args}")
    return True
