"""CLI for managing the scheduler worker."""

import asyncio
import sys
from aiadvent.scheduler.worker import run_worker


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: scheduler <command>")
        print("\nCommands:")
        print("  start    Start the scheduler worker")
        print("  help     Show this help message")
        return
    
    command = sys.argv[1]
    
    if command == "start":
        print("🚀 Starting scheduler worker...")
        print("Press Ctrl+C to stop")
        print()
        try:
            asyncio.run(run_worker())
        except KeyboardInterrupt:
            print("\n✅ Scheduler stopped")
    
    elif command == "help":
        print("Scheduler CLI")
        print("\nCommands:")
        print("  start    Start the scheduler worker")
        print("  help     Show this help message")
    
    else:
        print(f"Unknown command: {command}")
        print("Run 'scheduler help' for usage")


if __name__ == "__main__":
    main()
