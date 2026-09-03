"""Tests for NVIDIA config and AI provider order parsing."""
from pocket_desk_agent import config, configure


def test_nvidia_defaults(monkeypatch) -> None:
    for var in ("NVIDIA_API_KEY", "NVIDIA_BASE_URL", "NVIDIA_MODEL", "AI_PROVIDER_ORDER"):
        monkeypatch.delenv(var, raising=False)

    config.Config.load()

    assert config.Config.NVIDIA_API_KEY == ""
    assert config.Config.NVIDIA_BASE_URL == "https://integrate.api.nvidia.com/v1"
    assert config.Config.NVIDIA_MODEL == "meta/llama-3.3-70b-instruct"
    assert config.Config.AI_PROVIDER_ORDER == ["gemini", "nvidia"]


def test_ai_provider_order_parses_valid_csv(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER_ORDER", "nvidia,gemini")
    config.Config.load()
    assert config.Config.AI_PROVIDER_ORDER == ["nvidia", "gemini"]


def test_ai_provider_order_drops_unknown_tokens(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER_ORDER", "nvidia,bogus,gemini")
    config.Config.load()
    assert config.Config.AI_PROVIDER_ORDER == ["nvidia", "gemini"]


def test_ai_provider_order_falls_back_when_empty_after_filtering(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER_ORDER", "bogus,also_bogus")
    config.Config.load()
    assert config.Config.AI_PROVIDER_ORDER == ["gemini", "nvidia"]


def test_ini_env_map_covers_nvidia_fields() -> None:
    env_map = configure._INI_ENV_MAP
    assert env_map[("credentials", "default", "nvidia_api_key")] == "NVIDIA_API_KEY"
    assert env_map[("config", "bot", "nvidia_model")] == "NVIDIA_MODEL"
    assert env_map[("config", "bot", "ai_provider_order")] == "AI_PROVIDER_ORDER"


def test_load_into_environ_reads_nvidia_ini_values(tmp_path, monkeypatch) -> None:
    cfg_dir = tmp_path / ".pdagent"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "credentials").write_text(
        "[default]\nnvidia_api_key = nvapi-test\n", encoding="utf-8"
    )
    (cfg_dir / "config").write_text(
        "[bot]\nnvidia_model = meta/llama-3.1-70b-instruct\nai_provider_order = nvidia,gemini\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(configure, "app_path_candidates", lambda name: (cfg_dir / name,))
    for var in ("NVIDIA_API_KEY", "NVIDIA_MODEL", "AI_PROVIDER_ORDER"):
        monkeypatch.delenv(var, raising=False)

    configure.load_into_environ()

    import os

    assert os.environ["NVIDIA_API_KEY"] == "nvapi-test"
    assert os.environ["NVIDIA_MODEL"] == "meta/llama-3.1-70b-instruct"
    assert os.environ["AI_PROVIDER_ORDER"] == "nvidia,gemini"
