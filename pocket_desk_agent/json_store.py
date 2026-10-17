"""Crash-safe JSON persistence helpers for the registry files under ~/.pdagent."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def atomic_write_json(path: Path, data: Any) -> None:
    """Write ``data`` as JSON via a temp file + ``os.replace``.

    A crash or full disk mid-write leaves the previous file intact instead
    of a truncated one that the next load would treat as corrupt.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def quarantine_corrupt_file(path: Path) -> None:
    """Move an unreadable data file aside so the next save can't destroy it."""
    try:
        if path.exists():
            backup = path.with_name(path.name + ".corrupt")
            os.replace(path, backup)
            logger.warning("Moved unreadable data file to %s", backup)
    except OSError as exc:
        logger.warning("Could not quarantine unreadable file %s: %s", path, exc)
