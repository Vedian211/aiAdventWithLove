"""SQLite storage for scheduled tasks and results."""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class SchedulerStorage:
    """Storage for scheduled tasks and execution results."""
    
    def __init__(self, db_path: str = "scheduler.db"):
        """Initialize storage with SQLite database."""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                schedule TEXT NOT NULL,
                data TEXT NOT NULL,
                next_run TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL
            )
        """)
        
        # Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                executed_at TEXT NOT NULL,
                result TEXT,
                status TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES scheduled_tasks (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_task(self, task_type: str, schedule: str, data: Dict[str, Any], next_run: datetime) -> int:
        """Save a new task and return its ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scheduled_tasks (type, schedule, data, next_run, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            task_type,
            schedule,
            json.dumps(data),
            next_run.isoformat(),
            datetime.now().isoformat()
        ))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return task_id
    
    def load_tasks(self, status: str = "active") -> List[Dict[str, Any]]:
        """Load all tasks with given status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, type, schedule, data, next_run, status, created_at
            FROM scheduled_tasks
            WHERE status = ?
        """, (status,))
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                "id": row[0],
                "type": row[1],
                "schedule": row[2],
                "data": json.loads(row[3]),
                "next_run": datetime.fromisoformat(row[4]),
                "status": row[5],
                "created_at": datetime.fromisoformat(row[6])
            })
        
        conn.close()
        return tasks
    
    def update_task_status(self, task_id: int, status: str):
        """Update task status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE scheduled_tasks
            SET status = ?
            WHERE id = ?
        """, (status, task_id))
        
        conn.commit()
        conn.close()
    
    def update_next_run(self, task_id: int, next_run: datetime):
        """Update next run time for a task."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE scheduled_tasks
            SET next_run = ?
            WHERE id = ?
        """, (next_run.isoformat(), task_id))
        
        conn.commit()
        conn.close()
    
    def save_result(self, task_id: int, result: Any, status: str = "success"):
        """Save task execution result."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO task_results (task_id, executed_at, result, status)
            VALUES (?, ?, ?, ?)
        """, (
            task_id,
            datetime.now().isoformat(),
            json.dumps(result) if result else None,
            status
        ))
        
        conn.commit()
        conn.close()
    
    def get_results(self, task_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get task execution results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if task_id:
            cursor.execute("""
                SELECT id, task_id, executed_at, result, status
                FROM task_results
                WHERE task_id = ?
                ORDER BY executed_at DESC
                LIMIT ?
            """, (task_id, limit))
        else:
            cursor.execute("""
                SELECT id, task_id, executed_at, result, status
                FROM task_results
                ORDER BY executed_at DESC
                LIMIT ?
            """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "task_id": row[1],
                "executed_at": datetime.fromisoformat(row[2]),
                "result": json.loads(row[3]) if row[3] else None,
                "status": row[4]
            })
        
        conn.close()
        return results
    
    def get_summary(self, period: str = "day") -> Dict[str, Any]:
        """Get aggregated summary for a period."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate time range
        now = datetime.now()
        if period == "hour":
            time_filter = now.replace(minute=0, second=0, microsecond=0).isoformat()
        elif period == "day":
            time_filter = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif period == "week":
            days_back = now.weekday()
            time_filter = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        else:
            time_filter = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        # Get statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed
            FROM task_results
            WHERE executed_at >= ?
        """, (time_filter,))
        
        row = cursor.fetchone()
        total = row[0] or 0
        successful = row[1] or 0
        failed = row[2] or 0
        
        # Get task type distribution
        cursor.execute("""
            SELECT t.type, COUNT(*) as count
            FROM task_results r
            JOIN scheduled_tasks t ON r.task_id = t.id
            WHERE r.executed_at >= ?
            GROUP BY t.type
            ORDER BY count DESC
        """, (time_filter,))
        
        task_types = {}
        for row in cursor.fetchall():
            task_types[row[0]] = row[1]
        
        conn.close()
        
        return {
            "period": period,
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / total * 100, 1) if total > 0 else 0,
            "task_types": task_types
        }
