"""AntigravityAuth.has_credentials must never hit the network."""
import types

from pocket_desk_agent import auth as auth_module
from pocket_desk_agent.auth import AntigravityAuth


def _manager(monkeypatch, tokens_by_mode):
    manager = AntigravityAuth()
    monkeypatch.setattr(auth_module.Config, "GEMINI_AUTH_MODE", "antigravity")

    def build(user_id, mode):
        return types.SimpleNamespace(
            storage=types.SimpleNamespace(load_tokens=lambda: tokens_by_mode.get(mode)),
            load_saved_tokens=lambda: (_ for _ in ()).throw(AssertionError("must not refresh")),
        )

    monkeypatch.setattr(manager, "_build_oauth_instance", build)
    return manager


def test_saved_refresh_token_counts_even_when_access_token_expired(monkeypatch) -> None:
    manager = _manager(monkeypatch, {"antigravity": {"refresh_token": "r", "expires_at": 0}})
    assert manager.has_credentials(1) is True


def test_no_saved_tokens_means_no_credentials(monkeypatch) -> None:
    manager = _manager(monkeypatch, {})
    assert manager.has_credentials(1) is False


def test_api_key_mode_uses_the_key(monkeypatch) -> None:
    manager = AntigravityAuth()
    monkeypatch.setattr(auth_module.Config, "GEMINI_AUTH_MODE", "apikey")
    monkeypatch.setattr(auth_module.Config, "GOOGLE_API_KEY", "k")
    assert manager.has_credentials(1) is True
    monkeypatch.setattr(auth_module.Config, "GOOGLE_API_KEY", "")
    assert manager.has_credentials(1) is False
