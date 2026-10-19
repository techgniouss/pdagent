"""Crash-safe / private file writers."""
import json
import os
import stat

import pytest

from pocket_desk_agent.json_store import atomic_write_json, quarantine_corrupt_file, write_private_text


def test_atomic_write_round_trips_and_leaves_no_temp(tmp_path) -> None:
    target = tmp_path / "data.json"
    atomic_write_json(target, {"a": [1, 2]})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": [1, 2]}
    assert not (tmp_path / "data.json.tmp").exists()


def test_failed_write_keeps_previous_file(tmp_path) -> None:
    target = tmp_path / "data.json"
    atomic_write_json(target, {"ok": True})
    with pytest.raises(TypeError):
        atomic_write_json(target, {"bad": object()})
    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    assert not (tmp_path / "data.json.tmp").exists()


def test_quarantine_moves_corrupt_file_aside(tmp_path) -> None:
    target = tmp_path / "data.json"
    target.write_text("{not json", encoding="utf-8")
    quarantine_corrupt_file(target)
    assert not target.exists()
    assert (tmp_path / "data.json.corrupt").read_text(encoding="utf-8") == "{not json"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_private_write_is_owner_only(tmp_path) -> None:
    target = tmp_path / "creds"
    write_private_text(target, "secret")
    assert target.read_text(encoding="utf-8") == "secret"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
