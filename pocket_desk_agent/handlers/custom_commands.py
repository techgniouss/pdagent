"""Custom command recording and execution handlers."""

import logging
import os
import platform
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    recording_sessions,
    RECORDING_TIMEOUT_SECS,
    PYWINAUTO_AVAILABLE,
    record_action_if_active,
)

logger = logging.getLogger(__name__)

async def savecommand_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /savecommand command - start recording a custom command."""
    if not update.message:
        return
    
    user_id = update.effective_user.id
    
    # Get command name argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /savecommand <command_name>\n\n"
            "Start recording a custom command sequence.\n\n"
            "Examples:\n"
            "/savecommand quick_reply\n"
            "/savecommand auto_login\n\n"
            "Command names can only contain letters, numbers, and underscores."
        )
        return
    
    command_name = context.args[0]
    
    # Validate command name
    from pocket_desk_agent.automation_utils import validate_command_name
    if not validate_command_name(command_name):
        await update.message.reply_text(
            f"❌ Invalid command name: '{command_name}'\n\n"
            "Command names must contain only:\n"
            "• Letters (a-z, A-Z)\n"
            "• Numbers (0-9)\n"
            "• Underscores (_)\n\n"
            "Examples: quick_reply, auto_login, paste_search"
        )
        return
    
    # Check if command already exists
    from pocket_desk_agent.command_registry import get_registry
    registry = get_registry()
    
    if registry.command_exists(command_name):
        # Send confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Overwrite", callback_data=f"overwrite_cmd_{command_name}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_overwrite")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ Command '{command_name}' already exists.\n\n"
            "Do you want to overwrite it?",
            reply_markup=reply_markup
        )
        return
    
    # Initialize recording session with timestamp
    recording_sessions[user_id] = {
        "command_name": command_name,
        "actions": [],
        "started_at": time.time(),
        "scheduled_at": None  # None = savecommand (run on demand)
    }
    
    await update.message.reply_text(
        f"✅ Recording command: {command_name}\n\n"
        "Send automation commands to add to the sequence:\n"
        "• /hotkey <keys> [text]\n"
        "• /clipboard <text>\n"
        "• /findtext <text>\n"
        "• /smartclick <text>\n"
        "• /pasteenter\n"
        "• /typeenter <text>\n\n"
        "When done: /done\n"
        "To cancel: /cancelrecord"
    )
    logger.info(f"Started recording session for user {user_id}, command: {command_name}")


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /done command - finish recording and save custom command."""
    if not update.message:
        return
    
    user_id = update.effective_user.id
    
    # Check if user has active recording session
    if user_id not in recording_sessions:
        await update.message.reply_text(
            "❌ No active recording session.\n\n"
            "Start recording with: /savecommand <command_name>"
        )
        return
    
    session = recording_sessions[user_id]
    command_name = session["command_name"]
    actions = session["actions"]
    scheduled_at = session.get("scheduled_at")  # None = savecommand, ISO str = schedule
    
    # Validate at least one action was recorded
    if len(actions) == 0:
        await update.message.reply_text(
            "❌ No actions recorded.\n\n"
            "Add at least one action before saving.\n"
            "Use /cancelrecord to cancel."
        )
        return
    
    action_summary = "\n".join([
        f"• {action.type}: {' '.join(str(a) for a in action.args) if action.args else '(no args)'}"
        for action in actions
    ])
    
    if scheduled_at:
        # ── SCHEDULED SESSION: save to scheduler registry ──
        from pocket_desk_agent.scheduler_registry import get_scheduler_registry, ScheduledTask
        sched_registry = get_scheduler_registry()
        task_id = f"sched_{int(time.time())}"
        task = ScheduledTask(
            id=task_id,
            user_id=user_id,
            command=f"custom_cmd:{command_name}",
            execute_at=scheduled_at
        )
        
        # Also persist the actions under the temp command name so scheduler can run them
        from pocket_desk_agent.command_registry import get_registry as get_cmd_registry
        get_cmd_registry().add_command(command_name, actions)
        
        sched_registry.add_task(task)
        del recording_sessions[user_id]
        
        import datetime as _dt
        scheduled_str = _dt.datetime.fromisoformat(scheduled_at).strftime('%Y-%m-%d %H:%M')
        await update.message.reply_text(
            f"✅ *Scheduled task saved!*\n\n"
            f"Will execute at: `{scheduled_str}`\n\n"
            f"Actions ({len(actions)}):\n{action_summary}",
            parse_mode="Markdown"
        )
        logger.info(f"Scheduled task '{command_name}' with {len(actions)} actions at {scheduled_at}")
    else:
        # ── SAVECOMMAND SESSION: save to command registry for on-demand use ──
        from pocket_desk_agent.command_registry import get_registry, CommandAction
        registry = get_registry()
        success = registry.add_command(command_name, actions)
        
        if success:
            del recording_sessions[user_id]
            await update.message.reply_text(
                f"✅ Command saved: `{command_name}`\n\n"
                f"Actions: {len(actions)}\n"
                f"{action_summary}\n\n"
                f"Use: /{command_name}",
                parse_mode="Markdown"
            )
            logger.info(f"Saved command '{command_name}' with {len(actions)} actions")
        else:
            await update.message.reply_text(
                "❌ Failed to save command to storage.\n"
                "Check bot logs for details."
            )
            logger.error(f"Failed to save command '{command_name}'")




async def cancelrecord_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancelrecord command - cancel recording session."""
    if not update.message:
        return
    
    user_id = update.effective_user.id
    
    # Check if user has active recording session
    if user_id not in recording_sessions:
        await update.message.reply_text(
            "ℹ️ No active recording session to cancel."
        )
        return
    
    command_name = recording_sessions[user_id]["command_name"]
    del recording_sessions[user_id]
    
    await update.message.reply_text(
        f"❌ Recording cancelled.\n\n"
        f"Command '{command_name}' was not saved."
    )
    logger.info(f"Cancelled recording session for user {user_id}")


async def listcommands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /listcommands command - list all saved custom commands."""
    if not update.message:
        return
    
    from pocket_desk_agent.command_registry import get_registry
    registry = get_registry()
    
    commands = registry.list_commands()
    
    if not commands:
        await update.message.reply_text(
            "📋 No saved commands yet.\n\n"
            "Create one with: /savecommand <command_name>"
        )
        return
    
    # Build command list
    command_list = "\n".join([
        f"{idx}. /{name} ({count} actions)"
        for idx, (name, count) in enumerate(commands.items(), start=1)
    ])
    
    await update.message.reply_text(
        f"📋 Saved Commands ({len(commands)}):\n\n"
        f"{command_list}\n\n"
        f"Use: /<command_name>\n"
        f"Delete: /deletecommand <name>"
    )
    logger.info(f"Listed {len(commands)} saved commands")


async def deletecommand_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deletecommand command - delete a saved custom command."""
    if not update.message:
        return
    
    # Get command name argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /deletecommand <command_name>\n\n"
            "Delete a saved custom command.\n\n"
            "Example:\n"
            "/deletecommand quick_reply\n\n"
            "See all commands: /listcommands"
        )
        return
    
    command_name = context.args[0]
    
    # Check if command exists
    from pocket_desk_agent.command_registry import get_registry
    registry = get_registry()
    
    if not registry.command_exists(command_name):
        await update.message.reply_text(
            f"❌ Command '{command_name}' not found.\n\n"
            "See all commands: /listcommands"
        )
        return
    
    # Send confirmation keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ Delete", callback_data=f"delete_cmd_{command_name}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ Delete command '{command_name}'?\n\n"
        "This action cannot be undone.",
        reply_markup=reply_markup
    )



async def execute_custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command_name: str):
    """Execute a saved custom command sequence."""
    if not update.message:
        return
    
    from pocket_desk_agent.command_registry import get_registry
    import pyautogui
    import pyperclip
    from pocket_desk_agent.automation_utils import (
        map_keys_to_pyautogui,
        press_key,
        send_hotkey,
        write_text,
    )
    
    registry = get_registry()
    actions = registry.get_command(command_name)
    
    if not actions:
        await update.message.reply_text(
            f"❌ Command '{command_name}' not found.\n\n"
            "See all commands: /listcommands"
        )
        return
    
    await update.message.reply_text(f"\U0001f916 Executing: {command_name}")
    
    idx = 0  # initialise so except block can always reference it
    try:
        for idx, action in enumerate(actions, start=1):
            action_type = action.type
            args = action.args
            
            # Execute based on action type
            if action_type == "hotkey":
                if args:
                    mapped_keys = map_keys_to_pyautogui(args[0])
                    
                    if mapped_keys:
                        if len(mapped_keys) == 1:
                            press_key(pyautogui, mapped_keys[0])
                        else:
                            send_hotkey(pyautogui, *mapped_keys)
                            
                        # If there's clipboard text after the hotkey
                        if len(args) > 1:
                            pyperclip.copy(args[1])
                            await asyncio.sleep(0.1)
                            
                        await update.message.reply_text(f"✅ Step {idx}/{len(actions)}: hotkey {args[0]}")
                    
            elif action_type == "clipboard":
                if args:
                    pyperclip.copy(args[0])
                    await update.message.reply_text(f"✅ Step {idx}/{len(actions)}: clipboard copied")
                    
            elif action_type == "findtext":
                if args:
                    search_text = args[0]
                    await update.message.reply_text(f"⏳ Step {idx}/{len(actions)}: finding text '{search_text}'...")
                    
                    from pocket_desk_agent.automation_utils import find_text_in_image
                    screenshot = pyautogui.screenshot()
                    matches = find_text_in_image(screenshot, search_text)
                    
                    if matches:
                        await update.message.reply_text(f"✅ Step {idx}/{len(actions)}: found '{search_text}' at ({matches[0].x}, {matches[0].y})")
                    else:
                        await update.message.reply_text(f"⚠️ Step {idx}/{len(actions)}: '{search_text}' not found")
                    
            elif action_type == "smartclick":
                if args:
                    search_text = args[0]
                    await update.message.reply_text(f"⏳ Step {idx}/{len(actions)}: smart clicking '{search_text}'...")
                    
                    from pocket_desk_agent.automation_utils import find_text_in_image
                    screenshot = pyautogui.screenshot()
                    matches = find_text_in_image(screenshot, search_text)
                    
                    if matches:
                        # Click the first match
                        match = matches[0]
                        pyautogui.click(match.x, match.y)
                        await update.message.reply_text(f"✅ Step {idx}/{len(actions)}: clicked '{search_text}' at ({match.x}, {match.y})")
                    else:
                        await update.message.reply_text(f"❌ Step {idx}/{len(actions)}: '{search_text}' not found for click")
                    
            elif action_type == "pasteenter":
                send_hotkey(pyautogui, "ctrl", "v")
                await asyncio.sleep(0.2)
                press_key(pyautogui, "enter")
                await update.message.reply_text(f"✅ Step {idx}/{len(actions)}: pasteenter")
            
            elif action_type == "typeenter":
                if args:
                    # Check if first argument is underscore (no-space mode)
                    if args[0] == "_":
                        # Join without spaces
                        text_to_type = "".join(args[1:])
                    else:
                        # Keep spaces between words
                        text_to_type = " ".join(args)
                    
                    write_text(pyautogui, text_to_type, interval=0.05)
                    await asyncio.sleep(0.2)
                    press_key(pyautogui, "enter")
                    await update.message.reply_text(f"✅ Step {idx}/{len(actions)}: typeenter {text_to_type}")
            
            elif action_type == "scrollup":
                amount = int(args[0]) if args else 500
                import pygetwindow as gw
                active = gw.getActiveWindow()
                if active:
                    target_x = active.left + int(active.width * 0.90)  # Middle-right end
                    target_y = active.top + int(active.height * 0.5)
                else:
                    screen_width, screen_height = pyautogui.size()
                    target_x, target_y = int(screen_width * 0.90), int(screen_height * 0.5)
                
                pyautogui.moveTo(target_x, target_y, duration=0.1)
                pyautogui.click()  # Ensure chat pane takes window scroll focus
                pyautogui.scroll(amount)
                await update.message.reply_text(f"✅ Step {idx}/{len(actions)}: scrollup {amount}")
                
            elif action_type == "scrolldown":
                amount = int(args[0]) if args else 500
                import pygetwindow as gw
                active = gw.getActiveWindow()
                if active:
                    target_x = active.left + int(active.width * 0.90)  # Middle-right end
                    target_y = active.top + int(active.height * 0.5)
                else:
                    screen_width, screen_height = pyautogui.size()
                    target_x, target_y = int(screen_width * 0.90), int(screen_height * 0.5)
                
                pyautogui.moveTo(target_x, target_y, duration=0.1)
                pyautogui.click()  # Ensure chat pane takes window scroll focus
                pyautogui.scroll(-amount)
                await update.message.reply_text(f"✅ Step {idx}/{len(actions)}: scrolldown {amount}")
            
            # Small delay between actions
            await asyncio.sleep(0.5)
        
        await update.message.reply_text(f"✅ Command '{command_name}' completed successfully!")
        logger.info(f"Executed custom command: {command_name}")
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error at step {idx}/{len(actions)}: {str(e)}\n\n"
            f"Command execution stopped."
        )
        logger.error(f"Error executing custom command '{command_name}': {e}", exc_info=True)



