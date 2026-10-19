"""Credentials must never reach logs or user-visible error text."""
import io
import logging

from pocket_desk_agent.log_redaction import SecretRedactingFilter, redact_secrets

BOT_TOKEN = "123456789:AAEhBP0av28YfakeFAKEfakeFAKEfakeFAKE12"
GOOGLE_KEY = "AIzaSyD-FAKEfakeFAKEfakeFAKEfakeFAKE1234"


def test_redacts_known_secret_shapes() -> None:
    text = (
        f"The token `{BOT_TOKEN}` was rejected; url ...generateContent?key={GOOGLE_KEY}&alt=sse "
        "Authorization: Bearer ya29.a0AfH6SMBfakefakefakefakefakefake nvapi-abcdefghijklmnop"
    )
    redacted = redact_secrets(text)
    for secret in (BOT_TOKEN, GOOGLE_KEY, "ya29.a0AfH6SMB", "nvapi-abcdefghijklmnop"):
        assert secret not in redacted
    assert "&alt=sse" in redacted  # unrelated query params survive


def test_ordinary_text_is_untouched() -> None:
    text = "Sent 12:30 reminder to user 123456 about build 7"
    assert redact_secrets(text) == text


def test_filter_scrubs_message_args_and_traceback() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(SecretRedactingFilter())
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("redaction-test")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        try:
            raise RuntimeError(f"request failed for ?key={GOOGLE_KEY}")
        except RuntimeError:
            logger.error("token is %s", BOT_TOKEN, exc_info=True)
    finally:
        logger.removeHandler(handler)

    output = stream.getvalue()
    assert BOT_TOKEN not in output and GOOGLE_KEY not in output
    assert "***REDACTED***" in output


def test_api_key_mode_request_keeps_key_out_of_the_url(monkeypatch) -> None:
    from pocket_desk_agent import gemini_client as gc

    seen = {}

    class FakeResp:
        status_code = 200

        def json(self):
            return {"candidates": []}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen["url"], seen["headers"] = url, headers
        return FakeResp()

    monkeypatch.setattr(gc.requests, "post", fake_post)
    monkeypatch.setattr(gc.Config, "GOOGLE_API_KEY", GOOGLE_KEY)
    client = gc.GeminiClient.__new__(gc.GeminiClient)
    wrapped, resolved = gc._build_wrapped_body("", "gemini-2.5-flash", [], "hi")
    client._call_api_key_raw(wrapped, resolved)

    assert GOOGLE_KEY not in seen["url"] and "key=" not in seen["url"]
    assert seen["headers"]["x-goog-api-key"] == GOOGLE_KEY
