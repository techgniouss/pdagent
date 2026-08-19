"""Regression tests for Qubo smart plug fields in the configure wizard.

Covers the gap where QUBO_USERNAME/QUBO_PASSWORD/QUBO_DEVICE_NAME and the
battery thresholds were declared in Config but never wired into the INI
config/credentials files the wizard reads and writes — so values saved via
`pdagent configure` never made it into os.environ.
"""

from pocket_desk_agent import configure


def test_ini_env_map_covers_smart_plug_fields() -> None:
    env_map = configure._INI_ENV_MAP
    assert env_map[("credentials", "default", "qubo_username")] == "QUBO_USERNAME"
    assert env_map[("credentials", "default", "qubo_password")] == "QUBO_PASSWORD"
    assert env_map[("config", "smartplug", "qubo_device_name")] == "QUBO_DEVICE_NAME"
    assert env_map[("config", "smartplug", "battery_high_threshold")] == "BATTERY_HIGH_THRESHOLD"
    assert env_map[("config", "smartplug", "battery_low_threshold")] == "BATTERY_LOW_THRESHOLD"
    assert env_map[("config", "smartplug", "battery_poll_interval")] == "BATTERY_POLL_INTERVAL"


def test_load_into_environ_reads_smart_plug_ini_values(tmp_path, monkeypatch) -> None:
    cfg_dir = tmp_path / ".pdagent"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    (cfg_dir / "credentials").write_text(
        "[default]\nqubo_username = test@example.com\nqubo_password = hunter2\n",
        encoding="utf-8",
    )
    (cfg_dir / "config").write_text(
        "[smartplug]\n"
        "qubo_device_name = My Plug\n"
        "battery_high_threshold = 90\n"
        "battery_low_threshold = 20\n"
        "battery_poll_interval = 120\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        configure, "app_path_candidates", lambda name: (cfg_dir / name,)
    )

    for var in (
        "QUBO_USERNAME",
        "QUBO_PASSWORD",
        "QUBO_DEVICE_NAME",
        "BATTERY_HIGH_THRESHOLD",
        "BATTERY_LOW_THRESHOLD",
        "BATTERY_POLL_INTERVAL",
    ):
        monkeypatch.delenv(var, raising=False)

    configure.load_into_environ()

    import os

    assert os.environ["QUBO_USERNAME"] == "test@example.com"
    assert os.environ["QUBO_PASSWORD"] == "hunter2"
    assert os.environ["QUBO_DEVICE_NAME"] == "My Plug"
    assert os.environ["BATTERY_HIGH_THRESHOLD"] == "90"
    assert os.environ["BATTERY_LOW_THRESHOLD"] == "20"
    assert os.environ["BATTERY_POLL_INTERVAL"] == "120"


def test_read_existing_parsers_seeds_smartplug_section_for_old_configs(
    tmp_path, monkeypatch
) -> None:
    """A config file written before this feature existed has no [smartplug]
    section. The selective-update handler must not KeyError on it."""
    cfg_dir = tmp_path / ".pdagent"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "credentials").write_text(
        "[default]\ntelegram_bot_token = x\n", encoding="utf-8"
    )
    (cfg_dir / "config").write_text(
        "[bot]\nauthorized_user_ids = 1\n", encoding="utf-8"
    )

    monkeypatch.setattr(
        configure, "existing_app_path", lambda name: cfg_dir / name
    )

    cred_parser, cfg_parser = configure._read_existing_parsers()

    assert cfg_parser.has_section("smartplug")
    # Would raise KeyError if the section weren't pre-created.
    cfg_parser["smartplug"]["qubo_device_name"] = "Plug"


def test_selective_menu_includes_smart_plug() -> None:
    labels = [label for label, _ in configure._SELECTIVE_MENU]
    assert any("Smart Plug" in label for label in labels)
