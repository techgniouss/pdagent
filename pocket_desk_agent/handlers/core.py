"""Core bot command and message handlers."""

import asyncio
import logging
import platform
from typing import Any
from telegram import Update, BotCommand
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    auth_client,
    gemini_client,
    file_manager,
    recording_sessions,
    record_action_if_active,
    register_media_group_item,
    PYWINAUTO_AVAILABLE,
)
from pocket_desk_agent.updater import (
    get_version_string,
    apply_update,
    restart_bot_after_delay,
)
from pocket_desk_agent.config import Config
from pocket_desk_agent.constants import AUTH_MODE_APIKEY

logger = logging.getLogger(__name__)


def _get_gemini_auth_context(user_id: int) -> tuple[str, Any | None]:
    """Resolve the active auth mode and OAuth instance for the current user."""
    auth_mode = auth_client.get_auth_mode(user_id, fallback=Config.GEMINI_AUTH_MODE)
    if auth_mode == AUTH_MODE_APIKEY:
        return auth_mode, None
    return auth_mode, auth_client._get_oauth_instance(user_id, auth_mode=auth_mode)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    # Check if authenticated with antigravity
    authenticated = auth_client.is_authenticated(user_id)

    if authenticated:
        user_info = auth_client.get_user_info(user_id)
        await update.message.reply_text(
            f"Welcome! I'm your personal automation assistant.\n\n"
            f"✅ Gemini AI: Authenticated as {user_info.get('email', 'Unknown')}\n\n"
            f"You have access to:\n"
            f"• 🤖 Gemini AI chat (text & image analysis)\n"
            f"• 🖥️ System control (screenshot, privacy mode, battery, sleep, etc.)\n"
            f"• 📁 File system access\n"
            f"• ⌨️ Automation (hotkeys, clipboard, OCR, etc.)\n"
            f"• 🎯 Custom command sequences\n"
            f"• 💻 Claude desktop control\n"
            f"• 🔨 Build & APK management\n\n"
            f"Commands:\n"
            f"/help - Show all commands\n"
            f"/status - Check your session status"
        )
    else:
        await update.message.reply_text(
            f"Welcome! I'm your personal automation assistant.\n\n"
            f"⚠️ Gemini AI: Not authenticated\n\n"
            f"You can use:\n"
            f"• 🖥️ System control (screenshot, privacy mode, battery, sleep, etc.)\n"
            f"• 📁 File system access\n"
            f"• ⌨️ Automation (hotkeys, clipboard, OCR, etc.)\n"
            f"• 🎯 Custom command sequences\n"
            f"• 💻 Claude desktop control\n"
            f"• 🔨 Build & APK management\n\n"
            f"To enable Gemini AI chat:\n"
            f"Use /login to authenticate with Google\n\n"
            f"Commands:\n"
            f"/help - Show all commands\n"
            f"/login - Authenticate for Gemini AI"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    if not update.message:
        return

    user_id = update.effective_user.id
    is_authenticated = auth_client.is_authenticated(user_id)

    auth_note = (
        ""
        if is_authenticated
        else "\n\n⚠️ Note: Gemini AI commands require authentication. Use /login to enable."
    )

    await update.message.reply_text(
        "Available commands:\n\n"
        "🤖 Gemini AI (requires /login):\n"
        "• Chat naturally with text or images\n"
        "/new - Start a new conversation\n"
        "/enhance <text> - Enhance your text prompt\n\n"
        "🔐 Authentication:\n"
        "/start - Initialize the bot\n"
        "/login - Get authentication link\n"
        "/authcode <code> - Submit authorization code\n"
        "/checkauth - Verify authentication status\n"
        "/logout - Sign out and clear tokens\n"
        "/status - Check your session status\n\n"
        "🧪 Diagnostics:\n"
        "/selftest - Run non-GUI functional self-checks\n\n"
        "📁 File System Commands:\n"
        "/pwd - Show current directory\n"
        "/cd <path> - Change directory\n"
        "/ls [path] - List directory contents\n"
        "/cat <file> - Read file contents\n"
        "/getfile [path] - Download a file or browse interactively\n"
        "/find <pattern> - Search for files\n"
        "/info <path> - Get file/directory info\n\n"
        "🔌 System Commands:\n"
        "/stopbot - Stop the bot process\n"
        "/shutdown - Shutdown the laptop\n"
        "/sleep - Put PC to sleep (bot stays awake)\n"
        "/privacy <on|off|status> - Blank or wake the display without locking\n"
        "/wakeup - Info about waking up PC\n"
        "/clauderemote - Run claude remote-control in default repo\n"
        "/stopclaude - Stop claude remote-control\n"
        "/openclaude - Open Claude desktop app\n"
        "/battery - Check battery status\n"
        "/screenshot - Capture current screen\n"
        "/hotkey <keys> [text] - Execute shortcuts & type text\n"
        "/clipboard <text> - Set PC clipboard content\n"
        "/pasteimage - Reply to Telegram image and paste into focused app (auto-clears image clipboard in 2m)\n"
        "/pasteimages - Reply to album photo/image doc and paste all images (auto-clears image clipboard in 2m)\n"
        "/viewclipboard - View current PC clipboard\n"
        "/findtext <text> - Find text and show coordinates\n"
        "/clicktext <x> <y> - Click at screen coordinates\n"
        "/smartclick <text> - Find and click text (with selection)\n"
        "/findelements - Find and label all UI icons/symbols on screen\n"
        "/clickelement <num> - Click a labeled UI element from /findelements\n"
        "/pasteenter - Paste clipboard and press Enter\n"
        "/typeenter <text> - Type words without spaces and press Enter\n"
        "/scrollup [amount] - Hover centrally and scroll up\n"
        "/scrolldown [amount] - Hover centrally and scroll down\n\n"
        "🖥️ Remote Desktop:\n"
        "/remote - Start a live browser-based remote control session (HTTPS URL + QR)\n"
        "/remoteinfo - Show active remote session details\n"
        "/stopremote - Stop the active remote desktop session\n\n"
        "🎯 Custom Commands:\n"
        "/savecommand <name> - Start recording command sequence\n"
        "/done - Finish recording and save command\n"
        "/cancelrecord - Cancel current recording\n"
        "/listcommands - Show all saved commands\n"
        "/deletecommand <name> - Delete a saved command\n"
        "/<custom_name> - Execute a saved custom command\n\n"
        "🧩 Workflow Recipes:\n"
        "/recipecreate <name> - Create a workflow recipe\n"
        "/recipeaddcommand <name> <saved_command> - Add recorded command step\n"
        "/recipeaddclaude <name> <prompt> - Add Claude prompt step\n"
        "/recipeaddwait <name> <duration> - Add fixed wait step\n"
        "/recipeaddwaittext <name> <text> | timeout=2m scope=claude - Add OCR wait step\n"
        "/recipeaddnotify <name> <message> - Add Telegram notification step\n"
        "/recipelist - List recipes\n"
        "/recipeshow <name> - Show recipe steps\n"
        "/reciperun <name> [key=value ...] - Run recipe with optional variables\n"
        "/recipedelete <name> - Delete recipe\n\n"
        "🤖 Claude Desktop Control:\n"
        "/claudeask <message> - Send message to Claude desktop\n"
        "/claudenew [message] - Create new chat (optionally with first message)\n"
        "/clauderepo - Show repo selector and list (reply with number/name)\n"
        "/claudebranch <name> - Select git branch (use in new session only)\n"
        "/claudelatest [section] - Open latest session (today/yesterday/older)\n"
        "/claudesearch [query] - Search conversations and show results\n"
        "/claudeselect <number/text> - Select conversation from search\n"
        "/claudemode [number] - Change Claude mode (list modes if no number)\n"
        "/claudemodel [number] - Change Claude model (list models if no number)\n"
        "/claudescreen - Get screenshot of Claude desktop\n"
        "/claudechat <message> - Send message and get screenshot\n\n"
        "🌌 Antigravity Control:\n"
        "/openantigravity - Open or bring Antigravity to front\n"
        "/antigravitychat - Open Antigravity agent chat\n"
        "/antigravitymode <planning|fast> - Select agent mode\n"
        "/antigravitymodel [name] - Select specific AI model\n"
        "/antigravityclaudecodeopen - Focus Claude Code input in VS Code\n"
        "/openclaudeinvscode - Run Claude Code: Open in VS Code\n\n"
        "🔨 Build Workflow:\n"
        "/build - Start React Native build workflow\n"
        "  → Lists local repos with package.json\n"
        "  → Shows available npm scripts\n"
        "  → Executes build and monitors progress\n"
        "  → Finds and sends APK file\n\n"
        "/getapk - Retrieve existing APK files\n"
        "  → Browse local repositories\n"
        "  → Navigate build output folders\n"
        "  → Select and download APK files\n"
        "  → No rebuild required\n\n"
        "🕒 Task Scheduling:\n"
        "/schedule <time> - Record automation commands to run at a time\n"
        "/scheduleshutdown <time> - Schedule a confirmed one-shot system shutdown\n"
        "/repeatschedule every <interval> for <duration> - Repeat a recorded automation\n"
        "/watchperm <target> every <interval> for <duration> - Auto-click app approval prompts\n"
        "/watchscreen <text> every <interval> press <hotkey> - Watch screen/app text and send a hotkey\n"
        "/watchnotify <text> every <interval> - Watch screen/app text and notify only\n"
        "/watchstatus - Show active watchers only\n"
        "/stopscreenwatch [task_id|all] - Stop one or all active screen watchers\n"
        "/claudeschedule <time> <msg> - Schedule a prompt for Claude\n"
        "/listschedules - View all pending scheduled tasks\n"
        "/cancelschedule <id> - Cancel a pending scheduled task\n\n"
        "💬 Gemini AI Chat:\n"
        "Just send me a message or image to chat!"
        f"{auth_note}"
    )


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /new command - start a new conversation."""
    if not update.message:
        return

    user_id = update.effective_user.id
    gemini_client.clear_session(user_id)

    await update.message.reply_text(
        "Started a new conversation. Previous chat history has been cleared."
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    if not update.message:
        return

    user_id = update.effective_user.id
    is_auth = auth_client.is_authenticated(user_id)
    has_session = user_id in gemini_client.sessions

    user_info = auth_client.get_user_info(user_id)

    status_text = f"📊 *Bot Status*\n\n"
    status_text += f"📦 Version: `{get_version_string()}`\n\n"
    status_text += f"• Authenticated: {'✅' if is_auth else '❌'}\n"

    if user_info:
        status_text += f"• Email: {user_info.get('email', 'Unknown')}\n"
        status_text += f"• Project ID: {user_info.get('project_id', 'Unknown')}\n"

    status_text += f"• Active chat session: {'✅' if has_session else '❌'}\n"
    status_text += f"• User ID: `{user_id}`"

    try:
        await update.message.reply_text(status_text, parse_mode="Markdown")
    except Exception:
        # Fallback to plain text if Markdown fails
        await update.message.reply_text(status_text.replace("*", "").replace("`", ""))


async def enhance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /enhance command - enhance text prompts using Gemini."""
    if not update.message:
        return

    user_id = update.effective_user.id

    # Check authentication
    if not auth_client.is_authenticated(user_id):
        await update.message.reply_text("Please authenticate first using /start")
        return

    # Get text to enhance
    if not context.args:
        await update.message.reply_text(
            "Usage: /enhance <text>\n\n"
            "Enhance and improve your text prompt using AI.\n\n"
            "Examples:\n"
            "/enhance write a function to sort numbers\n"
            "/enhance explain quantum computing\n"
            "/enhance create a todo app\n\n"
            "The AI will make your prompt more detailed, clear, and effective."
        )
        return

    original_text = " ".join(context.args)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # Create enhancement prompt
    enhancement_prompt = f"""You are a prompt enhancement expert. Your task is to take the user's brief prompt and enhance it to be more detailed, clear, and effective.

Original prompt: "{original_text}"

Please enhance this prompt by:
1. Making it more specific and detailed
2. Adding relevant context and requirements
3. Clarifying the expected output or goal
4. Maintaining the original intent

Provide ONLY the enhanced prompt, without any explanations or meta-commentary."""

    try:
        auth_mode, oauth = _get_gemini_auth_context(user_id)
        # Get response from Gemini
        response = await gemini_client.send_message(
            user_id,
            enhancement_prompt,
            file_manager,
            auth_mode=auth_mode,
            oauth=oauth,
        )

        # Send enhanced prompt
        await update.message.reply_text(
            f"✨ Enhanced Prompt:\n\n{response}\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Original: {original_text}"
        )

        # Copy to PC clipboard if on Windows
        if platform.system() == "Windows":
            try:
                import pyperclip

                pyperclip.copy(response)
                await update.message.reply_text(
                    "📋 Copied enhanced prompt to PC clipboard."
                )

                # Also record for custom command if active
                record_action_if_active(user_id, "clipboard", [response])

            except ImportError:
                logger.warning(
                    "pyperclip not installed. Cannot copy enhanced prompt to clipboard."
                )
            except Exception as e:
                logger.error(f"Failed to copy to clipboard: {e}")

        logger.info(f"Enhanced prompt for user {user_id}")

    except Exception as e:
        await update.message.reply_text(f"❌ Error enhancing prompt: {str(e)}")
        logger.error(f"Error in enhance_command: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages."""
    if not update.effective_user or not update.message or not update.message.text:
        return

    user_id = update.effective_user.id

    # Check if this is a repo selection (before Gemini processing)
    # Deferred imports to avoid circular dependencies between handler modules.
    from pocket_desk_agent.handlers.claude import check_repo_selection, check_model_selection
    from pocket_desk_agent.handlers.build import (
        check_build_selection,
        check_apk_retrieval_selection,
    )
    from pocket_desk_agent.handlers.filesystem import check_getfile_selection
    from pocket_desk_agent.handlers.custom_commands import execute_custom_command

    if await check_repo_selection(update, context):
        return

    if await check_model_selection(update, context):
        return

    # Check if this is part of build workflow
    if await check_build_selection(update, context):
        return

    # Check if this is part of APK retrieval workflow
    if await check_apk_retrieval_selection(update, context):
        return

    # Check if this is part of generic file retrieval workflow
    if await check_getfile_selection(update, context):
        return

    # Check if this is a custom command (starts with /)
    user_message = update.message.text
    if user_message.startswith("/"):
        command_name = user_message[1:].split()[0]  # Remove / and get first word

        # Check if it's a saved custom command
        from pocket_desk_agent.command_registry import get_registry

        registry = get_registry()

        if registry.command_exists(command_name):
            await execute_custom_command(update, context, command_name)
            return

    # Check authentication only after non-Gemini reply workflows are handled.
    if not auth_client.is_authenticated(user_id):
        await update.message.reply_text("Please authenticate first using /start")
        return

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    auth_mode, oauth = _get_gemini_auth_context(user_id)

    # Get response from Gemini with full file manager access
    response = await gemini_client.send_message(
        user_id,
        user_message,
        file_manager,
        tool_runtime={"bot": context.bot, "chat_id": update.effective_chat.id},
        auth_mode=auth_mode,
        oauth=oauth,
    )

    # Send response
    await update.message.reply_text(response)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if update.message.photo and update.message.media_group_id:
        register_media_group_item(
            user_id=user_id,
            media_group_id=str(update.message.media_group_id),
            message_id=update.message.message_id,
            file_id=update.message.photo[-1].file_id,
        )

    if not auth_client.is_authenticated(user_id):
        await update.message.reply_text("Please authenticate first using /start")
        return

    # Get the largest photo
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_bytes = bytes(await photo_file.download_as_bytearray())
    await _reply_with_gemini_image_analysis(
        update=update,
        context=context,
        user_id=user_id,
        image_bytes=photo_bytes,
    )


async def handle_image_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image document messages (including document-based Telegram albums)."""
    if not update.effective_user or not update.message or not update.message.document:
        return

    document = update.message.document
    mime_type = str(document.mime_type or "").lower()
    if not mime_type.startswith("image/"):
        return

    user_id = update.effective_user.id

    if update.message.media_group_id:
        register_media_group_item(
            user_id=user_id,
            media_group_id=str(update.message.media_group_id),
            message_id=update.message.message_id,
            file_id=document.file_id,
        )

    if not auth_client.is_authenticated(user_id):
        await update.message.reply_text("Please authenticate first using /start")
        return

    document_file = await document.get_file()
    image_bytes = bytes(await document_file.download_as_bytearray())
    await _reply_with_gemini_image_analysis(
        update=update,
        context=context,
        user_id=user_id,
        image_bytes=image_bytes,
    )


async def _reply_with_gemini_image_analysis(
    *,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    image_bytes: bytes,
) -> None:
    """Send image bytes + caption to Gemini and relay response to Telegram."""
    if not update.message:
        return

    caption = update.message.caption or "What's in this image?"

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    auth_mode, oauth = _get_gemini_auth_context(user_id)
    response = await gemini_client.send_message_with_image(
        user_id,
        caption,
        image_bytes,
        auth_mode=auth_mode,
        oauth=oauth,
    )
    await update.message.reply_text(response)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global fallback handler for any exception that escapes a handler.

    safe_command catches errors in registered handlers first.
    This handler covers edge cases: polling errors, network blips, etc.
    """
    import traceback

    error = context.error
    logger.error(f"Global error_handler caught: {error}", exc_info=error)

    tb_list = traceback.format_exception(
        None, error, error.__traceback__ if error else None
    )
    tb_string = "".join(tb_list)
    short_error = f"{type(error).__name__}: {str(error)}"

    # Resolve chat id
    chat_id = None

    from telegram import Update as _Update

    if isinstance(update, _Update):
        if update.effective_message:
            chat_id = update.effective_message.chat_id
        elif update.effective_chat:
            chat_id = update.effective_chat.id
    if not chat_id:
        return  # Nothing we can do without a destination

    # --- Notify user (Markdown, then plain-text fallback) ---
    md_msg = (
        f"\U0001f6a8 *An unexpected error occurred!*\n\n"
        f"`{short_error[:500]}`\n\n"
        f"_The bot is still running and ready for your next command._"
    )
    try:
        await context.bot.send_message(
            chat_id=chat_id, text=md_msg, parse_mode="Markdown"
        )
    except Exception:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"\U0001f6a8 Unexpected error: {short_error[:500]}\n\nThe bot is still running.",
            )
        except Exception as last_err:
            logger.error(f"error_handler: could not notify user: {last_err}")
            return

    # Tracebacks are logged locally only — never sent to external services
    # as they may contain file paths, env values, or token fragments.
    logger.debug(f"Full traceback for error_handler:\n{tb_string}")


# File System Commands


def _run_selftest_checks(user_id: int) -> list[tuple[str, bool, str]]:
    """Run non-GUI functional checks and return (name, ok, detail)."""
    checks: list[tuple[str, bool, str]] = []

    try:
        from pocket_desk_agent.command_map import COMMAND_REGISTRY

        required = {
            "remoteinfo",
            "watchnotify",
            "watchstatus",
            "pasteimage",
            "pasteimages",
            "recipecreate",
            "recipeaddwaittext",
            "reciperun",
            "selftest",
        }
        registered = {cmd for cmd, _, _ in COMMAND_REGISTRY}
        missing = sorted(required - registered)
        checks.append(
            (
                "command_registry",
                not missing,
                "all required commands registered"
                if not missing
                else f"missing commands: {', '.join(missing)}",
            )
        )
    except Exception as exc:
        checks.append(("command_registry", False, f"registry check error: {exc}"))

    try:
        bot_commands = get_bot_commands()
        from pocket_desk_agent.command_map import COMMAND_REGISTRY

        ok = len(bot_commands) == len(COMMAND_REGISTRY)
        detail = (
            f"menu size matches registry ({len(bot_commands)})"
            if ok
            else (
                "menu size mismatch: "
                f"menu={len(bot_commands)}, registry={len(COMMAND_REGISTRY)}"
            )
        )
        checks.append(("telegram_menu", ok, detail))
    except Exception as exc:
        checks.append(("telegram_menu", False, f"menu check error: {exc}"))

    try:
        from pocket_desk_agent.handlers.scheduling import parse_screen_notify_request

        cases = [
            (
                "Usage limit reached every 30s in claude cooldown 2m",
                ("Usage limit reached", 30, "claude", 120),
            ),
            (
                "text every 10s on antigravity",
                ("text", 10, "antigravity", 0),
            ),
            (
                "text every 10s",
                ("text", 10, "screen", 0),
            ),
        ]
        parsed_ok = True
        for raw, expected in cases:
            if parse_screen_notify_request(raw) != expected:
                parsed_ok = False
                break
        checks.append(
            (
                "watchnotify_parser",
                parsed_ok,
                "suffix parsing for scope/cooldown works"
                if parsed_ok
                else "unexpected parse result for watchnotify expression",
            )
        )
    except Exception as exc:
        checks.append(
            ("watchnotify_parser", False, f"watchnotify parser check error: {exc}")
        )

    try:
        from pocket_desk_agent.remote.session import ACTIVE_SESSIONS
        from pocket_desk_agent.handlers.remote import sanitized_status

        status = sanitized_status(user_id)
        is_dict = isinstance(status, dict)
        has_active_key = "active" in status if is_dict else False
        active_count = len(ACTIVE_SESSIONS)
        checks.append(
            (
                "remote_status",
                is_dict and has_active_key,
                f"status shape valid; active_sessions={active_count}",
            )
        )
    except Exception as exc:
        checks.append(("remote_status", False, f"remote status check error: {exc}"))

    try:
        from pocket_desk_agent.recipe_registry import get_recipe_registry

        recipes = get_recipe_registry().list_recipes()
        checks.append(
            (
                "recipe_registry",
                True,
                f"recipe registry loaded ({len(recipes)} recipes)",
            )
        )
    except Exception as exc:
        checks.append(
            ("recipe_registry", False, f"recipe registry check error: {exc}")
        )

    return checks


async def selftest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /selftest - run safe non-GUI functional checks."""
    if not update.message or not update.effective_user:
        return

    await update.message.reply_text("Running non-GUI selftest checks...")
    results = _run_selftest_checks(update.effective_user.id)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    status = "PASS" if failed == 0 else "FAIL"

    lines = [f"Selftest: {status} ({passed}/{len(results)} checks passed)", ""]
    for name, ok, detail in results:
        marker = "OK" if ok else "FAIL"
        lines.append(f"- {marker} {name}: {detail}")

    if failed:
        lines.extend(
            [
                "",
                "Note: this command validates non-GUI functional paths only.",
                "Use live commands (/claudeask, /watchnotify, /remoteinfo) for desktop-level validation.",
            ]
        )

    await update.message.reply_text("\n".join(lines))


async def sync_commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sync command - manual sync of bot commands with Telegram."""
    if not update.message:
        return

    await update.message.reply_text("🔄 Syncing bot commands with Telegram...")

    try:
        commands = get_bot_commands()
        await context.bot.set_my_commands(commands)
        await update.message.reply_text(
            "✅ Successfully synced commands with Telegram!"
        )
        logger.info(f"Bot commands manually synced by user {update.effective_user.id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error syncing commands: {str(e)}")
        logger.error(f"Manual sync failed: {e}")


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /update — apply an update and restart when code changed."""
    if not update.message:
        return

    await update.message.reply_text("🔄 Applying update…")

    loop = asyncio.get_running_loop()
    success, msg = await loop.run_in_executor(None, apply_update)

    try:
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(msg)

    if success:
        await update.message.reply_text("♻️ Restarting bot…")
        asyncio.create_task(restart_bot_after_delay())


def get_bot_commands():
    """Return a list of BotCommand objects for the Telegram menu."""
    from pocket_desk_agent.command_map import COMMAND_REGISTRY

    return [BotCommand(cmd, desc) for cmd, _, desc in COMMAND_REGISTRY]


# Antigravity Automation Commands
