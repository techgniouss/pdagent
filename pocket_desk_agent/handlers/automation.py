"""UI automation command handlers (OCR, click, scroll, type)."""

import logging
import os
import platform
import time
import io
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    PYWINAUTO_AVAILABLE,
    findui_options,
    record_action_if_active,
)

logger = logging.getLogger(__name__)

async def clicktext_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clicktext command - click at coordinates or search text."""
    if not update.message:
        return
    
    # Get arguments
    if not context.args:
        await update.message.reply_text(
            "Usage: /clicktext <x> <y>\n\n"
            "Click at specific screen coordinates.\n\n"
            "Examples:\n"
            "/clicktext 500 800 - Click at position (500, 800)\n\n"
            "Tip: Use /findtext <text> to find coordinates first."
        )
        return
    
    try:
        import pyautogui
        
        # Parse coordinates
        if len(context.args) >= 2:
            try:
                x = int(context.args[0])
                y = int(context.args[1])
                
                await update.message.reply_text(f"🖱️ Clicking at ({x}, {y})...")
                
                # Click at the specified position
                pyautogui.click(x, y)
                time.sleep(0.3)
                
                await update.message.reply_text(f"✅ Clicked at ({x}, {y})")
                logger.info(f"Clicked at coordinates ({x}, {y})")
                
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid coordinates. Please provide numbers.\n\n"
                    "Example: /clicktext 500 800"
                )
        else:
            await update.message.reply_text(
                "❌ Please provide both X and Y coordinates.\n\n"
                "Example: /clicktext 500 800"
            )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in clicktext_command: {e}", exc_info=True)


async def findtext_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /findtext command - find text on screen and show coordinates."""
    if not update.message:
        return
    
    # Get text argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /findtext <text>\n\n"
            "Find text on screen and show its coordinates.\n\n"
            "Examples:\n"
            "/findtext Reply\n"
            "/findtext Submit\n\n"
            "Shows coordinates so you can use /clicktext to click it."
        )
        return
    
    search_text = " ".join(context.args)
    
    await update.message.reply_text(f"🔍 Searching for '{search_text}'...")
    
    try:
        import pyautogui
        from PIL import Image, ImageDraw, ImageFont
        
        # Check if pytesseract is available
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
                        logger.info(f"Using Tesseract at: {path}")
                        break
        except ImportError:
            await update.message.reply_text(
                "❌ pytesseract not installed.\n\n"
                "Install: pip install pytesseract\n"
                "Then install Tesseract OCR from:\n"
                "https://github.com/UB-Mannheim/tesseract/releases"
            )
            return
        
        # Check if Tesseract is installed
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            await update.message.reply_text(
                "❌ Tesseract OCR not installed.\n\n"
                "Run `pdagent setup` to install automatically, or install manually:\n"
                "`winget install UB-Mannheim.TesseractOCR`\n\n"
                "After installing, restart the bot.",
                parse_mode="Markdown",
            )
            return
        
        logger.info(f"Searching for: {search_text}")

        # ── Recording check FIRST — if recording, save & skip OCR ──
        user_id = update.effective_user.id
        if record_action_if_active(user_id, "findtext", [search_text]):
            await update.message.reply_text(f"\U0001f4dd Recorded: `/findtext {search_text}`", parse_mode="Markdown")
            return
        
        # Take screenshot
        screenshot = pyautogui.screenshot()
        
        # Use OCR
        text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
        
        # Search (case-insensitive)
        search_lower = search_text.lower()
        matches = []
        
        for i, word in enumerate(text_data['text']):
            if word and search_lower in word.lower():
                x = text_data['left'][i] + (text_data['width'][i] // 2)
                y = text_data['top'][i] + (text_data['height'][i] // 2)
                matches.append((word, x, y, i))
        
        if matches:
            # Draw boxes
            draw = ImageDraw.Draw(screenshot)
            
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except Exception:
                font = ImageFont.load_default()
            
            for idx, (word, x, y, i) in enumerate(matches[:10]):
                left = text_data['left'][i]
                top = text_data['top'][i]
                width = text_data['width'][i]
                height = text_data['height'][i]
                
                draw.rectangle([left, top, left + width, top + height], outline="red", width=3)
                draw.text((left, top - 25), f"{idx+1}: ({x},{y})", fill="red", font=font)
            
            # Save
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Build message
            match_list = "\n".join([f"{idx+1}. '{m[0]}' at ({m[1]}, {m[2]})" for idx, m in enumerate(matches[:10])])
            
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=img_byte_arr,
                caption=f"\u2705 Found {len(matches)} match(es):\n\n{match_list}\n\nUse: /clicktext X Y"
            )
            logger.info(f"Found {len(matches)} matches")

        else:
            await update.message.reply_text(
                f"❌ '{search_text}' not found.\n\n"
                "Tips:\n"
                "• Text must be visible\n"
                "• Try single words\n"
                "• Check spelling"
            )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in findtext_command: {e}", exc_info=True)


async def smartclick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /smartclick command - find text and click with disambiguation."""
    if not update.message:
        return
    
    user_id = update.effective_user.id
    
    # Get text argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /smartclick <text>\n\n"
            "Find text on screen and click it. If multiple matches are found, "
            "you'll be able to choose which one to click.\n\n"
            "Examples:\n"
            "/smartclick Submit\n"
            "/smartclick Reply\n"
        )
        return
    
    search_text = " ".join(context.args)
    
    await update.message.reply_text(f"🔍 Searching for '{search_text}'...")
    
    try:
        import pyautogui
        from pocket_desk_agent.automation_utils import find_text_in_image, annotate_screenshot_with_markers
        
        # Check if pytesseract is available
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
                        logger.info(f"Using Tesseract at: {path}")
                        break
        except ImportError:
            await update.message.reply_text(
                "❌ pytesseract not installed.\n\n"
                "Install: pip install pytesseract\n"
                "Then install Tesseract OCR from:\n"
                "https://github.com/UB-Mannheim/tesseract/releases"
            )
            return
        
        # Check if Tesseract is installed
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            await update.message.reply_text(
                "❌ Tesseract OCR not installed.\n\n"
                "Run `pdagent setup` to install automatically, or install manually:\n"
                "`winget install UB-Mannheim.TesseractOCR`\n\n"
                "After installing, restart the bot.",
                parse_mode="Markdown",
            )
            return
        
        logger.info(f"Smart click searching for: {search_text}")
        
        # Take screenshot
        screenshot = pyautogui.screenshot()
        
        # Find all occurrences using utility function
        matches = find_text_in_image(screenshot, search_text)
        
        if len(matches) == 0:
            # No matches found
            await update.message.reply_text(
                f"❌ '{search_text}' not found on screen.\n\n"
                "Tips:\n"
                "• Make sure the text is visible\n"
                "• Try searching for single words\n"
                "• Check spelling\n\n"
                "💡 **Looking for a generic symbol or icon (like an 'X')?**\n"
                "Try using `/findelements`! This uses computer vision to label all clickable symbols on the screen, letting you choose exactly which one to click via `/clickelement <num>`.",
                parse_mode="Markdown"
            )
            logger.info(f"No matches found for '{search_text}'")
            
        elif len(matches) == 1:
            # Single match — recording check FIRST, then click
            match = matches[0]

            user_id = update.effective_user.id
            if record_action_if_active(user_id, "smartclick", [search_text]):
                await update.message.reply_text(f"\U0001f4dd Recorded: `/smartclick {search_text}`", parse_mode="Markdown")
                return

            pyautogui.click(match.x, match.y)
            await update.message.reply_text(
                f"\u2705 Clicked '{match.text}' at ({match.x}, {match.y})"
            )
            logger.info(f"Single match clicked at ({match.x}, {match.y})")
            
        else:
            # Multiple matches - show selection keyboard
            # Annotate screenshot with numbered markers
            annotated_screenshot = annotate_screenshot_with_markers(screenshot, matches)
            
            # Create inline keyboard with numbered buttons
            keyboard = []
            row = []
            for idx, match in enumerate(matches, start=1):
                # Create button with callback data containing index and coordinates
                button = InlineKeyboardButton(
                    f"{idx}",
                    callback_data=f"smartclick_{idx}_{match.x}_{match.y}"
                )
                row.append(button)
                
                # 5 buttons per row
                if len(row) == 5:
                    keyboard.append(row)
                    row = []
            
            # Add remaining buttons
            if row:
                keyboard.append(row)
            
            # Add cancel button
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="smartclick_cancel")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Save screenshot to bytes
            img_byte_arr = io.BytesIO()
            annotated_screenshot.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Build match list for caption
            match_list = "\n".join([
                f"{idx}. '{m.text}' at ({m.x}, {m.y})"
                for idx, m in enumerate(matches[:20], start=1)
            ])
            
            caption = (
                f"✅ Found {len(matches)} match(es) for '{search_text}':\n\n"
                f"{match_list}\n\n"
                f"Select which one to click:"
            )
            
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=img_byte_arr,
                caption=caption,
                reply_markup=reply_markup
            )
            
            logger.info(f"Found {len(matches)} matches, showing selection keyboard")
        
    except ImportError as e:
        await update.message.reply_text(
            f"❌ Missing dependency: {str(e)}\n\n"
            "Make sure pytesseract is installed:\n"
            "pip install pytesseract"
        )
        logger.error(f"Import error in smartclick_command: {e}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error in smartclick_command: {e}", exc_info=True)


async def findelements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /findelements command - find all UI elements on screen and label them."""
    if not update.message:
        return
        
    user_id = update.effective_user.id
    await update.message.reply_text("🔍 Scanning screen for UI icons and symbols...")
    
    try:
        import pyautogui
        from pocket_desk_agent.automation_utils import find_ui_elements, annotate_screenshot_with_markers
        
        screenshot = pyautogui.screenshot()
        matches = find_ui_elements(screenshot)
        
        if not matches:
            await update.message.reply_text("❌ No clickable UI elements found on the screen.")
            return
            
        # Store in dict for clickelement
        findui_options[user_id] = {}
        for idx, match in enumerate(matches, start=1):
            findui_options[user_id][idx] = (match.x, match.y)
            
        # Annotate and send image
        annotated = annotate_screenshot_with_markers(screenshot, matches)
        
        import io
        img_byte_arr = io.BytesIO()
        annotated.save(img_byte_arr, format='JPEG', quality=85)
        img_byte_arr = img_byte_arr.getvalue()
        
        await update.message.reply_photo(
            photo=img_byte_arr,
            caption=(
                f"✨ Found {len(matches)} potential graphical elements!\n\n"
                "To click one, use: `/clickelement <number>`\n"
                "Example: `/clickelement 5`"
            ),
            parse_mode="Markdown"
        )
        
        logger.info(f"Found {len(matches)} UI elements for user {user_id}")
        
    except ImportError:
        await update.message.reply_text(
            "❌ opencv-python or numpy could not be imported. "
            "Your installation may be incomplete or corrupted.\n\n"
            "Try reinstalling:\n"
            "`pip install --upgrade pocket-desk-agent`\n\n"
            "Then restart the bot.",
            parse_mode="Markdown",
        )
        logger.warning("findelements_command: opencv-python or numpy import failed — installation may be incomplete")
    except Exception as e:
        await update.message.reply_text(f"❌ Error finding elements: {str(e)}")
        logger.error(f"Error in findelements_command: {e}", exc_info=True)


async def clickelement_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clickelement command - click an element labeled by /findelements."""
    if not update.message:
        return
        
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Usage: /clickelement <number>\nExample: /clickelement 5")
        return
        
    try:
        element_num = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid number.")
        return
        
    if user_id not in findui_options or not findui_options[user_id]:
        await update.message.reply_text(
            "❌ No labeled elements found in memory. Please run `/findelements` first.",
            parse_mode="Markdown"
        )
        return
        
    if element_num not in findui_options[user_id]:
        max_num = max(findui_options[user_id].keys())
        await update.message.reply_text(f"❌ Invalid element number. Valid numbers are 1 to {max_num}.")
        return
        
    target_x, target_y = findui_options[user_id][element_num]
    
    # Check if we are recording
    if record_action_if_active(user_id, "clicktext", [target_x, target_y]):
        await update.message.reply_text(f"📝 Recorded: `/clicktext {target_x} {target_y}` (Element {element_num})", parse_mode="Markdown")
        # Clear the saved elements to free memory
        del findui_options[user_id]
        return
        
    try:
        import pyautogui
        pyautogui.click(target_x, target_y)
        await update.message.reply_text(f"✅ Clicked element {element_num} at ({target_x}, {target_y})")
        logger.info(f"User {user_id} clicked element {element_num} at ({target_x}, {target_y})")
        
        # We don't automatically delete `findui_options[user_id]` here just in case they want to click another one nearby
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error clicking element: {str(e)}")
        logger.error(f"Error in clickelement_command: {e}", exc_info=True)


async def pasteenter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pasteenter command - paste clipboard content and press Enter."""
    if not update.message:
        return
    
    try:
        import pyautogui
        import pyperclip
        
        # Record action if recording — skip actual execution if recording
        user_id = update.effective_user.id
        if record_action_if_active(user_id, "pasteenter", []):
            await update.message.reply_text("📝 Recorded: `/pasteenter`", parse_mode="Markdown")
            return  # Don't execute, just record

        # Check clipboard content
        clipboard_content = pyperclip.paste()
        
        if not clipboard_content:
            await update.message.reply_text(
                "❌ Clipboard is empty.\n\n"
                "Copy some text first, then use /pasteenter"
            )
            return
        
        await update.message.reply_text("⌨️ Pasting and pressing Enter...")
        
        # Execute Ctrl+V then Enter
        pyautogui.hotkey('ctrl', 'v')
        await asyncio.sleep(0.2)
        pyautogui.press('enter')
        
        # Send confirmation with text preview
        preview = clipboard_content[:200]
        if len(clipboard_content) > 200:
            preview += "..."
        
        await update.message.reply_text(
            f"✅ Pasted and pressed Enter\n\n"
            f"Text: {preview}"
        )
        logger.info(f"Paste-enter completed, text length: {len(clipboard_content)}")
        
    except ImportError as e:
        await update.message.reply_text(
            f"❌ Missing dependency: {str(e)}\n\n"
            "Install required packages:\n"
            "pip install pyautogui pyperclip"
        )
        logger.error(f"Import error in pasteenter_command: {e}")
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error executing paste and enter: {str(e)}"
        )
        logger.error(f"Error in pasteenter_command: {e}", exc_info=True)




async def typeenter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /typeenter command - type text and press Enter."""
    if not update.message:
        return
    
    # Get text argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /typeenter [_] <text>\n\n"
            "Type text and press Enter.\n"
            "• Use _ as first argument to join without spaces\n"
            "• Without _, keeps spaces between words\n\n"
            "Examples:\n"
            "/typeenter _ 1 9 1 6\n"
            "  → Types: 1916 and presses Enter\n\n"
            "/typeenter _ Check Issues\n"
            "  → Types: CheckIssues and presses Enter\n\n"
            "/typeenter Hello World\n"
            "  → Types: Hello World and presses Enter\n\n"
            "/typeenter Check the issues\n"
            "  → Types: Check the issues and presses Enter"
        )
        return
    
    # Check if first argument is underscore (no-space mode)
    if context.args[0] == "_":
        # Join without spaces
        text_to_type = "".join(context.args[1:])
    else:
        # Keep spaces between words
        text_to_type = " ".join(context.args)
    
    await update.message.reply_text(f"⌨️ Typing: {text_to_type}")
    
    try:
        import pyautogui
        
        # Record action if recording — skip actual typing if recording
        user_id = update.effective_user.id
        if record_action_if_active(user_id, "typeenter", context.args):
            await update.message.reply_text(f"📝 Recorded: `/typeenter {text_to_type}`", parse_mode="Markdown")
            return  # Don't execute, just record
        
        # Type the text
        pyautogui.write(text_to_type, interval=0.05)
        
        # Wait a bit
        await asyncio.sleep(0.2)
        
        # Press Enter
        pyautogui.press('enter')
        
        await update.message.reply_text(
            f"✅ Typed '{text_to_type}' and pressed Enter"
        )
        
        logger.info(f"Typed and entered: {text_to_type}")
        
    except ImportError as e:
        await update.message.reply_text(
            f"❌ Missing dependency: {str(e)}\n\n"
            "Install: pip install pyautogui"
        )
        logger.error(f"Import error in typeenter_command: {e}")
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error typing text: {str(e)}"
        )
        logger.error(f"Error in typeenter_command: {e}", exc_info=True)


async def scrollup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /scrollup [clicks] command."""
    if not update.message:
        return
        
    amount = 500
    if context.args:
        try:
            amount = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid number of clicks.")
            return

    user_id = update.effective_user.id
    if record_action_if_active(user_id, "scrollup", [str(amount)]):
        await update.message.reply_text(f"📝 Recorded: `/scrollup {amount}`", parse_mode="Markdown")
        return

    try:
        import pyautogui
        import pygetwindow as gw
        
        # Prefer the active window bounds (e.g. split screen)
        # We target the middle-right end (90% width, 50% height) to explicitly hit the Chat sidebar
        active_window = gw.getActiveWindow()
        if active_window:
            target_x = active_window.left + int(active_window.width * 0.90)
            target_y = active_window.top + int(active_window.height * 0.5)
        else:
            screen_width, screen_height = pyautogui.size()
            target_x, target_y = int(screen_width * 0.90), int(screen_height * 0.5)
            
        pyautogui.moveTo(target_x, target_y, duration=0.1)
        pyautogui.click()  # Gain focus on the chat pane before scrolling
        
        # Positive value means scroll up
        pyautogui.scroll(amount)
        await update.message.reply_text(f"✅ Scrolled up by {amount} clicks")
        logger.info(f"User {user_id} scrolled up {amount}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error scrolling: {str(e)}")
        logger.error(f"Error in scrollup_command: {e}", exc_info=True)


async def scrolldown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /scrolldown [clicks] command."""
    if not update.message:
        return
        
    amount = 500
    if context.args:
        try:
            amount = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid number of clicks.")
            return

    user_id = update.effective_user.id
    if record_action_if_active(user_id, "scrolldown", [str(amount)]):
        await update.message.reply_text(f"📝 Recorded: `/scrolldown {amount}`", parse_mode="Markdown")
        return

    try:
        import pyautogui
        import pygetwindow as gw
        
        # Prefer the active window bounds (e.g. split screen)
        # We target the middle-right end (90% width, 50% height) to explicitly hit the Chat sidebar
        active_window = gw.getActiveWindow()
        if active_window:
            target_x = active_window.left + int(active_window.width * 0.90)
            target_y = active_window.top + int(active_window.height * 0.5)
        else:
            screen_width, screen_height = pyautogui.size()
            target_x, target_y = int(screen_width * 0.90), int(screen_height * 0.5)
            
        pyautogui.moveTo(target_x, target_y, duration=0.1)
        pyautogui.click()  # Gain focus on the chat pane before scrolling
        
        # Negative value means scroll down
        pyautogui.scroll(-amount)
        await update.message.reply_text(f"✅ Scrolled down by {amount} clicks")
        logger.info(f"User {user_id} scrolled down {amount}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error scrolling: {str(e)}")
        logger.error(f"Error in scrolldown_command: {e}", exc_info=True)



