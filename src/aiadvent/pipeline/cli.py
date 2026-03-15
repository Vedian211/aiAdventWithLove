"""CLI for MCP pipeline: search → summarize → save_to_file."""

import os
import sys
import asyncio
import json
from datetime import datetime
from aiadvent.agent.agent import Agent
from aiadvent.agent.mcp.config import MCPServerConfig


async def run_pipeline(query: str):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        sys.exit(1)

    mcp_config = MCPServerConfig(
        command="python",
        args=["-m", "aiadvent.mcp_server.pipeline_server"],
        env={**os.environ, "OPENAI_API_KEY": api_key},
    )

    agent = Agent(
        api_key=api_key,
        model="gpt-4o-mini",
        system_prompt="You are a helpful assistant.",
        mcp_server_config=mcp_config,
    )

    print("🔗 MCP Pipeline: search → summarize → save_to_file")
    print("=" * 60)
    print(f"📝 Query: {query}")
    print()

    await agent.init_mcp()

    # Step 1: search
    print("1️⃣  Searching...")
    search_result = await agent.call_mcp_tool("search", {"query": query})
    print(f"   ✅ Got {len(search_result)} chars")

    # Step 2: summarize
    print("2️⃣  Summarizing...")
    summary = await agent.call_mcp_tool("summarize", {"text": search_result})
    print(f"   ✅ Got {len(summary)} chars")

    # Step 3: save
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"pipeline_{timestamp}.txt"
    print(f"3️⃣  Saving to output/{filename}...")
    save_result = await agent.call_mcp_tool(
        "save_to_file", {"content": summary, "filename": filename}
    )
    path = json.loads(save_result)["saved"]
    print(f"   ✅ Saved to: {path}")

    print()
    print("=" * 60)
    print("📄 Result:")
    print("-" * 40)
    print(summary)

    for client in agent.mcp_clients.values():
        await client.disconnect()


def main():
    if len(sys.argv) < 2:
        print("Usage: pipeline \"your query here\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    asyncio.run(run_pipeline(query))


if __name__ == "__main__":
    main()
