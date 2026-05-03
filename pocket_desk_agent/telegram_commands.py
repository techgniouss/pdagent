"""Helpers for building Telegram bot command menus safely."""

from collections.abc import Sequence
from typing import Any

TELEGRAM_MAX_BOT_COMMANDS = 100
CommandRegistryEntry = tuple[str, Any, str]


def trim_registry_for_telegram(
    command_registry: Sequence[CommandRegistryEntry],
) -> tuple[list[tuple[str, str]], int]:
    """Return command/description pairs capped to Telegram's command limit."""
    trimmed_registry = command_registry[:TELEGRAM_MAX_BOT_COMMANDS]
    commands = [(command, description) for command, _, description in trimmed_registry]
    dropped = max(0, len(command_registry) - TELEGRAM_MAX_BOT_COMMANDS)
    return commands, dropped
