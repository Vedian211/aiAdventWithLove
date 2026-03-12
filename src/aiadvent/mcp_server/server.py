"""MCP Server for Mock API."""

import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from . import mock_api


# Initialize MCP server
app = Server("mock-api-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_users",
            description="Get list of all users in the system",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_user",
            description="Get detailed information about a specific user by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The ID of the user to retrieve"
                    }
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="create_task",
            description="Create a new task and assign it to a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the task"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Name of the person to assign the task to"
                    }
                },
                "required": ["title", "assignee"]
            }
        ),
        Tool(
            name="list_tasks",
            description="Get list of all tasks in the system",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "get_users":
        result = mock_api.get_users()
    elif name == "get_user":
        user_id = arguments.get("user_id")
        result = mock_api.get_user(user_id)
    elif name == "create_task":
        title = arguments.get("title")
        assignee = arguments.get("assignee")
        result = mock_api.create_task(title, assignee)
    elif name == "list_tasks":
        result = mock_api.list_tasks()
    else:
        result = {"error": f"Unknown tool: {name}"}
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
