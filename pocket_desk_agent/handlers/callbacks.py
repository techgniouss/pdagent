"""Inline button callback handlers."""

import logging
import os
import sys
import platform
import subprocess
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from pocket_desk_agent.gemini_actions import handle_gemini_confirmation_callback
from pocket_desk_agent.handlers._shared import (
    auth_client,
    recording_sessions,
    openfolder_options,
    claudecli_options,
    large_file_upload_state,
    window_switch_options,
)

logger = logging.getLogger(__name__)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks for confirmations."""
    query = update.callback_query
    if not query or not query.data:
        return
    
    await query.answer()

    if await handle_gemini_confirmation_callback(update, context):
        return
    
    if query.data == "confirm_stopbot":
        await query.edit_message_text("🛑 Stopping bot... Goodbye!")
        logger.info("Bot stop requested via Telegram command")
        # Give time for message to send
        await asyncio.sleep(1)
        # Stop the bot gracefully via the application's shutdown mechanism
        asyncio.get_event_loop().call_soon(lambda: sys.exit(0))
    
    elif query.data == "cancel_stopbot":
        await query.edit_message_text("✅ Bot stop cancelled. Bot is still running.")
    
    elif query.data == "confirm_shutdown":
        await query.edit_message_text("💤 Shutting down laptop... Goodbye!")
        logger.info("Laptop shutdown requested via Telegram command")
        # Give time for message to send
        await asyncio.sleep(1)
        
        # Execute shutdown command based on OS
        system = platform.system()
        try:
            if system == "Windows":
                # Windows shutdown - no special permissions needed
                subprocess.run(["shutdown", "/s", "/t", "5"], check=True)
            elif system == "Linux":
                # Linux - try without sudo first, then with sudo
                try:
                    subprocess.run(["shutdown", "-h", "now"], check=True)
                except subprocess.CalledProcessError:
                    subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
            elif system == "Darwin":  # macOS
                # macOS - try without sudo first, then with sudo
                try:
                    subprocess.run(["shutdown", "-h", "now"], check=True)
                except subprocess.CalledProcessError:
                    subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")
            # Try to notify user if possible (though connection might be lost)
            try:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"❌ Shutdown failed: {str(e)}"
                )
            except Exception:
                pass
    
    elif query.data == "cancel_shutdown":
        await query.edit_message_text("✅ Shutdown cancelled. Laptop is still running.")
    
    # Handle smartclick selections
    elif query.data.startswith("smartclick_"):
        if query.data == "smartclick_cancel":
            await query.edit_message_caption(
                caption="❌ Smart click cancelled.",
                reply_markup=None
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
                        caption=f"✅ Clicked occurrence {index} at ({x}, {y})",
                        reply_markup=None
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
            await query.edit_message_text("Invalid window selection. Run /windows again.")
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
    elif query.data.startswith("upload_tempfile_") or query.data.startswith("upload_dropbox_"):
        await handle_upload_choice(update, context, query)
    
    # Handle Dropbox file deletion
    elif query.data.startswith("delete_dropbox_"):
        await handle_dropbox_delete(update, context, query)
    
    # Handle command overwrite confirmation
    elif query.data.startswith("overwrite_cmd_"):
        command_name = query.data.replace("overwrite_cmd_", "")
        user_id = update.effective_user.id
        
        # Initialize recording session — include all required fields so
        # record_action_if_active never hits a KeyError on 'started_at' / 'scheduled_at'
        recording_sessions[user_id] = {
            "command_name": command_name,
            "actions": [],
            "started_at": time.time(),
            "scheduled_at": None,
        }
        
        await query.edit_message_text(
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
        logger.info(f"Started recording session (overwrite) for user {user_id}, command: {command_name}")
    
    elif query.data == "cancel_overwrite":
        await query.edit_message_text("✅ Cancelled. Command was not overwritten.")
    
    # Handle command deletion confirmation
    elif query.data.startswith("delete_cmd_"):
        command_name = query.data.replace("delete_cmd_", "")
        
        from pocket_desk_agent.command_registry import get_registry
        registry = get_registry()
        
        success = registry.delete_command(command_name)
        
        if success:
            await query.edit_message_text(
                f"✅ Command '{command_name}' deleted successfully."
            )
            logger.info(f"Deleted command: {command_name}")
        else:
            await query.edit_message_text(
                f"❌ Failed to delete command '{command_name}'.\n"
                "Check bot logs for details."
            )
            logger.error(f"Failed to delete command: {command_name}")
    
    elif query.data == "cancel_delete":
        await query.edit_message_text("✅ Cancelled. Command was not deleted.")
    
    # Handle logout confirmation and new login selections
    elif query.data in ("confirm_logout", "cancel_logout") or query.data.startswith("login:"):
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
                await query.answer("Selection expired. Run /claudecli again.", show_alert=True)
                return

            await query.edit_message_text(f"💻 Opening Claude CLI in `{folder_path}`...", parse_mode="Markdown")

            if platform.system() == "Windows":
                import threading

                def launch_and_type():
                    try:
                        normalized_path = os.path.normpath(folder_path)
                        # Launch Claude Code via cmd — use list form with cwd to
                        # avoid shell injection via folder names containing quotes
                        # or shell metacharacters.
                        process = subprocess.Popen(
                            ["cmd.exe", "/k", "title Claude CLI && claude"],
                            cwd=normalized_path,
                        )

                        if initial_prompt:
                            import pygetwindow as gw
                            import pyautogui
                            
                            window_found = False
                            # Retry loop up to 10 seconds to wait for Claude CLI to load
                            for _ in range(10):
                                time.sleep(1.0)
                                for w in gw.getAllWindows():
                                    if "Claude CLI" in w.title and w.visible:
                                        try:
                                            if w.isMinimized:
                                                w.restore()
                                            w.activate()
                                            time.sleep(0.5)
                                            window_found = True
                                            break
                                        except Exception:
                                            pass
                                if window_found:
                                    break
                            
                            if window_found:
                                time.sleep(1.5)  # additional sleep for the node process to be interactive
                                pyautogui.write(initial_prompt, interval=0.01)
                                pyautogui.press('enter')
                            else:
                                logger.error("Could not find Claude CLI window to type prompt into")
                    except Exception as e:
                        logger.error(f"Error in launch_and_type: {e}", exc_info=True)

                threading.Thread(target=launch_and_type, daemon=True).start()
                
                await update.effective_chat.send_message(
                    f"✅ Claude CLI opened!\n\n"
                    f"Repository: {folder_path}"
                )
            else:
                await query.answer("This feature is currently only supported on Windows.", show_alert=True)
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
                await query.answer("Selection expired. Run /antigravityopenfolder again.", show_alert=True)
                return

            await query.edit_message_text(f"📂 Opening `{folder_path}` in VS Code...", parse_mode="Markdown")

            if platform.system() == "Windows":
                import pyautogui
                import pygetwindow as gw
                import pyperclip

                # Find VS Code window robustly
                vscode_window = None
                for w in gw.getAllWindows():
                    try:
                        if "visual studio code" in w.title.lower() and w.visible:
                            vscode_window = w
                            break
                    except Exception:
                        continue

                if vscode_window:
                    # Bring VS Code to front
                    try:
                        if vscode_window.isMinimized:
                            vscode_window.restore()
                            time.sleep(0.5)
                        vscode_window.activate()
                    except Exception:
                        pass
                    time.sleep(0.8)

                    # Use Ctrl+K then Ctrl+O to open folder dialog
                    pyautogui.hotkey('ctrl', 'k')
                    time.sleep(0.3)
                    pyautogui.hotkey('ctrl', 'o')
                    time.sleep(1.2)  # Wait for the file dialog to open

                    # Paste path and confirm
                    pyperclip.copy(folder_path)
                    pyautogui.hotkey('ctrl', 'a')  # Select all existing text first
                    time.sleep(0.2)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.6)
                    pyautogui.press('enter')
                    time.sleep(0.5)

                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"✅ VS Code opening folder:\n`{folder_path}`\n\n_Used Ctrl+K → Ctrl+O shortcut_",
                        parse_mode="Markdown"
                    )
                else:
                    # VS Code not open — open it directly with the folder
                    subprocess.Popen(["code", folder_path])
                    time.sleep(2)
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"✅ Launched VS Code with folder:\n`{folder_path}`",
                        parse_mode="Markdown"
                    )
            else:
                subprocess.Popen(["code", folder_path], shell=True)
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"✅ Opened in VS Code:\n`{folder_path}`",
                    parse_mode="Markdown"
                )

            openfolder_options.pop(user_id, None)

        except Exception as e:
            await query.answer(f"Error: {str(e)}", show_alert=True)
            logger.error(f"Error in openfolder callback: {e}", exc_info=True)


    # Handle browser open selection
    elif query.data.startswith("browser_"):
        browser_key = query.data.replace("browser_", "")

        BROWSER_PATHS = {
            "edge": [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ],
            "chrome": [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ],
            "firefox": [
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
            ],
            "brave": [
                os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            ],
        }

        BROWSER_LABELS = {
            "edge": "Microsoft Edge",
            "chrome": "Google Chrome",
            "firefox": "Mozilla Firefox",
            "brave": "Brave",
        }

        paths = BROWSER_PATHS.get(browser_key, [])
        exe_path = next((p for p in paths if os.path.exists(p)), None)

        if not exe_path:
            # fallback: try launching by name via shell
            fallback_names = {"edge": "msedge", "chrome": "chrome", "firefox": "firefox", "brave": "brave"}
            exe_path = fallback_names.get(browser_key, browser_key)
            use_shell = True
        else:
            use_shell = False

        label = BROWSER_LABELS.get(browser_key, browser_key.title())

        try:
            if use_shell:
                subprocess.Popen(
                    f'start /max "" {exe_path}',
                    shell=True
                )
            else:
                subprocess.Popen(
                    [exe_path, "--start-maximized"],
                    shell=False
                )

            await query.edit_message_text(
                f"✅ Opening *{label}* in maximized window...",
                parse_mode="Markdown"
            )
            logger.info(f"Opened browser: {label} via {exe_path}")

        except Exception as e:
            await query.edit_message_text(f"❌ Failed to open {label}: {str(e)}")
            logger.error(f"Browser open error ({browser_key}): {e}")



async def handle_dropbox_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    """Handle Dropbox file deletion request."""
    try:
        # Parse callback data: delete_dropbox_{user_id}_{file_path}
        parts = query.data.split('_', 3)
        if len(parts) < 4:
            await query.answer("Invalid delete request", show_alert=True)
            return
        
        dropbox_path = parts[3]
        
        await query.edit_message_text(
            f"🗑️ Deleting file from Dropbox...\n\n"
            f"File: {os.path.basename(dropbox_path)}"
        )
        
        # Delete from Dropbox
        result = await asyncio.to_thread(delete_from_dropbox, dropbox_path)
        
        if result['success']:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"✅ File deleted from Dropbox successfully!\n\n"
                     f"File: {os.path.basename(dropbox_path)}"
            )
            logger.info(f"Deleted file from Dropbox: {dropbox_path}")
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"❌ Failed to delete file from Dropbox:\n{result['error']}\n\n"
                     f"You can delete it manually from the Dropbox app."
            )
            logger.error(f"Failed to delete from Dropbox: {result['error']}")
    
    except Exception as e:
        logger.error(f"Error in handle_dropbox_delete: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"❌ Error: {str(e)}"
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
        return {'success': False, 'error': 'Dropbox library not installed. Run: pip install dropbox'}

    try:
        logger.info(f"Deleting from Dropbox: {dropbox_path}")

        access_token = os.getenv('DROPBOX_ACCESS_TOKEN')
        if not access_token or access_token == 'your_dropbox_access_token_here':
            return {'success': False, 'error': 'Dropbox not configured'}

        dbx = dropbox.Dropbox(access_token)

        try:
            dbx.files_delete_v2(dropbox_path)
            logger.info(f"Successfully deleted: {dropbox_path}")
            return {'success': True}
        except ApiError as e:
            err_str = str(e)
            if 'not_found' in err_str or 'path/not_found' in err_str:
                return {
                    'success': False,
                    'error': 'File not found (may have already been deleted)'
                }
            return {'success': False, 'error': f'ApiError: {err_str}'}

    except AuthError as e:
        logger.error(f"Dropbox auth error during delete: {e}")
        return {'success': False, 'error': f'Authentication error: {str(e)}'}
    except Exception as e:
        logger.error(f"Dropbox delete exception: {type(e).__name__}: {str(e)}")
        return {'success': False, 'error': f'{type(e).__name__}: {str(e)}'}



async def handle_upload_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    """Handle user's choice for large file upload."""
    try:
        user_id = update.effective_user.id
        
        # Check if we have state for this user
        if user_id not in large_file_upload_state:
            await query.edit_message_text(
                "❌ Upload session expired. Please try again."
            )
            return
        
        # Check if state is too old (10 minutes)
        if time.time() - large_file_upload_state[user_id]['timestamp'] > 600:
            del large_file_upload_state[user_id]
            await query.edit_message_text(
                "❌ Upload session expired (10 minutes). Please try again."
            )
            return
        
        file_path = large_file_upload_state[user_id]['file_path']
        file_size_mb = large_file_upload_state[user_id]['file_size_mb']
        
        # Determine which service was chosen
        if query.data.startswith("upload_tempfile_"):
            service = 'tempfile'
            service_name = 'TempFile.org'
            await query.edit_message_text(
                f"⚡ Starting TempFile.org upload...\n\n"
                f"Uploading {file_size_mb:.2f} MB..."
            )
        elif query.data.startswith("upload_dropbox_"):
            service = 'dropbox'
            service_name = 'Dropbox'
            await query.edit_message_text(
                f"☁️ Starting Dropbox upload...\n\n"
                f"Uploading {file_size_mb:.2f} MB...\n"
                f"This may take a few minutes for large files..."
            )
        else:
            await query.edit_message_text("❌ Unknown upload service")
            return
        
        # Upload file
        from pocket_desk_agent.handlers.build import upload_large_file
        upload_result = await asyncio.to_thread(upload_large_file, file_path, service)
        
        if upload_result['success']:
            service_used = upload_result.get('service', service_name)
            expiry = upload_result.get('expiry', 'Unknown')
            
            message_text = (
                f"✅ Upload successful!\n\n"
                f"📥 Download your APK:\n{upload_result['link']}\n\n"
                f"ℹ️ Service: {service_used}\n"
                f"⏰ Expires: {expiry}\n\n"
                f"💡 Tip: Open the link on your Android device to install directly!\n\n"
                f"📂 Local path (if needed):\n{file_path}"
            )
            
            # Add delete button for Dropbox uploads
            if service == 'dropbox':
                # Store dropbox file path for deletion
                dropbox_file_path = f'/{os.path.basename(file_path)}'
                
                keyboard = [
                    [InlineKeyboardButton("🗑️ Delete from Dropbox", callback_data=f"delete_dropbox_{user_id}_{dropbox_file_path}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=message_text,
                    reply_markup=reply_markup
                )
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=message_text
                )
            
            logger.info(f"Uploaded large APK to {service_used}: {file_path} ({file_size_mb:.2f} MB)")
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"❌ Upload failed: {upload_result['error']}\n\n"
                     f"📂 File location:\n{file_path}\n\n"
                     f"Please retrieve it manually or try another upload method."
            )
            logger.error(f"Upload to {service_name} failed: {upload_result['error']}")
        
        # Clear state
        del large_file_upload_state[user_id]
        
    except Exception as e:
        logger.error(f"Error in handle_upload_choice: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"❌ Error: {str(e)}"
        )


# Claude Desktop Automation Commands


