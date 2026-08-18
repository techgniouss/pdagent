import datetime as dt

import pytest

from pocket_desk_agent import scheduler_registry as sr
from pocket_desk_agent.scheduler_registry import (
    MAX_CONSECUTIVE_FAILURES,
    ScheduledTask,
    SchedulerRegistry,
)
from pocket_desk_agent.scheduling_utils import local_now


@pytest.fixture
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "SCHEDULER_PATH", tmp_path / "scheduled_tasks.json")
    monkeypatch.setattr(sr, "existing_app_path", lambda name: tmp_path / name)
    return SchedulerRegistry()


def _repeating_task(task_id: str = "watch_1") -> ScheduledTask:
    now = local_now()
    return ScheduledTask(
        id=task_id,
        user_id=1,
        command="screen_watch",
        execute_at=now.isoformat(),
        task_type="screen_watch",
        interval_seconds=30,
        repeat_until=(now + dt.timedelta(days=30)).isoformat(),
        next_run_at=now.isoformat(),
    )


def test_repeating_task_survives_transient_failure(registry):
    registry.add_task(_repeating_task())

    updated = registry.finalize_task_run("watch_1", success=False, error="OCR blip")

    assert updated is not None
    assert updated.status == "pending"
    assert updated.consecutive_failures == 1
    assert updated.next_run_at is not None
    assert updated.error == "OCR blip"


def test_repeating_task_fails_after_max_consecutive_failures(registry):
    registry.add_task(_repeating_task())

    for _ in range(MAX_CONSECUTIVE_FAILURES - 1):
        updated = registry.finalize_task_run("watch_1", success=False, error="boom")
        assert updated.status == "pending"

    updated = registry.finalize_task_run("watch_1", success=False, error="boom")
    assert updated.status == "failed"
    assert updated.next_run_at is None


def test_successful_run_resets_failure_counter(registry):
    registry.add_task(_repeating_task())

    registry.finalize_task_run("watch_1", success=False, error="boom")
    updated = registry.finalize_task_run("watch_1", success=True)

    assert updated.status == "pending"
    assert updated.consecutive_failures == 0
    assert updated.error is None


def test_one_shot_task_fails_immediately(registry):
    now = local_now()
    registry.add_task(
        ScheduledTask(
            id="claude_1",
            user_id=1,
            command="claude_msg:hello",
            execute_at=now.isoformat(),
            task_type="claude_prompt",
        )
    )

    updated = registry.finalize_task_run("claude_1", success=False, error="no window")

    assert updated.status == "failed"
    assert updated.next_run_at is None


def test_legacy_task_dict_without_failure_field_loads(registry):
    # Simulate a task persisted before consecutive_failures existed.
    legacy = _repeating_task("legacy_1").to_dict()
    legacy.pop("consecutive_failures")
    registry.tasks.append(legacy)

    updated = registry.finalize_task_run("legacy_1", success=False, error="boom")

    assert updated.status == "pending"
    assert updated.consecutive_failures == 1
