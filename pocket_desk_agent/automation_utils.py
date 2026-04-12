"""Utility functions for Windows automation commands."""

import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


@dataclass
class OCRMatch:
    """Represents a text match found via OCR."""
    text: str
    x: int  # Center X coordinate
    y: int  # Center Y coordinate
    left: int
    top: int
    width: int
    height: int
    confidence: float


def validate_command_name(name: str) -> bool:
    """
    Validate that a command name contains only alphanumeric characters and underscores.
    
    Args:
        name: The command name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_]+$', name))


def find_text_in_image(image: Image.Image, search_text: str) -> List[OCRMatch]:
    """
    Find all occurrences of text in an image using OCR with preprocessing.
    """
    try:
        import pytesseract
        import platform
        import os
        from PIL import ImageOps
        
        # Set Tesseract path for Windows if not already set
        if platform.system() == "Windows":
            try:
                pytesseract.get_tesseract_version()
            except Exception:
                tesseract_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
                ]
                for path in tesseract_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        break
    except ImportError:
        logger.error("pytesseract not installed")
        raise ImportError("pytesseract is required. Install: pip install pytesseract")
    
    matches = []
    search_text_lower = search_text.lower()
    
    try:
        # PREPROCESSING: Improve OCR accuracy for small text/buttons
        # 1. Convert to grayscale
        processed_image = ImageOps.grayscale(image)
        
        # 2. Resize (2x upscaling) to help with small UI elements
        width, height = processed_image.size
        upscale_factor = 2
        processed_image = processed_image.resize(
            (width * upscale_factor, height * upscale_factor), 
            resample=Image.LANCZOS
        )
        
        # Get OCR data with bounding boxes
        # Using --psm 11 (Sparse text) which is often better for UI buttons
        custom_config = r'--oem 3 --psm 11'
        ocr_data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT, config=custom_config)
        
        # Iterate through detected text
        n_boxes = len(ocr_data['text'])
        for i in range(n_boxes):
            text = ocr_data['text'][i].strip()
            if not text or len(text) < 2: # Ignore single character artifacts
                continue
                
            # Case-insensitive substring match
            if search_text_lower in text.lower():
                # Get coordinates in the upscaled image
                u_left = ocr_data['left'][i]
                u_top = ocr_data['top'][i]
                u_width = ocr_data['width'][i]
                u_height = ocr_data['height'][i]
                u_confidence = float(ocr_data['conf'][i])
                
                # Scale back to original coordinates
                left = u_left // upscale_factor
                top = u_top // upscale_factor
                width_orig = u_width // upscale_factor
                height_orig = u_height // upscale_factor
                
                # Calculate center coordinates on original scale
                center_x = left + width_orig // 2
                center_y = top + height_orig // 2
                
                match = OCRMatch(
                    text=text,
                    x=center_x,
                    y=center_y,
                    left=left,
                    top=top,
                    width=width_orig,
                    height=height_orig,
                    confidence=u_confidence
                )
                matches.append(match)
                
        logger.info(f"OCR Pre-processed: Found {len(matches)} occurrences of '{search_text}'")
        return matches
        
    except Exception as e:
        logger.error(f"OCR failed: {e}", exc_info=True)
        raise


def find_ui_elements(image: Image.Image) -> List[OCRMatch]:
    """
    Find all potential UI elements (icons, buttons, text blocks) on screen
    using OpenCV contour detection. Useful when OCR fails to detect symbols.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.error("opencv-python or numpy not found — package installation may be incomplete")
        raise ImportError(
            "opencv-python and numpy are required but could not be imported. "
            "Try reinstalling: pip install --upgrade pocket-desk-agent"
        )

    cv_image = np.array(image.convert('RGB'))
    gray = cv2.cvtColor(cv_image, cv2.COLOR_RGB2GRAY)
    
    # Use Canny edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Use a specifically stretched horizontal dilation kernel.
    # This physically merges adjacent text characters into wide horizontal blocks,
    # severely skewing their aspect ratio so they get completely dropped, 
    # while standalone icons and symbols (which are isolated) remain intact!
    morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (14, 5))
    dilated = cv2.dilate(edges, morph_kernel, iterations=1)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    matches = []
    
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        
        # Filter purely based on size: UI elements are usually between 12x12 and 150x150
        if 12 < w < 150 and 12 < h < 150:
            aspect_ratio = float(w) / h
            
            # Icons and single symbols are roughly square or slightly rectangular.
            # Three vertical dots ~0.2, three horizontal dots ~3.0
            if 0.2 < aspect_ratio < 3.2:
                # Calculate fill ratio to eliminate sparse, empty layout boxes
                contour_area = cv2.contourArea(c)
                fill_ratio = contour_area / (w * h)
                
                if fill_ratio > 0.3:
                    center_x = x + w // 2
                    center_y = y + h // 2
                    
                    # Simple overlap check to avoid cluster duplicates
                    overlap = False
                    for match in matches:
                        if abs(match.x - center_x) < max(20, w//2) and abs(match.y - center_y) < max(20, h//2):
                            overlap = True
                            break
                    
                    if not overlap:
                        match = OCRMatch(
                            text="UI Element",
                            x=center_x,
                            y=center_y,
                            left=x,
                            top=y,
                            width=w,
                            height=h,
                            confidence=1.0
                        )
                        matches.append(match)

    logger.info(f"UI Element Detection: Found {len(matches)} elements")
    
    # Sort matches row by row (top to bottom, left to right) for predictable numbering
    matches.sort(key=lambda m: (m.y // 20, m.x))
    
    return matches


def annotate_screenshot_with_markers(
    image: Image.Image,
    matches: List[OCRMatch]
) -> Image.Image:
    """
    Draw numbered markers on a screenshot at each match location.
    
    Args:
        image: PIL Image to annotate
        matches: List of OCRMatch objects to mark
        
    Returns:
        Annotated PIL Image
    """
    # Create a copy to avoid modifying original
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    
    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font = ImageFont.load_default()
    
    # Draw markers for each match
    for idx, match in enumerate(matches, start=1):
        # Draw clean bounding box outline around the element
        # This keeps the center (the icon itself) completely visible
        bbox_outline = [
            match.left - 2,
            match.top - 2,
            match.left + match.width + 2,
            match.top + match.height + 2
        ]
        draw.rectangle(bbox_outline, outline="red", width=2)
        
        # Prepare the number text
        number_text = str(idx)
        text_bbox = draw.textbbox((0, 0), number_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Position the text label tab at the top-left corner of the bounding box outline
        label_x = match.left - 2
        
        # Make sure the label doesn't go off the top of the screen
        label_y = match.top - 2 - text_height - 6
        if label_y < 0:
            label_y = match.top + match.height + 2  # Place it below if there's no room above
            
        bg_bbox = [
            label_x,
            label_y,
            label_x + text_width + 8,
            label_y + text_height + 8
        ]
        
        # Draw red label background with white text
        draw.rectangle(bg_bbox, fill="red")
        draw.text((label_x + 4, label_y + 2), number_text, fill="white", font=font)
    
    logger.info(f"Annotated screenshot with {len(matches)} markers")
    return annotated

# Key mapping for pyautogui
KEY_MAPPING = {
    'ctrl': 'ctrl',
    'control': 'ctrl',
    'alt': 'alt',
    'shift': 'shift',
    'win': 'win',
    'windows': 'win',
    'cmd': 'command',
    'command': 'command',
    'esc': 'escape',
    'escape': 'escape',
    'del': 'delete',
    'delete': 'delete',
    'backspace': 'backspace',
    'tab': 'tab',
    'enter': 'enter',
    'return': 'enter',
    'space': 'space',
    'up': 'up',
    'down': 'down',
    'left': 'left',
    'right': 'right',
    'pageup': 'pageup',
    'pagedown': 'pagedown',
    'home': 'home',
    'end': 'end',
    'insert': 'insert',
}

# Add function keys f1-f12
for i in range(1, 13):
    KEY_MAPPING[f'f{i}'] = f'f{i}'


def map_keys_to_pyautogui(hotkey_str: str) -> List[str]:
    """
    Map a hotkey string (e.g., 'ctrl+c') to a list of pyautogui key names.
    
    Args:
        hotkey_str: Hotkey string with keys separated by '+' or spaces
        
    Returns:
        List of valid pyautogui key names
    """
    # Parse the hotkey string
    keys = [k.strip().lower() for k in hotkey_str.replace("+", " ").split()]
    
    mapped_keys = []
    for key in keys:
        if key in KEY_MAPPING:
            mapped_keys.append(KEY_MAPPING[key])
        elif len(key) == 1:  # Single character (letter/number)
            mapped_keys.append(key)
        else:
            logger.warning(f"Unknown key: '{key}'")
            # If unknown but not mapping, keep as is (pyautogui might handle it)
            mapped_keys.append(key)
            
    return mapped_keys
