"""JPEG frame generator for the live remote-desktop stream.

Captures the screen at a tunable FPS, downscales to ``session.max_width``,
encodes as JPEG, and emits bytes. Skips emission when the (downscaled)
frame is identical to the previous one, which drops idle CPU dramatically.

All heavy imports (mss, PIL, xxhash) happen inside the generator body so
that importing this module costs nothing.
"""

from __future__ import annotations

import asyncio
import io
import logging
from typing import AsyncIterator

from pocket_desk_agent.remote.session import RemoteSession

logger = logging.getLogger(__name__)

_THUMB_SIZE = 64


def _try_import_mss():
    try:
        import mss  # type: ignore

        return mss
    except Exception:
        return None


def _pil_from_screen(mss_module, sct):
    """Grab the primary monitor and return a PIL Image."""
    from PIL import Image  # type: ignore

    if mss_module is not None and sct is not None:
        monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        raw = sct.grab(monitor)
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    import pyautogui  # type: ignore

    return pyautogui.screenshot()


def _thumb_hash(image, xxhash_module) -> int:
    from PIL import Image  # type: ignore

    thumb = image.convert("L").resize((_THUMB_SIZE, _THUMB_SIZE), Image.BILINEAR)
    return xxhash_module.xxh64_intdigest(thumb.tobytes())


def _encode_jpeg(image, quality: int, max_width: int) -> bytes:
    from PIL import Image  # type: ignore

    width, height = image.size
    if width > max_width:
        ratio = max_width / float(width)
        new_size = (max_width, max(1, int(height * ratio)))
        image = image.resize(new_size, Image.BILINEAR)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=False)
    return buffer.getvalue()


async def frame_iter(session: RemoteSession) -> AsyncIterator[bytes]:
    """Yield JPEG bytes forever until the session is torn down.

    Emits ``b""`` as a sentinel after consecutive skipped frames so the
    caller can keep its loop cadence; callers should ignore empty bytes.
    """
    import xxhash  # type: ignore

    mss_module = _try_import_mss()
    sct = mss_module.mss() if mss_module is not None else None

    last_hash: int | None = None
    loop = asyncio.get_running_loop()

    try:
        while not session.torn_down:
            target_interval = 1.0 / max(2, session.fps)
            next_t = loop.time() + target_interval

            try:
                def _grab() -> bytes:
                    nonlocal last_hash
                    image = _pil_from_screen(mss_module, sct)
                    current = _thumb_hash(image, xxhash)
                    if current == last_hash:
                        return b""
                    last_hash = current
                    return _encode_jpeg(image, session.quality, session.max_width)

                jpeg = await asyncio.to_thread(_grab)
            except Exception as exc:
                logger.warning("[remote] capture failed: %s", exc)
                yield b""
                await asyncio.sleep(1.0)
                continue

            yield jpeg

            delay = next_t - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
    finally:
        if sct is not None:
            try:
                sct.close()
            except Exception:
                pass
