"""Task scheduling command handlers."""

import logging
import os
import platform
import time
import asyncio
import datetime
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    PYWINAUTO_AVAILABLE,
    recording_sessions,
    RECORDING_TIMEOUT_SECS,
)
from pocket_desk_agent.scheduler_registry import get_scheduler_registry, ScheduledTask

logger = logging.getLogger(__name__)

def parse_schedule_time(time_str: str) -> Optional[datetime.datetime]:
    """Parse time string into a timezone-aware datetime object (local time)."""
    from datetime import timezone as _tz
    now = datetime.datetime.now().astimezone()  # local timezone-aware
    try:
        # HH:MM
        if ":" in time_str and "-" not in time_str:
            t = datetime.datetime.strptime(time_str, "%H:%M")
            dt = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            if dt < now:
                dt += datetime.timedelta(days=1)
            return dt
        # YYYY-MM-DD HH:MM — assume local timezone
        dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=now.tzinfo)
    except Exception:
        return None


async def claudeschedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudeschedule <time> <prompt> - schedule a message to Claude."""
    if not update.message:
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /claudeschedule <HH:MM> <prompt>\n"
            "Example: /claudeschedule 18:30 run the build script"
        )
        return

    time_str = context.args[0]
    prompt = " ".join(context.args[1:])
    
    execute_at = parse_schedule_time(time_str)
    if not execute_at:
        await update.message.reply_text("❌ Invalid time format. Use HH:MM or YYYY-MM-DD HH:MM")
        return

    registry = get_scheduler_registry()
    task_id = f"claude_{int(time.time())}"
    task = ScheduledTask(
        id=task_id,
        user_id=update.effective_user.id,
        command=f"claude_msg:{prompt}",
        execute_at=execute_at.isoformat()
    )
    registry.add_task(task)

    await update.message.reply_text(
        f"📅 *Task Scheduled!*\n\n"
        f"Prompt: `{prompt}`\n"
        f"Time: `{execute_at.strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
        f"This will be sent to Claude automatically.",
        parse_mode="Markdown"
    )


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /schedule <time> - enter recording mode for commands to run at set time."""
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /schedule <HH:MM>\n"
            "Example: /schedule 21:00\n\n"
            "After this, type commands you want to schedule.\n"
            "They will be SAVED (not executed) and run at the given time.\n"
            "Type /done when finished, or /cancelrecord to abort."
        )
        return

    time_str = context.args[0]
    execute_at = parse_schedule_time(time_str)
    if not execute_at:
        await update.message.reply_text("❌ Invalid time format. Use HH:MM or YYYY-MM-DD HH:MM")
        return

    user_id = update.effective_user.id

    # Check if already recording
    if user_id in recording_sessions:
        await update.message.reply_text(
            "⚠️ You already have an active recording session.\n"
            "Use /done to save it, or /cancelrecord to discard it first."
        )
        return

    # Generate a unique name for this scheduled task
    task_name = f"scheduled_{int(time.time())}"

    recording_sessions[user_id] = {
        "command_name": task_name,
        "actions": [],
        "started_at": time.time(),
        "scheduled_at": execute_at.isoformat()  # marks this as a scheduled session
    }

    timeout_str = f"{RECORDING_TIMEOUT_SECS // 60} minutes"
    await update.message.reply_text(
        f"📅 *Schedule recording started!*\n\n"
        f"Scheduled time: `{execute_at.strftime('%Y-%m-%d %H:%M')}`\n\n"
        f"Now send the commands you want to run at that time.\n"
        f"They will be *saved only* — nothing executes now.\n\n"
        f"Supported commands:\n"
        f"• /hotkey <keys>\n"
        f"• /clipboard <text>\n"
        f"• /smartclick <text>\n"
        f"• /pasteenter\n"
        f"• /typeenter <text>\n\n"
        f"Type /done to save, /cancelrecord to abort.\n"
        f"⏰ Auto-cancels after {timeout_str} of inactivity.",
        parse_mode="Markdown"
    )


async def listschedules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /listschedules - show all pending scheduled tasks."""
    if not update.message:
        return

    user_id = update.effective_user.id
    registry = get_scheduler_registry()
    all_pending = registry.get_all_pending()

    # Filter to this user's tasks only
    user_tasks = [t for t in all_pending if t.get("user_id") == user_id]

    if not user_tasks:
        await update.message.reply_text(
            "📭 *No pending scheduled tasks.*\n\n"
            "Use /schedule to schedule automation commands.\n"
            "Use /claudeschedule to schedule a Claude prompt.",
            parse_mode="Markdown"
        )
        return

    now = datetime.datetime.now()
    lines = ["📅 *Pending Scheduled Tasks*\n"]

    for i, t in enumerate(user_tasks, start=1):
        task_id = t.get("id", "?")
        command = t.get("command", "")
        execute_at_str = t.get("execute_at", "")

        # Determine type
        if command.startswith("claude_msg:"):
            kind = "🤖 Claude"
            detail = command.replace("claude_msg:", "").strip()
            if len(detail) > 50:
                detail = detail[:50] + "…"
        elif command.startswith("custom_cmd:"):
            kind = "⚙️ Automation"
            detail = command.replace("custom_cmd:", "").strip()
        else:
            kind = "⚙️ Automation"
            detail = command.strip()

        # Parse scheduled time
        try:
            execute_at = datetime.datetime.fromisoformat(execute_at_str)
            time_str = execute_at.strftime("%Y-%m-%d %H:%M")
            delta = execute_at - now
            if delta.total_seconds() > 0:
                mins = int(delta.total_seconds() // 60)
                if mins < 60:
                    eta = f"in {mins}m"
                else:
                    eta = f"in {mins // 60}h {mins % 60}m"
            else:
                eta = "due now"
        except Exception:
            time_str = execute_at_str
            eta = "?"

        lines.append(
            f"*{i}.* {kind}\n"
            f"   📌 `{detail}`\n"
            f"   🕒 {time_str} ({eta})\n"
            f"   🆔 `{task_id}`\n"
        )

    lines.append("─────────────────────")
    lines.append("To cancel: `/cancelschedule <id>`")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cancelschedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancelschedule <task_id> - cancel a pending scheduled task."""
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: `/cancelschedule <task_id>`\n\n"
            "Find the task ID with /listschedules.",
            parse_mode="Markdown"
        )
        return

    task_id = context.args[0].strip()
    user_id = update.effective_user.id
    registry = get_scheduler_registry()

    # Verify the task belongs to this user before deleting
    all_pending = registry.get_all_pending()
    task = next((t for t in all_pending if t.get("id") == task_id), None)

    if not task:
        await update.message.reply_text(
            f"❌ No pending task found with ID `{task_id}`.\n\n"
            "Use /listschedules to see your pending tasks.",
            parse_mode="Markdown"
        )
        return

    if task.get("user_id") != user_id:
        await update.message.reply_text("❌ You can only cancel your own scheduled tasks.")
        return

    command = task.get("command", "")
    removed = registry.delete_task(task_id)

    if removed:
        # Describe what was cancelled
        if command.startswith("claude_msg:"):
            desc = f"Claude prompt: `{command.replace('claude_msg:', '').strip()[:60]}`"
        elif command.startswith("custom_cmd:"):
            desc = f"Automation: `{command.replace('custom_cmd:', '').strip()}`"
        else:
            desc = f"`{command.strip()[:60]}`"

        try:
            execute_at = datetime.datetime.fromisoformat(task.get("execute_at", ""))
            time_str = execute_at.strftime("%Y-%m-%d %H:%M")
        except Exception:
            time_str = task.get("execute_at", "?")

        await update.message.reply_text(
            f"✅ *Scheduled task cancelled!*\n\n"
            f"Task: {desc}\n"
            f"Was scheduled for: `{time_str}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Failed to cancel task `{task_id}`.", parse_mode="Markdown")


async def execute_scheduled_task(task: ScheduledTask, bot):
    """Execute a single scheduled task in background."""
    try:
        if task.command.startswith("claude_msg:"):
            prompt = task.command.replace("claude_msg:", "")
            # Need to call the actual logic from claudeask_command but without 'Update'
            # We'll use a modified version
            await bot.send_message(chat_id=task.user_id, text=f"🚀 Executing scheduled Claude prompt: `{prompt}`", parse_mode="Markdown")
            
            # Bring Claude to foreground (restore + activate) WITHOUT opening a new session
            from pocket_desk_agent.handlers.claude import ensure_claude_open
            window = ensure_claude_open()
            if not window:
                raise Exception("Could not open or find Claude desktop app")
            
            window.activate()
            await asyncio.sleep(1.5)
            
            import pyautogui
            import pyperclip
            
            logger.info(f"[Scheduler] Sending Claude prompt on latest session: {prompt[:50]}")
            input_clicked = False

            # Method 1: OCR — find the input placeholder text at the bottom of the window
            try:
                import pytesseract
                if platform.system() == "Windows":
                    for tp in [
                        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
                    ]:
                        if os.path.exists(tp):
                            pytesseract.pytesseract.tesseract_cmd = tp
                            break

                bottom_height = 200
                screenshot = pyautogui.screenshot(region=(
                    window.left,
                    window.top + window.height - bottom_height,
                    window.width,
                    bottom_height,
                ))
                text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
                search_terms = ['reply', 'find', 'todo', 'ask', 'type', 'message', 'chat']
                for i, word in enumerate(text_data['text']):
                    if word and any(t in word.lower() for t in search_terms):
                        x = text_data['left'][i] + (text_data['width'][i] // 2) + window.left
                        y = (text_data['top'][i] + (text_data['height'][i] // 2)
                             + window.top + window.height - bottom_height)
                        pyautogui.click(x, y)
                        await asyncio.sleep(0.5)
                        input_clicked = True
                        break
            except Exception as e:
                logger.warning(f"[Scheduler] OCR method failed: {e}")

            # Method 2: pywinauto Edit control
            if not input_clicked:
                try:
                    from pywinauto import Application
                    app = Application(backend="uia").connect(title_re=".*Claude.*")
                    claude_win = app.window(title_re=".*Claude.*")
                    input_box = claude_win.child_window(control_type="Edit", found_index=0)
                    input_box.click_input()
                    await asyncio.sleep(0.5)
                    input_clicked = True
                except Exception as e:
                    logger.warning(f"[Scheduler] pywinauto method failed: {e}")

            # Method 3: coordinate fallback — bottom-centre of window
            if not input_clicked:
                click_x = window.left + (window.width // 2)
                click_y = window.top + window.height - 35
                pyautogui.click(click_x, click_y)
                await asyncio.sleep(0.5)

            # Paste the prompt and submit
            pyperclip.copy(prompt)
            await asyncio.sleep(0.3)
            pyautogui.hotkey('ctrl', 'v')
            await asyncio.sleep(0.5)
            pyautogui.press('enter')
            
            await bot.send_message(chat_id=task.user_id, text="✅ Scheduled Claude prompt sent successfully.")

            
        elif task.command.startswith("custom_cmd:"):
            cmd_name = task.command.replace("custom_cmd:", "")
            await bot.send_message(chat_id=task.user_id, text=f"🚀 Executing scheduled custom command: `{cmd_name}`", parse_mode="Markdown")
            
            from pocket_desk_agent.command_registry import get_registry
            registry = get_registry()
            actions = registry.get_command(cmd_name)
            
            if not actions:
                raise Exception(f"Command '{cmd_name}' not found")
            
            # Execute actions via the shared helper
            await run_custom_actions(actions)
            
            await bot.send_message(chat_id=task.user_id, text=f"✅ Scheduled command `{cmd_name}` completed.")
            
        return True, None
    except Exception as e:
        logger.error(f"Error executing scheduled task {task.id}: {e}")
        return False, str(e)


async def run_custom_actions(actions):
    """Helper to run a sequence of actions without an update object."""
    import pyautogui
    import pyperclip
    from pocket_desk_agent.automation_utils import find_text_in_image, map_keys_to_pyautogui
    
    for action in actions:
        if action.type == "hotkey":
            if len(action.args) >= 1:
                keys = map_keys_to_pyautogui(action.args[0])
                pyautogui.hotkey(*keys)
                if len(action.args) >= 2: # text to type
                    await asyncio.sleep(0.5)
                    pyautogui.typewrite(action.args[1], interval=0.02)
        elif action.type == "clipboard":
            if action.args:
                pyperclip.copy(action.args[0])
        elif action.type == "findtext":
            # OCR scan — informational only in scheduled context, log the result
            if action.args:
                try:
                    screenshot = pyautogui.screenshot()
                    found = bool(find_text_in_image(screenshot, action.args[0]))
                    logger.info(f"[scheduler] findtext '{action.args[0]}': {'found' if found else 'not found'}")
                except Exception as e:
                    logger.warning(f"[scheduler] findtext failed: {e}")
        elif action.type == "smartclick":
            # OCR click — find text on screen and click the first match
            if action.args:
                try:
                    screenshot = pyautogui.screenshot()
                    matches = find_text_in_image(screenshot, action.args[0])
                    if matches:
                        best_match = matches[0]  # find_text_in_image returns strongest matches first.
                        pyautogui.click(best_match.x, best_match.y)
                        logger.info(
                            f"[scheduler] smartclick '{action.args[0]}' at ({best_match.x},{best_match.y})"
                        )
                    else:
                        logger.info(f"[scheduler] smartclick '{action.args[0]}': not found")
                except Exception as e:
                    logger.warning(f"[scheduler] smartclick failed: {e}")
        elif action.type == "pasteenter":
            pyautogui.hotkey('ctrl', 'v')
            await asyncio.sleep(0.5)
            pyautogui.press('enter')
        elif action.type == "typeenter":
            if action.args:
                pyautogui.typewrite(action.args[0], interval=0.02)
                pyautogui.press('enter')
        
        await asyncio.sleep(0.5)  # Gap between actions

