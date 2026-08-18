"""Smart plug and auto battery management command handlers.

Commands:
    /autobattery on|off|status|high <n>|low <n>|interval <n>
        Enable/disable the auto battery manager or adjust thresholds.

    /smartplug on|off|status|toggle
        Direct manual control of the smart plug (Qubo Smart Plug 10A).

The auto battery manager runs as a background asyncio task.  It polls the
laptop battery every BATTERY_POLL_INTERVAL seconds (default 300 s / 5 min)
and automatically turns the smart plug on or off to keep the battery within
the configured thresholds.

State is persisted to ~/.pdagent/autobattery.json so monitoring resumes after
a bot restart when it was previously enabled.
"""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
from typing import Any, Optional

import psutil
from telegram import Update
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import safe_command

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_STATE_FILE = pathlib.Path.home() / ".pdagent" / "autobattery.json"

# ── Module-level singleton state ──────────────────────────────────────────────
# All fields are guarded by asyncio (single-threaded event loop); no lock needed.
_enabled: bool = False
_high_threshold: int = 85      # plug OFF above this % while charging
_low_threshold: int = 15       # plug ON below this % while not charging
_poll_interval: int = 300      # seconds between battery checks

_monitor_task: Optional[asyncio.Task] = None
_plug: Optional[Any] = None        # QuboClient instance (created lazily)
_user_id: Optional[int] = None     # Telegram user to notify
_bot: Optional[Any] = None         # telegram.Bot instance for notifications

_last_plug_action: Optional[str] = None  # "on" | "off" — avoid duplicate sends


# ── Persistence ───────────────────────────────────────────────────────────────

def _load_state() -> None:
    """Load persisted auto-battery state from disk (called at import time)."""
    global _enabled, _high_threshold, _low_threshold, _poll_interval, _user_id
    try:
        if _STATE_FILE.exists():
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            _enabled = bool(data.get("enabled", False))
            _high_threshold = int(data.get("high_threshold", 85))
            _low_threshold = int(data.get("low_threshold", 15))
            _poll_interval = int(data.get("poll_interval", 300))
            raw_uid = data.get("user_id")
            _user_id = int(raw_uid) if raw_uid is not None else None
    except Exception as exc:
        logger.warning("Failed to load autobattery state: %s", exc)


def _save_state() -> None:
    """Persist current auto-battery state to disk."""
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(
            json.dumps(
                {
                    "enabled": _enabled,
                    "high_threshold": _high_threshold,
                    "low_threshold": _low_threshold,
                    "poll_interval": _poll_interval,
                    "user_id": _user_id,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Failed to save autobattery state: %s", exc)


# Load state at import time so the manager can auto-start after a restart.
_load_state()


# ── Smart plug client helpers ─────────────────────────────────────────────────

def _get_plug_credentials() -> tuple[str, str, str]:
    """Return (username, password, device_name) from Config, raising if missing."""
    from pocket_desk_agent.config import Config
    username = getattr(Config, "QUBO_USERNAME", "").strip()
    password = getattr(Config, "QUBO_PASSWORD", "").strip()
    device_name = getattr(Config, "QUBO_DEVICE_NAME", "Smart Plug 10A").strip()
    if not username or not password:
        raise RuntimeError(
            "QUBO_USERNAME and QUBO_PASSWORD must be set in your "
            "~/.pdagent/config to use the smart plug.\n\n"
            "Add these lines:\n"
            "QUBO_USERNAME=your-qubo-email\n"
            "QUBO_PASSWORD=your-qubo-password\n"
            "QUBO_DEVICE_NAME=Smart Plug 10A"
        )
    return username, password, device_name


async def _get_or_create_plug() -> Any:
    """Return the module-level QuboClient, creating and starting it if needed."""
    global _plug
    from pocket_desk_agent.qubo_client import QuboClient

    if _plug is not None:
        return _plug

    username, password, device_name = _get_plug_credentials()
    client = QuboClient(username=username, password=password, device_name=device_name)
    await client.start()
    _plug = client
    return _plug


async def _stop_plug() -> None:
    """Stop and discard the module-level QuboClient."""
    global _plug
    if _plug is not None:
        try:
            await _plug.stop()
        except Exception as exc:
            logger.warning("Error stopping smart plug client: %s", exc)
        _plug = None


# ── Background battery manager loop ──────────────────────────────────────────

async def _battery_manager_loop() -> None:
    """Monitor battery and control smart plug automatically.

    Rules:
      - Battery plugged AND percent >= high_threshold  →  turn plug OFF
      - Battery NOT plugged AND percent <= low_threshold → turn plug ON
      - Only acts when the plug state needs to change (avoids spamming).
      - Errors reaching the plug are logged as warnings; the loop keeps running.
    """
    global _last_plug_action

    logger.info(
        "Auto battery manager started (high=%d%%, low=%d%%, interval=%ds)",
        _high_threshold,
        _low_threshold,
        _poll_interval,
    )

    try:
        plug = await _get_or_create_plug()
    except Exception as exc:
        msg = (
            f"❌ Auto battery manager failed to connect to the smart plug:\n{exc}\n\n"
            "Use /autobattery off to disable, then fix the credentials and re-enable."
        )
        logger.error("Auto battery manager startup failed: %s", exc)
        if _bot and _user_id:
            try:
                await _bot.send_message(chat_id=_user_id, text=msg)
            except Exception:
                pass
        return

    # Seed _last_plug_action from the current physical plug state so we don't
    # send a redundant command on the first poll cycle.
    try:
        initial_status = await plug.get_status()
        initial_state = initial_status.get("state")
        if initial_state == "ON":
            _last_plug_action = "on"
        elif initial_state == "OFF":
            _last_plug_action = "off"
        # If UNKNOWN, leave as None so the first cycle evaluates normally.
        logger.info("Auto battery manager: initial plug state is %s", initial_state)
    except Exception as exc:
        logger.warning("Auto battery manager: could not read initial plug state: %s", exc)

    while True:
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                logger.debug("Auto battery manager: no battery detected, sleeping")
                await asyncio.sleep(_poll_interval)
                continue

            percent = battery.percent
            plugged = battery.power_plugged

            # Determine desired plug action
            desired_action: Optional[str] = None
            if plugged and percent >= _high_threshold:
                desired_action = "off"
            elif not plugged and percent <= _low_threshold:
                desired_action = "on"

            if desired_action and desired_action != _last_plug_action:
                # State needs to change — send the command
                turn_on = desired_action == "on"
                try:
                    result = await plug.set_power(turn_on)
                    confirmed = result.get("confirmed", False)
                    state_str = result.get("state")

                    if turn_on:
                        emoji = "🔌"
                        action_text = "turned ON"
                        reason = f"battery at {percent:.0f}% and not charging"
                    else:
                        emoji = "🔋"
                        action_text = "turned OFF"
                        reason = f"battery at {percent:.0f}% while charging"

                    status_note = (
                        "✅ confirmed"
                        if confirmed
                        else f"⚠️ unconfirmed (reported state: {state_str})"
                    )

                    msg = (
                        f"{emoji} Auto battery: smart plug {action_text}\n"
                        f"• Reason: {reason}\n"
                        f"• Status: {status_note}"
                    )
                    logger.info(
                        "Auto battery: plug %s (battery=%.0f%%, plugged=%s)",
                        action_text,
                        percent,
                        plugged,
                    )
                    # Only record the action after a successful send.
                    _last_plug_action = desired_action
                    if _bot and _user_id:
                        try:
                            await _bot.send_message(chat_id=_user_id, text=msg)
                        except Exception as notify_exc:
                            logger.warning("Failed to notify user: %s", notify_exc)

                except Exception as exc:
                    logger.warning(
                        "Auto battery: set_power(%s) failed: %s", turn_on, exc
                    )
                    # Do NOT update _last_plug_action so we retry next cycle.

        except asyncio.CancelledError:
            logger.info("Auto battery manager loop cancelled")
            raise
        except Exception as exc:
            logger.warning(
                "Auto battery manager poll error: %s", exc, exc_info=True
            )

        await asyncio.sleep(_poll_interval)


async def _start_monitor(user_id: int, bot: Any) -> None:
    """Start the background battery monitor task."""
    global _monitor_task, _user_id, _bot, _last_plug_action
    _user_id = user_id
    _bot = bot
    _last_plug_action = None  # reset so the loop re-seeds from real plug state
    if _monitor_task and not _monitor_task.done():
        _monitor_task.cancel()
        try:
            await _monitor_task
        except asyncio.CancelledError:
            pass
    _monitor_task = asyncio.create_task(
        _battery_manager_loop(), name="auto-battery-manager"
    )


async def _stop_monitor() -> None:
    """Cancel the background battery monitor task."""
    global _monitor_task, _last_plug_action
    if _monitor_task and not _monitor_task.done():
        _monitor_task.cancel()
        try:
            await _monitor_task
        except asyncio.CancelledError:
            pass
    _monitor_task = None
    _last_plug_action = None


# ── Auto-start on bot boot (if previously enabled) ───────────────────────────

async def resume_if_enabled(bot: Any) -> None:
    """Called by main.py at startup to resume monitoring if it was previously on.

    Pass the telegram.Bot instance so the manager can send notifications.
    """
    if _enabled and _user_id:
        logger.info(
            "Auto battery manager was previously enabled — resuming for user %s",
            _user_id,
        )
        await _start_monitor(_user_id, bot)


# ── /autobattery command ──────────────────────────────────────────────────────

@safe_command
async def autobattery_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /autobattery — enable/disable or configure the battery manager.

    Usage:
        /autobattery on           Enable auto battery management
        /autobattery off          Disable auto battery management
        /autobattery status       Show current state and battery info
        /autobattery high <n>     Set high threshold (plug turns off above n%)
        /autobattery low <n>      Set low threshold (plug turns on below n%)
        /autobattery interval <n> Set poll interval in seconds (min 30)
    """
    global _enabled, _high_threshold, _low_threshold, _poll_interval, _user_id

    if not update.message or not update.effective_user:
        return

    args = context.args or []
    sub = args[0].lower() if args else "status"

    # ── status ────────────────────────────────────────────────────────────────
    if sub == "status":
        battery = psutil.sensors_battery()
        bat_str = "No battery detected"
        if battery is not None:
            charging = "🔌 Charging" if battery.power_plugged else "🔋 Not Charging"
            bat_str = f"{battery.percent:.0f}% — {charging}"

        state_str = "🟢 ENABLED" if _enabled else "🔴 DISABLED"
        task_alive = _monitor_task is not None and not _monitor_task.done()
        task_str = "running" if task_alive else "not running"

        await update.message.reply_text(
            f"🔋 Auto Battery Manager\n\n"
            f"• Status: {state_str} ({task_str})\n"
            f"• Battery: {bat_str}\n"
            f"• High threshold: {_high_threshold}% (plug OFF above this while charging)\n"
            f"• Low threshold: {_low_threshold}% (plug ON below this while discharging)\n"
            f"• Poll interval: {_poll_interval}s "
            f"({_poll_interval // 60}m {_poll_interval % 60}s)\n\n"
            f"Commands:\n"
            f"/autobattery on — enable\n"
            f"/autobattery off — disable\n"
            f"/autobattery high 90 — set high threshold\n"
            f"/autobattery low 20 — set low threshold\n"
            f"/autobattery interval 300 — set poll interval"
        )
        return

    # ── on ────────────────────────────────────────────────────────────────────
    if sub == "on":
        try:
            _get_plug_credentials()  # validate config before enabling
        except RuntimeError as exc:
            await update.message.reply_text(f"❌ Cannot enable: {exc}")
            return

        _enabled = True
        _user_id = update.effective_user.id   # FIX: set before _save_state()
        _save_state()
        await _start_monitor(update.effective_user.id, context.bot)
        await update.message.reply_text(
            "✅ Auto battery manager enabled\n\n"
            f"• High threshold: {_high_threshold}% → plug will turn OFF\n"
            f"• Low threshold: {_low_threshold}% → plug will turn ON\n"
            f"• Polling every {_poll_interval}s\n\n"
            "Use /autobattery status to check at any time."
        )
        logger.info(
            "Auto battery manager enabled by user %s", update.effective_user.id
        )
        return

    # ── off ───────────────────────────────────────────────────────────────────
    if sub == "off":
        _enabled = False
        _save_state()
        await _stop_monitor()
        await _stop_plug()
        await update.message.reply_text(
            "🔴 Auto battery manager disabled.\n"
            "The smart plug will no longer be controlled automatically."
        )
        logger.info(
            "Auto battery manager disabled by user %s", update.effective_user.id
        )
        return

    # ── high <n> ──────────────────────────────────────────────────────────────
    if sub == "high":
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: /autobattery high <percentage>\nExample: /autobattery high 90"
            )
            return
        try:
            val = int(args[1])
            if not (1 <= val <= 100):
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "❌ Please provide a valid percentage (1–100)."
            )
            return
        if val <= _low_threshold:
            await update.message.reply_text(
                f"❌ High threshold ({val}%) must be greater than the "
                f"low threshold ({_low_threshold}%)."
            )
            return
        _high_threshold = val
        _save_state()
        await update.message.reply_text(
            f"✅ High threshold set to {_high_threshold}%.\n"
            f"Plug will turn OFF when battery reaches {_high_threshold}% while charging."
        )
        return

    # ── low <n> ───────────────────────────────────────────────────────────────
    if sub == "low":
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: /autobattery low <percentage>\nExample: /autobattery low 20"
            )
            return
        try:
            val = int(args[1])
            if not (0 <= val <= 99):
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "❌ Please provide a valid percentage (0–99)."
            )
            return
        if val >= _high_threshold:
            await update.message.reply_text(
                f"❌ Low threshold ({val}%) must be less than the "
                f"high threshold ({_high_threshold}%)."
            )
            return
        _low_threshold = val
        _save_state()
        await update.message.reply_text(
            f"✅ Low threshold set to {_low_threshold}%.\n"
            f"Plug will turn ON when battery drops to {_low_threshold}% while not charging."
        )
        return

    # ── interval <n> ──────────────────────────────────────────────────────────
    if sub == "interval":
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: /autobattery interval <seconds>\n"
                "Example: /autobattery interval 300"
            )
            return
        try:
            val = int(args[1])
            if val < 30:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "❌ Interval must be a number of seconds (minimum 30)."
            )
            return
        _poll_interval = val
        _save_state()
        await update.message.reply_text(
            f"✅ Poll interval set to {_poll_interval}s "
            f"({_poll_interval // 60}m {_poll_interval % 60}s).\n"
            "Run /autobattery off then /autobattery on to apply the new interval."
        )
        return

    # ── unrecognised subcommand ────────────────────────────────────────────────
    await update.message.reply_text(
        "❓ Unknown subcommand. Usage:\n\n"
        "/autobattery on — enable\n"
        "/autobattery off — disable\n"
        "/autobattery status — show state\n"
        "/autobattery high <n> — set high threshold\n"
        "/autobattery low <n> — set low threshold\n"
        "/autobattery interval <n> — set poll interval (seconds)"
    )


# ── /smartplug command ────────────────────────────────────────────────────────

@safe_command
async def smartplug_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /smartplug — direct manual control of the smart plug.

    Usage:
        /smartplug on      Turn plug on
        /smartplug off     Turn plug off
        /smartplug status  Show plug connection/power state
        /smartplug toggle  Toggle plug state
    """
    if not update.message:
        return

    args = context.args or []
    sub = args[0].lower() if args else "status"

    if sub not in ("on", "off", "status", "toggle"):
        await update.message.reply_text(
            "❓ Unknown subcommand. Usage:\n\n"
            "/smartplug on — turn plug on\n"
            "/smartplug off — turn plug off\n"
            "/smartplug status — show plug state\n"
            "/smartplug toggle — toggle plug"
        )
        return

    await update.message.reply_text("⏳ Connecting to smart plug…")

    try:
        plug = await _get_or_create_plug()
    except RuntimeError as exc:
        await update.message.reply_text(f"❌ Cannot connect to smart plug:\n{exc}")
        return
    except Exception as exc:
        logger.error("Error creating smart plug client: %s", exc, exc_info=True)
        await update.message.reply_text(
            f"❌ Failed to connect to smart plug: {exc}"
        )
        return

    if sub == "status":
        try:
            info = await plug.get_status()
        except Exception as exc:
            await update.message.reply_text(
                f"❌ Error fetching smart plug status: {exc}"
            )
            return
        connected_str = "🟢 Connected" if info.get("connected") else "🔴 Disconnected"
        state_str = info.get("state", "UNKNOWN")
        state_emoji = (
            "🔌" if state_str == "ON"
            else ("🔴" if state_str == "OFF" else "❓")
        )
        device_str = info.get("device") or "Unknown"
        await update.message.reply_text(
            f"🔌 Smart Plug\n\n"
            f"• Device: {device_str}\n"
            f"• MQTT: {connected_str}\n"
            f"• Power: {state_emoji} {state_str}"
        )
        return

    if sub == "toggle":
        try:
            current = await plug.get_status()
        except Exception as exc:
            await update.message.reply_text(f"❌ Error reading plug state: {exc}")
            return
        current_state = current.get("state")
        if current_state not in ("ON", "OFF"):
            await update.message.reply_text(
                f"❌ Current plug state is unknown ({current_state}). "
                "Use /smartplug on or /smartplug off explicitly."
            )
            return
        sub = "off" if current_state == "ON" else "on"

    turn_on = sub == "on"
    try:
        result = await plug.set_power(turn_on)
    except Exception as exc:
        logger.error("Smartplug set_power(%s) error: %s", turn_on, exc, exc_info=True)
        await update.message.reply_text(f"❌ Smart plug command failed: {exc}")
        return

    confirmed = result.get("confirmed", False)
    final_state = result.get("state")
    action = "ON" if turn_on else "OFF"
    emoji = "🔌" if turn_on else "🔴"

    if confirmed:
        await update.message.reply_text(
            f"{emoji} Smart plug turned {action} ✅\n"
            f"Physical state confirmed."
        )
    else:
        await update.message.reply_text(
            f"{emoji} Smart plug {action} command sent\n"
            f"⚠️ State confirmation timed out (reported state: {final_state}).\n"
            "Check /smartplug status to verify."
        )
    logger.info(
        "Smart plug manual %s by user %s (confirmed=%s)",
        action,
        update.effective_user.id if update.effective_user else "?",
        confirmed,
    )
