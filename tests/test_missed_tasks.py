"""One-shot scheduled tasks that were missed must be skipped, not run late."""
import datetime as dt

from pocket_desk_agent.main import (
    MISSED_SHUTDOWN_GRACE_SECONDS,
    MISSED_TASK_GRACE_SECONDS,
    missed_task_lateness,
)
from pocket_desk_agent.scheduler_registry import ScheduledTask
from pocket_desk_agent.scheduling_utils import local_now


def _task(seconds_overdue: float, **kwargs) -> ScheduledTask:
    due = local_now() - dt.timedelta(seconds=seconds_overdue)
    return ScheduledTask(id="t", user_id=1, command=kwargs.pop("command", "claude_msg:hi"),
                         execute_at=due.isoformat(), **kwargs)


def test_on_time_task_runs() -> None:
    assert missed_task_lateness(_task(5)) is None
    assert missed_task_lateness(_task(MISSED_TASK_GRACE_SECONDS - 30)) is None


def test_long_overdue_task_is_missed() -> None:
    lateness = missed_task_lateness(_task(MISSED_TASK_GRACE_SECONDS + 600))
    assert lateness is not None and lateness > MISSED_TASK_GRACE_SECONDS


def test_shutdown_has_a_much_tighter_window() -> None:
    task = _task(MISSED_SHUTDOWN_GRACE_SECONDS + 60, command="system_shutdown", task_type="system_shutdown")
    assert missed_task_lateness(task) is not None
    # The same lateness is still acceptable for a non-shutdown task.
    assert missed_task_lateness(_task(MISSED_SHUTDOWN_GRACE_SECONDS + 60)) is None


def test_repeating_tasks_are_never_missed() -> None:
    task = _task(86400, task_type="screen_watch", command="screen_watch", interval_seconds=60)
    assert missed_task_lateness(task) is None
