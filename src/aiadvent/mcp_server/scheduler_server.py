"""MCP Server for Task Scheduler."""

import asyncio
import json
from datetime import datetime, timedelta
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from aiadvent.scheduler.storage import SchedulerStorage
from aiadvent.scheduler.task_scheduler import TaskScheduler


# Initialize storage and scheduler
storage = SchedulerStorage("scheduler.db")
scheduler = TaskScheduler(storage)

# Initialize MCP server
app = Server("scheduler-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available scheduler tools."""
    return [
        Tool(
            name="schedule_reminder",
            description="Schedule a one-time reminder at a specific time",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The reminder message"
                    },
                    "minutes_from_now": {
                        "type": "integer",
                        "description": "How many minutes from now to trigger the reminder"
                    }
                },
                "required": ["message", "minutes_from_now"]
            }
        ),
        Tool(
            name="schedule_periodic_task",
            description="Schedule a task that runs periodically at fixed intervals",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "description": "Type of task (e.g., 'data_collection', 'monitoring')"
                    },
                    "interval_minutes": {
                        "type": "integer",
                        "description": "Interval in minutes between executions"
                    },
                    "data": {
                        "type": "object",
                        "description": "Additional data for the task"
                    }
                },
                "required": ["task_type", "interval_minutes"]
            }
        ),
        Tool(
            name="list_scheduled_tasks",
            description="List all scheduled tasks",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status: 'active', 'completed', 'cancelled'",
                        "enum": ["active", "completed", "cancelled"]
                    }
                }
            }
        ),
        Tool(
            name="cancel_task",
            description="Cancel a scheduled task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task to cancel"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="get_summary",
            description="Get execution summary for a time period",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "Time period: 'hour', 'day', or 'week'",
                        "enum": ["hour", "day", "week"]
                    }
                }
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "schedule_reminder":
        message = arguments["message"]
        minutes = arguments["minutes_from_now"]
        run_at = datetime.now() + timedelta(minutes=minutes)
        
        task_id = scheduler.add_reminder(message, run_at)
        
        result = {
            "task_id": task_id,
            "message": message,
            "scheduled_for": run_at.isoformat(),
            "status": "scheduled"
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    elif name == "schedule_periodic_task":
        task_type = arguments["task_type"]
        interval = arguments["interval_minutes"]
        data = arguments.get("data", {})
        
        task_id = scheduler.add_periodic_task(task_type, interval, data)
        
        result = {
            "task_id": task_id,
            "task_type": task_type,
            "interval_minutes": interval,
            "status": "scheduled"
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    elif name == "list_scheduled_tasks":
        status = arguments.get("status", "active")
        tasks = scheduler.get_tasks(status)
        
        # Format tasks for display
        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append({
                "id": task["id"],
                "type": task["type"],
                "schedule": task["schedule"],
                "next_run": task["next_run"].isoformat(),
                "status": task["status"],
                "data": task["data"]
            })
        
        result = {
            "total": len(formatted_tasks),
            "tasks": formatted_tasks
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    elif name == "cancel_task":
        task_id = arguments["task_id"]
        scheduler.cancel_task(task_id)
        
        result = {
            "task_id": task_id,
            "status": "cancelled"
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    elif name == "get_summary":
        period = arguments.get("period", "day")
        summary = scheduler.get_summary(period)
        
        return [TextContent(
            type="text",
            text=json.dumps(summary, indent=2)
        )]
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
