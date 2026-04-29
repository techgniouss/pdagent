"""Claude desktop automation command handlers."""

import logging
import os
import re
import sys
import platform
import subprocess
import asyncio
import time
import io
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    PYWINAUTO_AVAILABLE,
    search_results,
    repo_lists,
    repo_selection_state,
    record_action_if_active,
    file_manager,
)

# Lazy-loaded on first call to _load_win_deps() to avoid ~15-20 MB at startup.
Application = None
send_keys = None
gw = None
ImageGrab = None


def _load_win_deps():
    """Load Windows UI automation modules on first use (cached after that)."""
    global Application, send_keys, gw, ImageGrab
    if gw is not None:
        return
    from pywinauto import Application as _App
    from pywinauto.keyboard import send_keys as _sk
    import pygetwindow as _gw
    from PIL import ImageGrab as _ig
    Application = _App
    send_keys = _sk
    gw = _gw
    ImageGrab = _ig

logger = logging.getLogger(__name__)

_INPUT_HINT_TERMS = (
    "reply", "find", "todo", "ask", "type", "message", "chat",
    "prompt", "command", "describe", "task", "question",
)
_NEW_CHAT_HINT_TERMS = ("new", "chat", "session", "conversation")
_NEW_CHAT_TITLE_PATTERNS = (
    r".*[Nn]ew.*([Cc]hat|[Ss]ession|[Cc]onversation).*",
    r".*[Ss]tart.*[Nn]ew.*",
)

# Bottom status bar is ~30 px tall; click its vertical midpoint from window bottom.
_BOTTOM_BAR_Y_OFFSET = 15

# Approximate x-ratios for bottom-bar items (fraction of window.width).
_BOTTOM_X_REPO   = 0.37   # repo name button
_BOTTOM_X_BRANCH = 0.46   # branch button
_BOTTOM_X_MODE   = 0.57   # accept-edits / mode selector
_BOTTOM_X_MODEL  = 0.87   # model selector (right side)

# Keywords that identify a model name in OCR output.
_MODEL_KEYWORDS = ("opus", "sonnet", "haiku", "claude")

# Store claude process PID in a file for persistence
CLAUDE_PID_FILE = os.path.join(os.getenv("TEMP", "/tmp"), "claude_remote_control.pid")


def save_claude_pid(pid):
    """Save Claude process PID to file."""
    try:
        with open(CLAUDE_PID_FILE, 'w') as f:
            f.write(str(pid))
        logger.info(f"Saved Claude PID {pid} to {CLAUDE_PID_FILE}")
    except Exception as e:
        logger.error(f"Failed to save Claude PID: {e}")


def load_claude_pid():
    """Load Claude process PID from file and verify it's still running."""
    try:
        if os.path.exists(CLAUDE_PID_FILE):
            with open(CLAUDE_PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process is still running
            try:
                os.kill(pid, 0)  # Signal 0 just checks if process exists
                logger.info(f"Found running Claude process with PID {pid}")
                return pid
            except OSError:
                # Process is dead, remove stale PID file
                os.remove(CLAUDE_PID_FILE)
                logger.info(f"Removed stale Claude PID file (process {pid} not running)")
                return None
    except Exception as e:
        logger.error(f"Failed to load Claude PID: {e}")
    return None


def clear_claude_pid():
    """Remove Claude PID file."""
    try:
        if os.path.exists(CLAUDE_PID_FILE):
            os.remove(CLAUDE_PID_FILE)
            logger.info("Cleared Claude PID file")
    except Exception as e:
        logger.error(f"Failed to clear Claude PID: {e}")


def get_claude_process():
    """Get Claude process if it's running."""
    pid = load_claude_pid()
    if pid:
        try:
            # Try to get process handle (Windows-specific, but we'll handle cross-platform)
            import psutil
            return psutil.Process(pid)
        except Exception:
            # psutil not available, just return PID
            return pid
    return None


def is_claude_running():
    """Check if Claude remote-control is currently running."""
    pid = load_claude_pid()
    if not pid:
        return False
    
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        clear_claude_pid()
        return False


def _iter_new_chat_shortcuts():
    """Return fallback shortcuts for creating a fresh Claude conversation."""
    return (
        ("ctrl", "n"),
        ("ctrl", "shift", "o"),
    )


def _configure_tesseract():
    """Import pytesseract and configure a common Windows binary path if present."""
    try:
        import pytesseract
    except Exception:
        return None

    if platform.system() == "Windows":
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
    return pytesseract


def _click_bottom_bar_ocr(window, pyautogui, keywords: tuple, strip_height: int = 40) -> bool:
    """OCR the bottom status bar and click the first word matching any keyword.

    Returns True if a click was performed.
    """
    strip_top = window.top + window.height - strip_height
    pytesseract = _configure_tesseract()
    if not pytesseract:
        return False
    try:
        from PIL import ImageGrab
        shot = ImageGrab.grab(bbox=(
            window.left, strip_top,
            window.left + window.width, window.top + window.height,
        ))
        data = pytesseract.image_to_data(shot, output_type=pytesseract.Output.DICT)
        for i, word in enumerate(data["text"]):
            w = (word or "").strip().lower()
            if w and any(k.lower() in w for k in keywords):
                x = data["left"][i] + data["width"][i] // 2 + window.left
                y = data["top"][i] + data["height"][i] // 2 + strip_top
                pyautogui.click(x, y)
                time.sleep(0.4)
                logger.info("Bottom-bar OCR click '%s' at (%d, %d)", word, x, y)
                return True
    except Exception as exc:
        logger.warning("Bottom-bar OCR failed: %s", exc)
    return False


def _click_claude_input(window, pyautogui) -> None:
    """Focus Claude's composer input using UIA/OCR fallbacks."""
    if PYWINAUTO_AVAILABLE:
        try:
            _load_win_deps()
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
            for spec in (
                {"control_type": "Edit", "found_index": 0},
                {"control_type": "Document", "found_index": 0},
                {"title_re": ".*(Ask|Message|Prompt|Chat|Reply|Describe|Task|Question).*", "control_type": "Edit"},
            ):
                try:
                    control = claude_window.child_window(**spec)
                    control.click_input()
                    time.sleep(0.4)
                    logger.info("Focused Claude input via pywinauto: %s", spec)
                    return
                except Exception:
                    continue
        except Exception as exc:
            logger.warning("pywinauto input focus failed: %s", exc)

    pytesseract = _configure_tesseract()
    if pytesseract:
        try:
            bottom_height = 220
            screenshot = pyautogui.screenshot(
                region=(
                    window.left,
                    window.top + window.height - bottom_height,
                    window.width,
                    bottom_height,
                )
            )
            text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
            for index, raw_word in enumerate(text_data["text"]):
                word = (raw_word or "").strip().lower()
                if not word or not any(term in word for term in _INPUT_HINT_TERMS):
                    continue
                x = text_data["left"][index] + (text_data["width"][index] // 2) + window.left
                y = (
                    text_data["top"][index]
                    + (text_data["height"][index] // 2)
                    + window.top
                    + window.height
                    - bottom_height
                )
                pyautogui.click(x, y)
                time.sleep(0.4)
                logger.info("Focused Claude input via OCR term '%s' at (%s, %s)", word, x, y)
                return
        except Exception as exc:
            logger.warning("OCR input focus failed: %s", exc)

    pyautogui.click(window.left + (window.width // 2), window.top + window.height - 40)
    time.sleep(0.4)
    logger.info("Focused Claude input via coordinate fallback")


def send_prompt_to_claude(window, prompt: str, *, submit: bool = True) -> None:
    """Focus Claude input, paste prompt text, and optionally submit."""
    import pyautogui
    import pyperclip

    _click_claude_input(window, pyautogui)
    pyperclip.copy(prompt)
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.6)
    if submit:
        pyautogui.press("enter")
        time.sleep(0.3)



async def clauderemote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clauderemote command - open a cmd window in current repo and run claude remote-control."""
    if not update.message:
        return

    # Check if already running
    if is_claude_running():
        pid = load_claude_pid()
        await update.message.reply_text(
            "⚠️ Claude remote-control is already running!\n"
            f"Process ID: {pid}\n\n"
            "Use /stopclaude to stop it first."
        )
        return

    repo_path = str(file_manager.get_current_dir(update.effective_user.id))
    await update.message.reply_text(
        f"🚀 Starting claude remote-control...\n📁 Repo: `{repo_path}`",
        parse_mode="Markdown",
    )

    try:
        process = subprocess.Popen(
            ["cmd.exe", "/k", "claude remote-control"],
            cwd=repo_path,
        )

        # Save PID for persistence
        save_claude_pid(process.pid)

        await update.message.reply_text(
            "✅ Claude remote-control started in a new terminal!\n"
            f"Process ID: {process.pid}"
        )
        logger.info(f"Claude remote-control started (PID {process.pid}) in {repo_path}")

    except FileNotFoundError:
        await update.message.reply_text(
            "❌ Error: 'claude' command not found.\n"
            "Make sure Claude CLI is installed and in your PATH."
        )
        logger.error("Claude CLI not found in PATH")
    except Exception as e:
        await update.message.reply_text(f"❌ Error starting claude remote-control: {str(e)}")
        logger.error(f"Error starting claude remote-control: {e}")


async def stopclaude_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stopclaude command - stop claude remote-control."""
    if not update.message:
        return
    
    # Check if process exists and is running
    if not is_claude_running():
        await update.message.reply_text(
            "ℹ️ Claude remote-control is not running.\n"
            "Use /clauderemote to start it."
        )
        return
    
    try:
        pid = load_claude_pid()
        
        # Try to terminate the process
        if platform.system() == "Windows":
            # Windows: use taskkill
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
        else:
            # Linux/Mac: use kill
            os.kill(pid, 15)  # SIGTERM
            await asyncio.sleep(1)
            
            # Force kill if still running
            try:
                os.kill(pid, 0)  # Check if still alive
                os.kill(pid, 9)  # SIGKILL
                await update.message.reply_text(
                    f"🛑 Claude remote-control (PID: {pid}) force stopped."
                )
            except OSError:
                # Process already terminated
                await update.message.reply_text(
                    f"✅ Claude remote-control (PID: {pid}) stopped successfully."
                )
        
        if platform.system() == "Windows":
            await update.message.reply_text(
                f"✅ Claude remote-control (PID: {pid}) stopped successfully."
            )
        
        logger.info(f"Claude remote-control stopped (PID: {pid})")
        clear_claude_pid()
        
    except subprocess.CalledProcessError as e:
        await update.message.reply_text(f"❌ Error stopping claude: Process not found or already stopped")
        logger.error(f"Error stopping claude remote-control: {e}")
        clear_claude_pid()
    except Exception as e:
        await update.message.reply_text(f"❌ Error stopping claude: {str(e)}")
        logger.error(f"Error stopping claude remote-control: {e}")


async def openclaude_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /openclaude command - open Claude desktop app or restore if minimized."""
    if not update.message:
        return
    
    await update.message.reply_text("🚀 Opening Claude desktop app...")
    
    try:
        # First check if Claude is already running
        if PYWINAUTO_AVAILABLE:
            window = find_claude_window()
            if window:
                # Claude is already open, just restore and activate
                try:
                    if window.isMinimized:
                        window.restore()
                        await asyncio.sleep(0.5)
                    window.activate()
                    await asyncio.sleep(0.3)
                    await update.message.reply_text(
                        "✅ Claude desktop app is now active!\n\n"
                        "The window has been restored and brought to front."
                    )
                    logger.info("Claude window restored and activated")
                    return
                except Exception as e:
                    logger.warning(f"Failed to restore window, will try to reopen: {e}")
        
        # If not running or failed to restore, open it
        system = platform.system()
        
        if system == "Windows":
            # Try Windows Store app first (most common)
            try:
                subprocess.Popen(["explorer.exe", "shell:AppsFolder\\AnthropicPBC.Claude_jh5q8rxbfr2da!Claude"])
                await asyncio.sleep(3)  # Wait for app to open
                
                # Verify it opened
                if PYWINAUTO_AVAILABLE:
                    window = find_claude_window()
                    if window:
                        await update.message.reply_text("✅ Claude desktop app opened successfully!")
                        logger.info("Claude desktop app opened via Windows Store")
                        return
                else:
                    await update.message.reply_text("✅ Claude desktop app opened!")
                    logger.info("Claude desktop app opened via Windows Store")
                    return
            except Exception as e:
                logger.warning(f"Failed to open via Windows Store: {e}")
            
            # Fallback: Try common installation paths
            possible_paths = [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Claude\Claude.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Claude\Claude.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Claude\Claude.exe"),
            ]
            
            # Try to find and launch Claude
            launched = False
            for path in possible_paths:
                if os.path.exists(path):
                    subprocess.Popen([path])
                    await asyncio.sleep(3)
                    await update.message.reply_text(
                        f"✅ Claude desktop app opened!\n"
                        f"Path: {path}"
                    )
                    logger.info(f"Claude desktop app opened from: {path}")
                    launched = True
                    break
            
            if not launched:
                # Try using start command (works if Claude is in PATH or has file association)
                try:
                    subprocess.Popen("start claude://", shell=True)
                    await update.message.reply_text("✅ Claude desktop app opened via protocol handler!")
                    logger.info("Claude desktop app opened via protocol handler")
                except Exception:
                    await update.message.reply_text(
                        "❌ Could not find Claude desktop app.\n\n"
                        "Searched locations:\n" + "\n".join(f"• {p}" for p in possible_paths) + "\n\n"
                        "Please make sure Claude desktop is installed."
                    )
                    logger.error("Claude desktop app not found in any common location")
        
        elif system == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", "Claude"])
            await update.message.reply_text("✅ Claude desktop app opened!")
            logger.info("Claude desktop app opened on macOS")
        
        elif system == "Linux":
            subprocess.Popen(["claude"])
            await update.message.reply_text("✅ Claude desktop app opened!")
            logger.info("Claude desktop app opened on Linux")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error opening Claude app: {str(e)}")
        logger.error(f"Error opening Claude desktop app: {e}")




def find_claude_window():
    """Find Claude desktop window and restore if minimized."""
    if not PYWINAUTO_AVAILABLE:
        return None
    _load_win_deps()

    try:
        # Try to find Claude window - try multiple title variations
        window = None
        
        # Try exact match first
        windows = gw.getWindowsWithTitle("Claude")
        if windows:
            window = windows[0]
        
        # If not found, try partial match (in case title has extra text)
        if not window:
            all_windows = gw.getAllTitles()
            for title in all_windows:
                if "Claude" in title and "Claude.exe" not in title:
                    windows = gw.getWindowsWithTitle(title)
                    if windows:
                        window = windows[0]
                        logger.info(f"Found Claude window with title: {title}")
                        break
        
        if window:
            # Check if window is minimized and restore it
            if window.isMinimized:
                logger.info("Claude window is minimized, restoring...")
                window.restore()
                time.sleep(0.5)  # Wait for window to restore
            
            # Make sure window is visible and active
            if not window.isActive:
                window.activate()
                time.sleep(0.3)
            
            return window
        
        return None
    except Exception as e:
        logger.error(f"Error finding Claude window: {e}")
        return None


def ensure_claude_open():
    """Ensure Claude desktop is open, visible, and return the window."""
    window = find_claude_window()
    
    if not window:
        # Try to open Claude
        logger.info("Claude window not found, attempting to open...")
        try:
            system = platform.system()
            if system == "Windows":
                # Try Windows Store app first
                try:
                    subprocess.Popen(["explorer.exe", "shell:AppsFolder\\AnthropicPBC.Claude_jh5q8rxbfr2da!Claude"])
                    time.sleep(4)  # Wait longer for app to open
                    window = find_claude_window()
                    if window:
                        logger.info("Claude opened successfully via Windows Store")
                        return window
                except Exception as e:
                    logger.warning(f"Failed to open via Windows Store: {e}")
                
                # Fallback to traditional paths
                possible_paths = [
                    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Claude\Claude.exe"),
                    os.path.expandvars(r"%PROGRAMFILES%\Claude\Claude.exe"),
                    os.path.expandvars(r"%PROGRAMFILES(X86)%\Claude\Claude.exe"),
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        logger.info(f"Trying to open Claude from: {path}")
                        subprocess.Popen([path])
                        time.sleep(4)  # Wait for app to open
                        window = find_claude_window()
                        if window:
                            logger.info(f"Claude opened successfully from: {path}")
                            return window
                
                # Last resort: try protocol handler
                try:
                    subprocess.Popen("start claude://", shell=True)
                    time.sleep(4)
                    window = find_claude_window()
                    if window:
                        logger.info("Claude opened via protocol handler")
                        return window
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Error opening Claude: {e}")
    else:
        # Window exists, make sure it's restored and active
        logger.info("Claude window found, ensuring it's active...")
        try:
            if window.isMinimized:
                logger.info("Restoring minimized Claude window")
                window.restore()
                time.sleep(0.5)
            window.activate()
            time.sleep(0.3)
            logger.info("Claude window activated successfully")
        except Exception as e:
            logger.error(f"Error restoring/activating window: {e}")
    
    return window


def capture_claude_screenshot():
    """Capture screenshot of Claude window."""
    _load_win_deps()
    try:
        window = find_claude_window()
        if not window:
            return None
        
        # Activate and bring to front
        window.activate()
        time.sleep(0.5)
        
        # Get window position and size
        left, top, width, height = window.left, window.top, window.width, window.height
        
        # Take screenshot using PIL
        from PIL import ImageGrab
        screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr
    except Exception as e:
        logger.error(f"Error capturing screenshot: {e}")
        return None




async def claudeask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudeask command - send message to Claude desktop."""
    if not update.message:
        return
    
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto is not available.\n"
            "This feature only works on Windows with pywinauto installed."
        )
        return
    
    # Get message argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /claudeask <message>\n"
            "Example: /claudeask What is Python?"
        )
        return
    
    message = " ".join(context.args)
    
    await update.message.reply_text("🤖 Sending message to Claude desktop...")
    
    try:
        # Ensure Claude is open
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            return
        
        # Activate window and bring to front
        window.activate()
        await asyncio.sleep(1.5)
        
        logger.info(f"Attempting to send message to Claude: {message[:50]}")
        send_prompt_to_claude(window, message)
        
        logger.info(f"Sent message to Claude: {message[:50]}")
        
        await update.message.reply_text(
            f"✅ Message sent to Claude!\n\n"
            f"Message: {message[:100]}{'...' if len(message) > 100 else ''}\n\n"
            f"Use /claudescreen to see the response."
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending message: {str(e)}")
        logger.error(f"Error in claudeask_command: {e}", exc_info=True)



async def claudenew_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudenew command - create new chat in Claude desktop."""
    if not update.message:
        return

    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto is not available.\n"
            "This feature only works on Windows with pywinauto installed."
        )
        return

    # Check if user provided a message to send after creating new chat
    initial_message = " ".join(context.args) if context.args else None

    if initial_message:
        await update.message.reply_text(
            f"🆕 Creating new chat and sending message...\n\n"
            f"Message: {initial_message[:100]}{'...' if len(initial_message) > 100 else ''}"
        )
    else:
        await update.message.reply_text("🆕 Creating new chat in Claude desktop...")

    try:
        # Ensure Claude is open
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            return

        # Activate window
        window.activate()
        await asyncio.sleep(1.0)

        import pyautogui
        
        new_session_clicked = False

        # Method 1: Try OCR to find "New chat/session" button
        try:
            pytesseract = _configure_tesseract()
            if not pytesseract:
                raise RuntimeError("pytesseract unavailable")
            
            logger.info("Using OCR to find 'New chat/session' button...")
            
            # Take screenshot of top-left area where button usually is
            search_width = 300
            search_height = 150
            screenshot = pyautogui.screenshot(region=(
                window.left,
                window.top,
                search_width,
                search_height
            ))
            
            # Use OCR to find text
            text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
            
            # Search for words commonly used in the new-conversation control.
            for i, word in enumerate(text_data['text']):
                if word:
                    word_lower = word.lower()
                    if any(term in word_lower for term in _NEW_CHAT_HINT_TERMS):
                        # Calculate absolute screen position
                        x = text_data['left'][i] + (text_data['width'][i] // 2) + window.left
                        y = text_data['top'][i] + (text_data['height'][i] // 2) + window.top
                        logger.info(f"Found '{word}' at ({x}, {y}), clicking...")
                        pyautogui.click(x, y)
                        await asyncio.sleep(1.0)
                        new_session_clicked = True
                        logger.info("Clicked 'New session' using OCR")
                        break
            
            if not new_session_clicked:
                logger.warning("'New chat/session' text not found with OCR")
                
        except Exception as e:
            logger.warning(f"OCR method failed: {e}")

        # Method 2: Try keyboard shortcut fallbacks.
        if not new_session_clicked:
            for keys in _iter_new_chat_shortcuts():
                try:
                    logger.info("Trying keyboard shortcut: %s", "+".join(keys))
                    pyautogui.hotkey(*keys)
                    await asyncio.sleep(1.0)
                    new_session_clicked = True
                    logger.info("Used keyboard shortcut for new session: %s", "+".join(keys))
                    break
                except Exception as e:
                    logger.warning("Keyboard shortcut %s failed: %s", "+".join(keys), e)

        # Method 3: Try pywinauto
        if not new_session_clicked:
            try:
                app = Application(backend="uia").connect(title_re=".*Claude.*")
                claude_window = app.window(title_re=".*Claude.*")

                for pattern in _NEW_CHAT_TITLE_PATTERNS:
                    if new_session_clicked:
                        break
                    for control_type in ("Button", "Text"):
                        try:
                            new_session_control = claude_window.child_window(
                                title_re=pattern,
                                control_type=control_type,
                            )
                            new_session_control.click_input()
                            logger.info(
                                "Clicked new chat control using pywinauto pattern '%s' (%s)",
                                pattern,
                                control_type,
                            )
                            new_session_clicked = True
                            break
                        except Exception:
                            continue

                await asyncio.sleep(1.0)

            except Exception as e:
                logger.warning(f"pywinauto method failed: {e}")

        # Method 4: Fallback to coordinate-based clicking
        if not new_session_clicked:
            logger.warning("All methods failed, using coordinate fallback")
            # Try multiple possible positions for the button
            possible_positions = [
                (window.left + 68, window.top + 85),   # Legacy position
                (window.left + 90, window.top + 90),   # Current build fallback
                (window.left + 60, window.top + 110),  # Wider title bar fallback
            ]
            
            for x, y in possible_positions:
                logger.info(f"Trying coordinate click at ({x}, {y})")
                pyautogui.click(x, y)
                await asyncio.sleep(0.5)
                break

        await asyncio.sleep(1.0)  # Wait for new session to be created

        if initial_message:
            try:
                send_prompt_to_claude(window, initial_message)
                logger.info("Sent initial message after creating new session")
            except Exception as e:
                logger.warning(f"Failed to send initial message after new session: {e}")
                raise
            
            await update.message.reply_text(
                f"✅ New session created and message sent!\n\n"
                f"Use /claudescreen to see the response."
            )
            logger.info(f"Created new session and sent message: {initial_message[:50]}")
        else:
            await update.message.reply_text(
                "✅ New session created in Claude desktop!\n\n"
                "Use /claudeask to send a message."
            )
            logger.info("Created new session in Claude desktop")

    except Exception as e:
        await update.message.reply_text(f"❌ Error creating new session: {str(e)}")
        logger.error(f"Error in claudenew_command: {e}", exc_info=True)
        logger.error(f"Error in claudenew_command: {e}")




async def claudescreen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudescreen command - get screenshot of Claude desktop."""
    if not update.message:
        return
    
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto is not available.\n"
            "This feature only works on Windows with pywinauto installed."
        )
        return
    
    await update.message.reply_text("📸 Capturing Claude desktop screenshot...")
    
    try:
        # Ensure Claude is open
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            return
        
        # Capture screenshot
        screenshot = capture_claude_screenshot()
        
        if screenshot:
            await update.message.reply_photo(
                photo=screenshot,
                caption="📸 Claude Desktop Screenshot"
            )
            logger.info("Sent Claude desktop screenshot")
        else:
            await update.message.reply_text("❌ Failed to capture screenshot.")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error capturing screenshot: {str(e)}")
        logger.error(f"Error in claudescreen_command: {e}")


async def claudechat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudechat command - send message and get screenshot."""
    if not update.message:
        return
    
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto is not available.\n"
            "This feature only works on Windows with pywinauto installed."
        )
        return
    
    # Get message argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /claudechat <message>\n"
            "Example: /claudechat What is Python?\n\n"
            "This will send the message and return a screenshot after Claude responds."
        )
        return
    
    message = " ".join(context.args)
    
    await update.message.reply_text("🤖 Sending message to Claude desktop...")
    
    try:
        # Ensure Claude is open
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            return
        
        # Activate window
        window.activate()
        await asyncio.sleep(1.5)
        
        logger.info(f"Attempting to send message: {message[:50]}")
        send_prompt_to_claude(window, message)
        
        await update.message.reply_text(
            f"✅ Message sent!\n\n"
            f"Message: {message[:100]}{'...' if len(message) > 100 else ''}\n\n"
            f"⏳ Waiting for Claude to respond..."
        )
        
        # Wait for response (longer wait for better results)
        await asyncio.sleep(6)
        
        # Capture screenshot
        screenshot = capture_claude_screenshot()
        
        if screenshot:
            await update.message.reply_photo(
                photo=screenshot,
                caption=f"📸 Claude's response to: {message[:50]}{'...' if len(message) > 50 else ''}"
            )
            logger.info(f"Sent message and screenshot")
        else:
            await update.message.reply_text(
                "✅ Message sent but failed to capture screenshot.\n"
                "Use /claudescreen to manually get the screenshot."
            )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in claudechat_command: {e}", exc_info=True)


async def claudelatest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudelatest command - open the most recent session."""
    if not update.message:
        return
    
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto is not available.\n"
            "This feature only works on Windows with pywinauto installed."
        )
        return
    
    # Check if user specified a section (today, yesterday, older)
    section = "today"  # default
    if context.args:
        section = context.args[0].lower()
        if section not in ["today", "yesterday", "older"]:
            await update.message.reply_text(
                "Usage: /claudelatest [section]\n\n"
                "Sections:\n"
                "• today (default) - Latest session from today\n"
                "• yesterday - Latest session from yesterday\n"
                "• older - Latest session from older\n\n"
                "Example: /claudelatest yesterday"
            )
            return
    
    await update.message.reply_text(f"🔄 Opening latest session from '{section.title()}'...")
    
    try:
        # Ensure Claude is open
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            return
        
        # Activate window
        window.activate()
        await asyncio.sleep(0.5)
        
        import pyautogui
        
        try:
            # Try to use pywinauto to find and click the section and first session
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
            
            # Try to find the section header and click the first item below it
            try:
                # Find the section text (Today, Yesterday, Older)
                section_text = claude_window.child_window(title_re=f".*{section.title()}.*", control_type="Text")
                section_rect = section_text.rectangle()
                
                # Click slightly below the section header to get the first session
                # Adjust Y position to click on first item in that section
                session_x = window.left + 100  # Middle of sidebar
                session_y = section_rect.top + 40  # 40px below section header
                
                pyautogui.click(session_x, session_y)
                logger.info(f"Clicked latest session in '{section}' section using section header")
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Could not find section header: {e}, trying coordinate fallback")
                # Fallback: use approximate coordinates based on section
                session_x = window.left + 100
                
                if section == "today":
                    session_y = window.top + 307  # First item under "Today"
                elif section == "yesterday":
                    session_y = window.top + 370  # Approximate position for "Yesterday" section
                elif section == "older":
                    session_y = window.top + 433  # Approximate position for "Older" section
                
                pyautogui.click(session_x, session_y)
                logger.info(f"Clicked latest session in '{section}' using coordinates")
                await asyncio.sleep(0.5)
            
            await update.message.reply_text(
                f"✅ Opened latest session from '{section.title()}'!\n\n"
                f"Use /claudescreen to see it or /claudeask to continue the conversation."
            )
            logger.info(f"Opened latest Claude session from '{section}'")
            
        except Exception as e:
            logger.error(f"Error opening latest session: {e}")
            await update.message.reply_text(
                f"❌ Could not open latest session from '{section}'.\n"
                f"Try using /claudenew to create a new session instead."
            )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in claudelatest_command: {e}")


async def claudemode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudemode command - change Claude desktop mode."""
    if not update.message:
        return
    
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto is not available.\n"
            "This feature only works on Windows with pywinauto installed."
        )
        return
    
    # Available modes
    modes = {
        "1": "Ask permissions",
        "2": "Auto accept edits",
        "3": "Plan mode",
        "4": "Bypass permissions"
    }
    
    # Check if user provided a mode selection
    if not context.args:
        mode_list = "\n".join([f"{key}. {value}" for key, value in modes.items()])
        await update.message.reply_text(
            f"🔧 Available Claude modes:\n\n{mode_list}\n\n"
            f"Usage: /claudemode <number>\n"
            f"Example: /claudemode 2"
        )
        return
    
    mode_choice = context.args[0]
    
    if mode_choice not in modes:
        await update.message.reply_text(
            f"❌ Invalid mode. Please choose 1-4.\n"
            f"Use /claudemode to see available modes."
        )
        return
    
    selected_mode = modes[mode_choice]
    await update.message.reply_text(f"🔧 Changing mode to '{selected_mode}'...")
    
    try:
        # Ensure Claude is open
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            return
        
        # Activate window
        window.activate()
        await asyncio.sleep(0.5)
        
        import pyautogui
        
        try:
            # Try to use pywinauto to find and click the dropdown
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
            
            # Find the mode dropdown (accept-edits selector) in the bottom bar.
            mode_clicked = False
            for pattern in (
                ".*[Aa]uto.*[Aa]ccept.*",
                ".*[Aa]ccept.*[Ee]dits.*",
                ".*[Pp]lan.*[Mm]ode.*",
                ".*[Aa]sk.*[Pp]ermissions.*",
                ".*[Bb]ypass.*",
            ):
                try:
                    dropdown_btn = claude_window.child_window(title_re=pattern, control_type="Button")
                    dropdown_btn.click_input()
                    mode_clicked = True
                    logger.info("Clicked mode dropdown via pywinauto pattern '%s'", pattern)
                    await asyncio.sleep(0.5)
                    break
                except Exception:
                    continue

            if not mode_clicked:
                if not _click_bottom_bar_ocr(window, pyautogui, ("accept", "auto", "plan", "ask", "bypass")):
                    dropdown_x = window.left + int(window.width * _BOTTOM_X_MODE)
                    dropdown_y = window.top + window.height - _BOTTOM_BAR_Y_OFFSET
                    pyautogui.click(dropdown_x, dropdown_y)
                    logger.info("Clicked mode dropdown at coord fallback (%d, %d)", dropdown_x, dropdown_y)
                await asyncio.sleep(0.5)
            
            # Now find and click the selected mode option
            try:
                mode_option = claude_window.child_window(title_re=f".*{selected_mode}.*")
                mode_option.click_input()
                logger.info(f"Selected mode '{selected_mode}' using pywinauto")
            except Exception:
                # Keyboard fallback: 0-based index (first option needs 0 presses).
                for _ in range(int(mode_choice) - 1):
                    pyautogui.press('down')
                    await asyncio.sleep(0.1)
                pyautogui.press('enter')
                logger.info(f"Selected mode '{selected_mode}' using keyboard")
            
            await update.message.reply_text(
                f"✅ Mode changed to '{selected_mode}'!\n\n"
                f"Use /claudescreen to verify the change."
            )
            logger.info(f"Changed Claude mode to '{selected_mode}'")
            
        except Exception as e:
            logger.error(f"Error changing mode: {e}")
            await update.message.reply_text(
                f"❌ Could not change mode.\n"
                f"Error: {str(e)}"
            )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in claudemode_command: {e}")


async def claudeacceptedits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudeacceptedits [ask|auto|plan|bypass] — set Claude edit mode."""
    if not update.message:
        return

    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto not available.\nWindows only."
        )
        return

    _MODES = {
        "1": "Ask permissions",
        "2": "Auto accept edits",
        "3": "Plan mode",
        "4": "Bypass permissions",
        "ask": "Ask permissions",
        "auto": "Auto accept edits",
        "plan": "Plan mode",
        "bypass": "Bypass permissions",
    }

    if not context.args:
        lines = "\n".join(f"{k}. {v}" for k, v in [
            ("1", "Ask permissions"),
            ("2", "Auto accept edits"),
            ("3", "Plan mode"),
            ("4", "Bypass permissions"),
        ])
        await update.message.reply_text(
            f"🔧 Claude edit modes:\n\n{lines}\n\n"
            "Usage: /claudeacceptedits <number or keyword>\n"
            "Example: /claudeacceptedits 2  or  /claudeacceptedits auto"
        )
        return

    arg = context.args[0].lower()
    selected_mode = _MODES.get(arg)
    if not selected_mode:
        for val in _MODES.values():
            if arg in val.lower():
                selected_mode = val
                break

    if not selected_mode:
        await update.message.reply_text(
            "❌ Unknown mode. Use: ask, auto, plan, bypass (or 1–4)."
        )
        return

    await update.message.reply_text(f"🔧 Setting mode to '{selected_mode}'...")

    try:
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open Claude desktop.")
            return

        window.activate()
        await asyncio.sleep(1.0)

        import pyautogui
        _load_win_deps()

        # pywinauto connect is optional — OCR/coord fallbacks work without it.
        claude_window = None
        try:
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
        except Exception as exc:
            logger.warning("pywinauto connect failed, using fallbacks: %s", exc)

        # ── Open the mode dropdown ─────────────────────────────────────
        mode_opened = False
        if claude_window:
            for pattern in (
                ".*[Aa]uto.*[Aa]ccept.*",
                ".*[Aa]ccept.*[Ee]dits.*",
                ".*[Pp]lan.*[Mm]ode.*",
                ".*[Aa]sk.*[Pp]ermissions.*",
                ".*[Bb]ypass.*",
            ):
                try:
                    btn = claude_window.child_window(title_re=pattern, control_type="Button")
                    btn.click_input()
                    mode_opened = True
                    logger.info("Opened mode dropdown via pywinauto: %s", pattern)
                    await asyncio.sleep(0.5)
                    break
                except Exception:
                    continue

        if not mode_opened:
            if not _click_bottom_bar_ocr(
                window, pyautogui,
                ("accept", "auto", "plan", "ask", "bypass", "edits", "permissions"),
            ):
                click_x = window.left + int(window.width * _BOTTOM_X_MODE)
                click_y = window.top + window.height - _BOTTOM_BAR_Y_OFFSET
                pyautogui.click(click_x, click_y)
                logger.info("Opened mode dropdown at coord fallback (%d, %d)", click_x, click_y)
            await asyncio.sleep(0.5)

        # ── Click the target option ────────────────────────────────────
        option_clicked = False
        if claude_window:
            try:
                opt = claude_window.child_window(title_re=f".*{re.escape(selected_mode)}.*")
                opt.click_input()
                option_clicked = True
                logger.info("Clicked mode option '%s' via pywinauto", selected_mode)
            except Exception:
                pass

        if not option_clicked:
            from PIL import ImageGrab
            shot = ImageGrab.grab(bbox=(
                window.left, window.top,
                window.left + window.width, window.top + window.height,
            ))
            pytesseract = _configure_tesseract()
            if pytesseract:
                data = pytesseract.image_to_data(shot, output_type=pytesseract.Output.DICT)
                hint = selected_mode.split()[0].lower()
                for i, word in enumerate(data["text"]):
                    if hint in (word or "").lower():
                        x = data["left"][i] + data["width"][i] // 2 + window.left
                        y = data["top"][i] + data["height"][i] // 2 + window.top
                        pyautogui.click(x, y)
                        option_clicked = True
                        logger.info("Clicked mode option '%s' via OCR at (%d, %d)", selected_mode, x, y)
                        break

        if not option_clicked:
            order = ["Ask permissions", "Auto accept edits", "Plan mode", "Bypass permissions"]
            idx = order.index(selected_mode) if selected_mode in order else 0
            for _ in range(idx):
                pyautogui.press("down")
                await asyncio.sleep(0.1)
            pyautogui.press("enter")
            logger.info("Clicked mode option '%s' via keyboard", selected_mode)

        await asyncio.sleep(0.4)
        await update.message.reply_text(
            f"✅ Mode set to '{selected_mode}'!\nUse /claudescreen to verify."
        )
        logger.info("Set Claude edit mode to '%s'", selected_mode)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        logger.error("Error in claudeacceptedits_command: %s", e, exc_info=True)


async def claudemodel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudemodel — scan models (no args) or select by number / name.

    Step 1 — /claudemodel
        Opens the model dropdown, screenshots it, reads available models with
        pywinauto + OCR, closes the dropdown, sends a numbered list to the user.

    Step 2 — /claudemodel <number|name>  (or plain reply via check_model_selection)
        Re-opens the dropdown and clicks the chosen model.
    """
    if not update.message:
        return

    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto not available.\nWindows only."
        )
        return

    user_id = update.effective_user.id

    if context.args:
        await _claudemodel_select(update, user_id, " ".join(context.args))
        return

    # ── STEP 1: scan dropdown ──────────────────────────────────────────────
    await update.message.reply_text("🤖 Opening model selector to scan available models...")

    try:
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open Claude desktop.")
            return

        window.activate()
        await asyncio.sleep(1.0)

        import pyautogui
        _load_win_deps()

        # pywinauto connect is optional — OCR/coord fallbacks work without it.
        claude_window = None
        try:
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
        except Exception as exc:
            logger.warning("pywinauto connect failed, using fallbacks: %s", exc)

        # ── Click the model button ─────────────────────────────────────
        model_btn_clicked = False
        if claude_window:
            try:
                model_btn = claude_window.child_window(
                    title_re=".*(Opus|Sonnet|Haiku).*", control_type="Button"
                )
                model_btn.click_input()
                model_btn_clicked = True
                logger.info("Clicked model button via pywinauto")
            except Exception:
                pass

        if not model_btn_clicked:
            if not _click_bottom_bar_ocr(window, pyautogui, _MODEL_KEYWORDS):
                x = window.left + int(window.width * _BOTTOM_X_MODEL)
                y = window.top + window.height - _BOTTOM_BAR_Y_OFFSET
                pyautogui.click(x, y)
                logger.info("Clicked model button at coord fallback (%d, %d)", x, y)

        await asyncio.sleep(0.7)

        # ── Try pywinauto accessibility tree first ─────────────────────
        models_found: list[str] = []
        if claude_window:
            for ctrl_type in ("MenuItem", "ListItem"):
                try:
                    for item in claude_window.descendants(control_type=ctrl_type):
                        text = (item.window_text() or "").strip()
                        if text and any(k in text.lower() for k in _MODEL_KEYWORDS):
                            if text not in models_found:
                                models_found.append(text)
                except Exception:
                    pass
                if models_found:
                    break

        # ── OCR fallback ───────────────────────────────────────────────
        screenshot_bytes = capture_claude_screenshot()
        if not models_found and screenshot_bytes:
            try:
                pytesseract = _configure_tesseract()
                if pytesseract:
                    from PIL import Image
                    screenshot_bytes.seek(0)
                    img = Image.open(screenshot_bytes)
                    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    seen: set[str] = set()
                    for word in data["text"]:
                        w = (word or "").strip()
                        if w and any(k in w.lower() for k in _MODEL_KEYWORDS) and w not in seen:
                            models_found.append(w)
                            seen.add(w)
            except Exception as exc:
                logger.warning("OCR model scan failed: %s", exc)

        # ── Close dropdown ─────────────────────────────────────────────
        pyautogui.press("escape")
        await asyncio.sleep(0.3)

        # ── Store and reply ────────────────────────────────────────────
        from pocket_desk_agent.handlers._shared import model_selection_state

        if models_found:
            model_selection_state[user_id] = {
                "models": models_found,
                "timestamp": time.time(),
            }
            numbered = "\n".join(f"{i + 1}. {m}" for i, m in enumerate(models_found))
            caption = (
                f"🤖 Available models detected:\n\n{numbered}\n\n"
                "Reply with the number or use /claudemodel <number> to select."
            )
        else:
            fallback = ["Claude Opus 4.7", "Claude Sonnet 4.6", "Claude Haiku 4.5"]
            model_selection_state[user_id] = {
                "models": fallback,
                "timestamp": time.time(),
            }
            numbered = "\n".join(f"{i + 1}. {m}" for i, m in enumerate(fallback))
            caption = (
                "🤖 Could not read dropdown — using known models:\n\n"
                f"{numbered}\n\n"
                "Reply with the number or use /claudemodel <number> to select."
            )

        if screenshot_bytes:
            screenshot_bytes.seek(0)
            await update.message.reply_photo(photo=screenshot_bytes, caption=caption)
        else:
            await update.message.reply_text(caption)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        logger.error("Error in claudemodel_command: %s", e, exc_info=True)


async def _claudemodel_select(
    update: Update, user_id: int, selection: str
) -> None:
    """Select a model by number or name (shared by command + message handler)."""
    from pocket_desk_agent.handlers._shared import model_selection_state

    state = model_selection_state.get(user_id, {})
    stored_models: list[str] = state.get("models", [])

    # Resolve selection to a model name.
    selected: str | None = None
    if selection.isdigit():
        idx = int(selection) - 1
        if 0 <= idx < len(stored_models):
            selected = stored_models[idx]
        else:
            await update.message.reply_text(
                f"❌ Invalid number. Choose 1–{len(stored_models) or '?'}.\n"
                "Use /claudemodel to scan available models."
            )
            return
    else:
        sel_lower = selection.lower()
        for m in stored_models:
            if sel_lower in m.lower():
                selected = m
                break

    if not selected:
        await update.message.reply_text(
            f"❌ Model '{selection}' not found.\nUse /claudemodel to scan available models."
        )
        return

    await update.message.reply_text(f"🤖 Selecting model: {selected}...")

    try:
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open Claude desktop.")
            return

        window.activate()
        await asyncio.sleep(1.0)

        import pyautogui
        _load_win_deps()

        # pywinauto connect is optional — OCR/coord fallbacks work without it.
        claude_window = None
        try:
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
        except Exception as exc:
            logger.warning("pywinauto connect failed, using fallbacks: %s", exc)

        # Re-open the model dropdown.
        btn_clicked = False
        if claude_window:
            try:
                model_btn = claude_window.child_window(
                    title_re=".*(Opus|Sonnet|Haiku).*", control_type="Button"
                )
                model_btn.click_input()
                btn_clicked = True
            except Exception:
                pass

        if not btn_clicked:
            if not _click_bottom_bar_ocr(window, pyautogui, _MODEL_KEYWORDS):
                x = window.left + int(window.width * _BOTTOM_X_MODEL)
                y = window.top + window.height - _BOTTOM_BAR_Y_OFFSET
                pyautogui.click(x, y)

        await asyncio.sleep(0.7)

        # Click the option.
        option_clicked = False
        if claude_window:
            try:
                opt = claude_window.child_window(title_re=f".*{re.escape(selected)}.*")
                opt.click_input()
                option_clicked = True
                logger.info("Selected model '%s' via pywinauto", selected)
            except Exception:
                pass

        if not option_clicked:
            from PIL import ImageGrab
            shot = ImageGrab.grab(bbox=(
                window.left, window.top,
                window.left + window.width, window.top + window.height,
            ))
            pytesseract = _configure_tesseract()
            if pytesseract:
                data = pytesseract.image_to_data(shot, output_type=pytesseract.Output.DICT)
                hint = selected.split()[-1].lower()
                for i, word in enumerate(data["text"]):
                    if hint in (word or "").lower():
                        x = data["left"][i] + data["width"][i] // 2 + window.left
                        y = data["top"][i] + data["height"][i] // 2 + window.top
                        pyautogui.click(x, y)
                        option_clicked = True
                        logger.info("Selected model '%s' via OCR at (%d, %d)", selected, x, y)
                        break

        if not option_clicked:
            idx = stored_models.index(selected) if selected in stored_models else 0
            for _ in range(idx):
                pyautogui.press("down")
                await asyncio.sleep(0.1)
            pyautogui.press("enter")
            logger.info("Selected model '%s' via keyboard", selected)

        await asyncio.sleep(0.4)
        model_selection_state.pop(user_id, None)
        await update.message.reply_text(
            f"✅ Model changed to {selected}!\nUse /claudescreen to verify."
        )
        logger.info("Changed Claude model to '%s'", selected)

    except Exception as e:
        await update.message.reply_text(f"❌ Error selecting model: {e}")
        logger.error("Error selecting model '%s': %s", selected, e, exc_info=True)


async def check_model_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Intercept plain-text replies when user is in model-selection state.

    Returns True if the message was consumed (caller should return early).
    """
    if not update.effective_user or not update.message or not update.message.text:
        return False

    user_id = update.effective_user.id

    from pocket_desk_agent.handlers._shared import model_selection_state

    state = model_selection_state.get(user_id)
    if not state:
        return False

    # Expire after 5 minutes.
    if time.time() - state.get("timestamp", 0) > 300:
        model_selection_state.pop(user_id, None)
        return False

    text = update.message.text.strip()
    # Only intercept short numeric or model-name replies.
    if not (text.isdigit() or any(k in text.lower() for k in _MODEL_KEYWORDS)):
        return False

    await _claudemodel_select(update, user_id, text)
    return True


async def claudesearch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudesearch command - search conversations and show results."""
    if not update.message:
        return
    
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto is not available.\n"
            "This feature only works on Windows with pywinauto installed."
        )
        return
    
    # Get optional search query
    search_query = " ".join(context.args) if context.args else ""
    
    if search_query:
        await update.message.reply_text(f"🔍 Searching for: '{search_query}'...")
    else:
        await update.message.reply_text("🔍 Opening search to show all conversations...")
    
    try:
        # Ensure Claude is open
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            return
        
        # Activate window
        window.activate()
        await asyncio.sleep(0.5)
        
        import pyautogui
        
        try:
            # Try to use pywinauto to find and click Search
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
            
            # Find and click Search button
            try:
                search_btn = claude_window.child_window(title="Search", control_type="Button")
                search_btn.click_input()
                logger.info("Clicked Search button using pywinauto")
            except Exception:
                # Fallback: use keyboard shortcut Ctrl+K
                pyautogui.hotkey('ctrl', 'k')
                logger.info("Opened search using Ctrl+K")
            
            await asyncio.sleep(1.0)  # Wait for search dialog to open
            
            # If search query provided, type it
            if search_query:
                import pyperclip
                pyperclip.copy(search_query)
                pyautogui.hotkey('ctrl', 'v')
                await asyncio.sleep(0.5)
            
            # Capture screenshot of search results
            screenshot = capture_claude_screenshot()
            
            if screenshot:
                user_id = update.effective_user.id
                search_results[user_id] = {
                    'query': search_query,
                    'timestamp': time.time()
                }
                
                caption = "🔍 Search Results\n\n"
                if search_query:
                    caption += f"Query: '{search_query}'\n\n"
                caption += "To select a conversation:\n"
                caption += "• /claudeselect <number> - Select by position (1-10)\n"
                caption += "• /claudeselect <text> - Select by matching text\n\n"
                caption += "Example: /claudeselect 2 or /claudeselect payment issues"
                
                await update.message.reply_photo(
                    photo=screenshot,
                    caption=caption
                )
                logger.info(f"Sent search results screenshot for query: '{search_query}'")
            else:
                await update.message.reply_text("❌ Failed to capture search results.")
            
        except Exception as e:
            logger.error(f"Error in search: {e}")
            await update.message.reply_text(f"❌ Could not open search.\nError: {str(e)}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in claudesearch_command: {e}")


async def claudeselect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudeselect command - select a conversation from search results."""
    if not update.message:
        return
    
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto is not available.\n"
            "This feature only works on Windows with pywinauto installed."
        )
        return
    
    # Check if user provided selection
    if not context.args:
        await update.message.reply_text(
            "Usage: /claudeselect <number or text>\n\n"
            "Examples:\n"
            "• /claudeselect 2 - Select 2nd conversation\n"
            "• /claudeselect payment - Select conversation with 'payment' in title\n\n"
            "First use /claudesearch to see available conversations."
        )
        return
    
    selection = " ".join(context.args)
    user_id = update.effective_user.id
    
    # Check if user has recent search results
    if user_id not in search_results:
        await update.message.reply_text(
            "⚠️ No recent search results found.\n"
            "Please use /claudesearch first to see available conversations."
        )
        return
    
    await update.message.reply_text(f"🎯 Selecting conversation: '{selection}'...")
    
    try:
        # Ensure Claude is open
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            return
        
        # Activate window
        window.activate()
        await asyncio.sleep(0.5)
        
        import pyautogui
        
        try:
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
            
            # Check if selection is a number
            if selection.isdigit():
                position = int(selection)
                
                if position < 1 or position > 10:
                    await update.message.reply_text("❌ Position must be between 1 and 10.")
                    return

                selected_via_list = False
                try:
                    visible_items = [
                        item
                        for item in claude_window.descendants(control_type="ListItem")
                        if item.is_visible()
                    ]
                    if len(visible_items) >= position:
                        visible_items[position - 1].click_input()
                        selected_via_list = True
                        logger.info("Clicked conversation #%s via ListItem", position)
                except Exception:
                    selected_via_list = False

                if not selected_via_list:
                    pyautogui.press('down', presses=max(position - 1, 0), interval=0.08)
                    pyautogui.press('enter')
                    logger.info("Selected conversation #%s via keyboard fallback", position)
                
            else:
                # Search by text - try to find matching conversation
                try:
                    # Find list item containing the search text
                    conversation = claude_window.child_window(title_re=f".*{selection}.*", control_type="ListItem")
                    conversation.click_input()
                    logger.info(f"Clicked conversation matching '{selection}'")
                except Exception:
                    # Fallback: keep current highlighted item and open it.
                    pyautogui.press('enter')
                    logger.info(f"Selected conversation using keyboard for '{selection}'")
            
            await asyncio.sleep(0.5)
            
            # Clear search results for this user
            if user_id in search_results:
                del search_results[user_id]
            
            await update.message.reply_text(
                f"✅ Conversation selected!\n\n"
                f"Use /claudescreen to see it or /claudeask to send a message."
            )
            logger.info(f"Selected conversation: '{selection}'")
            
        except Exception as e:
            logger.error(f"Error selecting conversation: {e}")
            await update.message.reply_text(
                f"❌ Could not select conversation.\n"
                f"Try using /claudesearch again and select by number."
            )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in claudeselect_command: {e}")


async def claudebranch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudebranch command - select a git branch in new session."""
    if not update.message:
        return
    
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto is not available.\n"
            "This feature only works on Windows with pywinauto installed."
        )
        return
    
    # Check if user provided branch name
    if not context.args:
        await update.message.reply_text(
            "Usage: /claudebranch <branch_name>\n\n"
            "Examples:\n"
            "• /claudebranch main\n"
            "• /claudebranch feature/google-maps-integration\n\n"
            "Note: This only works in a new session before starting any chat.\n"
            "Use /claudenew first to create a new session, then use this command."
        )
        return
    
    branch_name = " ".join(context.args)
    
    await update.message.reply_text(f"🌿 Selecting branch: '{branch_name}'...")
    
    try:
        # Ensure Claude is open
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            return
        
        # Activate window
        window.activate()
        await asyncio.sleep(0.5)
        
        import pyautogui
        import pyperclip

        _load_win_deps()

        # pywinauto connect is optional — OCR/coord fallbacks work without it.
        claude_window = None
        try:
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
        except Exception as exc:
            logger.warning("pywinauto connect failed, using fallbacks: %s", exc)

        # ── Step 1: open the branch selector ──────────────────────────
        branch_opened = False
        if claude_window:
            bottom_threshold = window.top + window.height - 60
            for btn in claude_window.descendants(control_type="Button"):
                try:
                    rect = btn.rectangle()
                    text = (btn.window_text() or "").strip()
                    if rect.top < bottom_threshold:
                        continue
                    if ("/" in text or text.lower() in ("main", "master", "develop", "dev")
                            or text.lower().startswith("feature")
                            or text.lower().startswith("fix")):
                        btn.click_input()
                        branch_opened = True
                        logger.info("Opened branch selector via pywinauto: '%s'", text)
                        await asyncio.sleep(0.8)
                        break
                except Exception:
                    continue

        if not branch_opened:
            if not _click_bottom_bar_ocr(
                window, pyautogui,
                ("main", "master", "feature", "develop", "branch"),
            ):
                click_x = window.left + int(window.width * _BOTTOM_X_BRANCH)
                click_y = window.top + window.height - _BOTTOM_BAR_Y_OFFSET
                pyautogui.click(click_x, click_y)
                logger.info("Opened branch selector at coord fallback (%d, %d)", click_x, click_y)
            await asyncio.sleep(0.8)

        # ── Step 2: type in the search box ────────────────────────────
        typed = False
        if claude_window:
            try:
                branch_search = claude_window.child_window(
                    title_re=".*[Ss]earch.*[Bb]ranch.*", control_type="Edit"
                )
                branch_search.click_input()
                await asyncio.sleep(0.3)
                pyperclip.copy(branch_name)
                branch_search.type_keys("^v")
                typed = True
                logger.info("Typed branch name via pywinauto edit control")
            except Exception:
                pass

        if not typed:
            click_x = window.left + window.width // 2
            click_y = window.top + window.height // 2 - 50
            pyautogui.click(click_x, click_y)
            await asyncio.sleep(0.3)
            pyperclip.copy(branch_name)
            pyautogui.hotkey("ctrl", "v")
            logger.info("Typed branch name via coordinate+paste fallback")

        await asyncio.sleep(0.5)

        # ── Step 3: select from list ──────────────────────────────────
        if claude_window:
            try:
                branch_item = claude_window.child_window(
                    title_re=f".*{re.escape(branch_name)}.*", control_type="ListItem"
                )
                branch_item.click_input()
                logger.info("Clicked branch ListItem via pywinauto")
            except Exception:
                pyautogui.press("enter")
                logger.info("Selected branch via Enter key")
        else:
            pyautogui.press("enter")
            logger.info("Selected branch via Enter key (no pywinauto)")

        await asyncio.sleep(0.5)
        await update.message.reply_text(
            f"✅ Branch '{branch_name}' selected!\n\n"
            "Use /claudeask or /claudechat to start chatting."
        )
        logger.info("Selected branch: '%s'", branch_name)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in claudebranch_command: {e}")


async def check_repo_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if message is a repo selection. Returns True if handled."""
    if not update.effective_user or not update.message or not update.message.text:
        return False
    
    user_id = update.effective_user.id
    
    # Check if user is in repo selection state
    if user_id not in repo_selection_state:
        return False
    
    # Check if state is too old (5 minutes)
    if time.time() - repo_selection_state[user_id]['timestamp'] > 300:
        del repo_selection_state[user_id]
        return False
    
    selection = update.message.text.strip()
    local_repos = repo_selection_state[user_id]['local_repos']
    
    await update.message.reply_text(f"📁 Selecting repository: '{selection}'...")
    
    try:
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            del repo_selection_state[user_id]
            return True
        
        window.activate()
        await asyncio.sleep(0.5)
        
        import pyautogui
        import pyperclip
        
        app = Application(backend="uia").connect(title_re=".*Claude.*")
        claude_window = app.window(title_re=".*Claude.*")
        
        # Check if selection is a number
        if selection.isdigit():
            position = int(selection)
            
            # 1-2: Select from Recent in Claude
            if position <= 2:
                # The Recent repos modal appears in the center of the window
                # We need to find the modal and click within it
                
                try:
                    # Try to find the Recent section and click relative to it
                    recent_section = claude_window.child_window(title_re=".*Recent.*", control_type="Text")
                    recent_rect = recent_section.rectangle()
                    
                    # Click below the "Recent" text
                    # First item is ~40px below "Recent" text
                    # Each item is ~60px apart (including path text)
                    click_x = recent_rect.left + 200  # Center of the item
                    click_y = recent_rect.bottom + 20 + ((position - 1) * 60)
                    
                    pyautogui.click(click_x, click_y)
                    logger.info(f"Clicked recent repo at position {position} using Recent section")
                except Exception:
                    # Fallback: Use window-relative coordinates
                    # Modal appears roughly in center of window
                    modal_top = window.top + (window.height // 2) - 100
                    item_height = 60  # Each repo item with path is taller
                    
                    click_y = modal_top + ((position - 1) * item_height) + 30
                    click_x = window.left + (window.width // 2)
                    
                    pyautogui.click(click_x, click_y)
                    logger.info(f"Clicked recent repo at position {position} using fallback coordinates")
                
                await asyncio.sleep(1.5)  # Wait for repo to load
                
                # Take screenshot to confirm selection
                screenshot = capture_claude_screenshot()
                
                if screenshot:
                    await update.message.reply_photo(
                        photo=screenshot,
                        caption=(
                            f"✅ Selected recent repository #{position}!\n\n"
                            f"Use /claudebranch <name> to select a branch."
                        )
                    )
                else:
                    await update.message.reply_text(
                        f"✅ Selected recent repository #{position}!\n\n"
                        f"Use /claudescreen to verify, then /claudebranch to select a branch."
                    )
            
            # 3+: Select from local list
            elif position <= len(local_repos) + 2:
                repo_index = position - 3  # Adjust for 1-2 being Recent
                if repo_index < len(local_repos):
                    repo_path = local_repos[repo_index]
                    await clauderepo_select_path(update, window, claude_window, repo_path)
                else:
                    await update.message.reply_text("❌ Invalid selection number.")
            else:
                await update.message.reply_text("❌ Invalid selection number.")
        
        else:
            # Text selection - try to match from Recent repos first, then local repos
            matched_recent = False
            
            # Try to find matching text in Recent repos using pywinauto
            try:
                # Look for ListItem or Text elements containing the selection text
                recent_item = claude_window.child_window(title_re=f".*{selection}.*", control_type="ListItem")
                recent_item.click_input()
                logger.info(f"Clicked Recent repo matching '{selection}' using pywinauto")
                matched_recent = True
                await asyncio.sleep(1.5)
                
                # Take screenshot to confirm
                screenshot = capture_claude_screenshot()
                if screenshot:
                    await update.message.reply_photo(
                        photo=screenshot,
                        caption=(
                            f"✅ Selected recent repository: '{selection}'!\n\n"
                            f"Use /claudebranch <name> to select a branch."
                        )
                    )
                else:
                    await update.message.reply_text(
                        f"✅ Selected recent repository: '{selection}'!\n\n"
                        f"Use /claudescreen to verify, then /claudebranch to select a branch."
                    )
            except Exception:
                # Not found in Recent repos, try local repos with EXACT name match
                matched_repo = None
                for repo_path in local_repos:
                    repo_name = os.path.basename(repo_path)
                    # Exact match (case-insensitive)
                    if selection.lower() == repo_name.lower():
                        matched_repo = repo_path
                        break
                
                if matched_repo:
                    # Found exact match in local repos - navigate to it
                    await clauderepo_select_path(update, window, claude_window, matched_repo)
                else:
                    # No match found
                    await update.message.reply_text(
                        f"❌ No repository found with name '{selection}'.\n\n"
                        f"Available local repos:\n" + 
                        "\n".join([f"• {os.path.basename(r)}" for r in local_repos[:5]]) +
                        (f"\n... and {len(local_repos) - 5} more" if len(local_repos) > 5 else "") +
                        f"\n\nUse /clauderepo to see the full list again."
                    )
        
        # Clear state after selection
        del repo_selection_state[user_id]
        return True
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in repo selection: {e}")
        del repo_selection_state[user_id]
        return True


async def clauderepo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clauderepo command - show screenshot and options."""
    if not update.message:
        return
    
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto is not available.\n"
            "This feature only works on Windows with pywinauto installed."
        )
        return
    
    user_id = update.effective_user.id
    
    try:
        # Ensure Claude is open
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            return
        
        window.activate()
        await asyncio.sleep(0.5)
        
        import pyautogui
        
        # Click the repository selector button in the bottom status bar.
        _load_win_deps()
        repo_clicked = False
        try:
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
            bottom_threshold = window.top + window.height - 60

            # Walk buttons in bottom bar; skip known non-repo labels.
            _skip = {"local", "worktree", "accept edits", "auto accept edits",
                     "plan mode", "bypass permissions", "ask permissions"}
            for btn in claude_window.descendants(control_type="Button"):
                try:
                    rect = btn.rectangle()
                    text = (btn.window_text() or "").strip()
                    if rect.top < bottom_threshold:
                        continue
                    if not text or text.lower() in _skip:
                        continue
                    # Skip model names and branch-like names already handled elsewhere.
                    if any(k in text.lower() for k in _MODEL_KEYWORDS):
                        continue
                    btn.click_input()
                    repo_clicked = True
                    logger.info("Clicked repo button '%s' via pywinauto", text)
                    await asyncio.sleep(1.5)
                    break
                except Exception:
                    continue
        except Exception as exc:
            logger.warning("pywinauto repo click failed: %s", exc)

        if not repo_clicked:
            if not _click_bottom_bar_ocr(window, pyautogui, ("pdagent", "repo", "project")):
                click_x = window.left + int(window.width * _BOTTOM_X_REPO)
                click_y = window.top + window.height - _BOTTOM_BAR_Y_OFFSET
                pyautogui.click(click_x, click_y)
                logger.info("Clicked repo at coordinate fallback (%d, %d)", click_x, click_y)
            await asyncio.sleep(1.5)  # wait for modal regardless of click method
        
        # Take screenshot of repo selector
        screenshot = capture_claude_screenshot()
        
        if not screenshot:
            await update.message.reply_text("❌ Failed to capture screenshot.")
            return
        
        # Get local repos
        local_repos = []
        current_dir_str = str(file_manager.get_current_dir(user_id))
        if os.path.exists(current_dir_str):
            for item in os.listdir(current_dir_str):
                item_path = os.path.join(current_dir_str, item)
                if os.path.isdir(item_path):
                    local_repos.append(item_path)
        
        # Store state
        repo_selection_state[user_id] = {
            'local_repos': local_repos,
            'timestamp': time.time()
        }
        
        # Build message
        caption = "📸 Claude Repository Selector\n\n"
        caption += "📁 Your local repositories:\n"
        for i, repo_path in enumerate(local_repos, 1):
            repo_name = os.path.basename(repo_path)
            caption += f"{i}. {repo_name}\n"
        
        caption += "\n💡 To select:\n"
        caption += "• Reply with 1-2 to select from Recent (in screenshot)\n"
        caption += "• Reply with 3+ or name to select from local list\n\n"
        caption += "Example: Send '3' or 'HomePay'"
        
        await update.message.reply_photo(
            photo=screenshot,
            caption=caption
        )
        logger.info(f"Showed repo selector to user {user_id}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in clauderepo_command: {e}")




async def clauderepo_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all repositories in the default folder."""
    try:
        user_id = update.effective_user.id
        current_dir_str = str(file_manager.get_current_dir(user_id))
        
        # Check if current path exists
        if not os.path.exists(current_dir_str):
            await update.message.reply_text(
                f"❌ Current directory not found:\n{current_dir_str}\n\n"
                f"Please use /cd to update your path."
            )
            return
        
        # Get all directories in the current path
        repos = []
        for item in os.listdir(current_dir_str):
            item_path = os.path.join(current_dir_str, item)
            if os.path.isdir(item_path):
                repos.append(item_path)
        
        if not repos:
            await update.message.reply_text(
                f"❌ No repositories found in:\n{current_dir_str}"
            )
            return
        
        # Store repo list for this user
        repo_lists[user_id] = repos
        
        # Build message with numbered list
        message = f"📁 Available repositories in:\n{current_dir_str}\n\n"
        
        for i, repo_path in enumerate(repos, 1):
            repo_name = os.path.basename(repo_path)
            message += f"{i}. {repo_name}\n"
        
        message += f"\n💡 To select a repo, use:\n/clauderepo <number>\n\nExample: /clauderepo 3"
        
        await update.message.reply_text(message)
        logger.info(f"Listed {len(repos)} repositories for user {user_id}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error listing repositories: {str(e)}")
        logger.error(f"Error in clauderepo_list: {e}")


async def clauderepo_select_path(update: Update, window, claude_window, repo_path):
    """Select repository by path."""
    import pyautogui
    import pyperclip
    
    try:
        # Find and click "Choose a different folder" button
        choose_folder_btn = claude_window.child_window(title_re=".*Choose a different folder.*")
        choose_folder_btn.click_input()
        logger.info("Clicked 'Choose a different folder' button")
        await asyncio.sleep(1.5)  # Wait for file dialog to open
        
        # Type the path in the folder path box
        pyperclip.copy(repo_path)
        pyautogui.hotkey('ctrl', 'l')  # Focus address bar in file dialog
        await asyncio.sleep(0.3)
        pyautogui.hotkey('ctrl', 'v')  # Paste path
        await asyncio.sleep(0.3)
        pyautogui.press('enter')  # Navigate to path
        await asyncio.sleep(0.8)  # Wait for folder to load
        
        # Click "Select Folder" button - try multiple methods
        select_folder_clicked = False
        
        # Method 1: Try to find "Select Folder" button by text
        try:
            # Look for the Select Folder button in the file dialog
            select_btn = claude_window.child_window(title_re=".*Select Folder.*", control_type="Button")
            select_btn.click_input()
            logger.info("Clicked 'Select Folder' button using pywinauto")
            select_folder_clicked = True
            await asyncio.sleep(1.0)
        except Exception:
            pass
        
        # Method 2: Try using Tab + Enter
        if not select_folder_clicked:
            try:
                pyautogui.press('tab')  # Tab to Select Folder button
                await asyncio.sleep(0.2)
                pyautogui.press('enter')  # Click it
                logger.info("Clicked 'Select Folder' using Tab+Enter")
                select_folder_clicked = True
                await asyncio.sleep(1.0)
            except Exception:
                pass
        
        # Method 3: Try Alt+S shortcut (common for Select button)
        if not select_folder_clicked:
            try:
                pyautogui.hotkey('alt', 's')
                logger.info("Clicked 'Select Folder' using Alt+S")
                select_folder_clicked = True
                await asyncio.sleep(1.0)
            except Exception:
                pass
        
        if not select_folder_clicked:
            logger.warning("Could not click 'Select Folder' button, trying to continue...")
            await asyncio.sleep(1.0)
        
        # Wait for Claude to process the selection
        await asyncio.sleep(1.5)
        
        # Take screenshot to confirm selection
        screenshot = capture_claude_screenshot()
        
        repo_name = os.path.basename(repo_path)
        
        if screenshot:
            # Send screenshot with confirmation message
            await update.message.reply_photo(
                photo=screenshot,
                caption=(
                    f"✅ Selected repository: {repo_name}\n\n"
                    f"Path: {repo_path}\n\n"
                    f"Use /claudebranch <name> to select a branch."
                )
            )
            logger.info(f"Selected folder and sent screenshot: {repo_path}")
        else:
            # Send text confirmation if screenshot fails
            await update.message.reply_text(
                f"✅ Selected repository: {repo_name}\n\n"
                f"Path: {repo_path}\n\n"
                f"Use /claudescreen to verify, then /claudebranch to select a branch."
            )
            logger.info(f"Selected folder (no screenshot): {repo_path}")
        
    except Exception as e:
        logger.error(f"Error selecting path: {e}")
        await update.message.reply_text(
            f"❌ Could not select repository path.\n\n"
            f"Try using /clauderepo browse to select manually."
        )


async def clauderepo_browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open folder browser for manual selection."""
    try:
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            return
        
        window.activate()
        await asyncio.sleep(0.5)
        
        import pyautogui
        
        app = Application(backend="uia").connect(title_re=".*Claude.*")
        claude_window = app.window(title_re=".*Claude.*")
        
        # Find and click "Choose a different folder"
        try:
            choose_folder_btn = claude_window.child_window(title_re=".*Choose a different folder.*")
            choose_folder_btn.click_input()
            logger.info("Opened folder browser")
            
            await update.message.reply_text(
                "📂 Folder browser opened!\n\n"
                "Navigate to your repository folder and click 'Select Folder'.\n\n"
                "After selecting, use /claudescreen to verify."
            )
            
        except Exception as e:
            logger.error(f"Error opening folder browser: {e}")
            # Fallback: click at approximate location
            click_x = window.left + (window.width // 2)
            click_y = window.top + window.height - 150  # Near bottom where button usually is
            
            pyautogui.click(click_x, click_y)
            
            await update.message.reply_text(
                "📂 Attempted to open folder browser.\n\n"
                "If it didn't open, try clicking 'Choose a different folder' manually."
            )
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in clauderepo_browse: {e}")



