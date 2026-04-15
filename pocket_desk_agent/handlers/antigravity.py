"""Antigravity and VS Code integration command handlers."""

import logging
import os
import platform
import subprocess
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    PYWINAUTO_AVAILABLE,
    openfolder_options,
    claudecli_options,
    DEFAULT_REPO_PATH,
)
from pocket_desk_agent.config import Config

# Lazy-loaded on first call to _load_win_deps() to avoid ~15 MB at startup.
Application = None
send_keys = None
gw = None


def _load_win_deps():
    """Load Windows UI automation modules on first use (cached after that)."""
    global Application, send_keys, gw
    if gw is not None:
        return
    from pywinauto import Application as _App
    from pywinauto.keyboard import send_keys as _sk
    import pygetwindow as _gw
    Application = _App
    send_keys = _sk
    gw = _gw


logger = logging.getLogger(__name__)

def find_antigravity_window():
    """Find Antigravity desktop window and restore if minimized."""
    if not PYWINAUTO_AVAILABLE:
        return None
    _load_win_deps()

    try:
        # Try to find Antigravity window
        window = None
        
        # Try exact match first
        windows = gw.getWindowsWithTitle("Antigravity")
        if windows:
            window = windows[0]
        
        # If not found, try partial match (common in Electron apps)
        if not window:
            all_windows = gw.getAllTitles()
            antigravity_titles = [t for t in all_windows if "Antigravity" in t]
            if antigravity_titles:
                windows = gw.getWindowsWithTitle(antigravity_titles[0])
                if windows:
                    window = windows[0]
        
        return window
    except Exception as e:
        logger.error(f"Error finding Antigravity window: {e}")
        return None


async def openantigravity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /openantigravity command - open Antigravity desktop app or restore if minimized."""
    if not update.message:
        return
    
    await update.message.reply_text("🚀 Opening Antigravity desktop app...")
    
    try:
        # First check if Antigravity is already running
        if PYWINAUTO_AVAILABLE:
            window = find_antigravity_window()
            if window:
                try:
                    if window.isMinimized:
                        window.restore()
                        time.sleep(0.5)
                    window.activate()
                    time.sleep(0.3)
                    await update.message.reply_text(
                        "✅ Antigravity app is now active!\n\n"
                        "The window has been brought to front."
                    )
                    logger.info("Antigravity window restored and activated")
                    return
                except Exception as e:
                    logger.warning(f"Failed to restore window: {e}")
        
        # Fallback: Try to launch it
        # Note: Since installation path can vary, we try common Electron app locations
        system = platform.system()
        if system == "Windows":
            # Try to launch via explorer shell or start command if available
            try:
                # Common Electron installation paths or protocol handler
                subprocess.Popen("start antigravity://", shell=True)
                time.sleep(3)
                await update.message.reply_text("✅ Attempted to open Antigravity via protocol handler.")
                return
            except Exception:
                # Try common paths
                possible_paths = [
                    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Antigravity\Antigravity.exe"),
                    os.path.expandvars(r"%PROGRAMFILES%\Antigravity\Antigravity.exe"),
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        subprocess.Popen([path])
                        await update.message.reply_text(f"✅ Opening Antigravity from: {path}")
                        return
                
                await update.message.reply_text(
                    "❌ Could not find Antigravity installation.\n\n"
                    "Please ensure Antigravity is installed and in your PATH, or that the protocol handler is registered."
                )
        else:
            await update.message.reply_text(f"❌ /openantigravity is currently optimized for Windows.")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error opening Antigravity: {str(e)}")


async def antigravitychat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /antigravitychat command - open agent chat (Ctrl+Shift+P then Ctrl+L)."""
    if not update.message:
        return
    
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text("❌ UI automation is only available on Windows with pywinauto.")
        return
        
    window = find_antigravity_window()
    if not window:
        await update.message.reply_text("❌ Antigravity window not found. Try /openantigravity first.")
        return
    
    try:
        window.activate()
        time.sleep(0.5)
        
        # Sequence provided by user: Ctrl+Shift+P then Ctrl+L
        send_keys('^+p')
        time.sleep(0.8)
        send_keys('^l')
        
        await update.message.reply_text("✅ Sent command sequence to Antigravity (Ctrl+Shift+P -> Ctrl+L).")
        logger.info("Executed Antigravity chat sequence")
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending commands: {str(e)}")


async def antigravitymode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /antigravitymode command - select Planning/Fast mode via OCR click."""
    if not update.message:
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /antigravitymode <planning|fast>")
        return
        
    mode = context.args[0].lower()
    if mode not in ["planning", "fast"]:
        await update.message.reply_text("❌ Mode must be 'planning' or 'fast'.")
        return
        
    await update.message.reply_text(f"🎯 Attempting to switch to {mode} mode...")

    try:
        import pyautogui
        from pocket_desk_agent.automation_utils import find_text_in_image
        from PIL import ImageGrab

        window = find_antigravity_window()
        if window:
            window.activate()
            time.sleep(0.5)

        # Step 1: check if the mode label is already visible on screen
        screenshot = ImageGrab.grab()
        mode_label = "Planning" if mode == "planning" else "Fast"
        matches = find_text_in_image(screenshot, mode_label)

        if not matches:
            # Step 2: click the mode selector button to open the dropdown
            if window:
                selector_x = window.left + window.width - 200
                selector_y = window.top + window.height - 50
            else:
                screen_w, screen_h = pyautogui.size()
                selector_x = screen_w // 2
                selector_y = screen_h - 50
            pyautogui.click(selector_x, selector_y)
            time.sleep(0.8)

            # Step 3: re-scan for the mode option in the now-open dropdown
            screenshot = ImageGrab.grab()
            matches = find_text_in_image(screenshot, mode_label)

        if matches:
            pyautogui.click(matches[0].x, matches[0].y)
            await update.message.reply_text(
                f"✅ Switched to {mode_label} mode (clicked at {matches[0].x}, {matches[0].y})."
            )
            logger.info(f"Switched Antigravity mode to {mode_label}")
        else:
            await update.message.reply_text(
                f"❌ Could not find '{mode_label}' option on screen.\n\n"
                "Make sure Antigravity is open and the mode selector is visible."
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Error switching mode: {str(e)}")


async def antigravitymodel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /antigravitymodel command - select or list Antigravity models."""
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text("❌ Automation is only available on Windows.")
        return
        
    window = find_antigravity_window()
    if not window:
        await update.message.reply_text("❌ Antigravity window not found. Try /openantigravity first.")
        return

    import pyautogui
    from pocket_desk_agent.automation_utils import find_text_in_image
    from PIL import ImageGrab
    
    # LISTING MODE: /antigravitymodel (no args)
    if not context.args:
        await update.message.reply_text("🔍 Locating model selector to list available models...")
        try:
            window.activate()
            time.sleep(0.5)
            
            screenshot = ImageGrab.grab()
            # Try to find common keywords to click selection trigger
            trigger_keywords = ["Model", "Gemini", "Claude", "GPT", "O1", "DeepSeek", "Pro", "Flash"]
            trigger_match = None
            for key in trigger_keywords:
                matches = find_text_in_image(screenshot, key)
                if matches:
                    trigger_match = matches[0]
                    break
            
            if trigger_match:
                pyautogui.click(trigger_match.x, trigger_match.y)
                time.sleep(1.0) # Wait for dropdown
                
                # Take new screenshot of the dropdown
                dropdown_screenshot = ImageGrab.grab()
                
                # Use OCR to find all text in the screenshot
                import pytesseract
                # Preprocess for better list accuracy
                from PIL import ImageOps
                gray = ImageOps.grayscale(dropdown_screenshot)
                text_list = pytesseract.image_to_string(gray, config='--oem 3 --psm 11')
                
                # Filter text to find models
                lines = [line.strip() for line in text_list.split('\n') if len(line.strip()) > 5]
                models = []
                for line in lines:
                    if any(key.lower() in line.lower() for key in trigger_keywords):
                        # Clean up common OCR artifacts
                        clean_model = line.replace('|', '').replace('[', '').replace(']', '').strip()
                        if clean_model not in models:
                            models.append(clean_model)
                
                if models:
                    msg = "📋 Available Antigravity Models:\n\n"
                    msg += "\n".join([f"• {m}" for m in models])
                    msg += "\n\nUse `/antigravitymodel <name>` to select one."
                    await update.message.reply_text(msg)
                else:
                    await update.message.reply_text("❌ Found the selector but couldn't read the model list. Please try again.")
            else:
                await update.message.reply_text("❌ Could not locate the model selector on screen.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error listing models: {str(e)}")
        return
        
    # SELECTION MODE: /antigravitymodel <model_name>
    model_name = " ".join(context.args)
    await update.message.reply_text(f"🎯 Attempting to select model: {model_name}...")
    
    try:
        window.activate()
        time.sleep(0.8)
        
        # Take initial screenshot
        screenshot = ImageGrab.grab()
        
        # Variations for search
        variations = [model_name]
        if ' ' in model_name: 
            variations.append(model_name.split()[-1]) # Try just the last word (e.g. "Flash")
            
        found_match = None
        
        # 1. Look for the model name directly (it might be the currently selected one or already open)
        for var in variations:
            matches = find_text_in_image(screenshot, var)
            if matches:
                found_match = matches[0]
                # If we found it, click it to see if it was the selector or a list item
                pyautogui.click(found_match.x, found_match.y)
                time.sleep(0.5)
                # If a new list appeared, we need to click again. Let's assume it might have been the trigger.
                break
        
        # 2. If not found or if we think we clicked the trigger, check again
        time.sleep(0.5)
        screenshot = ImageGrab.grab()
        
        # Try finding the keyword again in the (now potentially open) dropdown
        for var in variations:
            matches = find_text_in_image(screenshot, var)
            if matches:
                found_match = matches[0]
                break
                
        if not found_match:
            # 3. Last ditch: seek any generic model selector keyword and click it
            dropdown_keywords = ["Model", "Gemini", "Claude", "GPT", "O1", "DeepSeek", "Pro", "Flash"]
            for keyword in dropdown_keywords:
                selector_matches = find_text_in_image(screenshot, keyword)
                if selector_matches:
                    pyautogui.click(selector_matches[0].x, selector_matches[0].y)
                    time.sleep(1.0)
                    screenshot = ImageGrab.grab()
                    for var in variations:
                        m = find_text_in_image(screenshot, var)
                        if m:
                            found_match = m[0]
                            break
                    if found_match: break
                    
        if found_match:
            pyautogui.click(found_match.x, found_match.y)
            # Click slightly away and back or just press enter to confirm if needed
            pyautogui.press('enter')
            await update.message.reply_text(f"✅ Selected model '{model_name}' successfully.")
            logger.info(f"Model selected: {model_name}")
        else:
            await update.message.reply_text(
                f"❌ Could not find model '{model_name}'.\n"
                "Verify spelling or use /antigravitymodel without arguments to see available list."
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error during model selection: {str(e)}")


# Build Workflow Commands

# Store build state for conversational flow
build_state = {}

# Store large file upload choices
large_file_upload_state = {}




async def antigravityclaudecodeopen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /antigravityclaudecodeopen command - open Claude Code extension panel in VS Code."""
    if not update.message:
        return

    await update.message.reply_text("🧩 Opening Claude Code panel in VS Code...")

    try:
        import pyautogui
        import pygetwindow as gw

        # Find VS Code window — look for title containing 'Visual Studio Code'
        vscode_window = None
        for w in gw.getAllWindows():
            try:
                if "visual studio code" in w.title.lower() and w.visible:
                    vscode_window = w
                    break
            except Exception:
                continue

        if not vscode_window:
            # VS Code may show just the file name — try matching 'code' in process
            for w in gw.getAllWindows():
                try:
                    t = w.title.lower()
                    if ("code" in t) and w.visible and w.width > 200:
                        vscode_window = w
                        break
                except Exception:
                    continue

        if not vscode_window:
            await update.message.reply_text(
                "❌ Could not find VS Code window.\n\n"
                "Make sure VS Code is open and try again."
            )
            return

        # Restore if minimized and bring to front
        try:
            if vscode_window.isMinimized:
                vscode_window.restore()
                time.sleep(0.5)
            vscode_window.activate()
        except Exception:
            pass

        # Small delay to ensure focus
        time.sleep(0.8)

        # Use pyautogui to send Ctrl+Shift+P (command palette)
        pyautogui.hotkey('ctrl', 'shift', 'p')
        time.sleep(0.7)

        # Clear any existing text and type the command
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.2)
        pyautogui.typewrite('Claude: Focus on Claude Code Input', interval=0.04)
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(0.5)

        await update.message.reply_text(
            "✅ Claude Code panel opened in VS Code!\n\n"
            "The extension chat should now be visible."
        )
        logger.info("Opened Claude Code panel in VS Code via command palette")

    except ImportError:
        await update.message.reply_text(
            "❌ pyautogui is not installed.\n\n"
            "Run: pip install pyautogui"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error opening Claude Code panel: {str(e)}")
        logger.error(f"Error in antigravityclaudecodeopen_command: {e}", exc_info=True)


async def claudecli_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudecli - list folders and open Claude CLI in the selected one."""
    if not update.message:
        return

    user_id = update.effective_user.id
    
    # Extract any prompt the user wants to pass to Claude CLI
    prompt = " ".join(context.args) if context.args else ""

    await update.message.reply_text("🔍 Scanning folders for Claude CLI...")

    try:
        import pathlib

        # Build list of candidate root directories
        seed_paths = list(getattr(Config, "APPROVED_DIRECTORIES", []))

        # Always include common dev roots
        common = [
            str(pathlib.Path.home()),
            str(pathlib.Path.home() / "Downloads"),
            str(pathlib.Path.home() / "Desktop"),
            str(pathlib.Path.home() / "Documents"),
            os.path.expandvars(r"%USERPROFILE%\source"),
            os.path.expandvars(r"%USERPROFILE%\repos"),
        ]
        for p in common:
            if os.path.isdir(p) and p not in seed_paths:
                seed_paths.append(p)

        # Expand each seed to its immediate subdirectories (+ itself)
        folders = []
        seen = set()

        for root in seed_paths:
            if not os.path.isdir(root):
                continue
            # Include the root itself
            norm = os.path.normpath(root)
            if norm not in seen:
                seen.add(norm)
                folders.append(norm)
            # Include immediate subdirectories
            try:
                for entry in os.scandir(root):
                    if entry.is_dir(follow_symlinks=False):
                        norm_sub = os.path.normpath(entry.path)
                        if norm_sub not in seen:
                            seen.add(norm_sub)
                            folders.append(norm_sub)
            except PermissionError:
                pass

        if not folders:
            await update.message.reply_text(
                "❌ No folders found.\n\n"
                "Check that APPROVED_DIRECTORIES is configured in your .env."
            )
            return

        # Store options for this user (max 40)
        folders = folders[:40]
        claudecli_options[user_id] = {
            "paths": {i: p for i, p in enumerate(folders)},
            "prompt": prompt
        }

        # Build inline keyboard — one button per row
        keyboard = []
        for i, path in enumerate(folders):
            label = f"📁 {os.path.basename(path) or path}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"claudecli_{i}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = f"💻 *Select a repo to open in Claude CLI:*\n\n_{len(folders)} folder(s) found_"
        if prompt:
            message_text += f"\n\n*Prompt to send:* `{prompt}`"

        await update.message.reply_text(
            message_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error listing folders: {str(e)}")
        logger.error(f"Error in claudecli_command: {e}", exc_info=True)


async def claudeclisend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudeclisend - type a followup prompt into the open Claude CLI window."""
    if not update.message:
        return

    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text(
            "❌ Please provide a prompt.\n"
            "Example: `/claudeclisend expand on that last explanation`",
            parse_mode="Markdown"
        )
        return

    if platform.system() != "Windows":
        await update.message.reply_text("❌ This feature is only supported on Windows.")
        return

    await update.message.reply_text("⌨️ Sending follow-up to Claude CLI...")

    try:
        import pygetwindow as gw
        import pyautogui
        
        window_found = False
        for w in gw.getAllWindows():
            # Specifically targeting the CLI window we titled "Claude CLI"
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
            pyautogui.write(prompt, interval=0.01)
            pyautogui.press('enter')
            await update.message.reply_text("✅ Follow-up prompt sent to Claude CLI!")
        else:
            await update.message.reply_text(
                "❌ Could not find the open Claude CLI window.\n"
                "You must run /claudecli first to spawn the terminal session."
            )
    except Exception as e:
        logger.error(f"Error in claudeclisend_command: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error sending prompt: {str(e)}")


async def antigravityopenfolder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /antigravityopenfolder - list folders and open selected one in VS Code."""
    if not update.message:
        return

    user_id = update.effective_user.id

    await update.message.reply_text("🔍 Scanning folders...")

    try:
        import pathlib

        # Build list of candidate root directories
        seed_paths = list(getattr(Config, "APPROVED_DIRECTORIES", []))

        # Always include common dev roots
        common = [
            str(pathlib.Path.home()),
            str(pathlib.Path.home() / "Downloads"),
            str(pathlib.Path.home() / "Desktop"),
            str(pathlib.Path.home() / "Documents"),
            os.path.expandvars(r"%USERPROFILE%\source"),
            os.path.expandvars(r"%USERPROFILE%\repos"),
        ]
        for p in common:
            if os.path.isdir(p) and p not in seed_paths:
                seed_paths.append(p)

        # Expand each seed to its immediate subdirectories (+ itself)
        folders = []
        seen = set()

        for root in seed_paths:
            if not os.path.isdir(root):
                continue
            # Include the root itself
            norm = os.path.normpath(root)
            if norm not in seen:
                seen.add(norm)
                folders.append(norm)
            # Include immediate subdirectories
            try:
                for entry in os.scandir(root):
                    if entry.is_dir(follow_symlinks=False):
                        norm_sub = os.path.normpath(entry.path)
                        if norm_sub not in seen:
                            seen.add(norm_sub)
                            folders.append(norm_sub)
            except PermissionError:
                pass

        if not folders:
            await update.message.reply_text(
                "❌ No folders found.\n\n"
                "Check that APPROVED_DIRECTORIES is configured in your .env."
            )
            return

        # Store options for this user (max 40 to keep the list manageable)
        folders = folders[:40]
        openfolder_options[user_id] = {i: p for i, p in enumerate(folders)}

        # Build inline keyboard — one button per row
        keyboard = []
        for i, path in enumerate(folders):
            label = f"📁 {os.path.basename(path) or path}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"openfolder_{i}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📂 *Select a folder to open in VS Code:*\n\n"
            f"_{len(folders)} folder(s) found_",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error listing folders: {str(e)}")
        logger.error(f"Error in antigravityopenfolder_command: {e}")


async def openbrowser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /openbrowser - show browser options and open selected one maximized."""
    if not update.message:
        return

    # Detect which browsers are actually installed
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

    BROWSER_EMOJIS = {
        "edge": "🌐 Microsoft Edge",
        "chrome": "🔵 Google Chrome",
        "firefox": "🦊 Mozilla Firefox",
        "brave": "🦁 Brave",
    }

    # Build buttons only for installed browsers (always include Edge & Chrome as fallback)
    keyboard = []
    for key, paths in BROWSER_PATHS.items():
        installed = any(os.path.exists(p) for p in paths)
        if installed or key in ("edge", "chrome"):  # always show edge/chrome
            keyboard.append([InlineKeyboardButton(
                BROWSER_EMOJIS[key],
                callback_data=f"browser_{key}"
            )])

    if not keyboard:
        await update.message.reply_text("❌ No supported browsers detected on this system.")
        return

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌐 *Which browser would you like to open?*\n\n"
        "_Selected browser will open maximized._",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )



