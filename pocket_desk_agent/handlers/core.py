"""Core bot command and message handlers."""

import logging
import platform
from telegram import Update, BotCommand
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    auth_client,
    gemini_client,
    file_manager,
    recording_sessions,
    record_action_if_active,
    PYWINAUTO_AVAILABLE,
)
from pocket_desk_agent.updater import get_version_string
from pocket_desk_agent.config import Config

logger = logging.getLogger(__name__)

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
            f"• 🖥️ System control (screenshot, battery, sleep, etc.)\n"
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
            f"• 🖥️ System control (screenshot, battery, sleep, etc.)\n"
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
    
    auth_note = "" if is_authenticated else "\n\n⚠️ Note: Gemini AI commands require authentication. Use /login to enable."
    
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
        "📁 File System Commands:\n"
        "/pwd - Show current directory\n"
        "/cd <path> - Change directory\n"
        "/ls [path] - List directory contents\n"
        "/cat <file> - Read file contents\n"
        "/find <pattern> - Search for files\n"
        "/info <path> - Get file/directory info\n\n"
        "🔌 System Commands:\n"
        "/stopbot - Stop the bot process\n"
        "/shutdown - Shutdown the laptop\n"
        "/sleep - Put PC to sleep (bot stays awake)\n"
        "/wakeup - Info about waking up PC\n"
        "/clauderemote - Run claude remote-control in default repo\n"
        "/stopclaude - Stop claude remote-control\n"
        "/openclaude - Open Claude desktop app\n"
        "/battery - Check battery status\n"
        "/screenshot - Capture current screen\n"
        "/hotkey <keys> [text] - Execute shortcuts & type text\n"
        "/clipboard <text> - Set PC clipboard content\n"
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
        "🎯 Custom Commands:\n"
        "/savecommand <name> - Start recording command sequence\n"
        "/done - Finish recording and save command\n"
        "/cancelrecord - Cancel current recording\n"
        "/listcommands - Show all saved commands\n"
        "/deletecommand <name> - Delete a saved command\n"
        "/<custom_name> - Execute a saved custom command\n\n"
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
        "/antigravitymodel [name] - Select specific AI model\n\n"
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
        await update.message.reply_text(status_text.replace('*', '').replace('`', ''))




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
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
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
        # Get response from Gemini
        response = await gemini_client.send_message(user_id, enhancement_prompt, file_manager)
        
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
                await update.message.reply_text("📋 Copied enhanced prompt to PC clipboard.")
                
                # Also record for custom command if active
                record_action_if_active(user_id, "clipboard", [response])
                
            except ImportError:
                logger.warning("pyperclip not installed. Cannot copy enhanced prompt to clipboard.")
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

    # Check authentication
    if not auth_client.is_authenticated(user_id):
        await update.message.reply_text(
            "Please authenticate first using /start"
        )
        return
    
    # Check if this is a repo selection (before Gemini processing)
    # Deferred imports to avoid circular dependencies between handler modules.
    from pocket_desk_agent.handlers.claude import check_repo_selection
    from pocket_desk_agent.handlers.build import check_build_selection, check_apk_retrieval_selection
    from pocket_desk_agent.handlers.custom_commands import execute_custom_command

    if await check_repo_selection(update, context):
        return

    # Check if this is part of build workflow
    if await check_build_selection(update, context):
        return

    # Check if this is part of APK retrieval workflow
    if await check_apk_retrieval_selection(update, context):
        return

    # Check if this is a custom command (starts with /)
    user_message = update.message.text
    if user_message.startswith('/'):
        command_name = user_message[1:].split()[0]  # Remove / and get first word

        # Check if it's a saved custom command
        from pocket_desk_agent.command_registry import get_registry
        registry = get_registry()

        if registry.command_exists(command_name):
            await execute_custom_command(update, context, command_name)
            return
    
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Get response from Gemini with full file manager access
    response = await gemini_client.send_message(user_id, user_message, file_manager)
    
    # Send response
    await update.message.reply_text(response)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if not auth_client.is_authenticated(user_id):
        await update.message.reply_text("Please authenticate first using /start")
        return
    
    # Get the largest photo
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    # Get caption or default message
    caption = update.message.caption or "What's in this image?"
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Send to Gemini
    response = await gemini_client.send_message_with_image(user_id, caption, bytes(photo_bytes))
    
    await update.message.reply_text(response)




async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global fallback handler for any exception that escapes a handler.
    
    safe_command catches errors in registered handlers first.
    This handler covers edge cases: polling errors, network blips, etc.
    """
    import traceback
    
    error = context.error
    logger.error(f"Global error_handler caught: {error}", exc_info=error)
    
    tb_list = traceback.format_exception(None, error, error.__traceback__ if error else None)
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
        await context.bot.send_message(chat_id=chat_id, text=md_msg, parse_mode="Markdown")
    except Exception:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"\U0001f6a8 Unexpected error: {short_error[:500]}\n\nThe bot is still running."
            )
        except Exception as last_err:
            logger.error(f"error_handler: could not notify user: {last_err}")
            return
    
    # Tracebacks are logged locally only — never sent to external services
    # as they may contain file paths, env values, or token fragments.
    logger.debug(f"Full traceback for error_handler:\n{tb_string}")



# File System Commands



async def sync_commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sync command - manual sync of bot commands with Telegram."""
    if not update.message:
        return
    
    await update.message.reply_text("🔄 Syncing bot commands with Telegram...")
    
    try:
        commands = get_bot_commands()
        await context.bot.set_my_commands(commands)
        await update.message.reply_text("✅ Successfully synced commands with Telegram!")
        logger.info(f"Bot commands manually synced by user {update.effective_user.id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error syncing commands: {str(e)}")
        logger.error(f"Manual sync failed: {e}")





def get_bot_commands():
    """Return a list of BotCommand objects for the Telegram menu."""
    from pocket_desk_agent.command_map import COMMAND_REGISTRY
    return [BotCommand(cmd, desc) for cmd, _, desc in COMMAND_REGISTRY]


# Antigravity Automation Commands


