"""File system command handlers."""

import logging
import time
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    file_manager,
    getfile_retrieval_state,
)
from pocket_desk_agent.handlers.build import send_document_with_upload_fallback

logger = logging.getLogger(__name__)
GETFILE_STATE_TIMEOUT_SECS = 600


def _format_blocked_file_message(path: Path) -> str:
    """Render a consistent refusal for blocked file types."""
    suffix = path.suffix.lower() or "unknown"
    return (
        f"❌ Download blocked for `{path.name}`.\n\n"
        f"Blocked extension: `{suffix}`\n"
        "Blocked types: .exe, .msi, .bat, .cmd, .ps1, .com, .scr"
    )


def _list_getfile_items(folder_path: Path) -> list[Path]:
    """Return visible child items with folders first."""
    items = [
        item
        for item in folder_path.iterdir()
        if not item.name.startswith(".")
    ]
    return sorted(items, key=lambda item: (not item.is_dir(), item.name.lower()))


def _render_getfile_browser(folder_path: Path) -> str:
    """Build the interactive folder browser message for /getfile."""
    try:
        items = _list_getfile_items(folder_path)
    except Exception as exc:
        logger.error("Error reading /getfile folder %s: %s", folder_path, exc, exc_info=True)
        return f"❌ Error reading folder: {exc}"

    message = f"📂 /getfile browser\n\nCurrent path:\n{folder_path}\n\n"

    if not items:
        message += "(empty folder)\n\n"
    else:
        for index, item in enumerate(items, 1):
            if item.is_dir():
                message += f"{index}. 📁 {item.name}/\n"
                continue

            try:
                size_str = file_manager._format_size(item.stat().st_size)
            except Exception:
                size_str = "unknown size"

            label = "🚫" if file_manager.is_blocked_download_file(item) else "📄"
            message += f"{index}. {label} {item.name} ({size_str})\n"

    message += (
        "\nReply with:\n"
        "- A number to open a folder or send a file\n"
        "- `back` to go up one folder\n"
        "- `cancel` to exit"
    )
    return message


async def _send_requested_file(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_path: Path,
) -> None:
    """Send a requested file using the shared Telegram or fallback upload flow."""
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    await update.message.reply_text(
        f"📦 Found file!\n\n"
        f"File: {file_path.name}\n"
        f"Size: {file_size_mb:.2f} MB\n"
        f"Path: {file_path}\n\n"
        f"Preparing to send..."
    )

    await send_document_with_upload_fallback(
        update,
        context,
        str(file_path),
        caption=f"📄 {file_path.name}",
        kind_label="file",
        source="getfile",
        success_message="✅ File sent successfully!",
    )


async def pwd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pwd command - show current directory."""
    if not update.message:
        return

    user_id = update.effective_user.id
    current_dir = file_manager.get_current_dir(user_id)

    await update.message.reply_text(f"📂 Current directory:\n{current_dir}")


async def cd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cd command - change directory."""
    if not update.message:
        return

    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /cd <path>\nExample: /cd MyProject")
        return

    path = " ".join(context.args)
    success, message = file_manager.set_current_dir(user_id, path)

    if success:
        await update.message.reply_text(f"✅ Changed directory to:\n{message}")
    else:
        await update.message.reply_text(f"❌ {message}")


async def ls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ls command - list directory."""
    if not update.message:
        return

    user_id = update.effective_user.id
    path = " ".join(context.args) if context.args else None
    success, message = file_manager.list_directory(user_id, path)

    if success:
        await update.message.reply_text(message)
    else:
        await update.message.reply_text(f"❌ {message}")


async def cat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cat command - read file."""
    if not update.message:
        return

    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /cat <file>\nExample: /cat README.md")
        return

    path = " ".join(context.args)
    success, message = file_manager.read_file(user_id, path)

    if success:
        if len(message) > 4000:
            await update.message.reply_text(message[:4000] + "\n\n... (truncated, file too long)")
        else:
            await update.message.reply_text(message)
    else:
        await update.message.reply_text(f"❌ {message}")


async def getfile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /getfile command - send a file directly or start the browser."""
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id

    if context.args:
        path = " ".join(context.args)
        success, resolved = file_manager.resolve_downloadable_file(user_id, path)
        if not success:
            await update.message.reply_text(f"❌ {resolved}")
            return

        if file_manager.is_blocked_download_file(resolved):
            await update.message.reply_text(_format_blocked_file_message(resolved))
            return

        await _send_requested_file(update, context, resolved)
        return

    current_path = file_manager.get_current_dir(user_id)
    getfile_retrieval_state[user_id] = {
        "current_path": current_path,
        "timestamp": time.time(),
    }
    await update.message.reply_text(_render_getfile_browser(current_path))


async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /find command - search files."""
    if not update.message:
        return

    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /find <pattern>\nExample: /find .py")
        return

    pattern = " ".join(context.args)
    success, message = file_manager.search_files(user_id, pattern)

    if success:
        await update.message.reply_text(message)
    else:
        await update.message.reply_text(f"❌ {message}")


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /info command - get file info."""
    if not update.message:
        return

    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /info <path>\nExample: /info README.md")
        return

    path = " ".join(context.args)
    success, message = file_manager.get_file_info(user_id, path)

    if success:
        await update.message.reply_text(message)
    else:
        await update.message.reply_text(f"❌ {message}")


async def check_getfile_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle reply-based navigation for the /getfile browser."""
    if not update.effective_user or not update.message or not update.message.text:
        return False

    user_id = update.effective_user.id
    state = getfile_retrieval_state.get(user_id)
    if not state:
        return False

    if time.time() - state["timestamp"] > GETFILE_STATE_TIMEOUT_SECS:
        getfile_retrieval_state.pop(user_id, None)
        await update.message.reply_text("❌ /getfile session expired. Run /getfile again.")
        return True

    selection = update.message.text.strip()
    current_path = state["current_path"]

    if selection.lower() == "cancel":
        getfile_retrieval_state.pop(user_id, None)
        await update.message.reply_text("❌ /getfile cancelled.")
        return True

    if selection.lower() == "back":
        parent = current_path.parent
        if not file_manager._is_safe_path(parent):
            await update.message.reply_text(
                "⚠️ Already at the top allowed level for this browser.\nUse `cancel` to exit.",
                parse_mode="Markdown",
            )
            return True

        state["current_path"] = parent
        state["timestamp"] = time.time()
        await update.message.reply_text(_render_getfile_browser(parent))
        return True

    if not selection.isdigit():
        await update.message.reply_text("❌ Please reply with a number, `back`, or `cancel`.", parse_mode="Markdown")
        return True

    try:
        items = _list_getfile_items(current_path)
    except Exception as exc:
        logger.error("Error listing /getfile items in %s: %s", current_path, exc, exc_info=True)
        getfile_retrieval_state.pop(user_id, None)
        await update.message.reply_text(f"❌ Error reading folder: {exc}")
        return True

    index = int(selection)
    if index < 1 or index > len(items):
        await update.message.reply_text(f"❌ Invalid selection. Please choose 1-{len(items)}.")
        return True

    selected_item = items[index - 1]
    state["timestamp"] = time.time()

    if selected_item.is_dir():
        state["current_path"] = selected_item
        await update.message.reply_text(_render_getfile_browser(selected_item))
        return True

    if file_manager.is_blocked_download_file(selected_item):
        await update.message.reply_text(_format_blocked_file_message(selected_item))
        return True

    getfile_retrieval_state.pop(user_id, None)
    await _send_requested_file(update, context, selected_item)
    return True
