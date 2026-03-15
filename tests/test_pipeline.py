"""
Test: MCP Pipeline Composition

Verifies the automatic tool chain: search → summarize → save_to_file
Tests that data flows correctly between tools.
"""

import os
import sys
import asyncio
import json
from dotenv import load_dotenv
from aiadvent.agent.agent import Agent
from aiadvent.agent.mcp.config import MCPServerConfig


async def test_pipeline():
    load_dotenv()
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

    print("🧪 Test: MCP Pipeline Composition")
    print("=" * 60)

    # --- Init ---
    print("⚙️  Connecting to pipeline server...")
    await agent.init_mcp()
    tools = agent.get_mcp_tools()
    tool_names = [t["name"] for t in tools]
    print(f"   Tools: {tool_names}")
    assert "search" in tool_names, "search tool missing"
    assert "summarize" in tool_names, "summarize tool missing"
    assert "save_to_file" in tool_names, "save_to_file tool missing"
    print("   ✅ All 3 tools available")
    print()

    query = "What are the main benefits of using microservices architecture?"

    # --- Step 1: search ---
    print(f"1️⃣  search(query=\"{query[:50]}...\")")
    search_result = await agent.call_mcp_tool("search", {"query": query})
    assert isinstance(search_result, str), "search should return string"
    assert len(search_result) > 100, f"search result too short: {len(search_result)} chars"
    print(f"   ✅ Got {len(search_result)} chars")

    # --- Step 2: summarize (input = search output) ---
    print("2️⃣  summarize(text=<search result>)")
    summary = await agent.call_mcp_tool("summarize", {"text": search_result})
    assert isinstance(summary, str), "summarize should return string"
    assert len(summary) > 50, f"summary too short: {len(summary)} chars"
    assert len(summary) < len(search_result), "summary should be shorter than original"
    print(f"   ✅ Got {len(summary)} chars (compressed from {len(search_result)})")

    # --- Step 3: save_to_file (input = summarize output) ---
    filename = "test_pipeline_result.txt"
    print(f"3️⃣  save_to_file(content=<summary>, filename=\"{filename}\")")
    save_result = await agent.call_mcp_tool(
        "save_to_file", {"content": summary, "filename": filename}
    )
    save_data = json.loads(save_result)
    assert "saved" in save_data, "save_to_file should return saved path"
    filepath = save_data["saved"]
    assert os.path.exists(filepath), f"file not created: {filepath}"

    with open(filepath, encoding="utf-8") as f:
        saved_content = f.read()
    assert saved_content == summary, "saved content doesn't match summary"
    print(f"   ✅ Saved to: {filepath}")
    print(f"   ✅ Content matches summary")

    # --- Cleanup ---
    os.remove(filepath)
    print()
    print("=" * 60)
    print("✅ All pipeline tests passed!")

    for client in agent.mcp_clients.values():
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_pipeline())
