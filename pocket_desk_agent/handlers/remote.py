"""Telegram handlers for the live remote-desktop feature.

Exposes:

* ``remote_command``       — ``/remote`` — start or re-fetch a session.
* ``stopremote_command``   — ``/stopremote`` — stop the caller's session.
* ``start_remote_session`` — internal coroutine used by both the command
  and the Gemini confirmation flow. Guarantees rollback: if any step
  fails the partially-built state is torn down and nothing is added to
  ``ACTIVE_SESSIONS``.
* ``stop_remote_session`` — internal coroutine used by both the command,
  the Gemini confirmation flow, and the bot-shutdown hook.
* ``teardown_all_sessions`` — called from ``main.py`` on shutdown.

All heavy imports (aiohttp, qrcode, mss, xxhash) are deferred so the
idle bot never pays for them.
"""

from __future__ import annotations

import asyncio
import io
import logging
import socket
import time
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from pocket_desk_agent.config import Config
from pocket_desk_agent.handlers._shared import safe_command
from pocket_desk_agent.remote.session import (
    ACTIVE_SESSIONS,
    RemoteSession,
    get_for_user,
    teardown,
)

logger = logging.getLogger(__name__)

_WATCHDOG_INTERVAL_SECS = 30
_CLOUDFLARED_INSTALL_HINT = (
    "cloudflared is required for the remote tunnel.\n\n"
    "Install it once with:\n"
    "`winget install Cloudflare.cloudflared`\n\n"
    "Or download from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/\n"
    "and set `CLOUDFLARED_PATH` in `~/.pdagent/config` to the binary path.\n\n"
    "See docs/REMOTE.md for details."
)

# Pending auto-install approval: {user_id: {"chat_id": int, "created_at": float}}
# Populated when /remote detects a missing cloudflared binary and asks the
# user for install approval. Consumed by the callback handler.
pending_cloudflared_install: dict[int, dict] = {}
_INSTALL_PROMPT_TTL_SECS = 600


def _is_missing_cloudflared_message(message: str) -> bool:
    """Best-effort classifier for missing-cloudflared user-facing errors."""
    text = message.lower()
    return "cloudflared" in text and (
        "not found" in text
        or "could not locate" in text
        or "required for the remote tunnel" in text
        or "set `cloudflared_path`" in text
    )


def _hydrate_cloudflared_path_from_installs() -> bool:
    """Try to discover an existing cloudflared install and cache it in Config."""
    try:
        from pocket_desk_agent.remote.install import find_installed_binary

        resolved = find_installed_binary()
        if not resolved:
            return False
        Config.CLOUDFLARED_PATH = resolved
        return True
    except Exception:
        return False


def _build_viewer_url(tunnel_url: str, token: str) -> str:
    """Return ``tunnel_url`` with the required ``t=<token>`` query parameter."""
    parts = urlsplit(tunnel_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["t"] = token
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _has_viewer_token(url: str) -> bool:
    """Return True when ``url`` already includes a ``t`` query parameter."""
    return "t" in dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))


def _session_is_healthy(session: RemoteSession) -> bool:
    """Return True if an existing session still has a live tunnel process."""
    if session.torn_down:
        return False
    if session.tunnel_proc is None:
        return False
    return session.tunnel_proc.returncode is None


def _pick_free_port() -> int:
    """Ask the OS for a free localhost port. Small race is acceptable."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _build_qr_png(url: str) -> Optional[bytes]:
    """Render a PNG QR code for ``url``. Returns None on any failure."""
    try:
        import qrcode  # type: ignore

        img = qrcode.make(url)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception as exc:
        logger.info("[remote] qrcode generation failed: %s", exc)
        return None


def sanitized_status(user_id: int) -> dict:
    """Safe status dict for the Gemini ``get_remote_session_status`` tool.

    Never includes the raw token.
    """
    session = get_for_user(user_id)
    if not session:
        return {"active": False}
    return {
        "active": True,
        "url": session.tunnel_url,
        "idle_seconds": int(session.idle_seconds()),
        "fps": session.fps,
        "quality": session.quality,
        "max_width": session.max_width,
        "started_at": int(session.started_at),
    }


async def _rollback_partial_start(session: Optional[RemoteSession]) -> None:
    """Best-effort cleanup after a failed ``start_remote_session``."""
    if session is None:
        return
    try:
        await teardown(session)
    except Exception as exc:
        logger.debug("[remote] rollback teardown raised: %s", exc)


async def start_remote_session(user_id: int, chat_id: int, bot) -> tuple[bool, str]:
    """Create and fully wire up a remote session for ``user_id``.

    Returns ``(success, message)``. On success, ``message`` contains the
    public URL. On failure, ``message`` is a user-facing explanation. A
    QR-code PNG is sent as a separate photo when possible.
    """
    if not Config.REMOTE_ENABLED:
        return False, "Remote desktop feature is disabled by configuration (REMOTE_ENABLED=false)."

    existing = get_for_user(user_id)
    if existing:
        if _session_is_healthy(existing):
            if not _has_viewer_token(existing.tunnel_url):
                existing.tunnel_url = _build_viewer_url(existing.tunnel_url, existing.token)
            return (
                True,
                f"A remote session is already running.\n\nOpen: {existing.tunnel_url}\n\n"
                f"Use /stopremote to end it.",
            )
        logger.info("[remote] existing session for user %s is stale; recycling", user_id)
        await _rollback_partial_start(existing)

    try:
        from pocket_desk_agent.remote import tunnel as _tunnel_mod
        from pocket_desk_agent.remote import web_server as _web_server_mod
    except ImportError as exc:
        logger.warning("[remote] missing dependency: %s", exc)
        return (
            False,
            "Remote feature is missing a required Python package. "
            "Run `pip install --upgrade pocket-desk-agent` and try again.",
        )

    try:
        _tunnel_mod.resolve_binary()
    except _tunnel_mod.CloudflaredMissingError:
        return False, _CLOUDFLARED_INSTALL_HINT
    except Exception as exc:
        logger.exception("[remote] resolve_binary failed")
        return False, f"Could not locate cloudflared: {exc}"

    try:
        port = _pick_free_port()
    except OSError as exc:
        logger.exception("[remote] port allocation failed")
        return False, f"Could not allocate a local port: {exc}. Check firewall/AV."

    session = RemoteSession.create(
        user_id=user_id,
        chat_id=chat_id,
        port=port,
        fps=Config.REMOTE_DEFAULT_FPS,
        quality=Config.REMOTE_JPEG_QUALITY,
        max_width=Config.REMOTE_MAX_WIDTH,
    )

    try:
        try:
            runner, site = await _web_server_mod.start(session, Config.REMOTE_BIND_HOST)
        except Exception as exc:
            logger.exception("[remote] aiohttp server failed to start")
            await _rollback_partial_start(session)
            return False, f"Remote server failed to start: {exc}"
        session.server_runner = runner
        session.server_site = site

        try:
            proc, url = await _tunnel_mod.start_quick_tunnel(port)
        except _tunnel_mod.CloudflaredMissingError:
            await _rollback_partial_start(session)
            return False, _CLOUDFLARED_INSTALL_HINT
        except asyncio.TimeoutError:
            await _rollback_partial_start(session)
            return False, "Tunnel did not open in time. Retry or check your outbound network access."
        except Exception as exc:
            logger.exception("[remote] cloudflared failed")
            await _rollback_partial_start(session)
            return False, f"Tunnel process failed: {exc}"

        session.tunnel_proc = proc
        viewer_url = _build_viewer_url(url, session.token)
        session.tunnel_url = viewer_url

        session.watchdog_task = asyncio.create_task(_idle_watchdog(session, bot))

        qr_png = await asyncio.to_thread(_build_qr_png, viewer_url)
        if qr_png is not None:
            try:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=io.BytesIO(qr_png),
                    caption="Scan to open the remote viewer on your phone.",
                )
            except Exception as exc:
                logger.debug("[remote] QR send failed: %s", exc)

        logger.info("[remote] session started for user %s on port %d", user_id, port)
        return (
            True,
            (
                f"Remote desktop ready.\n\n"
                f"Open: {viewer_url}\n\n"
                f"- Mobile-first viewer (tap=click, drag=move, long-press=right-click,\n"
                f"  two-finger scroll, keyboard button for typing).\n"
                f"- Session ends after {Config.REMOTE_IDLE_TIMEOUT_SECS // 60} min idle or via /stopremote.\n"
                f"- Access is protected by the one-time URL token and secure session cookie.\n"
                f"- If the page does not open instantly, wait 2-3 seconds and refresh once."
            ),
        )
    except Exception as exc:
        logger.exception("[remote] unexpected start failure")
        await _rollback_partial_start(session)
        return False, f"Failed to start remote session: {exc}. Everything cleaned up."


async def stop_remote_session(user_id: int, bot=None, reason: str = "stopped") -> tuple[bool, str]:
    """Stop a running remote session for ``user_id``. Idempotent."""
    session = get_for_user(user_id)
    if not session:
        return False, "No active remote session."

    chat_id = session.chat_id
    try:
        await teardown(session)
    except Exception as exc:
        logger.exception("[remote] stop teardown raised")
        return False, f"Remote session ended with warnings: {exc}"

    if bot is not None and reason and chat_id:
        try:
            await bot.send_message(chat_id=chat_id, text=f"Remote session ended ({reason}).")
        except Exception:
            pass
    logger.info("[remote] session stopped for user %s (reason=%s)", user_id, reason)
    return True, "Remote session ended."


async def _idle_watchdog(session: RemoteSession, bot) -> None:
    """Tear down the session when it has been idle longer than the limit."""
    try:
        while not session.torn_down:
            await asyncio.sleep(_WATCHDOG_INTERVAL_SECS)
            if session.torn_down:
                return
            if session.idle_seconds() > Config.REMOTE_IDLE_TIMEOUT_SECS:
                logger.info("[remote] idle watchdog tearing down session for user %s", session.user_id)
                await stop_remote_session(session.user_id, bot=bot, reason="idle")
                return
    except asyncio.CancelledError:
        return
    except Exception as exc:
        logger.debug("[remote] watchdog loop exited: %s", exc)


async def teardown_all_sessions(bot=None) -> None:
    """Called from ``main.py`` on shutdown. Tears down every active session."""
    sessions = list(ACTIVE_SESSIONS.values())
    for session in sessions:
        try:
            if bot is not None:
                try:
                    await bot.send_message(
                        chat_id=session.chat_id,
                        text="Remote session ended (bot shutdown).",
                    )
                except Exception:
                    pass
            await teardown(session)
        except Exception as exc:
            logger.debug("[remote] shutdown teardown failed for user %s: %s", session.user_id, exc)


async def _prompt_cloudflared_install(update: Update, user_id: int, chat_id: int) -> None:
    """Ask the user for approval to auto-install cloudflared via winget."""
    pending_cloudflared_install[user_id] = {
        "chat_id": chat_id,
        "created_at": time.time(),
    }
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Install cloudflared", callback_data="install_cf_yes"),
                InlineKeyboardButton("Cancel", callback_data="install_cf_no"),
            ]
        ]
    )
    text = (
        "cloudflared is not installed - the remote tunnel needs it.\n\n"
        "I can install it for you by running:\n"
        "`winget install Cloudflare.cloudflared`\n\n"
        "Windows may show a UAC prompt on your PC. Proceed?"
    )
    try:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception:
        await update.message.reply_text(text, reply_markup=keyboard)


async def handle_install_cloudflared_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback target for the Install/Cancel inline buttons."""
    query = update.callback_query
    if not query or not query.data or not update.effective_user:
        return
    user_id = update.effective_user.id

    pending = pending_cloudflared_install.pop(user_id, None)
    if not pending:
        await query.edit_message_text("This install prompt has expired. Run /remote again.")
        return
    if time.time() - pending["created_at"] > _INSTALL_PROMPT_TTL_SECS:
        await query.edit_message_text("Install prompt expired. Run /remote again.")
        return

    chat_id = pending["chat_id"]

    if query.data == "install_cf_no":
        await query.edit_message_text("Install cancelled. Remote tunnel not started.")
        return

    from pocket_desk_agent.remote.install import winget_install_cloudflared

    await query.edit_message_text("Installing cloudflared via winget... this can take 1-2 minutes.")
    ok, detail = await winget_install_cloudflared()
    if not ok:
        await context.bot.send_message(chat_id=chat_id, text=f"Install failed.\n\n{detail}")
        logger.info("[remote] cloudflared auto-install failed for user %s: %s", user_id, detail)
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"cloudflared installed at: {detail}\nStarting remote tunnel...",
    )

    success, message = await start_remote_session(user_id, chat_id, context.bot)
    await context.bot.send_message(chat_id=chat_id, text=message)
    if not success:
        logger.info(
            "[remote] post-install /remote start failed for user %s: %s",
            user_id,
            message.splitlines()[0],
        )


@safe_command
async def remote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/remote`` — start a live remote-desktop session and return the URL."""
    if not update.message or not update.effective_user or not update.effective_chat:
        return

    if not Config.REMOTE_ENABLED:
        await update.message.reply_text(
            "Remote desktop feature is disabled (REMOTE_ENABLED=false in config)."
        )
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    from pocket_desk_agent.remote import tunnel as _tunnel_mod

    try:
        _tunnel_mod.resolve_binary()
    except _tunnel_mod.CloudflaredMissingError:
        if _hydrate_cloudflared_path_from_installs():
            logger.info("[remote] recovered cloudflared path from local install")
        else:
            await _prompt_cloudflared_install(update, user_id, chat_id)
            return
    except Exception as exc:
        # Older environments may not raise CloudflaredMissingError consistently.
        if _is_missing_cloudflared_message(str(exc)) and _hydrate_cloudflared_path_from_installs():
            logger.info("[remote] recovered cloudflared path after preflight error")
        elif _is_missing_cloudflared_message(str(exc)):
            await _prompt_cloudflared_install(update, user_id, chat_id)
            return
        else:
            # Non-missing errors fall through to start_remote_session's own handling.
            logger.debug("[remote] preflight resolve_binary raised non-missing error: %s", exc)
    # Re-validate if we populated Config.CLOUDFLARED_PATH from local install.
    try:
        _tunnel_mod.resolve_binary()
    except _tunnel_mod.CloudflaredMissingError:
        await _prompt_cloudflared_install(update, user_id, chat_id)
        return
    except Exception as exc:
        logger.debug("[remote] preflight re-validation raised: %s", exc)

    await update.message.reply_text("Opening remote tunnel... this usually takes 5-10 seconds.")

    success, message = await start_remote_session(user_id, chat_id, context.bot)
    if not success and _is_missing_cloudflared_message(message):
        await _prompt_cloudflared_install(update, user_id, chat_id)
        return
    await update.message.reply_text(message)
    if not success:
        logger.info("[remote] /remote start failed for user %s: %s", user_id, message.splitlines()[0])


@safe_command
async def stopremote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/stopremote`` — stop the caller's live remote-desktop session."""
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    success, message = await stop_remote_session(user_id, bot=context.bot, reason="stopped")
    await update.message.reply_text(message)
