"""Mock API for demonstration purposes."""

from typing import List, Dict, Any
from datetime import datetime


# Mock data storage
USERS = [
    {"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "role": "Developer"},
    {"id": 2, "name": "Bob Smith", "email": "bob@example.com", "role": "Designer"},
    {"id": 3, "name": "Carol White", "email": "carol@example.com", "role": "Manager"},
]

TASKS = [
    {"id": 1, "title": "Setup project", "assignee": "Alice Johnson", "status": "completed", "created_at": "2026-03-01"},
    {"id": 2, "title": "Design mockups", "assignee": "Bob Smith", "status": "in_progress", "created_at": "2026-03-05"},
]

task_counter = 3


def get_users() -> List[Dict[str, Any]]:
    """Get all users."""
    return USERS


def get_user(user_id: int) -> Dict[str, Any]:
    """Get user by ID."""
    for user in USERS:
        if user["id"] == user_id:
            return user
    return {"error": f"User {user_id} not found"}


def create_task(title: str, assignee: str) -> Dict[str, Any]:
    """Create a new task."""
    global task_counter
    task = {
        "id": task_counter,
        "title": title,
        "assignee": assignee,
        "status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d")
    }
    TASKS.append(task)
    task_counter += 1
    return task


def list_tasks() -> List[Dict[str, Any]]:
    """Get all tasks."""
    return TASKS
