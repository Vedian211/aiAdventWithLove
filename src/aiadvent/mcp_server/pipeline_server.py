"""MCP Server for Pipeline: search → summarize → save_to_file."""

import asyncio
import json
import os
from pathlib import Path
from openai import OpenAI
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("pipeline-server")

OUTPUT_DIR = Path(__file__).resolve().parents[3] / "output"


def _get_client():
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search",
            description="Search for information on a topic using AI",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="summarize",
            description="Summarize the given text into key points",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to summarize"}
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="save_to_file",
            description="Save content to a file in the output directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to save"},
                    "filename": {"type": "string", "description": "Output filename"}
                },
                "required": ["content", "filename"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search":
        client = _get_client()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a research assistant. Provide detailed, factual information on the topic."},
                {"role": "user", "content": arguments["query"]},
            ],
        )
        result = resp.choices[0].message.content

    elif name == "summarize":
        client = _get_client()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Summarize the following text into concise key points."},
                {"role": "user", "content": arguments["text"]},
            ],
        )
        result = resp.choices[0].message.content

    elif name == "save_to_file":
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filepath = OUTPUT_DIR / arguments["filename"]
        filepath.write_text(arguments["content"], encoding="utf-8")
        result = json.dumps({"saved": str(filepath)})

    else:
        result = json.dumps({"error": f"Unknown tool: {name}"})

    return [TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
