"""Background worker for executing scheduled tasks."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from .task_scheduler import TaskScheduler
from .storage import SchedulerStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchedulerWorker:
    """Background worker that executes scheduled tasks."""
    
    def __init__(self, scheduler: TaskScheduler, check_interval: int = 10):
        """
        Initialize worker.
        
        Args:
            scheduler: TaskScheduler instance
            check_interval: How often to check for due tasks (seconds)
        """
        self.scheduler = scheduler
        self.check_interval = check_interval
        self.running = False
    
    async def execute_task(self, task: Dict[str, Any]) -> Any:
        """Execute a single task."""
        task_id = task["id"]
        task_type = task["type"]
        data = task["data"]
        
        logger.info(f"Executing task #{task_id} ({task_type})")
        
        try:
            if task_type == "reminder":
                result = self._execute_reminder(data)
            elif task_type == "data_collection":
                result = await self._execute_data_collection(data)
            else:
                result = {"message": f"Executed {task_type}", "data": data}
            
            self.scheduler.mark_task_executed(task_id, result, "success")
            logger.info(f"Task #{task_id} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Task #{task_id} failed: {e}")
            self.scheduler.mark_task_executed(task_id, {"error": str(e)}, "error")
            raise
        finally:
            # Reschedule or mark as completed
            self.scheduler.reschedule_task(task_id, task)
    
    def _execute_reminder(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a reminder task."""
        message = data.get("message", "")
        logger.info(f"🔔 REMINDER: {message}")
        return {
            "type": "reminder",
            "message": message,
            "delivered_at": datetime.now().isoformat()
        }
    
    async def _execute_data_collection(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a data collection task."""
        source = data.get("source", "unknown")
        logger.info(f"📊 Collecting data from: {source}")
        
        # Simulate data collection
        await asyncio.sleep(0.5)
        
        return {
            "type": "data_collection",
            "source": source,
            "collected_at": datetime.now().isoformat(),
            "data": {"sample": "data"}
        }
    
    async def run(self):
        """Main worker loop."""
        self.running = True
        logger.info("🚀 Scheduler worker started")
        
        while self.running:
            try:
                # Get due tasks
                due_tasks = self.scheduler.get_due_tasks()
                
                if due_tasks:
                    logger.info(f"Found {len(due_tasks)} due task(s)")
                    
                    # Execute tasks
                    for task in due_tasks:
                        try:
                            await self.execute_task(task)
                        except Exception as e:
                            logger.error(f"Error executing task: {e}")
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(self.check_interval)
        
        logger.info("🛑 Scheduler worker stopped")
    
    def stop(self):
        """Stop the worker."""
        self.running = False


async def run_worker(db_path: str = "scheduler.db", check_interval: int = 10):
    """Run the scheduler worker."""
    storage = SchedulerStorage(db_path)
    scheduler = TaskScheduler(storage)
    worker = SchedulerWorker(scheduler, check_interval)
    
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        worker.stop()
