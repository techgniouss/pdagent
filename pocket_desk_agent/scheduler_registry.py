"""Registry for storing and managing scheduled tasks."""

from __future__ import annotations

import datetime as dt
import json
import logging
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from pocket_desk_agent.app_paths import app_path, existing_app_path
from pocket_desk_agent.scheduling_utils import (
    get_task_due_at,
    local_now,
    parse_iso_datetime,
)

logger = logging.getLogger(__name__)

SCHEDULER_PATH = app_path("scheduled_tasks.json")


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""

    id: str
    user_id: int
    command: str
    execute_at: str
    status: str = "pending"
    created_at: str = field(default_factory=lambda: local_now().isoformat())
    error: Optional[str] = None
    task_type: str = "legacy"
    interval_seconds: Optional[int] = None
    repeat_until: Optional[str] = None
    next_run_at: Optional[str] = None
    run_count: int = 0
    last_run_at: Optional[str] = None
    temporary_command: bool = False
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledTask":
        """Create an instance from persisted data."""
        return cls(**data)


class SchedulerRegistry:
    """Manages persistent storage of scheduled tasks."""

    def __init__(self) -> None:
        self.tasks: List[dict] = []
        self.load()

    def load(self) -> bool:
        """Load scheduled tasks from disk."""
        try:
            load_path = SCHEDULER_PATH
            if not load_path.exists():
                load_path = existing_app_path("scheduled_tasks.json")

            if load_path.exists():
                with open(load_path, "r", encoding="utf-8") as handle:
                    self.tasks = json.load(handle)
                logger.info("Loaded %s scheduled tasks", len(self.tasks))
            else:
                self.tasks = []
            return True
        except Exception as exc:
            logger.error("Failed to load scheduler registry: %s", exc, exc_info=True)
            self.tasks = []
            return False

    def save(self) -> bool:
        """Save scheduled tasks to disk."""
        try:
            SCHEDULER_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(SCHEDULER_PATH, "w", encoding="utf-8") as handle:
                json.dump(self.tasks, handle, indent=2, ensure_ascii=False)
            return True
        except Exception as exc:
            logger.error("Failed to save scheduler registry: %s", exc, exc_info=True)
            return False

    def add_task(self, task: ScheduledTask) -> None:
        """Add a new task."""
        task_dict = task.to_dict()
        if task_dict.get("interval_seconds") and not task_dict.get("next_run_at"):
            task_dict["next_run_at"] = task_dict["execute_at"]
        self.tasks.append(task_dict)
        self.save()

    def get_pending_tasks(self) -> List[ScheduledTask]:
        """Return all pending tasks that are due right now."""
        now = local_now()
        due_tasks: List[ScheduledTask] = []
        for task_dict in self.tasks:
            if task_dict.get("status") != "pending":
                continue

            due_at = get_task_due_at(task_dict)
            if due_at is None:
                logger.error(
                    "Invalid datetime format for task %s",
                    task_dict.get("id", "?"),
                )
                continue

            if due_at <= now:
                due_tasks.append(ScheduledTask.from_dict(task_dict))

        due_tasks.sort(
            key=lambda task: parse_iso_datetime(task.next_run_at or task.execute_at)
            or now,
        )
        return due_tasks

    def get_all_pending(self) -> List[dict]:
        """Return all pending tasks, including future runs."""
        pending = [task for task in self.tasks if task.get("status") == "pending"]
        pending.sort(key=lambda task: get_task_due_at(task) or local_now())
        return pending

    def update_task_status(self, task_id: str, status: str, error: str | None = None) -> bool:
        """Update the status of a task."""
        for task_dict in self.tasks:
            if task_dict.get("id") != task_id:
                continue
            task_dict["status"] = status
            if error:
                task_dict["error"] = error
            elif "error" in task_dict:
                task_dict["error"] = None
            return self.save()
        return False

    def update_task_metadata(self, task_id: str, metadata: dict) -> bool:
        """Replace the stored metadata for one task."""
        for task_dict in self.tasks:
            if task_dict.get("id") != task_id:
                continue
            task_dict["metadata"] = dict(metadata)
            return self.save()
        return False

    def finalize_task_run(
        self,
        task_id: str,
        *,
        success: bool,
        error: str | None = None,
        executed_at: dt.datetime | None = None,
    ) -> Optional[ScheduledTask]:
        """Persist the outcome of a task run and schedule the next run when needed."""
        executed = executed_at or local_now()
        for task_dict in self.tasks:
            if task_dict.get("id") != task_id:
                continue

            task_dict["last_run_at"] = executed.isoformat()
            task_dict["run_count"] = int(task_dict.get("run_count", 0)) + 1

            if error:
                task_dict["error"] = error
            else:
                task_dict["error"] = None

            interval_seconds = task_dict.get("interval_seconds")
            repeat_until = parse_iso_datetime(str(task_dict.get("repeat_until") or ""))

            if success and interval_seconds and repeat_until:
                next_run_at = executed + dt.timedelta(seconds=int(interval_seconds))
                if next_run_at <= repeat_until:
                    task_dict["next_run_at"] = next_run_at.isoformat()
                    task_dict["status"] = "pending"
                else:
                    task_dict["next_run_at"] = None
                    task_dict["status"] = "completed"
            else:
                task_dict["next_run_at"] = None
                task_dict["status"] = "completed" if success else "failed"

            self.save()
            return ScheduledTask.from_dict(task_dict)

        return None

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID."""
        return self.pop_task(task_id) is not None

    def pop_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Delete and return a task by ID."""
        for index, task_dict in enumerate(self.tasks):
            if task_dict.get("id") != task_id:
                continue

            removed = ScheduledTask.from_dict(task_dict)
            del self.tasks[index]
            self.save()
            return removed

        return None

    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Remove completed or failed tasks older than ``days``."""
        cutoff = local_now() - dt.timedelta(days=days)
        before = len(self.tasks)
        kept: list[dict] = []

        for task_dict in self.tasks:
            if task_dict.get("status", "pending") == "pending":
                kept.append(task_dict)
                continue

            created_at = parse_iso_datetime(str(task_dict.get("created_at") or ""))
            if created_at is None or created_at >= cutoff:
                kept.append(task_dict)

        removed = before - len(kept)
        if removed:
            self.tasks = kept
            self.save()
            logger.info("Cleaned up %s old task(s) older than %s days", removed, days)
        return removed


_scheduler_registry: Optional[SchedulerRegistry] = None


def get_scheduler_registry() -> SchedulerRegistry:
    """Return the shared scheduler registry instance."""
    global _scheduler_registry
    if _scheduler_registry is None:
        _scheduler_registry = SchedulerRegistry()
    return _scheduler_registry
