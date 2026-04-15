"""Task scheduling command handlers."""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import os
import platform
import time
from typing import Iterable, Optional

from telegram import Update
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import RECORDING_TIMEOUT_SECS, recording_sessions
from pocket_desk_agent.scheduler_registry import ScheduledTask, get_scheduler_registry
from pocket_desk_agent.scheduling_utils import (
    format_duration,
    format_eta,
    get_task_due_at,
    local_now,
    parse_repeat_expression,
    parse_schedule_time as _parse_schedule_time,
    parse_iso_datetime,
)

logger = logging.getLogger(__name__)

REPEAT_MIN_INTERVAL_SECONDS = 15
DEFAULT_PERMISSION_LABELS = ("Allow", "Run", "Approve", "Continue")


def parse_schedule_time(time_str: str) -> Optional[dt.datetime]:
    """Parse schedule strings into local timezone-aware datetimes."""
    return _parse_schedule_time(time_str)


def describe_task(task: ScheduledTask) -> str:
    """Return a compact human-readable summary of a scheduled task."""
    if task.task_type == "permission_watch":
        metadata = task.metadata or {}
        target = str(metadata.get("target", "desktop")).title()
        labels = _normalize_permission_labels(metadata.get("labels"))
        return f"{target} permission watcher ({', '.join(labels)})"

    if task.command.startswith("claude_msg:"):
        prompt = task.command.replace("claude_msg:", "", 1).strip()
        if len(prompt) > 60:
            prompt = f"{prompt[:57]}..."
        return f"Claude prompt: {prompt}"

    if task.command.startswith("custom_cmd:"):
        command_name = task.command.replace("custom_cmd:", "", 1).strip()
        return f"Automation: {command_name}"

    return task.command.strip() or task.id


def cleanup_scheduled_task_artifacts(task: ScheduledTask) -> None:
    """Delete temporary backing commands after a scheduled task finishes."""
    if not task.temporary_command:
        return
    if not task.command.startswith("custom_cmd:"):
        return

    command_name = task.command.replace("custom_cmd:", "", 1).strip()
    if not command_name:
        return

    try:
        from pocket_desk_agent.command_registry import get_registry

        get_registry().delete_command(command_name)
    except Exception as exc:
        logger.warning(
            "Failed to clean up temporary command '%s': %s",
            command_name,
            exc,
        )


async def claudeschedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /claudeschedule <time> <prompt>."""
    if not update.message:
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /claudeschedule <HH:MM> <prompt>\n"
            "Example: /claudeschedule 18:30 run the build script"
        )
        return

    execute_at = parse_schedule_time(context.args[0])
    if not execute_at:
        await update.message.reply_text(
            "Invalid time format. Use HH:MM or YYYY-MM-DD HH:MM."
        )
        return

    prompt = " ".join(context.args[1:])
    task = ScheduledTask(
        id=f"claude_{int(time.time())}",
        user_id=update.effective_user.id,
        command=f"claude_msg:{prompt}",
        execute_at=execute_at.isoformat(),
        task_type="claude_prompt",
    )
    get_scheduler_registry().add_task(task)

    await update.message.reply_text(
        "Claude prompt scheduled.\n\n"
        f"Prompt: {prompt}\n"
        f"Runs at: {execute_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /schedule <time> and record a one-shot automation."""
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /schedule <HH:MM>\n"
            "Example: /schedule 21:00\n\n"
            "After this, send the automation commands you want to run once.\n"
            "Type /done to save or /cancelrecord to abort."
        )
        return

    execute_at = parse_schedule_time(context.args[0])
    if not execute_at:
        await update.message.reply_text(
            "Invalid time format. Use HH:MM or YYYY-MM-DD HH:MM."
        )
        return

    user_id = update.effective_user.id
    if user_id in recording_sessions:
        await update.message.reply_text(
            "You already have an active recording session.\n"
            "Use /done to save it or /cancelrecord to discard it first."
        )
        return

    recording_sessions[user_id] = {
        "command_name": f"scheduled_{int(time.time())}",
        "actions": [],
        "started_at": time.time(),
        "scheduled_at": execute_at.isoformat(),
        "temporary_command": True,
    }

    await update.message.reply_text(
        _recording_prompt(
            heading="Scheduled recording started.",
            timing=f"Runs once at {execute_at.strftime('%Y-%m-%d %H:%M')}.",
        )
    )


async def repeatschedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /repeatschedule every <interval> for <duration>."""
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /repeatschedule every <interval> for <duration>\n"
            "Example: /repeatschedule every 1m for 15m\n\n"
            "After this, send the automation commands to repeat.\n"
            "The first run starts as soon as you save with /done."
        )
        return

    parsed = parse_repeat_expression(context.args)
    if not parsed:
        await update.message.reply_text(
            "Invalid repeat format. Example: /repeatschedule every 1m for 15m"
        )
        return

    interval_seconds, duration = parsed
    if interval_seconds < REPEAT_MIN_INTERVAL_SECONDS:
        await update.message.reply_text(
            f"Repeat interval must be at least {REPEAT_MIN_INTERVAL_SECONDS} seconds."
        )
        return

    user_id = update.effective_user.id
    if user_id in recording_sessions:
        await update.message.reply_text(
            "You already have an active recording session.\n"
            "Use /done to save it or /cancelrecord to discard it first."
        )
        return

    now = local_now()
    repeat_until = now + duration
    recording_sessions[user_id] = {
        "command_name": f"repeat_{int(time.time())}",
        "actions": [],
        "started_at": time.time(),
        "scheduled_at": now.isoformat(),
        "interval_seconds": interval_seconds,
        "repeat_until": repeat_until.isoformat(),
        "temporary_command": True,
    }

    await update.message.reply_text(
        _recording_prompt(
            heading="Repeating recording started.",
            timing=(
                f"Runs every {format_duration(interval_seconds)} until "
                f"{repeat_until.strftime('%Y-%m-%d %H:%M:%S')}."
            ),
        )
    )


async def watchperm_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /watchperm <claude|antigravity> every <interval> for <duration>."""
    if not update.message:
        return

    if platform.system() != "Windows":
        await update.message.reply_text(
            "/watchperm is only available on Windows."
        )
        return

    if len(context.args) < 5:
        await update.message.reply_text(
            "Usage: /watchperm <claude|antigravity> every <interval> for <duration> [labels=Allow,Run]\n"
            "Example: /watchperm claude every 1m for 15m"
        )
        return

    target = context.args[0].strip().lower()
    if target not in {"claude", "antigravity"}:
        await update.message.reply_text(
            "Target must be either 'claude' or 'antigravity'."
        )
        return

    labels = list(DEFAULT_PERMISSION_LABELS)
    repeat_tokens: list[str] = []
    for arg in context.args[1:]:
        if arg.lower().startswith("labels="):
            labels = _normalize_permission_labels(arg.split("=", 1)[1])
        else:
            repeat_tokens.append(arg)

    parsed = parse_repeat_expression(repeat_tokens)
    if not parsed:
        await update.message.reply_text(
            "Invalid repeat format. Example: /watchperm claude every 1m for 15m"
        )
        return

    interval_seconds, duration = parsed
    if interval_seconds < REPEAT_MIN_INTERVAL_SECONDS:
        await update.message.reply_text(
            f"Repeat interval must be at least {REPEAT_MIN_INTERVAL_SECONDS} seconds."
        )
        return

    now = local_now()
    repeat_until = now + duration
    task = ScheduledTask(
        id=f"watch_{target}_{int(time.time())}",
        user_id=update.effective_user.id,
        command=f"permission_watch:{target}",
        execute_at=now.isoformat(),
        task_type="permission_watch",
        interval_seconds=interval_seconds,
        repeat_until=repeat_until.isoformat(),
        next_run_at=now.isoformat(),
        metadata={"target": target, "labels": labels},
    )
    get_scheduler_registry().add_task(task)

    await update.message.reply_text(
        f"{target.title()} permission watcher started.\n\n"
        f"Checks every: {format_duration(interval_seconds)}\n"
        f"Stops at: {repeat_until.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Labels: {', '.join(labels)}\n"
        f"Task ID: {task.id}\n\n"
        "The first scan starts on the next scheduler check. Use /cancelschedule to stop it early."
    )


async def listschedules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /listschedules."""
    if not update.message:
        return

    user_id = update.effective_user.id
    pending = [
        ScheduledTask.from_dict(task)
        for task in get_scheduler_registry().get_all_pending()
        if task.get("user_id") == user_id
    ]

    if not pending:
        await update.message.reply_text(
            "No pending scheduled tasks.\n\n"
            "Use /schedule, /repeatschedule, /watchperm, or /claudeschedule."
        )
        return

    now = local_now()
    lines = ["Pending scheduled tasks:\n"]
    for index, task in enumerate(pending, start=1):
        due_at = get_task_due_at(task.to_dict())
        due_text = due_at.strftime("%Y-%m-%d %H:%M:%S") if due_at else "unknown"
        eta = format_eta(due_at, now=now) if due_at else "unknown"
        lines.append(f"{index}. {describe_task(task)}")
        lines.append(f"   Next run: {due_text} ({eta})")
        if task.interval_seconds and task.repeat_until:
            repeat_until = parse_iso_datetime(task.repeat_until)
            if repeat_until:
                lines.append(
                    "   Repeats: every "
                    f"{format_duration(task.interval_seconds)} until "
                    f"{repeat_until.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            lines.append(f"   Runs completed: {task.run_count}")
        lines.append(f"   Task ID: {task.id}")
        lines.append("")

    lines.append("Cancel a task with: /cancelschedule <task_id>")
    await update.message.reply_text("\n".join(lines).strip())


async def cancelschedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancelschedule <task_id>."""
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /cancelschedule <task_id>\n\n"
            "Find the task ID with /listschedules."
        )
        return

    task_id = context.args[0].strip()
    registry = get_scheduler_registry()
    existing = next(
        (
            ScheduledTask.from_dict(task)
            for task in registry.get_all_pending()
            if task.get("id") == task_id
        ),
        None,
    )

    if not existing:
        await update.message.reply_text(
            f"No pending task found with ID {task_id}."
        )
        return

    if existing.user_id != update.effective_user.id:
        await update.message.reply_text("You can only cancel your own scheduled tasks.")
        return

    removed = registry.pop_task(task_id)
    if not removed:
        await update.message.reply_text(f"Failed to cancel task {task_id}.")
        return

    cleanup_scheduled_task_artifacts(removed)
    await update.message.reply_text(
        "Scheduled task cancelled.\n\n"
        f"Task: {describe_task(removed)}"
    )


async def execute_scheduled_task(task: ScheduledTask, bot) -> tuple[bool, Optional[str]]:
    """Execute a single scheduled task."""
    try:
        if task.task_type == "permission_watch" or task.command.startswith("permission_watch:"):
            return await _execute_permission_watch(task, bot)

        if task.command.startswith("claude_msg:"):
            return await _execute_scheduled_claude_prompt(task, bot)

        if task.command.startswith("custom_cmd:"):
            return await _execute_scheduled_custom_command(task, bot)

        return False, f"Unsupported scheduled task: {task.command}"
    except Exception as exc:
        logger.error("Error executing scheduled task %s: %s", task.id, exc, exc_info=True)
        return False, str(exc)


async def run_custom_actions(actions: Iterable) -> None:
    """Run a sequence of saved custom actions without a Telegram update object."""
    import pyautogui
    import pyperclip

    from pocket_desk_agent.automation_utils import (
        find_text_in_image,
        map_keys_to_pyautogui,
        press_key,
        send_hotkey,
        typewrite_text,
    )

    for action in actions:
        if action.type == "hotkey":
            if action.args:
                keys = map_keys_to_pyautogui(action.args[0])
                if not keys:
                    logger.warning("Scheduled hotkey skipped because no keys were parsed")
                elif len(keys) == 1:
                    press_key(pyautogui, keys[0])
                else:
                    send_hotkey(pyautogui, *keys)

                if len(action.args) > 1:
                    await asyncio.sleep(0.5)
                    typewrite_text(pyautogui, action.args[1], interval=0.02)

        elif action.type == "clipboard":
            if action.args:
                pyperclip.copy(action.args[0])

        elif action.type == "findtext":
            if action.args:
                try:
                    matches = find_text_in_image(pyautogui.screenshot(), action.args[0])
                    logger.info(
                        "[scheduler] findtext '%s': %s",
                        action.args[0],
                        "found" if matches else "not found",
                    )
                except Exception as exc:
                    logger.warning("[scheduler] findtext failed: %s", exc)

        elif action.type == "smartclick":
            if action.args:
                try:
                    matches = find_text_in_image(pyautogui.screenshot(), action.args[0])
                    if matches:
                        pyautogui.click(matches[0].x, matches[0].y)
                        logger.info(
                            "[scheduler] smartclick '%s' at (%s, %s)",
                            action.args[0],
                            matches[0].x,
                            matches[0].y,
                        )
                    else:
                        logger.info("[scheduler] smartclick '%s': not found", action.args[0])
                except Exception as exc:
                    logger.warning("[scheduler] smartclick failed: %s", exc)

        elif action.type == "clicktext":
            if len(action.args) >= 2:
                pyautogui.click(int(action.args[0]), int(action.args[1]))

        elif action.type == "pasteenter":
            send_hotkey(pyautogui, "ctrl", "v")
            await asyncio.sleep(0.3)
            press_key(pyautogui, "enter")

        elif action.type == "typeenter":
            if action.args:
                if action.args[0] == "_":
                    text_to_type = "".join(action.args[1:])
                else:
                    text_to_type = " ".join(action.args)
                typewrite_text(pyautogui, text_to_type, interval=0.02)
                press_key(pyautogui, "enter")

        elif action.type == "scrollup":
            amount = int(action.args[0]) if action.args else 500
            _scroll_active_window(pyautogui, amount)

        elif action.type == "scrolldown":
            amount = int(action.args[0]) if action.args else 500
            _scroll_active_window(pyautogui, -amount)

        await asyncio.sleep(0.5)


async def _execute_scheduled_claude_prompt(task: ScheduledTask, bot) -> tuple[bool, Optional[str]]:
    prompt = task.command.replace("claude_msg:", "", 1)
    await bot.send_message(
        chat_id=task.user_id,
        text=f"Executing scheduled Claude prompt:\n{prompt}",
    )

    from pocket_desk_agent.handlers.claude import ensure_claude_open

    window = ensure_claude_open()
    if not window:
        raise RuntimeError("Could not open or find the Claude desktop app")

    try:
        window.activate()
    except Exception:
        pass
    await asyncio.sleep(1.5)

    import pyautogui
    import pyperclip

    input_clicked = False
    try:
        import pytesseract

        if platform.system() == "Windows":
            for candidate in (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            ):
                if candidate and os.path.exists(candidate):
                    pytesseract.pytesseract.tesseract_cmd = candidate
                    break

        bottom_height = 200
        screenshot = pyautogui.screenshot(
            region=(
                window.left,
                window.top + window.height - bottom_height,
                window.width,
                bottom_height,
            )
        )
        text_data = pytesseract.image_to_data(
            screenshot,
            output_type=pytesseract.Output.DICT,
        )
        for index, word in enumerate(text_data["text"]):
            if word and any(term in word.lower() for term in ("reply", "find", "todo", "ask", "type", "message", "chat")):
                x = text_data["left"][index] + (text_data["width"][index] // 2) + window.left
                y = (
                    text_data["top"][index]
                    + (text_data["height"][index] // 2)
                    + window.top
                    + window.height
                    - bottom_height
                )
                pyautogui.click(x, y)
                await asyncio.sleep(0.5)
                input_clicked = True
                break
    except Exception as exc:
        logger.warning("Scheduled Claude OCR input detection failed: %s", exc)

    if not input_clicked:
        try:
            from pywinauto import Application

            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
            input_box = claude_window.child_window(control_type="Edit", found_index=0)
            input_box.click_input()
            await asyncio.sleep(0.5)
            input_clicked = True
        except Exception as exc:
            logger.warning("Scheduled Claude pywinauto input detection failed: %s", exc)

    if not input_clicked:
        pyautogui.click(window.left + (window.width // 2), window.top + window.height - 35)
        await asyncio.sleep(0.5)

    pyperclip.copy(prompt)
    await asyncio.sleep(0.3)
    pyautogui.hotkey("ctrl", "v")
    await asyncio.sleep(0.5)
    pyautogui.press("enter")

    await bot.send_message(
        chat_id=task.user_id,
        text="Scheduled Claude prompt sent successfully.",
    )
    return True, None


async def _execute_scheduled_custom_command(task: ScheduledTask, bot) -> tuple[bool, Optional[str]]:
    command_name = task.command.replace("custom_cmd:", "", 1)
    await bot.send_message(
        chat_id=task.user_id,
        text=f"Executing scheduled automation: {command_name}",
    )

    from pocket_desk_agent.command_registry import get_registry

    actions = get_registry().get_command(command_name)
    if not actions:
        raise RuntimeError(f"Command '{command_name}' not found")

    await run_custom_actions(actions)

    if not task.interval_seconds:
        await bot.send_message(
            chat_id=task.user_id,
            text=f"Scheduled automation '{command_name}' completed.",
        )
    return True, None


async def _execute_permission_watch(task: ScheduledTask, bot) -> tuple[bool, Optional[str]]:
    if platform.system() != "Windows":
        return False, "Permission watcher is only available on Windows."

    metadata = task.metadata or {}
    target = str(metadata.get("target", "")).lower()
    labels = _normalize_permission_labels(metadata.get("labels"))
    if target not in {"claude", "antigravity"}:
        return False, "Permission watcher target must be 'claude' or 'antigravity'."

    try:
        import pyautogui
        from pocket_desk_agent.automation_utils import find_text_in_image
    except ImportError as exc:
        return False, f"Missing dependency: {exc}"

    window = _find_permission_target_window(target)
    if not window:
        logger.info("Permission watcher skipped because %s window was not found", target)
        return True, None

    await _activate_window(window)

    region = _window_region(window)
    if not region:
        logger.info("Permission watcher skipped because %s window bounds were invalid", target)
        return True, None

    screenshot = pyautogui.screenshot(region=region)
    candidates = []
    for label in labels:
        try:
            matches = find_text_in_image(screenshot, label)
        except Exception as exc:
            logger.warning(
                "Permission watcher OCR failed for label '%s' on %s: %s",
                label,
                target,
                exc,
            )
            continue

        for match in matches:
            if match.confidence < 87.0:
                continue
            candidates.append(
                {
                    "label": label,
                    "x": region[0] + match.x,
                    "y": region[1] + match.y,
                    "confidence": match.confidence,
                }
            )

    if not candidates:
        logger.info("Permission watcher found no approval prompts in %s", target)
        return True, None

    if len(candidates) != 1:
        logger.info(
            "Permission watcher skipped %s because OCR found %s possible buttons",
            target,
            len(candidates),
        )
        return True, None

    candidate = candidates[0]
    pyautogui.click(candidate["x"], candidate["y"])
    await bot.send_message(
        chat_id=task.user_id,
        text=(
            f"{target.title()} permission watcher clicked '{candidate['label']}' "
            f"at ({candidate['x']}, {candidate['y']})."
        ),
    )
    logger.info(
        "Permission watcher clicked '%s' in %s at (%s, %s)",
        candidate["label"],
        target,
        candidate["x"],
        candidate["y"],
    )
    return True, None


def _recording_prompt(*, heading: str, timing: str) -> str:
    timeout_minutes = RECORDING_TIMEOUT_SECS // 60
    return (
        f"{heading}\n\n"
        f"{timing}\n\n"
        "Now send the commands you want to record.\n"
        "Nothing executes until you finish with /done.\n\n"
        "Supported recorded actions:\n"
        "- /hotkey <keys>\n"
        "- /clipboard <text>\n"
        "- /findtext <text>\n"
        "- /smartclick <text>\n"
        "- /clicktext <x> <y>\n"
        "- /pasteenter\n"
        "- /typeenter <text>\n"
        "- /scrollup [amount]\n"
        "- /scrolldown [amount]\n\n"
        f"Use /done to save or /cancelrecord to abort. Auto-cancels after {timeout_minutes} minutes."
    )


def _normalize_permission_labels(raw_labels) -> list[str]:
    if isinstance(raw_labels, str):
        source = raw_labels.split(",")
    elif isinstance(raw_labels, (list, tuple, set)):
        source = raw_labels
    else:
        source = DEFAULT_PERMISSION_LABELS

    labels: list[str] = []
    seen: set[str] = set()
    for item in source:
        label = str(item).strip()
        if not label:
            continue
        normalized = label.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        labels.append(label)
    return labels or list(DEFAULT_PERMISSION_LABELS)


def _find_permission_target_window(target: str):
    if target == "claude":
        from pocket_desk_agent.handlers.claude import find_claude_window

        return find_claude_window()

    from pocket_desk_agent.handlers.antigravity import find_antigravity_window

    return find_antigravity_window()


async def _activate_window(window) -> None:
    try:
        if getattr(window, "isMinimized", False):
            window.restore()
            await asyncio.sleep(0.4)
        window.activate()
        await asyncio.sleep(0.3)
    except Exception as exc:
        logger.debug("Window activation skipped: %s", exc)


def _window_region(window) -> Optional[tuple[int, int, int, int]]:
    try:
        left = max(0, int(window.left))
        top = max(0, int(window.top))
        width = max(1, int(window.width))
        height = max(1, int(window.height))
    except Exception:
        return None
    return left, top, width, height


def _scroll_active_window(pyautogui, amount: int) -> None:
    try:
        import pygetwindow as gw

        active_window = gw.getActiveWindow()
    except Exception:
        active_window = None

    if active_window:
        target_x = active_window.left + int(active_window.width * 0.90)
        target_y = active_window.top + int(active_window.height * 0.5)
    else:
        screen_width, screen_height = pyautogui.size()
        target_x = int(screen_width * 0.90)
        target_y = int(screen_height * 0.5)

    pyautogui.moveTo(target_x, target_y, duration=0.1)
    pyautogui.click()
    pyautogui.scroll(amount)
