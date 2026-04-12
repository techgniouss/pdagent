"""System control command handlers."""

import logging
import os
import sys
import platform
import subprocess
import asyncio
import time
import io
import psutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    PYWINAUTO_AVAILABLE,
    record_action_if_active,
)

logger = logging.getLogger(__name__)

async def stopbot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stopbot command - stop the bot process with confirmation."""
    if not update.message:
        return
    
    # Create confirmation keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, stop bot", callback_data="confirm_stopbot"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_stopbot")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ Are you sure you want to stop the bot?\n\n"
        "This will terminate the bot process on your laptop.",
        reply_markup=reply_markup
    )


async def shutdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /shutdown command - shutdown laptop with confirmation."""
    if not update.message:
        return
    
    # Create confirmation keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, shutdown", callback_data="confirm_shutdown"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_shutdown")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ Are you sure you want to shutdown your laptop?\n\n"
        "This will power off the computer completely.",
        reply_markup=reply_markup
    )




async def battery_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /battery command - check battery status."""
    if not update.message:
        return
    
    try:
        battery = psutil.sensors_battery()
        
        if battery is None:
            await update.message.reply_text(
                "ℹ️ No battery detected.\n"
                "This device might be a desktop or battery info is unavailable."
            )
            return
        
        # Get battery percentage
        percent = battery.percent
        
        # Get charging status
        plugged = battery.power_plugged
        charging_status = "🔌 Charging" if plugged else "🔋 Not Charging"
        
        # Get time remaining (if available)
        time_left = battery.secsleft
        
        # Format time remaining
        if time_left == psutil.POWER_TIME_UNLIMITED:
            time_str = "Unlimited (plugged in)"
        elif time_left == psutil.POWER_TIME_UNKNOWN:
            time_str = "Unknown"
        else:
            hours = time_left // 3600
            minutes = (time_left % 3600) // 60
            time_str = f"{hours}h {minutes}m"
        
        # Choose battery emoji based on level
        if percent >= 60:
            battery_emoji = "🔋"
        elif percent >= 30:
            battery_emoji = "🪫"
        else:
            battery_emoji = "🪫🔴"
        
        # Build status message
        status_msg = (
            f"{battery_emoji} Battery Status\n\n"
            f"• Level: {percent}%\n"
            f"• Status: {charging_status}\n"
            f"• Time remaining: {time_str}"
        )
        
        await update.message.reply_text(status_msg)
        logger.info(f"Battery status requested: {percent}%, plugged={plugged}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting battery status: {str(e)}")
        logger.error(f"Error getting battery status: {e}")


async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /screenshot command - capture current screen."""
    if not update.message:
        return
    
    await update.message.reply_text("📸 Capturing screenshot...")
    
    try:
        import pyautogui
        img = pyautogui.screenshot()
        screenshot = io.BytesIO()
        img.save(screenshot, format='PNG')
        screenshot.seek(0)

        if screenshot:
            # Send screenshot to user
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=screenshot,
                caption="📸 Current Screen Capture"
            )
            logger.info("Screenshot captured and sent successfully")
        else:
            await update.message.reply_text("❌ Failed to capture screenshot.")
            logger.error("Screenshot capture returned None")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error capturing screenshot: {str(e)}")
        logger.error(f"Error in screenshot_command: {e}", exc_info=True)




async def sleep_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sleep command - put PC to sleep."""
    if not update.message:
        return
    
    await update.message.reply_text(
        "💤 Putting PC to sleep...\n\n"
        "⚠️ Note: The bot will stay awake and running.\n"
        "You can still send commands via Telegram."
    )
    
    try:
        system = platform.system()
        
        if system == "Windows":
            # Use rundll32 to sleep (suspend to RAM)
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
            logger.info("PC sleep command executed")
            
            # Send confirmation after a delay
            await asyncio.sleep(2)
            await update.message.reply_text("✅ PC is going to sleep. Bot remains active.")
            
        elif system == "Darwin":  # macOS
            subprocess.Popen(["pmset", "sleepnow"])
            await update.message.reply_text("✅ Mac is going to sleep. Bot remains active.")
            logger.info("Mac sleep command executed")
            
        elif system == "Linux":
            subprocess.Popen(["systemctl", "suspend"])
            await update.message.reply_text("✅ PC is going to sleep. Bot remains active.")
            logger.info("Linux sleep command executed")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error putting PC to sleep: {str(e)}")
        logger.error(f"Error in sleep_command: {e}")


async def wakeup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /wakeup command - wake up PC (requires Wake-on-LAN setup)."""
    if not update.message:
        return
    
    await update.message.reply_text(
        "⚠️ Wake-up command received.\n\n"
        "Note: Remote wake-up requires:\n"
        "1. Wake-on-LAN (WoL) enabled in BIOS\n"
        "2. Network adapter configured for WoL\n"
        "3. PC connected via Ethernet (not WiFi)\n\n"
        "Since the bot is running on the same PC, it's already awake!\n\n"
        "For true remote wake-up, you need a separate device to send WoL packets."
    )
    
    logger.info("Wakeup command called (PC already awake since bot is running)")


async def hotkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /hotkey command - execute keyboard shortcuts."""
    if not update.message:
        return
    
    # Get hotkey argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /hotkey <keys> [text]\n\n"
            "Execute keyboard shortcuts/hotkeys.\n\n"
            "Examples:\n"
            "/hotkey alt+tab - Switch windows\n"
            "/hotkey ctrl+c - Copy\n"
            "/hotkey ctrl+v - Paste\n"
            "/hotkey ctrl+shift+esc - Task Manager\n"
            "/hotkey win+d - Show desktop\n"
            "/hotkey alt+f4 - Close window\n\n"
            "With text (copies to clipboard first):\n"
            "/hotkey ctrl+v Hello World - Paste 'Hello World'\n"
            "/hotkey type This is my text - Type text directly\n\n"
            "Supported keys:\n"
            "• Modifiers: ctrl, alt, shift, win\n"
            "• Letters: a-z\n"
            "• Numbers: 0-9\n"
            "• Special: tab, esc, enter, space, delete, backspace\n"
            "• Function: f1-f12\n"
            "• Arrows: up, down, left, right\n"
            "• type - Type text directly (no hotkey)"
        )
        return
    
    # Check if first arg is "type" for direct typing
    if context.args[0].lower() == 'type':
        if len(context.args) < 2:
            await update.message.reply_text("❌ Please provide text to type.\nExample: /hotkey type Hello World")
            return
        
        text_to_type = " ".join(context.args[1:])
        await update.message.reply_text(f"⌨️ Typing: {text_to_type[:50]}{'...' if len(text_to_type) > 50 else ''}")
        
        try:
            import pyautogui
            pyautogui.write(text_to_type, interval=0.05)
            await update.message.reply_text(f"✅ Typed: {text_to_type[:100]}{'...' if len(text_to_type) > 100 else ''}")
            logger.info(f"Typed text: {text_to_type[:50]}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error typing text: {str(e)}")
            logger.error(f"Error typing text: {e}")
        return
    
    # Parse hotkey and optional text
    hotkey_str = context.args[0].lower()
    clipboard_text = None
    
    # Check if there's text after the hotkey
    if len(context.args) > 1:
        clipboard_text = " ".join(context.args[1:])
    
    await update.message.reply_text(f"\u2328\ufe0f Executing hotkey: {hotkey_str}")
    
    try:
        import pyautogui
        import pyperclip
        
        # ── Recording check FIRST — if recording, save & skip execution ──
        user_id = update.effective_user.id
        if record_action_if_active(user_id, "hotkey", [hotkey_str] + ([clipboard_text] if clipboard_text else [])):
            await update.message.reply_text(f"\U0001f4dd Recorded: `/hotkey {hotkey_str}`", parse_mode="Markdown")
            return

        # If text provided, copy to clipboard first
        if clipboard_text:
            pyperclip.copy(clipboard_text)
            logger.info(f"Copied to clipboard: {clipboard_text[:50]}")
            await update.message.reply_text(f"\U0001f4cb Copied to clipboard: {clipboard_text[:100]}{'...' if len(clipboard_text) > 100 else ''}")
            time.sleep(0.2)
        
        # Map the keys using utility function
        from pocket_desk_agent.automation_utils import map_keys_to_pyautogui
        mapped_keys = map_keys_to_pyautogui(hotkey_str)
        
        if not mapped_keys:
            await update.message.reply_text("\u274c No valid keys provided")
            return
        
        logger.info(f"Executing hotkey: {mapped_keys}")
        
        # Execute the hotkey
        if len(mapped_keys) == 1:
            pyautogui.press(mapped_keys[0])
        else:
            pyautogui.hotkey(*mapped_keys)
        
        time.sleep(0.3)
        
        result_msg = f"\u2705 Hotkey executed: {hotkey_str}"
        if clipboard_text:
            result_msg += f"\n\U0001f4cb Text ready to paste"
        
        await update.message.reply_text(result_msg)
        logger.info(f"Successfully executed hotkey: {hotkey_str}")
        
    except Exception as e:
        await update.message.reply_text(f"\u274c Error executing hotkey: {str(e)}")
        logger.error(f"Error in hotkey_command: {e}", exc_info=True)




async def clipboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clipboard command - set clipboard content."""
    if not update.message:
        return
    
    # Get text argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /clipboard <text>\n\n"
            "Copy text to clipboard.\n\n"
            "Examples:\n"
            "/clipboard Hello World\n"
            "/clipboard https://example.com\n"
            "/clipboard This is a long text that I want to paste\n\n"
            "After setting clipboard, use:\n"
            "• /hotkey ctrl+v to paste\n"
            "• Or manually paste with Ctrl+V"
        )
        return
    
    text = " ".join(context.args)
    
    try:
        import pyperclip

        # ── Recording check FIRST — if recording, save & skip execution ──
        user_id = update.effective_user.id
        if record_action_if_active(user_id, "clipboard", [text]):
            await update.message.reply_text("\U0001f4dd Recorded: `/clipboard` (text saved for later)")
            return

        pyperclip.copy(text)
        time.sleep(0.2)
        
        # Verify it was copied
        if pyperclip.paste() == text:
            await update.message.reply_text(
                f"\u2705 Copied to clipboard!\n\n"
                f"Text: {text[:200]}{'...' if len(text) > 200 else ''}\n\n"
                f"Use /hotkey ctrl+v to paste"
            )
            logger.info(f"Copied to clipboard: {text[:50]}")
        else:
            await update.message.reply_text("\u26a0\ufe0f Text copied but verification failed")
        
    except Exception as e:
        await update.message.reply_text(f"\u274c Error copying to clipboard: {str(e)}")
        logger.error(f"Error in clipboard_command: {e}", exc_info=True)


async def viewclipboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /viewclipboard command - get current clipboard content."""
    if not update.message:
        return
    
    try:
        import pyperclip
        content = pyperclip.paste()
        if content:
            if len(content) > 4000:
                content = content[:3900] + "\n...(truncated)"
            
            await update.message.reply_text(f"📋 Current PC Clipboard Content:\n\n{content}")
            logger.info(f"Clipboard viewed by user {update.effective_user.id}")
        else:
            await update.message.reply_text("📋 PC Clipboard is empty.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading clipboard: {str(e)}")
        logger.error(f"Error in viewclipboard_command: {e}")



