"""Shared application data path helpers.

Pocket Desk Agent stores its configuration, logs, PID files, and other
default state beneath a stable per-user directory so behavior does not vary
based on the shell's current working directory.
"""

from __future__ import annotations

from pathlib import Path


APP_DIR_NAME = ".pdagent"
LEGACY_APP_DIR_NAMES = (".pd-agent",)


def app_dir(home_dir: Path | None = None) -> Path:
    """Return the canonical Pocket Desk Agent data directory."""
    base_home = home_dir or Path.home()
    return base_home / APP_DIR_NAME


def legacy_app_dirs(home_dir: Path | None = None) -> tuple[Path, ...]:
    """Return legacy data directory locations kept for read compatibility."""
    base_home = home_dir or Path.home()
    return tuple(base_home / name for name in LEGACY_APP_DIR_NAMES)


def ensure_app_dir(home_dir: Path | None = None) -> Path:
    """Create the canonical app data directory when it does not exist."""
    path = app_dir(home_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def app_path(*parts: str, home_dir: Path | None = None) -> Path:
    """Return a path rooted in the canonical app data directory."""
    return app_dir(home_dir).joinpath(*parts)


def app_path_candidates(*parts: str, home_dir: Path | None = None) -> tuple[Path, ...]:
    """Return canonical and legacy candidate paths for a stored file."""
    primary = app_path(*parts, home_dir=home_dir)
    legacy = tuple(path.joinpath(*parts) for path in legacy_app_dirs(home_dir))
    return (primary, *legacy)


def existing_app_path(*parts: str, home_dir: Path | None = None) -> Path:
    """Return the first existing canonical/legacy path, else the canonical path."""
    candidates = app_path_candidates(*parts, home_dir=home_dir)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]
