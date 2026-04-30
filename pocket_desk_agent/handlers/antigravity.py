"""Antigravity and VS Code integration command handlers."""

import asyncio
import logging
import os
import platform
import subprocess
import time
import threading
from pathlib import Path
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

_BROWSER_PATHS = {
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
_BROWSER_FALLBACK_NAMES = {
    "edge": "msedge",
    "chrome": "chrome",
    "firefox": "firefox",
    "brave": "brave",
}
_BROWSER_LABELS = {
    "edge": "Microsoft Edge",
    "chrome": "Google Chrome",
    "firefox": "Mozilla Firefox",
    "brave": "Brave",
}
_FOLDER_SCAN_LIMIT = 40


def _find_vscode_window():
    """Return the first visible VS Code window, if any."""
    try:
        import pygetwindow as _gw

        for window in _gw.getAllWindows():
            try:
                if "visual studio code" in window.title.lower() and window.visible:
                    return window
            except Exception:
                continue

        for window in _gw.getAllWindows():
            try:
                title = window.title.lower()
                if "code" in title and window.visible and window.width > 200:
                    return window
            except Exception:
                continue
    except Exception as exc:
        logger.error(f"Error finding VS Code window: {exc}")

    return None


def _run_vscode_palette_command(command_text: str) -> tuple[bool, str]:
    """Focus VS Code and execute a command palette entry."""
    try:
        import pyautogui
    except ImportError:
        return False, "pyautogui is not installed.\n\nRun: pip install pyautogui"

    vscode_window = _find_vscode_window()
    if not vscode_window:
        return False, "Could not find VS Code window.\n\nMake sure VS Code is open and try again."

    try:
        if vscode_window.isMinimized:
            vscode_window.restore()
            time.sleep(0.5)
        vscode_window.activate()
    except Exception:
        pass

    time.sleep(0.8)
    pyautogui.hotkey('ctrl', 'shift', 'p')
    time.sleep(0.7)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyautogui.write(command_text, interval=0.04)
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(0.5)

    return True, ""


def _discover_candidate_folders(limit: int = _FOLDER_SCAN_LIMIT) -> list[str]:
    """Return likely workspace folders from approved roots and common dev locations."""
    from pocket_desk_agent.handlers._shared import file_manager

    seed_paths = list(getattr(Config, "APPROVED_DIRECTORIES", []))
    common = [
        str(Path.home()),
        str(Path.home() / "Downloads"),
        str(Path.home() / "Desktop"),
        str(Path.home() / "Documents"),
        os.path.expandvars(r"%USERPROFILE%\source"),
        os.path.expandvars(r"%USERPROFILE%\repos"),
    ]
    for candidate in common:
        if os.path.isdir(candidate) and candidate not in seed_paths:
            seed_paths.append(candidate)

    folders: list[str] = []
    seen: set[str] = set()
    for root in seed_paths:
        root_path = Path(os.path.expandvars(root)).expanduser()
        if not root_path.is_dir():
            continue

        normalized_root = str(root_path.resolve())
        if not file_manager._is_safe_path(Path(normalized_root)):
            continue
        if normalized_root not in seen:
            seen.add(normalized_root)
            folders.append(normalized_root)
            if len(folders) >= limit:
                break

        try:
            for entry in os.scandir(normalized_root):
                if not entry.is_dir(follow_symlinks=False):
                    continue
                normalized_subdir = str(Path(entry.path).expanduser().resolve())
                if not file_manager._is_safe_path(Path(normalized_subdir)):
                    continue
                if normalized_subdir in seen:
                    continue
                seen.add(normalized_subdir)
                folders.append(normalized_subdir)
                if len(folders) >= limit:
                    return folders
        except PermissionError:
            continue

    return folders[:limit]


def resolve_workspace_folder(query: str) -> tuple[bool, str]:
    """Resolve a folder path or folder name to one safe workspace path."""
    from pocket_desk_agent.handlers._shared import file_manager

    raw_query = query.strip()
    if not raw_query:
        return False, "Please provide a folder path or folder name."

    direct_path = Path(os.path.expandvars(raw_query)).expanduser()
    if direct_path.exists() and direct_path.is_dir():
        if file_manager._is_safe_path(direct_path):
            return True, str(direct_path.resolve())
        return False, f"Access denied: {direct_path} is outside the approved directories."

    folders = _discover_candidate_folders()
    lowered_query = raw_query.lower()
    exact_matches = [
        folder for folder in folders
        if lowered_query == os.path.basename(folder).lower() or lowered_query == folder.lower()
    ]
    matches = exact_matches or [
        folder for folder in folders
        if lowered_query in os.path.basename(folder).lower() or lowered_query in folder.lower()
    ]

    if not matches:
        return False, f"No folder matched '{raw_query}'."
    if len(matches) == 1:
        return True, matches[0]

    preview = "\n".join(f"- {path}" for path in matches[:6])
    if len(matches) > 6:
        preview += "\n- ..."
    return False, f"Multiple folders matched '{raw_query}'. Please be more specific.\n\n{preview}"


def launch_browser(browser_key: str) -> tuple[bool, str]:
    """Open a supported browser in a maximized window."""
    browser = browser_key.strip().lower()
    if browser not in _BROWSER_LABELS:
        supported = ", ".join(sorted(_BROWSER_LABELS))
        return False, f"Unsupported browser '{browser_key}'. Choose one of: {supported}."

    exe_path = next((path for path in _BROWSER_PATHS.get(browser, []) if os.path.exists(path)), None)
    label = _BROWSER_LABELS[browser]

    try:
        if exe_path:
            subprocess.Popen([exe_path, "--start-maximized"], shell=False)
        else:
            subprocess.Popen(f'start /max "" {_BROWSER_FALLBACK_NAMES[browser]}', shell=True)
        return True, f"Opening {label} in a maximized window."
    except Exception as exc:
        logger.error("Failed to open browser %s: %s", browser, exc, exc_info=True)
        return False, f"Failed to open {label}: {exc}"


def open_folder_in_vscode(folder_path: str) -> tuple[bool, str]:
    """Open a folder in VS Code, focusing the app first when possible."""
    from pocket_desk_agent.handlers._shared import file_manager

    target_path = Path(os.path.expandvars(folder_path)).expanduser()
    if not target_path.is_dir():
        return False, f"Folder not found: {target_path}"
    target = str(target_path.resolve())
    if not file_manager._is_safe_path(Path(target)):
        return False, f"Access denied: {target} is outside the approved directories."

    if platform.system() == "Windows":
        try:
            import pyautogui
            import pyperclip
        except ImportError as exc:
            return False, f"Missing dependency: {exc}"

        vscode_window = _find_vscode_window()
        if vscode_window:
            try:
                if vscode_window.isMinimized:
                    vscode_window.restore()
                    time.sleep(0.5)
                vscode_window.activate()
            except Exception:
                pass

            time.sleep(0.8)
            pyautogui.hotkey('ctrl', 'k')
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'o')
            time.sleep(1.2)
            pyperclip.copy(target)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.6)
            pyautogui.press('enter')
            time.sleep(0.5)
            return True, f"VS Code is opening folder:\n`{target}`"

        try:
            subprocess.Popen(["code", target], shell=False)
            return True, f"Launched VS Code with folder:\n`{target}`"
        except Exception as exc:
            logger.error("Failed to launch VS Code with %s: %s", target, exc, exc_info=True)
            return False, f"Failed to open VS Code folder {target}: {exc}"

    try:
        subprocess.Popen(["code", target], shell=False)
        return True, f"Opened in VS Code:\n`{target}`"
    except Exception as exc:
        logger.error("Failed to launch VS Code with %s: %s", target, exc, exc_info=True)
        return False, f"Failed to open VS Code folder {target}: {exc}"


def launch_claude_cli(folder_path: str, initial_prompt: str = "") -> tuple[bool, str]:
    """Open Claude CLI in a folder and optionally send an initial prompt."""
    from pocket_desk_agent.handlers._shared import file_manager

    target_path = Path(os.path.expandvars(folder_path)).expanduser()
    if not target_path.is_dir():
        return False, f"Folder not found: {target_path}"
    target = str(target_path.resolve())
    if not file_manager._is_safe_path(Path(target)):
        return False, f"Access denied: {target} is outside the approved directories."
    if platform.system() != "Windows":
        return False, "Claude CLI launching is currently only supported on Windows."

    def launch_and_type() -> None:
        try:
            subprocess.Popen(["cmd.exe", "/k", "title Claude CLI && claude"], cwd=target)
            if not initial_prompt:
                return

            import pyautogui
            import pygetwindow as _gw

            window_found = False
            for _ in range(10):
                time.sleep(1.0)
                for window in _gw.getAllWindows():
                    if "Claude CLI" not in window.title or not window.visible:
                        continue
                    try:
                        if window.isMinimized:
                            window.restore()
                        window.activate()
                        time.sleep(0.5)
                        window_found = True
                        break
                    except Exception:
                        continue
                if window_found:
                    break

            if window_found:
                time.sleep(1.5)
                pyautogui.write(initial_prompt, interval=0.01)
                pyautogui.press('enter')
            else:
                logger.error("Could not find Claude CLI window to type prompt into")
        except Exception as exc:
            logger.error("Error launching Claude CLI in %s: %s", target, exc, exc_info=True)

    threading.Thread(target=launch_and_type, daemon=True).start()
    if initial_prompt:
        return True, f"Claude CLI opened in:\n`{target}`\n\nInitial prompt queued."
    return True, f"Claude CLI opened in:\n`{target}`"


def send_prompt_to_claude_cli(prompt: str) -> tuple[bool, str]:
    """Send a prompt to the active Claude CLI window."""
    if platform.system() != "Windows":
        return False, "This feature is only supported on Windows."

    message = prompt.strip()
    if not message:
        return False, "Please provide a prompt to send to Claude CLI."

    try:
        import pyautogui
        import pygetwindow as _gw
    except ImportError as exc:
        return False, f"Missing dependency: {exc}"

    for window in _gw.getAllWindows():
        if "Claude CLI" not in window.title or not window.visible:
            continue
        try:
            if window.isMinimized:
                window.restore()
            window.activate()
            time.sleep(0.5)
            pyautogui.write(message, interval=0.01)
            pyautogui.press('enter')
            return True, "Follow-up prompt sent to Claude CLI."
        except Exception:
            continue

    return False, "Could not find the open Claude CLI window. Run /claudecli first."


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
    
    await update.message.reply_text("Opening Antigravity desktop app...")
    
    try:
        # First check if Antigravity is already running
        if PYWINAUTO_AVAILABLE:
            window = find_antigravity_window()
            if window:
                try:
                    if window.isMinimized:
                        window.restore()
                        await asyncio.sleep(0.5)
                    window.activate()
                    await asyncio.sleep(0.3)
                    await update.message.reply_text(
                        "Antigravity app is now active!\n\n"
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
                await asyncio.sleep(3)
                await update.message.reply_text("Attempted to open Antigravity via protocol handler.")
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
                        await update.message.reply_text(f"Opening Antigravity from: {path}")
                        return
                
                await update.message.reply_text(
                    "Could not find Antigravity installation.\n\n"
                    "Please ensure Antigravity is installed and in your PATH, or that the protocol handler is registered."
                )
        else:
            await update.message.reply_text(f"/openantigravity is currently optimized for Windows.")
            
    except Exception as e:
        await update.message.reply_text(f"Error opening Antigravity: {str(e)}")


async def antigravitychat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /antigravitychat command - open agent chat (Ctrl+Shift+P then Ctrl+L)."""
    if not update.message:
        return
    
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text("UI automation is only available on Windows with pywinauto.")
        return
        
    window = find_antigravity_window()
    if not window:
        await update.message.reply_text("Antigravity window not found. Try /openantigravity first.")
        return
    
    try:
        window.activate()
        await asyncio.sleep(0.5)
        
        # Sequence provided by user: Ctrl+Shift+P then Ctrl+L
        send_keys('^+p')
        await asyncio.sleep(0.8)
        send_keys('^l')
        
        await update.message.reply_text("Sent command sequence to Antigravity (Ctrl+Shift+P -> Ctrl+L).")
        logger.info("Executed Antigravity chat sequence")
    except Exception as e:
        await update.message.reply_text(f"Error sending commands: {str(e)}")


async def antigravitymode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /antigravitymode command - select Planning/Fast mode via OCR click."""
    if not update.message:
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /antigravitymode <planning|fast>")
        return
        
    mode = context.args[0].lower()
    if mode not in ["planning", "fast"]:
        await update.message.reply_text("Mode must be 'planning' or 'fast'.")
        return
        
    await update.message.reply_text(f"Attempting to switch to {mode} mode...")

    try:
        import pyautogui
        from pocket_desk_agent.automation_utils import find_text_in_image
        from PIL import ImageGrab

        window = find_antigravity_window()
        if window:
            window.activate()
            await asyncio.sleep(0.5)

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
            await asyncio.sleep(0.8)

            # Step 3: re-scan for the mode option in the now-open dropdown
            screenshot = ImageGrab.grab()
            matches = find_text_in_image(screenshot, mode_label)

        if matches:
            pyautogui.click(matches[0].x, matches[0].y)
            await update.message.reply_text(
                f"Switched to {mode_label} mode (clicked at {matches[0].x}, {matches[0].y})."
            )
            logger.info(f"Switched Antigravity mode to {mode_label}")
        else:
            await update.message.reply_text(
                f"Could not find '{mode_label}' option on screen.\n\n"
                "Make sure Antigravity is open and the mode selector is visible."
            )

    except Exception as e:
        await update.message.reply_text(f"Error switching mode: {str(e)}")


async def antigravitymodel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /antigravitymodel command - select or list Antigravity models."""
    if not PYWINAUTO_AVAILABLE:
        await update.message.reply_text("Automation is only available on Windows.")
        return
        
    window = find_antigravity_window()
    if not window:
        await update.message.reply_text("Antigravity window not found. Try /openantigravity first.")
        return

    import pyautogui
    from pocket_desk_agent.automation_utils import find_text_in_image
    from PIL import ImageGrab
    
    # LISTING MODE: /antigravitymodel (no args)
    if not context.args:
        await update.message.reply_text("Locating model selector to list available models...")
        try:
            window.activate()
            await asyncio.sleep(0.5)
            
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
                await asyncio.sleep(1.0) # Wait for dropdown
                
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
                    msg = "Available Antigravity Models:\n\n"
                    msg += "\n".join([f"- {m}" for m in models])
                    msg += "\n\nUse `/antigravitymodel <name>` to select one."
                    await update.message.reply_text(msg)
                else:
                    await update.message.reply_text("Found the selector but couldn't read the model list. Please try again.")
            else:
                await update.message.reply_text("Could not locate the model selector on screen.")
        except Exception as e:
            await update.message.reply_text(f"Error listing models: {str(e)}")
        return
        
    # SELECTION MODE: /antigravitymodel <model_name>
    model_name = " ".join(context.args)
    await update.message.reply_text(f"Attempting to select model: {model_name}...")
    
    try:
        window.activate()
        await asyncio.sleep(0.8)
        
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
                await asyncio.sleep(0.5)
                # If a new list appeared, we need to click again. Let's assume it might have been the trigger.
                break
        
        # 2. If not found or if we think we clicked the trigger, check again
        await asyncio.sleep(0.5)
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
                    await asyncio.sleep(1.0)
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
            await update.message.reply_text(f"Selected model '{model_name}' successfully.")
            logger.info(f"Model selected: {model_name}")
        else:
            await update.message.reply_text(
                f"Could not find model '{model_name}'.\n"
                "Verify spelling or use /antigravitymodel without arguments to see available list."
            )
            
    except Exception as e:
        await update.message.reply_text(f"Error during model selection: {str(e)}")


# Build Workflow Commands

# Store build state for conversational flow
build_state = {}

# Store large file upload choices
large_file_upload_state = {}




async def antigravityclaudecodeopen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /antigravityclaudecodeopen command - open Claude Code extension panel in VS Code."""
    if not update.message:
        return

    await update.message.reply_text("Opening Claude Code panel in VS Code...")

    try:
        success, error_message = _run_vscode_palette_command("Claude: Focus on Claude Code Input")
        if not success:
            await update.message.reply_text(f"{error_message}")
            return

        await update.message.reply_text(
            "Claude Code panel opened in VS Code!\n\n"
            "The extension chat should now be visible."
        )
        logger.info("Opened Claude Code panel in VS Code via command palette")

    except Exception as e:
        await update.message.reply_text(f"Error opening Claude Code panel: {str(e)}")
        logger.error(f"Error in antigravityclaudecodeopen_command: {e}", exc_info=True)


async def openclaudeinvscode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /openclaudeinvscode command - run Claude Code: Open in VS Code."""
    if not update.message:
        return

    await update.message.reply_text("Opening Claude Code in VS Code...")

    try:
        success, error_message = _run_vscode_palette_command("Claude Code: Open")
        if not success:
            await update.message.reply_text(f"{error_message}")
            return

        await update.message.reply_text(
            "Sent `Claude Code: Open` to the VS Code command palette.",
            parse_mode="Markdown",
        )
        logger.info("Executed Claude Code: Open in VS Code")
    except Exception as e:
        await update.message.reply_text(f"Error opening Claude Code in VS Code: {str(e)}")
        logger.error(f"Error in openclaudeinvscode_command: {e}", exc_info=True)


async def claudecli_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudecli - open directly when a folder arg resolves, else show picker."""
    if not update.message:
        return

    user_id = update.effective_user.id
    prompt = " ".join(context.args) if context.args else ""

    await update.message.reply_text("Scanning folders for Claude CLI...")

    try:
        if context.args:
            folder_query = context.args[0].strip()
            if folder_query:
                resolved, payload = resolve_workspace_folder(folder_query)
                normalized_query = folder_query.lower()
                resolved_name = os.path.basename(payload).lower() if resolved else ""
                is_explicit_dir = Path(os.path.expandvars(folder_query)).expanduser().is_dir()
                if resolved and (
                    is_explicit_dir
                    or normalized_query == resolved_name
                    or normalized_query == payload.lower()
                ):
                    direct_prompt = " ".join(context.args[1:]).strip()
                    await update.message.reply_text(
                        f"Opening Claude CLI in `{payload}`...",
                        parse_mode="Markdown",
                    )
                    success, message = launch_claude_cli(payload, direct_prompt)
                    await update.message.reply_text(message, parse_mode="Markdown")
                    if not success:
                        logger.warning("claudecli direct launch failed: %s", message)
                    return

        folders = _discover_candidate_folders(limit=_FOLDER_SCAN_LIMIT)
        if not folders:
            await update.message.reply_text(
                "No folders found.\n\n"
                "Check that APPROVED_DIRECTORIES is configured in your Pocket Desk Agent config."
            )
            return

        claudecli_options[user_id] = {
            "paths": {i: p for i, p in enumerate(folders)},
            "prompt": prompt,
        }

        keyboard = []
        for i, path in enumerate(folders):
            label = f"Folder: {os.path.basename(path) or path}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"claudecli_{i}")])

        message_text = f"*Select a repo to open in Claude CLI:*\n\n_{len(folders)} folder(s) found_"
        if prompt:
            message_text += f"\n\n*Prompt to send:* `{prompt}`"

        await update.message.reply_text(
            message_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as exc:
        await update.message.reply_text(f"Error listing folders: {exc}")
        logger.error("Error in claudecli_command: %s", exc, exc_info=True)

async def claudeclisend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claudeclisend - type a followup prompt into the open Claude CLI window."""
    if not update.message:
        return

    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text(
            "Please provide a prompt.\n"
            "Example: `/claudeclisend expand on that last explanation`",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text("Sending follow-up to Claude CLI...")

    success, message = send_prompt_to_claude_cli(prompt)
    await update.message.reply_text(message)
    if not success:
        logger.warning("claudeclisend failed: %s", message)

async def antigravityopenfolder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /antigravityopenfolder - open a provided path or show folder picker."""
    if not update.message:
        return

    user_id = update.effective_user.id
    await update.message.reply_text("Scanning folders...")

    try:
        if context.args:
            query = " ".join(context.args).strip()
            resolved, payload = resolve_workspace_folder(query)
            if not resolved:
                await update.message.reply_text(payload)
                return

            await update.message.reply_text(
                f"Opening `{payload}` in VS Code...",
                parse_mode="Markdown",
            )
            success, message = open_folder_in_vscode(payload)
            await update.message.reply_text(message, parse_mode="Markdown")
            if not success:
                logger.warning("antigravityopenfolder direct launch failed: %s", message)
            return

        folders = _discover_candidate_folders(limit=_FOLDER_SCAN_LIMIT)
        if not folders:
            await update.message.reply_text(
                "No folders found.\n\n"
                "Check that APPROVED_DIRECTORIES is configured in your Pocket Desk Agent config."
            )
            return

        openfolder_options[user_id] = {i: p for i, p in enumerate(folders)}

        keyboard = []
        for i, path in enumerate(folders):
            label = f"Folder: {os.path.basename(path) or path}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"openfolder_{i}")])

        await update.message.reply_text(
            f"*Select a folder to open in VS Code:*\n\n_{len(folders)} folder(s) found_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as exc:
        await update.message.reply_text(f"Error listing folders: {exc}")
        logger.error("Error in antigravityopenfolder_command: %s", exc, exc_info=True)

async def openbrowser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /openbrowser - open requested browser directly or show picker keyboard."""
    if not update.message:
        return

    if context.args:
        success, message = launch_browser(context.args[0])
        await update.message.reply_text(message)
        if not success:
            logger.warning("openbrowser direct launch failed: %s", message)
        return

    keyboard = []
    for key, paths in _BROWSER_PATHS.items():
        installed = any(os.path.exists(p) for p in paths)
        if installed or key in {"edge", "chrome"}:
            label = _BROWSER_LABELS.get(key, key.title())
            keyboard.append([InlineKeyboardButton(label, callback_data=f"browser_{key}")])

    if not keyboard:
        await update.message.reply_text("No supported browsers detected on this system.")
        return

    await update.message.reply_text(
        "*Which browser would you like to open?*\n\n"
        "_The selected browser will open maximized._",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )





