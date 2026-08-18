from pocket_desk_agent import config, gemini_client


def test_env_int_clamps_to_minimum(monkeypatch) -> None:
    monkeypatch.setenv("TEST_ENV_INT", "0")

    assert config._env_int("TEST_ENV_INT", 10, minimum=1) == 1


def test_allowed_tools_include_canonical_app_tools() -> None:
    assert "open_desktop_app" in gemini_client._ALLOWED_TOOLS
    assert "close_desktop_app" in gemini_client._ALLOWED_TOOLS


def test_battery_threshold_validation(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake:token")
    monkeypatch.setenv("AUTHORIZED_USER_IDS", "12345")

    # Valid thresholds
    monkeypatch.setenv("BATTERY_HIGH_THRESHOLD", "80")
    monkeypatch.setenv("BATTERY_LOW_THRESHOLD", "20")
    config.Config.load()
    assert config.Config.validate() == []

    # Low threshold not below high threshold
    monkeypatch.setenv("BATTERY_HIGH_THRESHOLD", "50")
    monkeypatch.setenv("BATTERY_LOW_THRESHOLD", "50")
    config.Config.load()
    errors = config.Config.validate()
    assert any("BATTERY_LOW_THRESHOLD must be below BATTERY_HIGH_THRESHOLD" in e for e in errors)

    # Low threshold greater than high threshold
    monkeypatch.setenv("BATTERY_HIGH_THRESHOLD", "30")
    monkeypatch.setenv("BATTERY_LOW_THRESHOLD", "70")
    config.Config.load()
    errors = config.Config.validate()
    assert any("BATTERY_LOW_THRESHOLD must be below BATTERY_HIGH_THRESHOLD" in e for e in errors)

    # High threshold out of bounds
    monkeypatch.setenv("BATTERY_HIGH_THRESHOLD", "105")
    monkeypatch.setenv("BATTERY_LOW_THRESHOLD", "20")
    config.Config.load()
    errors = config.Config.validate()
    assert any("BATTERY_HIGH_THRESHOLD must be between 1 and 100" in e for e in errors)

    # Low threshold out of bounds
    monkeypatch.setenv("BATTERY_HIGH_THRESHOLD", "80")
    monkeypatch.setenv("BATTERY_LOW_THRESHOLD", "-5")
    config.Config.load()
    errors = config.Config.validate()
    assert any("BATTERY_LOW_THRESHOLD must be between 0 and 99" in e for e in errors)

