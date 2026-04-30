"""Inline button callback handlers."""

import logging
import os
import sys
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from pocket_desk_agent.gemini_actions import handle_gemini_confirmation_callback
from pocket_desk_agent.handlers.antigravity import (
    launch_browser,
    launch_claude_cli,
    open_folder_in_vscode,
)
from pocket_desk_agent.handlers.system import perform_system_shutdown
from pocket_desk_agent.scheduler_registry import ScheduledTask, get_scheduler_registry
from pocket_desk_agent.scheduling_utils import parse_iso_datetime
from pocket_desk_agent.handlers._shared import (
    auth_client,
    recording_sessions,
    openfolder_options,
    claudecli_options,
    large_file_upload_state,
    window_switch_options,
    app_selection_options,
    app_forceclose_options,
    build_monitor_state,
    build_screenshot_tasks,
)

logger = logging.getLogger(__name__)


def _parse_app_selection_callback_data(data: str) -> tuple[str | None, str | None, int | None]:
    """Parse app-selection callback payloads, supporting legacy payloads."""
    parts = data.split("_", 3)
    if len(parts) == 4:
        _, request_id, action, raw_index = parts
    elif len(parts) == 3:
        request_id = None
        _, action, raw_index = parts
    else:
        return None, None, None

    try:
        selection = int(raw_index)
    except (TypeError, ValueError):
        return None, None, None
    return request_id, action, selection


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks for confirmations."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    if await handle_gemini_confirmation_callback(update, context):
        return

    if query.data.startswith("appselect_"):
        user_id = update.effective_user.id
        request_id, action, selection = _parse_app_selection_callback_data(query.data)
        if not action or selection is None:
            await query.edit_message_text("Invalid app selection. Please run the command again.")
            return

        state = app_selection_options.get(user_id, {})
        if state.get("request_id") != request_id:
            await query.edit_message_text("That app selection expired. Please run the command again.")
            return
        app_id = state.get("entries", {}).get(selection)
        if not app_id or state.get("action") != action:
            await query.edit_message_text("That app selection expired. Please run the command again.")
            return

        from pocket_desk_agent.app_catalog import get_app_entry_by_id
        from pocket_desk_agent.app_control import close_desktop_app, launch_desktop_app

        entry = get_app_entry_by_id(app_id)
        if not entry:
            await query.edit_message_text("That app could not be found anymore. Please search again.")
            return

        if action == "open":
            success, message = launch_desktop_app(entry)
            await query.edit_message_text(message)
            if success:
                app_selection_options.pop(user_id, None)
            return

        close_result = close_desktop_app(entry, force=False)
        if close_result.requires_force:
            app_selection_options.pop(user_id, None)
            app_forceclose_options[user_id] = {"app_id": entry.app_id}
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Force close", callback_data=f"appforceclose:{entry.app_id}")]]
            )
            await query.edit_message_text(
                f"{close_result.message}\n\n"
                "Tap below to force close the remaining process.",
                reply_markup=keyboard,
            )
            return

        app_selection_options.pop(user_id, None)
        await query.edit_message_text(close_result.message)
        return

    if query.data.startswith("appforceclose"):
        user_id = update.effective_user.id
        state = app_forceclose_options.get(user_id, {})
        requested_app_id = query.data.partition(":")[2] if ":" in query.data else ""
        app_id = requested_app_id or state.get("app_id")
        if not app_id:
            await query.edit_message_text("The force-close request expired. Run /closeapp again.")
            return
        if state.get("app_id") != app_id:
            await query.edit_message_text("The force-close request expired. Run /closeapp again.")
            return

        from pocket_desk_agent.app_catalog import get_app_entry_by_id
        from pocket_desk_agent.app_control import close_desktop_app

        entry = get_app_entry_by_id(app_id)
        if not entry:
            await query.edit_message_text("That app could not be found anymore. Run /closeapp again.")
            return

        result = close_desktop_app(entry, force=True)
        app_forceclose_options.pop(user_id, None)
        await query.edit_message_text(result.message)
        return

    if query.data == "confirm_stopbot":
        await query.edit_message_text("Stopping bot... Goodbye!")
        logger.info("Bot stop requested via Telegram command")
        # Give time for message to send
        await asyncio.sleep(1)
        # Stop the bot gracefully via the application's shutdown mechanism
        asyncio.get_event_loop().call_soon(lambda: sys.exit(0))

    elif query.data == "cancel_stopbot":
        await query.edit_message_text("Bot stop cancelled. Bot is still running.")

    elif query.data == "confirm_shutdown":
        await query.edit_message_text("Shutting down laptop... Goodbye!")
        logger.info("Laptop shutdown requested via Telegram command")
        # Give time for message to send
        await asyncio.sleep(1)

        try:
            perform_system_shutdown()
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")
            # Try to notify user if possible (though connection might be lost)
            try:
                await context.bot.send_message(
                    chat_id=query.message.chat_id, text=f"Shutdown failed: {str(e)}"
                )
            except Exception:
                pass

    elif query.data == "cancel_shutdown":
        await query.edit_message_text("Shutdown cancelled. Laptop is still running.")

    elif query.data.startswith("confirm_sched_shutdown:"):
        try:
            _, raw_user_id, raw_execute_at = query.data.split(":", 2)
            requester_id = int(raw_user_id)
        except (ValueError, TypeError):
            await query.edit_message_text(
                "Invalid shutdown schedule confirmation payload. Please run /scheduleshutdown again."
            )
            return
        if update.effective_user.id != requester_id:
            await query.answer(
                "Only the user who requested this can confirm.", show_alert=True
            )
            return

        execute_at = parse_iso_datetime(raw_execute_at)
        if not execute_at:
            await query.edit_message_text(
                "Could not parse the scheduled time. Please run /scheduleshutdown again."
            )
            return

        task = ScheduledTask(
            id=f"shutdown_{int(time.time() * 1000)}",
            user_id=requester_id,
            command="system_shutdown",
            execute_at=execute_at.isoformat(),
            task_type="system_shutdown",
        )
        get_scheduler_registry().add_task(task)

        await query.edit_message_text(
            "Shutdown schedule saved.\n\n"
            f"Runs at: {execute_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Task ID: {task.id}\n\n"
            "Cancel it any time with /cancelschedule <task_id>."
        )
        logger.info(
            "Scheduled shutdown task %s for user %s at %s",
            task.id,
            requester_id,
            execute_at.isoformat(),
        )

    elif query.data.startswith("cancel_sched_shutdown:"):
        try:
            _, raw_user_id, _ = query.data.split(":", 2)
            requester_id = int(raw_user_id)
        except (ValueError, TypeError):
            await query.edit_message_text(
                "Invalid shutdown schedule cancellation payload. Please run /scheduleshutdown again."
            )
            return
        if update.effective_user.id != requester_id:
            await query.answer(
                "Only the user who requested this can cancel.", show_alert=True
            )
            return
        await query.edit_message_text(
            "Shutdown schedule request cancelled. No task was created."
        )

    # Handle smartclick selections
    elif query.data.startswith("smartclick_"):
        if query.data == "smartclick_cancel":
            await query.edit_message_caption(
                caption="Smart click cancelled.", reply_markup=None
            )
            logger.info("Smart click cancelled by user")
        else:
            # Parse callback data: smartclick_{index}_{x}_{y}
            try:
                parts = query.data.split("_")
                if len(parts) == 4:
                    index = int(parts[1])
                    x = int(parts[2])
                    y = int(parts[3])

                    # Perform the click
                    import pyautogui

                    pyautogui.click(x, y)

                    await query.edit_message_caption(
                        caption=f"Clicked occurrence {index} at ({x}, {y})",
                        reply_markup=None,
                    )
                    logger.info(f"Smart click executed at ({x}, {y})")
                else:
                    await query.answer("Invalid selection data", show_alert=True)
            except Exception as e:
                await query.answer(f"Click failed: {str(e)}", show_alert=True)
                logger.error(f"Error in smartclick callback: {e}", exc_info=True)

    elif query.data.startswith("windowfocus_"):
        user_id = update.effective_user.id
        try:
            selection = int(query.data.replace("windowfocus_", ""))
        except ValueError:
            await query.edit_message_text(
                "Invalid window selection. Run /windows again."
            )
            return

        selected = window_switch_options.get(user_id, {}).get(selection)
        if not selected:
            await query.edit_message_text("Selection expired. Run /windows again.")
            return

        try:
            from pocket_desk_agent.window_utils import activate_window

            if activate_window(selected["handle"]):
                await query.edit_message_text(
                    f"Activated window {selection}: {selected['title']}"
                )
                logger.info(
                    "Activated window %s for user %s from callback: %s",
                    selection,
                    user_id,
                    selected["title"],
                )
            else:
                await query.edit_message_text(
                    "That window could not be activated. It may have been closed. Run /windows again."
                )
        except Exception as e:
            await query.edit_message_text(f"Window activation failed: {str(e)}")
            logger.error(f"Error in windowfocus callback: {e}", exc_info=True)

    # Handle large file upload choices
    elif query.data.startswith("upload_tempfile_") or query.data.startswith(
        "upload_dropbox_"
    ):
        await handle_upload_choice(update, context, query)

    # Handle Dropbox file deletion
    elif query.data.startswith("delete_dropbox_"):
        await handle_dropbox_delete(update, context, query)

    # Handle command overwrite confirmation
    elif query.data.startswith("overwrite_cmd_"):
        command_name = query.data.replace("overwrite_cmd_", "")
        user_id = update.effective_user.id

        # Initialize recording session - include all required fields so
        # record_action_if_active never hits a KeyError on 'started_at' / 'scheduled_at'
        recording_sessions[user_id] = {
            "command_name": command_name,
            "actions": [],
            "started_at": time.time(),
            "scheduled_at": None,
        }

        await query.edit_message_text(
            f"Recording command: {command_name}\n\n"
            "Send automation commands to add to the sequence:\n"
            "- /hotkey <keys> [text]\n"
            "- /clipboard <text>\n"
            "- /findtext <text>\n"
            "- /smartclick <text>\n"
            "- /pasteenter\n"
            "- /typeenter <text>\n\n"
            "When done: /done\n"
            "To cancel: /cancelrecord"
        )
        logger.info(
            f"Started recording session (overwrite) for user {user_id}, command: {command_name}"
        )

    elif query.data == "cancel_overwrite":
        await query.edit_message_text("Cancelled. Command was not overwritten.")

    # Handle command deletion confirmation
    elif query.data.startswith("delete_cmd_"):
        command_name = query.data.replace("delete_cmd_", "")

        from pocket_desk_agent.command_registry import get_registry

        registry = get_registry()

        success = registry.delete_command(command_name)

        if success:
            await query.edit_message_text(
                f"Command '{command_name}' deleted successfully."
            )
            logger.info(f"Deleted command: {command_name}")
        else:
            await query.edit_message_text(
                f"Failed to delete command '{command_name}'.\n"
                "Check bot logs for details."
            )
            logger.error(f"Failed to delete command: {command_name}")

    elif query.data == "cancel_delete":
        await query.edit_message_text("Cancelled. Command was not deleted.")

    # Handle logout confirmation and new login selections
    elif query.data in ("confirm_logout", "cancel_logout") or query.data.startswith(
        "login:"
    ):
        # Delegate to the newly consolidated auth callback handler
        from pocket_desk_agent.handlers.auth import login_button_callback

        await login_button_callback(update, context)

    # Handle Claude CLI selection
    elif query.data.startswith("claudecli_"):
        user_id = update.effective_user.id
        try:
            idx = int(query.data.replace("claudecli_", ""))
            options_data = claudecli_options.get(user_id, {})
            folder_path = options_data.get("paths", {}).get(idx)
            initial_prompt = options_data.get("prompt", "")

            if not folder_path:
                await query.answer(
                    "Selection expired. Run /claudecli again.", show_alert=True
                )
                return

            await query.edit_message_text(
                f"Opening Claude CLI in `{folder_path}`...", parse_mode="Markdown"
            )
            success, message = launch_claude_cli(folder_path, initial_prompt)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message,
                parse_mode="Markdown",
            )
            if success:
                claudecli_options.pop(user_id, None)
        except Exception as e:
            logger.error(f"Error handling claudecli callback: {e}", exc_info=True)
            await query.answer(f"Error: {str(e)}", show_alert=True)

    # Handle open folder selection
    elif query.data.startswith("openfolder_"):
        user_id = update.effective_user.id
        try:
            idx = int(query.data.replace("openfolder_", ""))
            options = openfolder_options.get(user_id, {})
            folder_path = options.get(idx)

            if not folder_path:
                await query.answer(
                    "Selection expired. Run /antigravityopenfolder again.",
                    show_alert=True,
                )
                return

            await query.edit_message_text(
                f"Opening `{folder_path}` in VS Code...", parse_mode="Markdown"
            )
            success, message = open_folder_in_vscode(folder_path)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message,
                parse_mode="Markdown",
            )
            if success:
                openfolder_options.pop(user_id, None)

        except Exception as e:
            await query.answer(f"Error: {str(e)}", show_alert=True)
            logger.error(f"Error in openfolder callback: {e}", exc_info=True)

    # Handle cloudflared auto-install approval from /remote
    elif query.data in ("install_cf_yes", "install_cf_no"):
        from pocket_desk_agent.handlers.remote import (
            handle_install_cloudflared_callback,
        )

        await handle_install_cloudflared_callback(update, context)

    # Handle build screenshot confirmation (Yes/No)
    elif query.data.startswith("build_screenshot_yes_") or query.data.startswith(
        "build_screenshot_no_"
    ):
        try:
            request_key = query.data.rsplit("_", 1)[-1]
        except IndexError:
            await query.edit_message_text("Invalid build screenshot payload.")
            return

        from pocket_desk_agent.handlers.build import (
            monitor_build_window,
            resolve_build_monitor_request,
        )

        state_key, state = resolve_build_monitor_request(request_key)
        if not state:
            await query.edit_message_text(
                "Build monitor state expired. Start a new build to enable screenshots."
            )
            return

        callback_user_id = (
            query.from_user.id
            if getattr(query, "from_user", None)
            else getattr(update.effective_user, "id", None)
        )
        if callback_user_id != state.get("user_id"):
            await query.edit_message_text("This confirmation is for another user.")
            return

        user_id = state["user_id"]

        if query.data.startswith("build_screenshot_yes_"):
            build_monitor_state.pop(state_key, None)

            # Cancel any existing monitor for this user before starting a new one
            old_task = build_screenshot_tasks.get(user_id)
            if old_task and not old_task.done():
                old_task.cancel()
                try:
                    await old_task
                except asyncio.CancelledError:
                    pass
                except Exception as exc:
                    logger.warning(
                        "Cancelled stale build screenshot task for user %s with %s",
                        user_id,
                        exc,
                    )

            task = asyncio.create_task(
                monitor_build_window(
                    context.bot,
                    state["chat_id"],
                    state["user_id"],
                    state["window_title"],
                    state["repo_path"],
                    state["build_type"],
                )
            )
            build_screenshot_tasks[user_id] = task
            await query.edit_message_text(
                "📸 Screenshot monitoring started! I'll send a full-screen capture every minute.\n"
                "Keep the Command Prompt window visible for the best view.\n\n"
                "Use /stopbuildscreenshot to stop at any time."
            )
        else:
            build_monitor_state.pop(state_key, None)
            await query.edit_message_text(
                "No problem! Use /getapk when the build finishes."
            )

    # Handle browser open selection
    elif query.data.startswith("browser_"):
        browser_key = query.data.replace("browser_", "")
        success, message = launch_browser(browser_key)
        await query.edit_message_text(message)
        if not success:
            logger.warning("Browser callback failed for %s: %s", browser_key, message)


async def handle_dropbox_delete(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query
):
    """Handle Dropbox file deletion request."""
    try:
        # Parse callback data: delete_dropbox_{user_id}_{file_path}
        parts = query.data.split("_", 3)
        if len(parts) < 4:
            await query.answer("Invalid delete request", show_alert=True)
            return

        dropbox_path = parts[3]

        await query.edit_message_text(
            f"Deleting file from Dropbox...\n\n"
            f"File: {os.path.basename(dropbox_path)}"
        )

        # Delete from Dropbox
        result = await asyncio.to_thread(delete_from_dropbox, dropbox_path)

        if result["success"]:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"File deleted from Dropbox successfully!\n\n"
                f"File: {os.path.basename(dropbox_path)}",
            )
            logger.info(f"Deleted file from Dropbox: {dropbox_path}")
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Failed to delete file from Dropbox:\n{result['error']}\n\n"
                f"You can delete it manually from the Dropbox app.",
            )
            logger.error(f"Failed to delete from Dropbox: {result['error']}")

    except Exception as e:
        logger.error(f"Error in handle_dropbox_delete: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id, text=f"Error: {str(e)}"
        )


def delete_from_dropbox(dropbox_path: str) -> dict:
    """
    Delete file from Dropbox.

    Returns:
        dict with 'success' and 'error' keys
    """
    try:
        import dropbox
        from dropbox.exceptions import AuthError, ApiError
    except ImportError:
        return {
            "success": False,
            "error": "Dropbox library not installed. Run: pip install dropbox",
        }

    try:
        logger.info(f"Deleting from Dropbox: {dropbox_path}")

        access_token = os.getenv("DROPBOX_ACCESS_TOKEN")
        if not access_token or access_token == "your_dropbox_access_token_here":
            return {"success": False, "error": "Dropbox not configured"}

        dbx = dropbox.Dropbox(access_token)

        try:
            dbx.files_delete_v2(dropbox_path)
            logger.info(f"Successfully deleted: {dropbox_path}")
            return {"success": True}
        except ApiError as e:
            err_str = str(e)
            if "not_found" in err_str or "path/not_found" in err_str:
                return {
                    "success": False,
                    "error": "File not found (may have already been deleted)",
                }
            return {"success": False, "error": f"ApiError: {err_str}"}

    except AuthError as e:
        logger.error(f"Dropbox auth error during delete: {e}")
        return {"success": False, "error": f"Authentication error: {str(e)}"}
    except Exception as e:
        logger.error(f"Dropbox delete exception: {type(e).__name__}: {str(e)}")
        return {"success": False, "error": f"{type(e).__name__}: {str(e)}"}


async def handle_upload_choice(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query
):
    """Handle user's choice for large file upload."""
    try:
        user_id = update.effective_user.id

        # Check if we have state for this user
        if user_id not in large_file_upload_state:
            await query.edit_message_text("Upload session expired. Please try again.")
            return

        # Check if state is too old (10 minutes)
        if time.time() - large_file_upload_state[user_id]["timestamp"] > 600:
            del large_file_upload_state[user_id]
            await query.edit_message_text(
                "Upload session expired (10 minutes). Please try again."
            )
            return

        file_path = large_file_upload_state[user_id]["file_path"]
        file_size_mb = large_file_upload_state[user_id]["file_size_mb"]

        # Determine which service was chosen
        if query.data.startswith("upload_tempfile_"):
            service = "tempfile"
            service_name = "TempFile.org"
            await query.edit_message_text(
                f"Starting TempFile.org upload...\n\n"
                f"Uploading {file_size_mb:.2f} MB..."
            )
        elif query.data.startswith("upload_dropbox_"):
            service = "dropbox"
            service_name = "Dropbox"
            await query.edit_message_text(
                f"Starting Dropbox upload...\n\n"
                f"Uploading {file_size_mb:.2f} MB...\n"
                f"This may take a few minutes for large files..."
            )
        else:
            await query.edit_message_text("Unknown upload service")
            return

        # Upload file
        from pocket_desk_agent.handlers.build import upload_large_file

        upload_result = await asyncio.to_thread(upload_large_file, file_path, service)

        if upload_result["success"]:
            service_used = upload_result.get("service", service_name)
            expiry = upload_result.get("expiry", "Unknown")

            message_text = (
                f"Upload successful!\n\n"
                f"Download your APK:\n{upload_result['link']}\n\n"
                f"Service: {service_used}\n"
                f"Expires: {expiry}\n\n"
                f"Tip: Open the link on your Android device to install directly!\n\n"
                f"Local path (if needed):\n{file_path}"
            )

            # Add delete button for Dropbox uploads
            if service == "dropbox":
                # Store dropbox file path for deletion
                dropbox_file_path = f"/{os.path.basename(file_path)}"

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Delete from Dropbox",
                            callback_data=f"delete_dropbox_{user_id}_{dropbox_file_path}",
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=message_text,
                    reply_markup=reply_markup,
                )
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id, text=message_text
                )

            logger.info(
                f"Uploaded large APK to {service_used}: {file_path} ({file_size_mb:.2f} MB)"
            )
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Upload failed: {upload_result['error']}\n\n"
                f"File location:\n{file_path}\n\n"
                f"Please retrieve it manually or try another upload method.",
            )
            logger.error(f"Upload to {service_name} failed: {upload_result['error']}")

        # Clear state
        del large_file_upload_state[user_id]

    except Exception as e:
        logger.error(f"Error in handle_upload_choice: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id, text=f"Error: {str(e)}"
        )


# Claude Desktop Automation Commands
