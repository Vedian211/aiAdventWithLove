"""Task scheduler for managing scheduled and periodic tasks."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from .storage import SchedulerStorage


class TaskScheduler:
    """Manages scheduled tasks and periodic execution."""
    
    def __init__(self, storage: SchedulerStorage):
        """Initialize scheduler with storage."""
        self.storage = storage
    
    def add_reminder(self, message: str, run_at: datetime) -> int:
        """Add a one-time reminder."""
        data = {"message": message}
        task_id = self.storage.save_task(
            task_type="reminder",
            schedule="once",
            data=data,
            next_run=run_at
        )
        return task_id
    
    def add_periodic_task(self, task_type: str, interval_minutes: int, data: Dict[str, Any]) -> int:
        """Add a periodic task that runs every N minutes."""
        next_run = datetime.now() + timedelta(minutes=interval_minutes)
        schedule = f"every_{interval_minutes}m"
        
        task_id = self.storage.save_task(
            task_type=task_type,
            schedule=schedule,
            data=data,
            next_run=next_run
        )
        return task_id
    
    def get_tasks(self, status: str = "active") -> List[Dict[str, Any]]:
        """Get all tasks with given status."""
        return self.storage.load_tasks(status)
    
    def cancel_task(self, task_id: int):
        """Cancel a task."""
        self.storage.update_task_status(task_id, "cancelled")
    
    def get_due_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks that are due to run now."""
        tasks = self.storage.load_tasks("active")
        now = datetime.now()
        
        due_tasks = []
        for task in tasks:
            if task["next_run"] <= now:
                due_tasks.append(task)
        
        return due_tasks
    
    def mark_task_executed(self, task_id: int, result: Any, status: str = "success"):
        """Mark task as executed and save result."""
        self.storage.save_result(task_id, result, status)
    
    def reschedule_task(self, task_id: int, task: Dict[str, Any]):
        """Reschedule a periodic task or mark one-time task as completed."""
        if task["schedule"] == "once":
            # One-time task - mark as completed
            self.storage.update_task_status(task_id, "completed")
        else:
            # Periodic task - calculate next run
            schedule = task["schedule"]
            if schedule.startswith("every_"):
                minutes = int(schedule.split("_")[1].rstrip("m"))
                next_run = datetime.now() + timedelta(minutes=minutes)
                self.storage.update_next_run(task_id, next_run)
    
    def get_summary(self, period: str = "day") -> Dict[str, Any]:
        """Get execution summary for a period."""
        return self.storage.get_summary(period)
