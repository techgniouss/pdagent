"""Tests for NVIDIA fallback configuration in the setup wizard."""

from pocket_desk_agent import configure


def test_validate_provider_order_accepts_known_tokens() -> None:
    assert configure._validate_provider_order("nvidia,gemini") is None
    assert configure._validate_provider_order("gemini") is None


def test_validate_provider_order_rejects_unknown_token() -> None:
    error = configure._validate_provider_order("nvidia,bogus")
    assert error is not None
    assert "bogus" in error


def test_validate_provider_order_rejects_empty() -> None:
    error = configure._validate_provider_order("")
    assert error is not None


def test_selective_menu_includes_nvidia_fallback() -> None:
    labels = [label for label, _ in configure._SELECTIVE_MENU]
    assert any("NVIDIA" in label for label in labels)


def test_read_existing_parsers_does_not_break_on_missing_nvidia_fields(tmp_path, monkeypatch) -> None:
    """A config file written before this feature existed has no nvidia_* keys —
    the selective handler must not KeyError reading them with .get()-style fallbacks."""
    cfg_dir = tmp_path / ".pdagent"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "credentials").write_text("[default]\ntelegram_bot_token = x\n", encoding="utf-8")
    (cfg_dir / "config").write_text("[bot]\nauthorized_user_ids = 1\n", encoding="utf-8")

    monkeypatch.setattr(configure, "existing_app_path", lambda name: cfg_dir / name)

    cred_parser, cfg_parser = configure._read_existing_parsers()

    assert cred_parser.get("default", "nvidia_api_key", fallback="") == ""
    assert cfg_parser.get("bot", "nvidia_model", fallback="") == ""
    assert cfg_parser.get("bot", "ai_provider_order", fallback="") == ""
