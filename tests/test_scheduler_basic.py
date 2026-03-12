"""Quick test of scheduler functionality."""

import asyncio
from datetime import datetime, timedelta
from aiadvent.scheduler.storage import SchedulerStorage
from aiadvent.scheduler.task_scheduler import TaskScheduler


def test_storage():
    """Test storage operations."""
    print("Testing storage...")
    
    # Create storage
    storage = SchedulerStorage("test_scheduler.db")
    
    # Save a task
    task_id = storage.save_task(
        task_type="reminder",
        schedule="once",
        data={"message": "Test reminder"},
        next_run=datetime.now() + timedelta(minutes=5)
    )
    
    print(f"✅ Created task #{task_id}")
    
    # Load tasks
    tasks = storage.load_tasks("active")
    print(f"✅ Loaded {len(tasks)} task(s)")
    
    # Save result
    storage.save_result(task_id, {"status": "delivered"}, "success")
    print(f"✅ Saved result for task #{task_id}")
    
    # Get summary
    summary = storage.get_summary("day")
    print(f"✅ Summary: {summary}")
    
    print()


def test_scheduler():
    """Test scheduler operations."""
    print("Testing scheduler...")
    
    storage = SchedulerStorage("test_scheduler.db")
    scheduler = TaskScheduler(storage)
    
    # Add reminder
    task_id = scheduler.add_reminder(
        "Test reminder",
        datetime.now() + timedelta(minutes=1)
    )
    print(f"✅ Added reminder #{task_id}")
    
    # Add periodic task
    task_id = scheduler.add_periodic_task(
        "data_collection",
        5,
        {"source": "test"}
    )
    print(f"✅ Added periodic task #{task_id}")
    
    # Get tasks
    tasks = scheduler.get_tasks("active")
    print(f"✅ Active tasks: {len(tasks)}")
    
    for task in tasks:
        print(f"   - Task #{task['id']}: {task['type']} (next: {task['next_run']})")
    
    # Cancel task
    if tasks:
        scheduler.cancel_task(tasks[0]['id'])
        print(f"✅ Cancelled task #{tasks[0]['id']}")
    
    print()


async def test_worker():
    """Test worker execution."""
    print("Testing worker...")
    
    from aiadvent.scheduler.worker import SchedulerWorker
    
    storage = SchedulerStorage("test_scheduler.db")
    scheduler = TaskScheduler(storage)
    
    # Add a task that's due now
    task_id = scheduler.add_reminder(
        "Immediate test",
        datetime.now()
    )
    print(f"✅ Added immediate task #{task_id}")
    
    # Create worker
    worker = SchedulerWorker(scheduler, check_interval=1)
    
    # Run worker for 3 seconds
    print("⏳ Running worker for 3 seconds...")
    
    async def run_limited():
        await asyncio.sleep(3)
        worker.stop()
    
    await asyncio.gather(
        worker.run(),
        run_limited()
    )
    
    print("✅ Worker test completed")
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Scheduler Tests")
    print("=" * 60)
    print()
    
    test_storage()
    test_scheduler()
    asyncio.run(test_worker())
    
    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    
    # Cleanup
    import os
    if os.path.exists("test_scheduler.db"):
        os.remove("test_scheduler.db")
        print("🧹 Cleaned up test database")


if __name__ == "__main__":
    main()
