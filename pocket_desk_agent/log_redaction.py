"""Keep credentials out of log files and the console.

Libraries put secrets in exception text and log lines in ways we don't
control (PTB's ``InvalidToken`` message embeds the bot token; ``requests``
errors embed the request URL). ``SecretRedactingFilter`` scrubs every record
before any handler formats it.
"""

from __future__ import annotations

import logging
import re

_REDACTED = "***REDACTED***"

_SECRET_PATTERNS = (
    # Telegram bot token: <numeric id>:<35-char secret>
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"),
    # NVIDIA NIM API key
    re.compile(r"\bnvapi-[A-Za-z0-9_-]{10,}"),
    # Google API key
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    # Authorization headers / bearer tokens
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    # key=... / api_key=... / access_token=... query parameters
    re.compile(r"(?i)([?&](?:key|api_key|apikey|access_token|token)=)[^&\s'\"]+"),
)


def redact_secrets(text: str) -> str:
    """Return ``text`` with anything that looks like a credential masked."""
    redacted = text
    for pattern in _SECRET_PATTERNS:
        if pattern.groups:
            redacted = pattern.sub(lambda m: m.group(1) + _REDACTED, redacted)
        else:
            redacted = pattern.sub(_REDACTED, redacted)
    return redacted


class SecretRedactingFilter(logging.Filter):
    """Logging filter that masks credentials in the message and traceback."""

    _exception_formatter = logging.Formatter()

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = redact_secrets(record.getMessage())
            record.args = ()
            if record.exc_info and not record.exc_text:
                record.exc_text = self._exception_formatter.formatException(record.exc_info)
            if record.exc_text:
                record.exc_text = redact_secrets(record.exc_text)
            if record.stack_info:
                record.stack_info = redact_secrets(record.stack_info)
        except Exception:
            # A logging filter must never break logging itself.
            pass
        return True
