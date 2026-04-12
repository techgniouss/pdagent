"""Registry for storing and managing scheduled tasks."""

import json
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Registry file location — under the project's config directory
SCHEDULER_PATH = Path.home() / ".pdagent" / "scheduled_tasks.json"

@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    id: str
    user_id: int
    command: str  # Custom command name or raw text for Claude
    execute_at: str  # ISO format datetime
    status: str = "pending"  # pending, completed, failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ScheduledTask':
        """Create from dictionary."""
        return cls(**data)


class SchedulerRegistry:
    """Manages persistent storage of scheduled tasks."""
    
    def __init__(self):
        """Initialize the scheduler registry."""
        self.tasks: List[dict] = []
        self.load()
    
    def load(self) -> bool:
        """Load scheduled tasks from disk."""
        try:
            if SCHEDULER_PATH.exists():
                with open(SCHEDULER_PATH, 'r', encoding='utf-8') as f:
                    self.tasks = json.load(f)
                logger.info(f"Loaded {len(self.tasks)} scheduled tasks")
                return True
            else:
                self.tasks = []
                return True
        except Exception as e:
            logger.error(f"Failed to load scheduler registry: {e}")
            self.tasks = []
            return False
    
    def save(self) -> bool:
        """Save scheduled tasks to disk."""
        try:
            SCHEDULER_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(SCHEDULER_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save scheduler registry: {e}")
            return False
    
    def add_task(self, task: ScheduledTask):
        """Add a new task."""
        self.tasks.append(task.to_dict())
        self.save()
    
    def get_pending_tasks(self) -> List[ScheduledTask]:
        """Get all tasks that are due and pending."""
        now = datetime.now()
        due_tasks = []
        for t_dict in self.tasks:
            if t_dict["status"] == "pending":
                task = ScheduledTask.from_dict(t_dict)
                try:
                    execute_at = datetime.fromisoformat(task.execute_at)
                    if execute_at <= now:
                        due_tasks.append(task)
                except ValueError:
                    logger.error(f"Invalid datetime format for task {task.id}: {task.execute_at}")
        return due_tasks

    def update_task_status(self, task_id: str, status: str, error: str = None):
        """Update status of a task."""
        for t_dict in self.tasks:
            if t_dict["id"] == task_id:
                t_dict["status"] = status
                if error:
                    t_dict["error"] = error
                break
        self.save()

    def delete_task(self, task_id: str) -> bool:
        """Remove a task by ID. Returns True if found and removed."""
        original_len = len(self.tasks)
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        if len(self.tasks) < original_len:
            self.save()
            return True
        return False

    def get_all_pending(self) -> List[dict]:
        """Return all tasks with status='pending' as raw dicts (not yet due)."""
        return [t for t in self.tasks if t.get("status") == "pending"]

    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Remove completed/failed tasks older than *days*.

        Returns the number of tasks removed.
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        before = len(self.tasks)

        kept: list[dict] = []
        for t in self.tasks:
            status = t.get("status", "pending")
            # Always keep pending tasks regardless of age
            if status == "pending":
                kept.append(t)
                continue
            # For completed/failed tasks, check age
            try:
                created = datetime.fromisoformat(t.get("created_at", ""))
                if created >= cutoff:
                    kept.append(t)
            except (ValueError, TypeError):
                # Unparseable date — keep it to be safe
                kept.append(t)

        removed = before - len(kept)
        if removed:
            self.tasks = kept
            self.save()
            logger.info(f"Cleaned up {removed} old task(s) (older than {days} days)")
        return removed

# Global registry instance
_scheduler_registry: Optional[SchedulerRegistry] = None

def get_scheduler_registry() -> SchedulerRegistry:
    """Get the global scheduler registry instance."""
    global _scheduler_registry
    if _scheduler_registry is None:
        _scheduler_registry = SchedulerRegistry()
    return _scheduler_registry
