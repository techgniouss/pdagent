"""Shared types exchanged between AI provider clients and AIRouter."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderResult:
    """Outcome of one AI provider's attempt to answer a message.

    ``text`` is the provider's answer, or — when ``is_retryable_error`` is
    True — an error message describing *this provider's* failure. AIRouter
    only shows that error text to the user if this was the last configured
    provider it tried; otherwise it moves on to the next provider and the
    text here is discarded (logged, not shown).
    """

    text: str
    is_retryable_error: bool = False
