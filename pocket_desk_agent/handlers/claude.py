"""Claude desktop automation command handlers."""

import logging
import os
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
    repo_selection_state,
    record_action_if_active,
    file_manager,
)
from pocket_desk_agent.config import Config

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



async def clauderemote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clauderemote command - open a cmd window at the default repo path and run claude remote-control."""
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
            "Use /claude to start it."
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
                        time.sleep(0.5)
                    window.activate()
                    time.sleep(0.3)
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
                time.sleep(3)  # Wait for app to open
                
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
                    time.sleep(3)
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
        time.sleep(1.5)
        
        import pyautogui
        import pyperclip
        
        logger.info(f"Attempting to send message to Claude: {message[:50]}")
        
        input_clicked = False
        
        # Method 1: Try to find input box using OCR
        try:
            import pytesseract
            
            # Set Tesseract path for Windows
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
            
            logger.info("Using OCR to find input box...")
            
            # Take screenshot of bottom portion of window
            bottom_height = 200
            screenshot = pyautogui.screenshot(region=(
                window.left,
                window.top + window.height - bottom_height,
                window.width,
                bottom_height
            ))
            
            # Use OCR to find text
            text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
            
            # Search for multiple possible placeholder texts
            search_terms = ['reply', 'find', 'todo', 'ask', 'type', 'message', 'chat']
            
            for i, word in enumerate(text_data['text']):
                if word:
                    word_lower = word.lower()
                    # Check if any search term is in the word
                    if any(term in word_lower for term in search_terms):
                        # Calculate absolute screen position
                        x = text_data['left'][i] + (text_data['width'][i] // 2) + window.left
                        y = text_data['top'][i] + (text_data['height'][i] // 2) + (window.top + window.height - bottom_height)
                        logger.info(f"Found input box text '{word}' at ({x}, {y}), clicking...")
                        pyautogui.click(x, y)
                        time.sleep(0.5)
                        input_clicked = True
                        break
            
            if not input_clicked:
                logger.warning("Input box text not found with OCR")
                
        except Exception as e:
            logger.warning(f"OCR method failed: {e}")
        
        # Method 2: Try pywinauto to find Edit control
        if not input_clicked:
            try:
                logger.info("Trying pywinauto to find input box...")
                app = Application(backend="uia").connect(title_re=".*Claude.*")
                claude_window = app.window(title_re=".*Claude.*")
                
                # Find the edit/input control (text box)
                input_box = claude_window.child_window(control_type="Edit", found_index=0)
                input_box.click_input()
                time.sleep(0.5)
                input_clicked = True
                logger.info("Clicked input box using pywinauto")
                
            except Exception as e:
                logger.warning(f"pywinauto method failed: {e}")
        
        # Method 3: Fallback to coordinate-based clicking
        if not input_clicked:
            logger.warning("Using coordinate fallback for input box")
            # Try multiple possible positions
            possible_positions = [
                (window.left + (window.width // 2), window.top + window.height - 35),  # Center bottom
                (window.left + (window.width // 2) + 50, window.top + window.height - 35),  # Slightly right
                (window.left + (window.width // 2), window.top + window.height - 60),  # Higher up
            ]
            
            # Try first position
            click_x, click_y = possible_positions[0]
            logger.info(f"Fallback clicking at ({click_x}, {click_y})")
            pyautogui.click(click_x, click_y)
            time.sleep(0.5)
        
        # Copy message to clipboard
        pyperclip.copy(message)
        time.sleep(0.3)
        
        # Paste the message
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1.0)
        
        # Verify paste worked
        current_clipboard = pyperclip.paste()
        if current_clipboard == message:
            logger.info("Message pasted successfully")
        else:
            logger.warning(f"Clipboard verification failed. Expected: {message[:30]}, Got: {current_clipboard[:30]}")
        
        # Press Enter to send
        pyautogui.press('enter')
        time.sleep(0.5)
        
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
        time.sleep(1.0)

        import pyautogui
        
        new_session_clicked = False

        # Method 1: Try OCR to find "New session" button
        try:
            import pytesseract
            
            # Set Tesseract path for Windows
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
            
            logger.info("Using OCR to find 'New session' button...")
            
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
            
            # Search for "New" or "session" text
            for i, word in enumerate(text_data['text']):
                if word:
                    word_lower = word.lower()
                    # Look for "new" or "session" text
                    if 'new' in word_lower or 'session' in word_lower:
                        # Calculate absolute screen position
                        x = text_data['left'][i] + (text_data['width'][i] // 2) + window.left
                        y = text_data['top'][i] + (text_data['height'][i] // 2) + window.top
                        logger.info(f"Found '{word}' at ({x}, {y}), clicking...")
                        pyautogui.click(x, y)
                        time.sleep(1.0)
                        new_session_clicked = True
                        logger.info("Clicked 'New session' using OCR")
                        break
            
            if not new_session_clicked:
                logger.warning("'New session' text not found with OCR")
                
        except Exception as e:
            logger.warning(f"OCR method failed: {e}")

        # Method 2: Try keyboard shortcut (most reliable)
        if not new_session_clicked:
            try:
                logger.info("Trying keyboard shortcut Ctrl+Shift+O")
                pyautogui.hotkey('ctrl', 'shift', 'o')
                time.sleep(1.0)
                new_session_clicked = True
                logger.info("Used keyboard shortcut for new session")
            except Exception as e:
                logger.warning(f"Keyboard shortcut failed: {e}")

        # Method 3: Try pywinauto
        if not new_session_clicked:
            try:
                app = Application(backend="uia").connect(title_re=".*Claude.*")
                claude_window = app.window(title_re=".*Claude.*")

                # Try to find and click "New session" button
                try:
                    new_session_btn = claude_window.child_window(title="New session", control_type="Button")
                    new_session_btn.click_input()
                    logger.info("Clicked 'New session' button using pywinauto")
                    new_session_clicked = True
                except Exception:
                    # Try as text element
                    try:
                        new_session_text = claude_window.child_window(title_re=".*New.*session.*")
                        new_session_text.click_input()
                        logger.info("Clicked 'New session' text using pywinauto")
                        new_session_clicked = True
                    except Exception:
                        pass

                time.sleep(1.0)

            except Exception as e:
                logger.warning(f"pywinauto method failed: {e}")

        # Method 4: Fallback to coordinate-based clicking
        if not new_session_clicked:
            logger.warning("All methods failed, using coordinate fallback")
            # Try multiple possible positions for the button
            possible_positions = [
                (window.left + 68, window.top + 85),   # Original position
                (window.left + 80, window.top + 70),   # Alternative 1
                (window.left + 60, window.top + 100),  # Alternative 2
            ]
            
            for x, y in possible_positions:
                logger.info(f"Trying coordinate click at ({x}, {y})")
                pyautogui.click(x, y)
                time.sleep(0.5)
                # Check if it worked by looking for input box
                break  # Just try the first one for now

        time.sleep(1.0)  # Wait for new session to be created

        if initial_message:
            # Try to find and click in the input box using pywinauto
            try:
                app = Application(backend="uia").connect(title_re=".*Claude.*")
                claude_window = app.window(title_re=".*Claude.*")
                
                # Find the edit/input control (text box)
                input_box = claude_window.child_window(control_type="Edit", found_index=0)
                input_box.click_input()
                time.sleep(0.3)
                
                # Set text directly using pywinauto
                input_box.set_focus()
                input_box.type_keys(initial_message, with_spaces=True)
                time.sleep(0.3)
                
                # Press Enter to send
                input_box.type_keys('{ENTER}')
                
                logger.info(f"Sent message using pywinauto text input: {initial_message[:50]}")
                
            except Exception as e:
                logger.warning(f"pywinauto text input failed: {e}, trying clipboard method")
                # Fallback to clipboard paste method (more reliable for special characters)
                click_x = window.left + (window.width // 2)
                click_y = window.top + window.height - 60
                
                pyautogui.click(click_x, click_y)
                time.sleep(0.3)
                
                # Use clipboard for more reliable text input
                import pyperclip
                pyperclip.copy(initial_message)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.3)
                
                pyautogui.press('enter')
            
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
        time.sleep(1.5)
        
        import pyautogui
        import pyperclip
        
        logger.info(f"Attempting to send message: {message[:50]}")
        
        input_clicked = False
        
        # Method 1: Try to find input box using OCR
        try:
            import pytesseract
            
            # Set Tesseract path for Windows
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
            
            logger.info("Using OCR to find input box...")
            
            # Take screenshot of bottom portion
            bottom_height = 200
            screenshot = pyautogui.screenshot(region=(
                window.left,
                window.top + window.height - bottom_height,
                window.width,
                bottom_height
            ))
            
            # Use OCR
            text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
            
            # Search for multiple possible placeholder texts
            search_terms = ['reply', 'find', 'todo', 'ask', 'type', 'message', 'chat']
            
            for i, word in enumerate(text_data['text']):
                if word:
                    word_lower = word.lower()
                    # Check if any search term is in the word
                    if any(term in word_lower for term in search_terms):
                        x = text_data['left'][i] + (text_data['width'][i] // 2) + window.left
                        y = text_data['top'][i] + (text_data['height'][i] // 2) + (window.top + window.height - bottom_height)
                        logger.info(f"Found input box text '{word}' at ({x}, {y})")
                        pyautogui.click(x, y)
                        time.sleep(0.5)
                        input_clicked = True
                        break
            
            if not input_clicked:
                logger.warning("Input box text not found with OCR")
                
        except Exception as e:
            logger.warning(f"OCR method failed: {e}")
        
        # Method 2: Try pywinauto to find Edit control
        if not input_clicked:
            try:
                logger.info("Trying pywinauto to find input box...")
                app = Application(backend="uia").connect(title_re=".*Claude.*")
                claude_window = app.window(title_re=".*Claude.*")
                
                # Find the edit/input control (text box)
                input_box = claude_window.child_window(control_type="Edit", found_index=0)
                input_box.click_input()
                time.sleep(0.5)
                input_clicked = True
                logger.info("Clicked input box using pywinauto")
                
            except Exception as e:
                logger.warning(f"pywinauto method failed: {e}")
        
        # Method 3: Fallback to coordinate-based clicking
        if not input_clicked:
            logger.warning("Using coordinate fallback for input box")
            click_x = window.left + (window.width // 2) + 50
            click_y = window.top + window.height - 35
            pyautogui.click(click_x, click_y)
            time.sleep(0.5)
        
        # Paste message
        pyperclip.copy(message)
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1.0)
        
        # Verify paste
        current_clipboard = pyperclip.paste()
        if current_clipboard == message:
            logger.info("Message pasted successfully")
        else:
            logger.warning(f"Clipboard verification failed")
        
        # Send
        pyautogui.press('enter')
        time.sleep(0.5)
        
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
        time.sleep(0.5)
        
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
                time.sleep(0.5)
                
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
                time.sleep(0.5)
            
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
        time.sleep(0.5)
        
        import pyautogui
        
        try:
            # Try to use pywinauto to find and click the dropdown
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
            
            # Find the "Auto accept edits" dropdown button (or similar text)
            try:
                # Look for the dropdown button - it shows current mode
                dropdown_btn = claude_window.child_window(title_re=".*Auto accept edits.*", control_type="Button")
                dropdown_btn.click_input()
                logger.info("Clicked mode dropdown using pywinauto")
                time.sleep(0.5)
            except Exception:
                # Fallback: click at approximate dropdown location (bottom of window)
                dropdown_x = window.left + (window.width // 2) - 100  # Left side of bottom area
                dropdown_y = window.top + window.height - 60
                
                pyautogui.click(dropdown_x, dropdown_y)
                logger.info("Clicked mode dropdown using coordinates")
                time.sleep(0.5)
            
            # Now find and click the selected mode option
            try:
                mode_option = claude_window.child_window(title_re=f".*{selected_mode}.*")
                mode_option.click_input()
                logger.info(f"Selected mode '{selected_mode}' using pywinauto")
            except Exception:
                # Fallback: use keyboard navigation
                # Press down arrow keys based on selection
                for _ in range(int(mode_choice)):
                    pyautogui.press('down')
                    time.sleep(0.1)
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


async def claudemodel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudemodel command - change Claude model."""
    if not update.message:
        return
    
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text(
            "❌ pywinauto is not available.\n"
            "This feature only works on Windows with pywinauto installed."
        )
        return
    
    # Available models
    models = {
        "1": "Opus 4.6",
        "2": "Sonnet 4.6",
        "3": "Haiku 4.5"
    }
    
    # Check if user provided a model selection
    if not context.args:
        model_list = "\n".join([f"{key}. {value}" for key, value in models.items()])
        await update.message.reply_text(
            f"🤖 Available Claude models:\n\n{model_list}\n\n"
            f"Usage: /claudemodel <number>\n"
            f"Example: /claudemodel 2"
        )
        return
    
    model_choice = context.args[0]
    
    if model_choice not in models:
        await update.message.reply_text(
            f"❌ Invalid model. Please choose 1-3.\n"
            f"Use /claudemodel to see available models."
        )
        return
    
    selected_model = models[model_choice]
    await update.message.reply_text(f"🤖 Changing model to '{selected_model}'...")
    
    try:
        # Ensure Claude is open
        window = ensure_claude_open()
        if not window:
            await update.message.reply_text("❌ Could not open or find Claude desktop app.")
            return
        
        # Activate window
        window.activate()
        time.sleep(0.5)
        
        import pyautogui
        
        try:
            # Try to use pywinauto to find and click the model dropdown
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
            
            # Find the model dropdown button (shows current model like "Opus 4.6")
            try:
                # Look for dropdown with model name
                model_dropdown = claude_window.child_window(title_re=".*(Opus|Sonnet|Haiku).*", control_type="Button")
                model_dropdown.click_input()
                logger.info("Clicked model dropdown using pywinauto")
                time.sleep(0.5)
            except Exception:
                # Fallback: click at approximate model dropdown location (bottom right area)
                dropdown_x = window.left + window.width - 150  # Right side of bottom area
                dropdown_y = window.top + window.height - 60
                
                pyautogui.click(dropdown_x, dropdown_y)
                logger.info("Clicked model dropdown using coordinates")
                time.sleep(0.5)
            
            # Now find and click the selected model option
            try:
                model_option = claude_window.child_window(title_re=f".*{selected_model}.*")
                model_option.click_input()
                logger.info(f"Selected model '{selected_model}' using pywinauto")
            except Exception:
                # Fallback: use keyboard navigation
                # Press down arrow keys based on selection
                for _ in range(int(model_choice)):
                    pyautogui.press('down')
                    time.sleep(0.1)
                pyautogui.press('enter')
                logger.info(f"Selected model '{selected_model}' using keyboard")
            
            await update.message.reply_text(
                f"✅ Model changed to '{selected_model}'!\n\n"
                f"Use /claudescreen to verify the change."
            )
            logger.info(f"Changed Claude model to '{selected_model}'")
            
        except Exception as e:
            logger.error(f"Error changing model: {e}")
            await update.message.reply_text(
                f"❌ Could not change model.\n"
                f"Error: {str(e)}"
            )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in claudemodel_command: {e}")


# Store search results for selection
search_results = {}

# Default repository base path - loaded from config
from pocket_desk_agent.config import Config
DEFAULT_REPO_PATH = Config.CLAUDE_DEFAULT_REPO_PATH

# Store repo list for selection
repo_lists = {}

# Store repo selection state for conversational flow
repo_selection_state = {}

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
        time.sleep(0.5)
        
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
            
            time.sleep(1.0)  # Wait for search dialog to open
            
            # If search query provided, type it
            if search_query:
                import pyperclip
                pyperclip.copy(search_query)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.5)
            
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
                caption += "• /claudeselect <number> - Select by position (1-10, excludes 'How to use Claude')\n"
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
            "• /claudeselect 2 - Select 2nd conversation (excludes 'How to use Claude')\n"
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
        time.sleep(0.5)
        
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
                
                # Calculate position (skip first item "How to use Claude")
                # Each item is approximately 37-40px apart
                search_dialog_top = window.top + 170  # Approximate top of first result
                item_height = 38  # Approximate height between items
                
                # Position 1 = second item (first after "How to use Claude")
                click_y = search_dialog_top + (position * item_height)
                click_x = window.left + (window.width // 2)
                
                pyautogui.click(click_x, click_y)
                logger.info(f"Clicked conversation at position {position}")
                
            else:
                # Search by text - try to find matching conversation
                try:
                    # Find list item containing the search text
                    conversation = claude_window.child_window(title_re=f".*{selection}.*", control_type="ListItem")
                    conversation.click_input()
                    logger.info(f"Clicked conversation matching '{selection}'")
                except Exception:
                    # Fallback: use keyboard navigation
                    # Press down arrow to skip "How to use Claude"
                    pyautogui.press('down')
                    time.sleep(0.2)
                    
                    # Search through items
                    for _ in range(10):  # Try up to 10 items
                        pyautogui.press('enter')
                        break
                    
                    logger.info(f"Selected conversation using keyboard for '{selection}'")
            
            time.sleep(0.5)
            
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
        time.sleep(0.5)
        
        import pyautogui
        import pyperclip
        
        try:
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
            
            # Try to find the branch search box
            try:
                # Look for "Search branches" input box
                branch_search = claude_window.child_window(title_re=".*[Ss]earch branches.*", control_type="Edit")
                branch_search.click_input()
                time.sleep(0.3)
                
                # Type branch name using clipboard
                pyperclip.copy(branch_name)
                branch_search.type_keys('^v')  # Ctrl+V
                time.sleep(0.5)
                
                logger.info(f"Typed branch name '{branch_name}' in search box")
                
                # Now find and click the matching branch from the list
                try:
                    # Try to find the branch in the list
                    branch_item = claude_window.child_window(title_re=f".*{branch_name}.*", control_type="ListItem")
                    branch_item.click_input()
                    logger.info(f"Clicked branch '{branch_name}' from list")
                except Exception:
                    # Fallback: just press Enter to select first match
                    pyautogui.press('enter')
                    logger.info(f"Selected branch using Enter key")
                
                time.sleep(0.5)
                
                await update.message.reply_text(
                    f"✅ Branch '{branch_name}' selected!\n\n"
                    f"Now you can start chatting with /claudeask or /claudechat."
                )
                logger.info(f"Selected branch: '{branch_name}'")
                
            except Exception as e:
                logger.warning(f"Could not find branch search box: {e}, trying coordinate method")
                
                # Fallback: click in the center where branch selector usually appears
                # Based on screenshot: branch selector is in the center of the window
                click_x = window.left + (window.width // 2)
                click_y = window.top + (window.height // 2) - 50  # Slightly above center
                
                pyautogui.click(click_x, click_y)
                time.sleep(0.3)
                
                # Type branch name
                pyperclip.copy(branch_name)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.5)
                
                # Press Enter to select
                pyautogui.press('enter')
                
                await update.message.reply_text(
                    f"✅ Attempted to select branch '{branch_name}'!\n\n"
                    f"Use /claudescreen to verify the selection."
                )
                logger.info(f"Selected branch using coordinates: '{branch_name}'")
            
        except Exception as e:
            logger.error(f"Error selecting branch: {e}")
            await update.message.reply_text(
                f"❌ Could not select branch.\n\n"
                f"Make sure:\n"
                f"• You're in a new session (use /claudenew)\n"
                f"• You haven't started chatting yet\n"
                f"• The branch selector is visible\n\n"
                f"Error: {str(e)}"
            )
        
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
        time.sleep(0.5)
        
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
                
                time.sleep(1.5)  # Wait for repo to load
                
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
                time.sleep(1.5)
                
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
        time.sleep(0.5)
        
        import pyautogui
        
        # Click on repository selector to open the dropdown/modal
        try:
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
            
            # Try to find repository selector button
            try:
                # Method 1: Look for button with repo path pattern (e.g., "techgniouse/gigs-jobs-swipe")
                repo_btn = claude_window.child_window(title_re=".*/.+", control_type="Button")
                repo_btn.click_input()
                logger.info("Clicked repository selector button (remote repo) using pywinauto")
                time.sleep(1.5)  # Wait for modal to open
            except Exception:
                try:
                    # Method 2: Look for button with local folder name (e.g., "MyDigitalStudio")
                    # This handles when a local folder is already selected
                    repo_btn = claude_window.child_window(title_re=".*", control_type="Button", found_index=-1)
                    # Try to find button near bottom of window
                    for btn in claude_window.descendants(control_type="Button"):
                        btn_rect = btn.rectangle()
                        # Check if button is in bottom area of window (last 100px)
                        if btn_rect.bottom > window.top + window.height - 100:
                            try:
                                btn.click_input()
                                logger.info(f"Clicked repository selector button (local folder): {btn.window_text()}")
                                time.sleep(1.5)
                                break
                            except Exception:
                                continue
                    else:
                        raise Exception("No repo button found in bottom area")
                except Exception:
                    # Method 3: Fallback to coordinate-based clicking
                    # Click at bottom left where repo selector is located
                    click_x = window.left + 400
                    click_y = window.top + window.height - 40  # 40px from bottom
                    
                    pyautogui.click(click_x, click_y)
                    logger.info(f"Clicked repository selector at ({click_x}, {click_y})")
                    time.sleep(1.5)  # Wait for modal to open
        
        except Exception as e:
            logger.warning(f"Could not click repo selector: {e}, continuing anyway...")
        
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
        time.sleep(1.5)  # Wait for file dialog to open
        
        # Type the path in the folder path box
        pyperclip.copy(repo_path)
        pyautogui.hotkey('ctrl', 'l')  # Focus address bar in file dialog
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 'v')  # Paste path
        time.sleep(0.3)
        pyautogui.press('enter')  # Navigate to path
        time.sleep(0.8)  # Wait for folder to load
        
        # Click "Select Folder" button - try multiple methods
        select_folder_clicked = False
        
        # Method 1: Try to find "Select Folder" button by text
        try:
            # Look for the Select Folder button in the file dialog
            select_btn = claude_window.child_window(title_re=".*Select Folder.*", control_type="Button")
            select_btn.click_input()
            logger.info("Clicked 'Select Folder' button using pywinauto")
            select_folder_clicked = True
            time.sleep(1.0)
        except Exception:
            pass
        
        # Method 2: Try using Tab + Enter
        if not select_folder_clicked:
            try:
                pyautogui.press('tab')  # Tab to Select Folder button
                time.sleep(0.2)
                pyautogui.press('enter')  # Click it
                logger.info("Clicked 'Select Folder' using Tab+Enter")
                select_folder_clicked = True
                time.sleep(1.0)
            except Exception:
                pass
        
        # Method 3: Try Alt+S shortcut (common for Select button)
        if not select_folder_clicked:
            try:
                pyautogui.hotkey('alt', 's')
                logger.info("Clicked 'Select Folder' using Alt+S")
                select_folder_clicked = True
                time.sleep(1.0)
            except Exception:
                pass
        
        if not select_folder_clicked:
            logger.warning("Could not click 'Select Folder' button, trying to continue...")
            time.sleep(1.0)
        
        # Wait for Claude to process the selection
        time.sleep(1.5)
        
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
        time.sleep(0.5)
        
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



