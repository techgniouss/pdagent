"""INI config handling: literal values, tolerant loading, atomic writes."""
import configparser
import os

from pocket_desk_agent import configure


def test_percent_in_values_round_trips(tmp_path) -> None:
    cred = tmp_path / "credentials"
    parser = configparser.ConfigParser(interpolation=None)
    parser["default"] = {"qubo_password": "pa%ss%word"}
    buffer_path = tmp_path / "out"
    configure.write_config_file(buffer_path, parser)

    reread = configparser.ConfigParser(interpolation=None)
    reread.read(buffer_path, encoding="utf-8")
    assert reread["default"]["qubo_password"] == "pa%ss%word"


def test_loader_survives_percent_and_malformed_files(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("QUBO_PASSWORD", raising=False)
    monkeypatch.delenv("SYSTEM_PROMPT", raising=False)

    good = tmp_path / "credentials"
    good.write_text("[default]\nqubo_password = pa%ss\n", encoding="utf-8")
    configure._load_file("credentials", good)
    assert os.environ["QUBO_PASSWORD"] == "pa%ss"

    bad = tmp_path / "config"
    bad.write_text("this is not an ini file\n[bot\n", encoding="utf-8")
    configure._load_file("config", bad)  # must not raise
    assert "SYSTEM_PROMPT" not in os.environ
    monkeypatch.delenv("QUBO_PASSWORD", raising=False)


def test_persist_approved_directories_is_atomic_and_literal(tmp_path, monkeypatch) -> None:
    target = tmp_path / "config"
    monkeypatch.setattr(configure, "config_path", lambda: target)
    configure.persist_approved_directories([tmp_path / "a%b", tmp_path / "c"])
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(target, encoding="utf-8")
    assert parser["bot"]["approved_directories"].split(",")[0].endswith("a%b")
    assert not (tmp_path / "config.tmp").exists()
