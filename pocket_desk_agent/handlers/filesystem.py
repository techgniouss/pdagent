"""File system command handlers."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    file_manager,
    record_action_if_active,
)

logger = logging.getLogger(__name__)

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
    
    # Get path argument
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
    
    # Get optional path argument
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
    
    # Get file path argument
    if not context.args:
        await update.message.reply_text("Usage: /cat <file>\nExample: /cat README.md")
        return
    
    path = " ".join(context.args)
    success, message = file_manager.read_file(user_id, path)
    
    if success:
        # Split long messages
        if len(message) > 4000:
            await update.message.reply_text(message[:4000] + "\n\n... (truncated, file too long)")
        else:
            await update.message.reply_text(message)
    else:
        await update.message.reply_text(f"❌ {message}")


async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /find command - search files."""
    if not update.message:
        return
    
    user_id = update.effective_user.id
    
    # Get search pattern
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
    
    # Get path argument
    if not context.args:
        await update.message.reply_text("Usage: /info <path>\nExample: /info README.md")
        return
    
    path = " ".join(context.args)
    success, message = file_manager.get_file_info(user_id, path)
    
    if success:
        await update.message.reply_text(message)
    else:
        await update.message.reply_text(f"❌ {message}")


# System Control Commands

