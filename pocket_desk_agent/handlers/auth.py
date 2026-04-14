"""Authentication command handlers (login, authcode, checkauth, logout).

/login     — shows an inline keyboard with 2 OAuth options (Antigravity / Gemini CLI)
/authcode  — accepts either a raw auth code or a full callback URL
/checkauth — checks current auth status
/logout    — signs out with confirmation
"""

import base64
import json
import logging
from urllib.parse import urlparse, parse_qs
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import auth_client, gemini_client
from pocket_desk_agent.config import Config
from pocket_desk_agent.constants import (
    AUTH_MODE_ANTIGRAVITY,
    AUTH_MODE_GEMINI_CLI,
    AUTH_MODE_APIKEY,
)

logger = logging.getLogger(__name__)

# ── Callback data constants ──────────────────────────────────────────────────
_CB_LOGIN_ANTIGRAVITY = "login:antigravity"
_CB_LOGIN_GEMINI_CLI  = "login:gemini-cli"
_CB_CONFIRM_LOGOUT    = "confirm_logout"
_CB_CANCEL_LOGOUT     = "cancel_logout"


def _decode_auth_state(state: str) -> tuple[str | None, str | None]:
    """Recover the PKCE verifier and auth mode embedded in the OAuth state payload."""
    if not state:
        return None, None

    try:
        padding = (-len(state)) % 4
        decoded = base64.urlsafe_b64decode(state + ("=" * padding)).decode("utf-8")
        payload = json.loads(decoded)
    except Exception as exc:
        logger.warning(f"Failed to decode OAuth state payload: {exc}")
        return None, None

    verifier = payload.get("verifier")
    auth_mode = payload.get("authMode")
    resolved_verifier = verifier if isinstance(verifier, str) and verifier else None
    resolved_auth_mode = auth_mode if auth_mode in (AUTH_MODE_ANTIGRAVITY, AUTH_MODE_GEMINI_CLI) else None
    return resolved_verifier, resolved_auth_mode


# ── /login ───────────────────────────────────────────────────────────────────

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /login — show OAuth method selection (or link if API key mode)."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    # API key mode — no login needed
    if Config.GEMINI_AUTH_MODE == AUTH_MODE_APIKEY:
        await update.message.reply_text(
            "ℹ️ Your bot is configured to use an *API Key* — no OAuth login needed.\n\n"
            "Just start chatting! Use /checkauth to verify.",
            parse_mode="Markdown",
        )
        return

    # Already authenticated
    if auth_client.is_authenticated(user_id):
        user_info = auth_client.get_user_info(user_id)
        if not user_info:
            await update.message.reply_text(
                "✅ Authentication is active, but user details could not be loaded right now.\n\n"
                "Use /checkauth to retry, or /logout if you want to re-authenticate."
            )
            return
        mode_label = {
            AUTH_MODE_ANTIGRAVITY: "Antigravity OAuth",
            AUTH_MODE_GEMINI_CLI:  "Gemini CLI OAuth",
        }.get(user_info.get("auth_mode", ""), "OAuth")
        await update.message.reply_text(
            f"✅ Already authenticated via *{mode_label}*\n\n"
            f"📧 Email: `{user_info.get('email', 'Unknown')}`\n\n"
            f"Use /logout to sign out.",
            parse_mode="Markdown",
        )
        return

    # Show 2-option inline keyboard
    keyboard = [
        [
            InlineKeyboardButton(
                "🔵 Antigravity OAuth",
                callback_data=_CB_LOGIN_ANTIGRAVITY,
            ),
            InlineKeyboardButton(
                "🟢 Gemini CLI OAuth",
                callback_data=_CB_LOGIN_GEMINI_CLI,
            ),
        ]
    ]
    await update.message.reply_text(
        "🔐 *Choose your authentication method:*\n\n"
        "🔵 *Antigravity OAuth* — Uses the internal Google API (requires GCP project)\n"
        "🟢 *Gemini CLI OAuth*  — Uses the public Gemini API (no GCP project needed)\n\n"
        "Both methods use browser-based Google login.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ── Inline button handler ────────────────────────────────────────────────────

async def login_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the OAuth method selection button press."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user_id = query.from_user.id
    data = query.data

    if data == _CB_CONFIRM_LOGOUT:
        await _do_logout(query, user_id)
        return
    if data == _CB_CANCEL_LOGOUT:
        await query.answer("Cancelled.")
        await query.edit_message_text("❌ Logout cancelled.")
        return

    if data not in (_CB_LOGIN_ANTIGRAVITY, _CB_LOGIN_GEMINI_CLI):
        await query.answer("Unknown action.")
        return

    auth_mode = AUTH_MODE_ANTIGRAVITY if data == _CB_LOGIN_ANTIGRAVITY else AUTH_MODE_GEMINI_CLI
    mode_label = "Antigravity OAuth" if auth_mode == AUTH_MODE_ANTIGRAVITY else "Gemini CLI OAuth"

    await query.answer(f"Generating {mode_label} link…")
    await query.edit_message_text(f"🔄 Generating *{mode_label}* link… please wait.", parse_mode="Markdown")

    try:
        # Get the right OAuth instance for this mode
        oauth = auth_client._get_oauth_instance(user_id, auth_mode=auth_mode)
        auth_url, verifier = oauth.build_authorization_url()

        # Store verifier + mode for /authcode
        auth_client._pending_verifiers[user_id] = verifier
        auth_client._pending_auth_modes[user_id] = auth_mode

        await query.edit_message_text(
            f"🔗 *{mode_label} — Authentication Link*\n\n"
            f"`{auth_url}`\n\n"
            f"📱 *Steps:*\n"
            f"1\\. Open the link above on any device\n"
            f"2\\. Sign in with your Google account\n"
            f"3\\. Grant the requested permissions\n"
            f"4\\. You'll land on a callback page — copy the *full URL* or just the code\n"
            f"5\\. Send it back here: `/authcode <code_or_full_url>`\n\n"
            f"⏰ Link expires in 10 minutes",
            parse_mode="MarkdownV2",
        )
        logger.info(f"Generated {auth_mode} auth link for user {user_id}")

    except Exception as e:
        await query.edit_message_text(f"❌ Error generating link: {e}")
        logger.error(f"login_button_callback error: {e}", exc_info=True)


# ── /authcode ────────────────────────────────────────────────────────────────

async def authcode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /authcode — accepts a raw code or full callback URL."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if auth_client.is_authenticated(user_id):
        await update.message.reply_text(
            "✅ You're already authenticated!\n\n"
            "Use /logout to sign out first if you want to re-authenticate."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "ℹ️ *Usage:* `/authcode <code_or_callback_url>`\n\n"
            "*Examples:*\n"
            "`/authcode 4/0AanRRrtT…`\n"
            "`/authcode http://localhost:51121/oauth-callback?code=4/0AanRRrtT…`\n\n"
            "Start with `/login` to get your authentication link.",
            parse_mode="Markdown",
        )
        return

    raw_input = " ".join(context.args).strip()

    # Auto-detect and extract code from callback URL
    auth_code = raw_input
    callback_state = None
    if raw_input.startswith("http://") or raw_input.startswith("https://"):
        try:
            parsed = urlparse(raw_input)
            params = parse_qs(parsed.query)
            if "code" in params:
                auth_code = params["code"][0]
                callback_state = params.get("state", [None])[0]
                logger.info(f"Extracted auth code from callback URL for user {user_id}")
            else:
                await update.message.reply_text(
                    "❌ The URL doesn't contain a `code` parameter.\n\n"
                    "Please paste the correct callback URL or just the authorization code."
                )
                return
        except Exception as exc:
            logger.warning(f"Failed to parse URL, treating as raw code: {exc}")

    decoded_auth_mode = None
    verifier = auth_client._pending_verifiers.get(user_id)
    if callback_state:
        decoded_verifier, decoded_auth_mode = _decode_auth_state(callback_state)
        if not verifier and decoded_verifier:
            verifier = decoded_verifier
            logger.info(f"Recovered verifier from callback state for user {user_id}")

    if not verifier:
        await update.message.reply_text(
            "❌ No pending authentication found.\n\n"
            "Please use /login first to start the authentication process. "
            "If you're pasting a callback URL, make sure it includes both `code` and `state`."
        )
        return

    auth_mode = (
        auth_client._pending_auth_modes.get(user_id)
        or decoded_auth_mode
        or auth_client.get_auth_mode(user_id, fallback=Config.GEMINI_AUTH_MODE)
    )

    await update.message.reply_text("🔄 Processing authorization code… please wait.")

    try:
        oauth = auth_client._get_oauth_instance(user_id, auth_mode=auth_mode)
        success = oauth.exchange_code(auth_code, verifier)

        if success:
            # Clean up pending state
            auth_client._pending_verifiers.pop(user_id, None)
            auth_client._pending_auth_modes.pop(user_id, None)

            user_info = auth_client.get_user_info(user_id, auth_mode=auth_mode) or {
                "email": oauth.email,
                "project_id": getattr(oauth, "project_id", None),
            }
            mode_label = "Gemini CLI OAuth" if auth_mode == AUTH_MODE_GEMINI_CLI else "Antigravity OAuth"
            project_line = ""
            if user_info.get("project_id"):
                project_line = f"\n🏗️ Project: `{user_info['project_id']}`"

            await update.message.reply_text(
                f"✅ *Authentication successful!*\n\n"
                f"🔑 Mode: *{mode_label}*\n"
                f"📧 Email: `{user_info.get('email', 'Unknown')}`"
                f"{project_line}\n\n"
                f"You can now use all bot features! Try /help.",
                parse_mode="Markdown",
            )
            logger.info(f"User {user_id} authenticated via {auth_mode}")

            # Refresh GeminiClient oauth if it matches the mode
            try:
                if gemini_client._auth_mode == auth_mode and gemini_client._oauth:
                    gemini_client._oauth = oauth
            except Exception:
                pass

        else:
            await update.message.reply_text(
                "❌ Authentication failed.\n\n"
                "Possible reasons:\n"
                "• Invalid or expired authorization code\n"
                "• Code already used\n"
                "• Network error\n\n"
                "Please use /login to get a new link."
            )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error processing authorization code: {e}\n\nPlease try /login again."
        )
        logger.error(f"authcode_command error: {e}", exc_info=True)


# ── /checkauth ───────────────────────────────────────────────────────────────

async def checkauth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /checkauth — display current authentication status."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if Config.GEMINI_AUTH_MODE == AUTH_MODE_APIKEY:
        key_set = bool(Config.GOOGLE_API_KEY)
        await update.message.reply_text(
            f"{'✅' if key_set else '❌'} *API Key Mode*\n\n"
            f"API key: {'configured ✓' if key_set else 'not set — run pdagent configure'}",
            parse_mode="Markdown",
        )
        return

    if auth_client.is_authenticated(user_id):
        user_info = auth_client.get_user_info(user_id)
        if not user_info:
            await update.message.reply_text(
                "✅ Authentication is active, but user details could not be loaded right now."
            )
            return
        mode_label = {
            AUTH_MODE_ANTIGRAVITY: "Antigravity OAuth",
            AUTH_MODE_GEMINI_CLI:  "Gemini CLI OAuth",
        }.get(user_info.get("auth_mode", ""), "OAuth")
        project_line = ""
        if user_info.get("project_id"):
            project_line = f"\n🏗️ Project: `{user_info['project_id']}`"

        await update.message.reply_text(
            f"✅ *Authenticated*\n\n"
            f"🔑 Mode: *{mode_label}*\n"
            f"📧 Email: `{user_info.get('email', 'Unknown')}`"
            f"{project_line}\n\n"
            f"You can use all bot features!",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "⏳ *Not authenticated yet.*\n\n"
            "Use /login to start the authentication process.",
            parse_mode="Markdown",
        )


# ── /logout ──────────────────────────────────────────────────────────────────

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /logout — confirm then clear authentication."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if not auth_client.is_authenticated(user_id):
        await update.message.reply_text(
            "ℹ️ You're not currently authenticated.\n\nUse /login to authenticate."
        )
        return

    keyboard = [[
        InlineKeyboardButton("✅ Yes, logout", callback_data=_CB_CONFIRM_LOGOUT),
        InlineKeyboardButton("❌ Cancel",      callback_data=_CB_CANCEL_LOGOUT),
    ]]
    await update.message.reply_text(
        "⚠️ Are you sure you want to logout?\n\n"
        "This will clear your authentication and you'll need to login again.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _do_logout(query, user_id: int):
    """Execute the actual logout after confirmation."""
    auth_client.logout_user(user_id)
    await query.answer("Logged out.")
    await query.edit_message_text(
        "✅ Logged out successfully.\n\nUse /login to authenticate again."
    )
    logger.info(f"User {user_id} logged out")
