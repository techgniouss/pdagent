"""Claude desktop automation command handlers."""

import logging
import os
import platform
import subprocess
import asyncio
import time
import io
from telegram import Update
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    PYWINAUTO_AVAILABLE,
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


# ── Claude composer input helpers ────────────────────────────────────────────
# Kept because /claudeschedule (scheduling.py) and recipe "claude_prompt" steps
# (workflow_recipes.py) drive Claude's desktop composer via send_prompt_to_claude.

# Composer-input hint terms used by the OCR fallback in _click_claude_input.
_INPUT_HINT_TERMS = (
    "reply", "todo", "ask", "type", "message", "chat",
    "prompt", "command", "describe", "task", "question",
)
_INPUT_PLACEHOLDER_TERMS = ("type", "/", "command")


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


def _click_claude_input(window, pyautogui) -> None:
    """Focus Claude's composer input using UIA/OCR fallbacks."""
    if PYWINAUTO_AVAILABLE:
        try:
            _load_win_deps()
            app = Application(backend="uia").connect(title_re=".*Claude.*")
            claude_window = app.window(title_re=".*Claude.*")
            for spec in (
                {
                    "title_re": r".*[Tt]ype\s*/\s*for\s*[Cc]ommand.*",
                    "control_type": "Text",
                },
                {
                    "title_re": r".*[Tt]ype\s*/\s*for\s*[Cc]ommand.*",
                    "control_type": "Edit",
                },
                {
                    "title_re": r".*[Tt]ype\s*/\s*for\s*[Cc]ommand.*",
                    "control_type": "Document",
                },
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
            bottom_height = max(180, min(320, int(window.height * 0.32)))
            screenshot = pyautogui.screenshot(
                region=(
                    window.left,
                    window.top + window.height - bottom_height,
                    window.width,
                    bottom_height,
                )
            )
            text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
            line_words: list[tuple[str, int, int, int, int]] = []
            for index, raw_word in enumerate(text_data["text"]):
                word = (raw_word or "").strip().lower()
                if not word:
                    continue
                left = int(text_data["left"][index])
                top = int(text_data["top"][index])
                width = int(text_data["width"][index])
                height = int(text_data["height"][index])
                line_words.append((word, left, top, width, height))

            # First pass: look for the exact placeholder phrase ("Type / for command").
            line_words.sort(key=lambda item: (item[2], item[1]))
            phrase_found = False
            for index in range(len(line_words)):
                word = line_words[index][0]
                if "type" not in word:
                    continue
                window_slice = line_words[index : index + 6]
                sequence = " ".join(item[0] for item in window_slice)
                if "/" not in sequence or "command" not in sequence:
                    continue
                phrase_left = min(item[1] for item in window_slice)
                phrase_top = min(item[2] for item in window_slice)
                phrase_right = max(item[1] + item[3] for item in window_slice)
                phrase_bottom = max(item[2] + item[4] for item in window_slice)
                click_x = window.left + ((phrase_left + phrase_right) // 2)
                # Click inside the textbox body (slightly below placeholder text baseline).
                click_y = window.top + window.height - bottom_height + phrase_bottom + max(
                    18,
                    int((phrase_bottom - phrase_top) * 0.8),
                )
                click_y = min(window.top + window.height - 20, click_y)
                pyautogui.click(click_x, click_y)
                time.sleep(0.4)
                logger.info(
                    "Focused Claude input via OCR placeholder phrase at (%s, %s)",
                    click_x,
                    click_y,
                )
                phrase_found = True
                break

            if phrase_found:
                return

            best_match = None
            for index, raw_word in enumerate(text_data["text"]):
                word = (raw_word or "").strip().lower()
                if not word:
                    continue
                term_score = 0
                if any(term in word for term in _INPUT_HINT_TERMS):
                    term_score += 2
                if any(term in word for term in _INPUT_PLACEHOLDER_TERMS):
                    term_score += 4
                if term_score == 0:
                    continue

                top = text_data["top"][index]
                height = text_data["height"][index]
                x = text_data["left"][index] + (text_data["width"][index] // 2) + window.left
                y = (
                    top
                    + (height // 2)
                    + window.top
                    + window.height
                    - bottom_height
                )
                # Favor words lower in the detected composer strip to avoid sidebar/header labels.
                vertical_score = y - window.top
                score = (term_score * 10000) + vertical_score
                if best_match is None or score > best_match[0]:
                    best_match = (score, x, y, word)

            if best_match:
                _, x, y, word = best_match
                pyautogui.click(x, y)
                time.sleep(0.4)
                logger.info("Focused Claude input via OCR term '%s' at (%s, %s)", word, x, y)
                return
        except Exception as exc:
            logger.warning("OCR input focus failed: %s", exc)

    # Coordinate fallback: click likely composer positions above the bottom bar.
    candidate_points = (
        (window.left + (window.width // 2), window.top + int(window.height * 0.86)),
        (window.left + (window.width // 2), window.top + int(window.height * 0.82)),
        (window.left + (window.width // 2), window.top + int(window.height * 0.78)),
    )
    for x, y in candidate_points:
        pyautogui.click(x, y)
        time.sleep(0.2)
    logger.info("Focused Claude input via coordinate fallback near composer area")


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
