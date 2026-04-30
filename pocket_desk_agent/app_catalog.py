"""Catalog and query helpers for launchable desktop applications."""

from __future__ import annotations

import hashlib
import os
import platform
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

_SAFE_EXTENSIONS = {".exe", ".lnk", ".url"}
_UNSAFE_EXTENSIONS = {".bat", ".cmd", ".com", ".ps1", ".psm1", ".vbs", ".js"}
_START_MENU_DIRS = (
    r"%APPDATA%\Microsoft\Windows\Start Menu\Programs",
    r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs",
)


@dataclass(frozen=True)
class DesktopAppEntry:
    """Normalized description of one launchable desktop app."""

    app_id: str
    display_name: str
    aliases: list[str]
    launch_target: str
    launch_type: str
    process_hints: list[str] = field(default_factory=list)
    source: str = "builtin"


@dataclass
class AppQueryResult:
    """Result of resolving a user query against the app catalog."""

    matches: list[DesktopAppEntry]
    selected: Optional[DesktopAppEntry] = None

    @property
    def is_ambiguous(self) -> bool:
        return self.selected is None and len(self.matches) > 1


def normalize_app_name(name: str) -> str:
    """Collapse punctuation and spacing into a stable lookup key."""
    cleaned = re.sub(r"[^a-z0-9]+", " ", (name or "").strip().lower())
    return " ".join(cleaned.split())


def is_safe_launch_target(target: str) -> bool:
    """Return True when a launch target uses an allowed file type."""
    raw_target = (target or "").strip()
    if not raw_target:
        return False

    lowered = raw_target.lower()
    if lowered.startswith(("shell:appsfolder\\", "ms-settings:", "http:", "https:", "mailto:")):
        return True

    suffix = Path(raw_target).suffix.lower()
    if suffix in _UNSAFE_EXTENSIONS:
        return False
    if suffix in _SAFE_EXTENSIONS:
        return True

    return False


def build_builtin_app_catalog() -> list[DesktopAppEntry]:
    """Return the curated built-in safe app catalog."""
    return [
        DesktopAppEntry(
            app_id="chrome",
            display_name="Google Chrome",
            aliases=["chrome", "google chrome"],
            launch_target=_first_existing_path(
                [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                ],
                default="chrome.exe",
            ),
            launch_type="exe",
            process_hints=["chrome"],
        ),
        DesktopAppEntry(
            app_id="edge",
            display_name="Microsoft Edge",
            aliases=["edge", "microsoft edge"],
            launch_target=_first_existing_path(
                [
                    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                ],
                default="msedge.exe",
            ),
            launch_type="exe",
            process_hints=["msedge"],
        ),
        DesktopAppEntry(
            app_id="firefox",
            display_name="Mozilla Firefox",
            aliases=["firefox", "mozilla firefox"],
            launch_target=_first_existing_path(
                [
                    r"C:\Program Files\Mozilla Firefox\firefox.exe",
                    r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
                ],
                default="firefox.exe",
            ),
            launch_type="exe",
            process_hints=["firefox"],
        ),
        DesktopAppEntry(
            app_id="brave",
            display_name="Brave",
            aliases=["brave", "brave browser"],
            launch_target=_first_existing_path(
                [
                    os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                ],
                default="brave.exe",
            ),
            launch_type="exe",
            process_hints=["brave"],
        ),
        DesktopAppEntry(
            app_id="notepad",
            display_name="Notepad",
            aliases=["notepad"],
            launch_target="notepad.exe",
            launch_type="exe",
            process_hints=["notepad"],
        ),
        DesktopAppEntry(
            app_id="calculator",
            display_name="Calculator",
            aliases=["calculator", "calc"],
            launch_target="calc.exe",
            launch_type="exe",
            process_hints=["calculator", "calc"],
        ),
        DesktopAppEntry(
            app_id="vscode",
            display_name="Visual Studio Code",
            aliases=["vscode", "vs code", "visual studio code", "code"],
            launch_target=_first_existing_path(
                [
                    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
                    r"C:\Program Files\Microsoft VS Code\Code.exe",
                    r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
                ],
                default="code.exe",
            ),
            launch_type="exe",
            process_hints=["code"],
        ),
        DesktopAppEntry(
            app_id="explorer",
            display_name="File Explorer",
            aliases=["explorer", "file explorer", "windows explorer"],
            launch_target="explorer.exe",
            launch_type="exe",
            process_hints=["explorer"],
        ),
    ]


def discover_desktop_apps() -> list[DesktopAppEntry]:
    """Return built-in apps plus safe Start Menu entries on Windows."""
    catalog = list(build_builtin_app_catalog())
    if platform.system() != "Windows":
        return catalog

    catalog.extend(_discover_start_menu_entries())
    return _dedupe_catalog(catalog)


def resolve_app_query(
    query: str,
    catalog: Optional[Iterable[DesktopAppEntry]] = None,
) -> AppQueryResult:
    """Resolve a user query to one app or an ambiguous list."""
    entries = list(catalog) if catalog is not None else discover_desktop_apps()
    normalized_query = normalize_app_name(query)
    if not normalized_query:
        return AppQueryResult(matches=[])

    exact_matches = [
        entry for entry in entries
        if normalized_query == normalize_app_name(entry.display_name)
        or normalized_query in {normalize_app_name(alias) for alias in entry.aliases}
    ]
    if exact_matches:
        selected = exact_matches[0]
        return AppQueryResult(matches=[selected], selected=selected)

    partial_matches = [
        entry for entry in entries
        if normalized_query in normalize_app_name(entry.display_name)
        or any(normalized_query in normalize_app_name(alias) for alias in entry.aliases)
    ]
    partial_matches.sort(key=lambda item: normalize_app_name(item.display_name))
    if len(partial_matches) == 1:
        return AppQueryResult(matches=partial_matches, selected=partial_matches[0])
    return AppQueryResult(matches=partial_matches)


def get_app_entry_by_id(
    app_id: str,
    catalog: Optional[Iterable[DesktopAppEntry]] = None,
) -> Optional[DesktopAppEntry]:
    """Return one catalog entry by stable app id."""
    entries = list(catalog) if catalog is not None else discover_desktop_apps()
    for entry in entries:
        if entry.app_id == app_id:
            return entry
    return None


def _discover_start_menu_entries() -> list[DesktopAppEntry]:
    """Discover launchable app shortcuts from common Start Menu locations."""
    entries: list[DesktopAppEntry] = []
    seen_targets: set[str] = set()

    for raw_dir in _START_MENU_DIRS:
        start_dir = Path(os.path.expandvars(raw_dir))
        if not start_dir.exists():
            continue
        for candidate in start_dir.rglob("*"):
            if not candidate.is_file():
                continue
            target = str(candidate)
            if not is_safe_launch_target(target):
                continue
            normalized_target = target.lower()
            if normalized_target in seen_targets:
                continue
            seen_targets.add(normalized_target)

            stem = candidate.stem.strip()
            if not stem:
                continue
            aliases = [stem]
            entries.append(
                DesktopAppEntry(
                    app_id=_build_start_menu_app_id(stem, target),
                    display_name=stem,
                    aliases=aliases,
                    launch_target=target,
                    launch_type=candidate.suffix.lower().lstrip("."),
                    process_hints=_derive_process_hints(stem),
                    source="start_menu",
                )
            )

    return entries


def _derive_process_hints(name: str) -> list[str]:
    """Return a few simple process-name hints for close matching."""
    normalized = normalize_app_name(name)
    if not normalized:
        return []
    collapsed = normalized.replace(" ", "")
    hints = [collapsed]
    first_word = normalized.split(" ", 1)[0]
    if first_word and first_word not in hints:
        hints.append(first_word)
    return hints


def _dedupe_catalog(entries: Iterable[DesktopAppEntry]) -> list[DesktopAppEntry]:
    """Keep the first entry for each normalized app identity."""
    deduped: list[DesktopAppEntry] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        key = (normalize_app_name(entry.display_name), entry.launch_target.lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def _first_existing_path(paths: list[str], default: str) -> str:
    """Return the first existing path or a safe fallback executable name."""
    for path in paths:
        if os.path.exists(path):
            return path
    return default


def _build_start_menu_app_id(name: str, target: str) -> str:
    """Create a stable unique id for one Start Menu entry."""
    slug = normalize_app_name(name).replace(" ", "-") or "app"
    digest = hashlib.sha1(target.lower().encode("utf-8")).hexdigest()[:8]
    return f"startmenu-{slug}-{digest}"
