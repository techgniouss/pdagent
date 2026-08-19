"""Regression tests: a corrupt/unreadable tokens.json must never crash the app.

Covers the gap where TokenStorage.load_tokens() previously called
json.load() with no error handling. Since GeminiClient() is constructed
at module-import time in handlers/_shared.py (before safe_command's
try/except exists), an unguarded exception there used to kill the bot
before it could ever report an error to Telegram.
"""

from pathlib import Path

from pocket_desk_agent.antigravity_auth import TokenStorage


def _patch_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)


def test_load_tokens_returns_none_when_file_missing(monkeypatch, tmp_path):
    _patch_home(monkeypatch, tmp_path)
    storage = TokenStorage(app_name="test-app")

    assert storage.load_tokens() is None


def test_load_tokens_survives_corrupt_json(monkeypatch, tmp_path):
    _patch_home(monkeypatch, tmp_path)
    storage = TokenStorage(app_name="test-app")
    storage.tokens_file.write_text("{not valid json!!", encoding="utf-8")

    # Must not raise — corrupt file is treated as "no saved tokens".
    assert storage.load_tokens() is None


def test_load_tokens_survives_empty_file(monkeypatch, tmp_path):
    _patch_home(monkeypatch, tmp_path)
    storage = TokenStorage(app_name="test-app")
    storage.tokens_file.write_text("", encoding="utf-8")

    assert storage.load_tokens() is None


def test_load_tokens_survives_valid_json_wrong_shape(monkeypatch, tmp_path):
    """Valid JSON that isn't an object (list/string/number) must not crash
    downstream `tokens.get(...)` calls in load_saved_tokens()."""
    _patch_home(monkeypatch, tmp_path)
    storage = TokenStorage(app_name="test-app")

    for payload in ("[]", '"just a string"', "42", "null"):
        storage.tokens_file.write_text(payload, encoding="utf-8")
        assert storage.load_tokens() is None


def test_antigravity_load_saved_tokens_survives_non_dict_json(monkeypatch, tmp_path):
    _patch_home(monkeypatch, tmp_path)
    from pocket_desk_agent.antigravity_auth import AntigravityOAuth

    oauth = AntigravityOAuth()
    oauth.storage.tokens_file.write_text("[1, 2, 3]", encoding="utf-8")

    # Must not raise (AttributeError on list.get) — just report "not logged in".
    assert oauth.load_saved_tokens() is False


def test_save_then_load_roundtrip_and_no_leftover_tmp_file(monkeypatch, tmp_path):
    _patch_home(monkeypatch, tmp_path)
    storage = TokenStorage(app_name="test-app")

    storage.save_tokens({"access_token": "abc", "refresh_token": "def"})

    assert storage.load_tokens() == {"access_token": "abc", "refresh_token": "def"}
    # save_tokens() must atomically replace, never leave a .json.tmp behind.
    assert not storage.tokens_file.with_suffix(".json.tmp").exists()


def test_gemini_client_does_not_crash_on_corrupt_tokens(monkeypatch, tmp_path):
    """GeminiClient() runs at import time — it must survive a corrupt
    tokens.json instead of raising and taking the whole bot down."""
    _patch_home(monkeypatch, tmp_path)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("AUTHORIZED_USER_IDS", "12345")
    monkeypatch.setenv("GEMINI_AUTH_MODE", "antigravity")

    from pocket_desk_agent.config import Config
    Config.load()

    storage = TokenStorage(app_name="antigravity-chatbot")
    storage.tokens_file.write_text("{corrupt", encoding="utf-8")

    from pocket_desk_agent.gemini_client import GeminiClient

    client = GeminiClient()  # must not raise

    assert client._oauth is not None
    assert client._oauth.access_token is None
