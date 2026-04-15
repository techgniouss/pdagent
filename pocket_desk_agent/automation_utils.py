"""Utility functions for Windows automation commands."""

import os
import platform
import re
import logging
import ctypes
from difflib import SequenceMatcher
from typing import Any, Callable, List, Optional
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

logger = logging.getLogger(__name__)

_UOI_NAME = 2


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
    except ImportError:
        logger.error("pytesseract not installed")
        raise ImportError("pytesseract is required. Install: pip install pytesseract")

    _configure_tesseract(pytesseract)

    cleaned_search_text = search_text.strip()
    if not cleaned_search_text:
        return []

    normalized_search = _normalize_ocr_text(cleaned_search_text)
    compact_search = _compact_ocr_text(cleaned_search_text)
    search_words = _split_normalized_words(cleaned_search_text)
    max_window = max(1, min(max(len(search_words) + 2, 3), 8))
    scored_matches: list[tuple[float, OCRMatch]] = []

    try:
        for processed_image, upscale_factor, config in _build_ocr_passes(image):
            ocr_data = pytesseract.image_to_data(
                processed_image,
                output_type=pytesseract.Output.DICT,
                config=config,
            )
            words = _extract_ocr_words(ocr_data, upscale_factor)
            candidates = _build_phrase_candidates(words, max_window=max_window)
            for candidate in candidates:
                score = _score_ocr_candidate(
                    candidate["text"],
                    normalized_search,
                    compact_search,
                )
                if score is None:
                    continue
                match = OCRMatch(
                    text=candidate["text"],
                    x=candidate["x"],
                    y=candidate["y"],
                    left=candidate["left"],
                    top=candidate["top"],
                    width=candidate["width"],
                    height=candidate["height"],
                    confidence=max(candidate["confidence"], score * 100.0),
                )
                scored_matches.append((score, match))

        matches = _dedupe_scored_matches(scored_matches)
        logger.info(f"OCR multi-pass: Found {len(matches)} occurrences of '{search_text}'")
        return matches

    except Exception as e:
        logger.error(f"OCR failed: {e}", exc_info=True)
        raise


def _configure_tesseract(pytesseract: Any) -> None:
    """Configure the Tesseract executable path on Windows when needed."""
    if platform.system() != "Windows":
        return

    try:
        pytesseract.get_tesseract_version()
        return
    except Exception:
        pass

    tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for path in tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return


def _build_ocr_passes(image: Image.Image) -> List[tuple[Image.Image, int, str]]:
    """Create a small set of OCR-friendly image variants for button and screen text."""
    grayscale = ImageOps.grayscale(image)
    upscale_factor = 2
    base = grayscale.resize(
        (grayscale.width * upscale_factor, grayscale.height * upscale_factor),
        resample=Image.LANCZOS,
    )
    sharpened = base.filter(ImageFilter.SHARPEN)
    high_contrast = ImageOps.autocontrast(sharpened)
    thresholded = high_contrast.point(lambda px: 255 if px > 165 else 0)
    inverted = ImageOps.invert(thresholded)

    return [
        (base, upscale_factor, "--oem 3 --psm 11"),
        (high_contrast, upscale_factor, "--oem 3 --psm 6"),
        (thresholded, upscale_factor, "--oem 3 --psm 11"),
        (inverted, upscale_factor, "--oem 3 --psm 11"),
    ]


def _extract_ocr_words(ocr_data: dict[str, list[Any]], upscale_factor: int) -> List[dict[str, Any]]:
    """Normalize raw Tesseract word boxes into a simpler structure."""
    words: List[dict[str, Any]] = []
    for index, raw_text in enumerate(ocr_data.get("text", [])):
        text = str(raw_text).strip()
        normalized = _normalize_ocr_text(text)
        compact = _compact_ocr_text(text)
        if not compact:
            continue

        width = max(1, int(ocr_data["width"][index]) // upscale_factor)
        height = max(1, int(ocr_data["height"][index]) // upscale_factor)
        left = int(ocr_data["left"][index]) // upscale_factor
        top = int(ocr_data["top"][index]) // upscale_factor

        words.append(
            {
                "text": text,
                "normalized": normalized,
                "compact": compact,
                "left": left,
                "top": top,
                "width": width,
                "height": height,
                "x": left + width // 2,
                "y": top + height // 2,
                "confidence": _safe_float(ocr_data.get("conf", []), index),
                "line_key": (
                    ocr_data.get("block_num", [0])[index] if len(ocr_data.get("block_num", [])) > index else 0,
                    ocr_data.get("par_num", [0])[index] if len(ocr_data.get("par_num", [])) > index else 0,
                    ocr_data.get("line_num", [0])[index] if len(ocr_data.get("line_num", [])) > index else 0,
                ),
            }
        )

    return words


def _build_phrase_candidates(words: List[dict[str, Any]], max_window: int) -> List[dict[str, Any]]:
    """Build single-word and multi-word OCR candidates from nearby line text."""
    candidates: List[dict[str, Any]] = []
    for word in words:
        candidates.append(word)

    grouped_lines: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for word in words:
        grouped_lines.setdefault(word["line_key"], []).append(word)

    for line_words in grouped_lines.values():
        ordered_words = sorted(line_words, key=lambda item: (item["left"], item["top"]))
        if len(ordered_words) < 2:
            continue

        for start in range(len(ordered_words)):
            for end in range(start + 2, min(len(ordered_words), start + max_window) + 1):
                chunk = ordered_words[start:end]
                left = min(item["left"] for item in chunk)
                top = min(item["top"] for item in chunk)
                right = max(item["left"] + item["width"] for item in chunk)
                bottom = max(item["top"] + item["height"] for item in chunk)
                phrase_text = " ".join(item["text"] for item in chunk)
                candidates.append(
                    {
                        "text": phrase_text,
                        "normalized": _normalize_ocr_text(phrase_text),
                        "compact": _compact_ocr_text(phrase_text),
                        "left": left,
                        "top": top,
                        "width": right - left,
                        "height": bottom - top,
                        "x": left + ((right - left) // 2),
                        "y": top + ((bottom - top) // 2),
                        "confidence": sum(item["confidence"] for item in chunk) / len(chunk),
                        "line_key": chunk[0]["line_key"],
                    }
                )

    return candidates


def _score_ocr_candidate(
    candidate_text: str,
    normalized_search: str,
    compact_search: str,
) -> Optional[float]:
    """Return a match score between 0 and 1, or None when not similar enough."""
    normalized_candidate = _normalize_ocr_text(candidate_text)
    compact_candidate = _compact_ocr_text(candidate_text)
    if not compact_candidate:
        return None

    if compact_candidate == compact_search:
        return 1.0
    if normalized_candidate == normalized_search:
        return 0.99
    if compact_search and compact_search in compact_candidate:
        return 0.97
    if normalized_search and normalized_search in normalized_candidate:
        return 0.94

    compact_ratio = SequenceMatcher(None, compact_search, compact_candidate).ratio()
    normalized_ratio = SequenceMatcher(None, normalized_search, normalized_candidate).ratio()
    ratio = max(compact_ratio, normalized_ratio)

    if len(compact_search) <= 2:
        if compact_candidate == compact_search:
            return 1.0
        return None

    if ratio >= 0.88:
        return ratio
    if ratio >= 0.76 and _token_overlap(normalized_search, normalized_candidate) >= 0.75:
        return ratio
    return None


def _token_overlap(left: str, right: str) -> float:
    """Measure how many search tokens appear in the OCR candidate."""
    left_tokens = left.split()
    right_tokens = set(right.split())
    if not left_tokens:
        return 0.0
    hits = sum(1 for token in left_tokens if token in right_tokens)
    return hits / len(left_tokens)


def _dedupe_scored_matches(scored_matches: List[tuple[float, OCRMatch]]) -> List[OCRMatch]:
    """Drop duplicate detections from multiple OCR passes while keeping the strongest hit."""
    ordered = sorted(
        scored_matches,
        key=lambda item: (
            -item[0],
            -item[1].confidence,
            item[1].top,
            item[1].left,
            item[1].width * item[1].height,
        ),
    )
    deduped: list[OCRMatch] = []
    for _, match in ordered:
        candidate_rect = (match.left, match.top, match.width, match.height, match.confidence)
        if any(_candidate_overlap(candidate_rect, (existing.left, existing.top, existing.width, existing.height, existing.confidence)) > 0.6 for existing in deduped):
            continue
        deduped.append(match)
    return deduped


def _normalize_ocr_text(value: str) -> str:
    """Normalize OCR text while preserving word boundaries for phrase matching."""
    cleaned = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(cleaned.split())


def _compact_ocr_text(value: str) -> str:
    """Normalize OCR text and strip separators for button-label matching."""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _split_normalized_words(value: str) -> List[str]:
    """Split normalized OCR text into comparable words."""
    normalized = _normalize_ocr_text(value)
    if not normalized:
        return []
    return normalized.split()


def _safe_float(values: List[Any], index: int, default: float = -1.0) -> float:
    """Best-effort conversion for Tesseract confidence values."""
    if len(values) <= index:
        return default
    try:
        return float(values[index])
    except Exception:
        return default


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

    cv_image = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(cv_image, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    masks = _build_ui_masks(cv2, enhanced)
    text_boxes = _find_ocr_text_boxes(image)

    raw_candidates: list[tuple[int, int, int, int, float]] = []
    for mask in masks:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            rect = cv2.boundingRect(contour)
            score = _score_ui_candidate(cv2, contour, rect)
            if score is not None:
                raw_candidates.append((*rect, score))

    deduped_candidates = _dedupe_ui_candidates(raw_candidates)
    filtered_candidates = [
        rect for rect in deduped_candidates
        if not _overlaps_text(rect, text_boxes)
    ]

    matches = []
    for x, y, w, h, score in filtered_candidates:
        center_x = x + w // 2
        center_y = y + h // 2
        matches.append(
            OCRMatch(
                text="UI Element",
                x=center_x,
                y=center_y,
                left=x,
                top=y,
                width=w,
                height=h,
                confidence=score,
            )
        )

    logger.info(f"UI Element Detection: Found {len(matches)} elements")
    
    # Sort matches row by row (top to bottom, left to right) for predictable numbering
    matches.sort(key=lambda m: (m.y // 20, m.x))
    
    return matches


def _build_ui_masks(cv2, gray_image):
    """Create multiple masks to capture both small icons and thin controls."""
    blurred = cv2.GaussianBlur(gray_image, (3, 3), 0)
    edges = cv2.Canny(blurred, 40, 120)

    adaptive = cv2.adaptiveThreshold(
        gray_image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,
        4,
    )

    edge_mask = cv2.dilate(
        edges,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
        iterations=1,
    )
    compact_mask = cv2.morphologyEx(
        adaptive,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)),
        iterations=1,
    )
    line_mask = cv2.morphologyEx(
        adaptive,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1)),
        iterations=1,
    )

    return [edge_mask, compact_mask, line_mask]


def _score_ui_candidate(cv2, contour, rect) -> Optional[float]:
    """Return a score for plausible UI candidates, or None when rejected."""
    x, y, w, h = rect
    box_area = w * h
    if box_area < 20 or box_area > 40000:
        return None

    max_side = max(w, h)
    min_side = min(w, h)
    if max_side < 6 or max_side > 220:
        return None

    aspect_ratio = max_side / max(min_side, 1)
    contour_area = cv2.contourArea(contour)
    fill_ratio = contour_area / max(box_area, 1)

    # Thin window controls such as minimize bars should be kept.
    is_thin_control = (
        (w >= 10 and h <= 8) or (h >= 10 and w <= 8)
    ) and aspect_ratio <= 12

    # Standard icons/buttons are compact and moderately filled.
    is_icon_like = (
        min_side >= 8
        and aspect_ratio <= 4.5
        and 0.08 <= fill_ratio <= 0.98
    )

    if not is_thin_control and not is_icon_like:
        return None

    # Reject common text-like shapes: small glyphs tend to be narrow, lightly filled,
    # and cluster horizontally; here we aggressively drop low-area letter-like boxes.
    if min_side < 12 and not is_thin_control and fill_ratio < 0.55:
        return None

    score = min(1.0, 0.4 + fill_ratio + (0.2 if is_thin_control else 0.0))
    return score


def _dedupe_ui_candidates(candidates: List[tuple[int, int, int, int, float]]) -> List[tuple[int, int, int, int, float]]:
    """Merge overlapping candidates from multiple detection passes."""
    ordered = sorted(candidates, key=lambda item: (-item[4], item[2] * item[3]))
    deduped: list[tuple[int, int, int, int, float]] = []

    for candidate in ordered:
        if any(_candidate_overlap(candidate, existing) > 0.45 for existing in deduped):
            continue
        deduped.append(candidate)

    return deduped


def _candidate_overlap(
    left: tuple[int, int, int, int, float],
    right: tuple[int, int, int, int, float],
) -> float:
    """Compute overlap ratio using the smaller box as denominator."""
    lx, ly, lw, lh, _ = left
    rx, ry, rw, rh, _ = right

    inter_left = max(lx, rx)
    inter_top = max(ly, ry)
    inter_right = min(lx + lw, rx + rw)
    inter_bottom = min(ly + lh, ry + rh)
    if inter_right <= inter_left or inter_bottom <= inter_top:
        return 0.0

    intersection = (inter_right - inter_left) * (inter_bottom - inter_top)
    smaller_area = min(lw * lh, rw * rh)
    return intersection / max(smaller_area, 1)


def _find_ocr_text_boxes(image: Image.Image) -> List[tuple[int, int, int, int]]:
    """Best-effort OCR to suppress text regions from UI element detection."""
    try:
        import pytesseract
    except ImportError:
        return []

    _configure_tesseract(pytesseract)

    try:
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 11",
        )
    except Exception:
        return []

    text_boxes = []
    for i, text in enumerate(data.get("text", [])):
        cleaned = text.strip()
        if len(cleaned) < 2:
            continue
        try:
            confidence = float(data["conf"][i])
        except Exception:
            confidence = -1.0
        if confidence < 35:
            continue
        text_boxes.append(
            (
                data["left"][i],
                data["top"][i],
                data["width"][i],
                data["height"][i],
            )
        )
    return text_boxes


def _overlaps_text(
    candidate: tuple[int, int, int, int, float],
    text_boxes: List[tuple[int, int, int, int]],
) -> bool:
    """Return True when a candidate substantially overlaps OCR-detected text."""
    x, y, w, h, _ = candidate
    candidate_area = w * h
    for tx, ty, tw, th in text_boxes:
        inter_left = max(x, tx)
        inter_top = max(y, ty)
        inter_right = min(x + w, tx + tw)
        inter_bottom = min(y + h, ty + th)
        if inter_right <= inter_left or inter_bottom <= inter_top:
            continue
        intersection = (inter_right - inter_left) * (inter_bottom - inter_top)
        if intersection / max(candidate_area, 1) >= 0.4:
            return True
    return False


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


def _run_keyboard_only_action(
    pyautogui: Any,
    action: Callable[[], None],
    *,
    description: str,
) -> bool:
    """
    Run a keyboard-only PyAutoGUI action with a lock-screen-friendly fallback.

    PyAutoGUI raises FailSafeException whenever the mouse cursor is in a screen
    corner, even if the requested action only uses the keyboard. For scenarios
    like entering a Windows lock-screen PIN, retry once with FAILSAFE
    temporarily disabled while keeping the global default safety behavior for
    mouse actions.
    """
    _ensure_keyboard_automation_available()

    try:
        action()
        return False
    except pyautogui.FailSafeException:
        previous_failsafe = getattr(pyautogui, "FAILSAFE", True)
        if not previous_failsafe:
            raise

        logger.warning(
            "PyAutoGUI fail-safe triggered during keyboard-only action '%s'; "
            "retrying once with FAILSAFE disabled.",
            description,
        )
        pyautogui.FAILSAFE = False
        try:
            action()
            return True
        finally:
            pyautogui.FAILSAFE = previous_failsafe


def write_text(pyautogui: Any, text: str, *, interval: float = 0.0) -> bool:
    """Type text via PyAutoGUI with a safe fail-safe retry for lock screens."""
    return _run_keyboard_only_action(
        pyautogui,
        lambda: pyautogui.write(text, interval=interval),
        description=f"write {len(text)} characters",
    )


def typewrite_text(pyautogui: Any, text: str, *, interval: float = 0.0) -> bool:
    """Type text via typewrite() with a safe fail-safe retry for lock screens."""
    return _run_keyboard_only_action(
        pyautogui,
        lambda: pyautogui.typewrite(text, interval=interval),
        description=f"typewrite {len(text)} characters",
    )


def press_key(pyautogui: Any, key: str) -> bool:
    """Press a key via PyAutoGUI with a safe fail-safe retry for lock screens."""
    return _run_keyboard_only_action(
        pyautogui,
        lambda: pyautogui.press(key),
        description=f"press '{key}'",
    )


def send_hotkey(pyautogui: Any, *keys: str) -> bool:
    """Send a hotkey via PyAutoGUI with a safe fail-safe retry for lock screens."""
    joined_keys = "+".join(keys)
    return _run_keyboard_only_action(
        pyautogui,
        lambda: pyautogui.hotkey(*keys),
        description=f"hotkey '{joined_keys}'",
    )


def _ensure_keyboard_automation_available() -> None:
    """Raise a clear error when Windows is on the secure lock-screen desktop."""
    if not is_windows_secure_input_desktop():
        return

    raise RuntimeError(
        "Windows is showing the secure lock screen, so synthetic keyboard input "
        "cannot reach the PIN box from this bot. Unlock the PC manually or via "
        "a remote desktop session first, then retry the command."
    )


def is_windows_secure_input_desktop() -> bool:
    """Return True when the active Windows input desktop is the secure Winlogon desktop."""
    desktop_name = get_windows_input_desktop_name()
    return bool(desktop_name) and desktop_name.lower() != "default"


def get_windows_input_desktop_name() -> Optional[str]:
    """Best-effort read of the active Windows input desktop name."""
    if platform.system() != "Windows":
        return None

    user32 = getattr(getattr(ctypes, "windll", None), "user32", None)
    if user32 is None:
        return None

    hdesk = None
    try:
        hdesk = user32.OpenInputDesktop(0, False, 0x0001)
        if not hdesk:
            return None

        needed = ctypes.c_uint(0)
        user32.GetUserObjectInformationW(hdesk, _UOI_NAME, None, 0, ctypes.byref(needed))
        if needed.value <= 2:
            return None

        buffer = ctypes.create_unicode_buffer(needed.value)
        if not user32.GetUserObjectInformationW(
            hdesk,
            _UOI_NAME,
            buffer,
            ctypes.sizeof(buffer),
            ctypes.byref(needed),
        ):
            return None
        return buffer.value or None
    except Exception:
        logger.debug("Could not read the current Windows input desktop name", exc_info=True)
        return None
    finally:
        if hdesk:
            try:
                user32.CloseDesktop(hdesk)
            except Exception:
                logger.debug("Failed to close input desktop handle", exc_info=True)
