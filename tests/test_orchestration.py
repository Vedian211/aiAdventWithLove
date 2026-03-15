"""
Test: MCP Orchestration — cross-server tool routing.

Scenario 1: mock-api + scheduler — agent must use tools from BOTH servers.
Scenario 2: pipeline server — agent must call tools in correct order.
"""

import os
import sys
import asyncio
import json
from dotenv import load_dotenv
from aiadvent.agent.mcp.config import MCPServerConfig
from aiadvent.orchestrator.orchestrator import Orchestrator


# ── helpers ──────────────────────────────────────────────────────────

def _env():
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("❌ OPENAI_API_KEY not set")
        sys.exit(1)
    return key


def _mock_and_scheduler_configs():
    return [
        MCPServerConfig(command="python", args=["-m", "aiadvent.mcp_server.server"]),
        MCPServerConfig(command="python", args=["-m", "aiadvent.mcp_server.scheduler_server"]),
    ]


def _pipeline_config():
    return [
        MCPServerConfig(
            command="python",
            args=["-m", "aiadvent.mcp_server.pipeline_server"],
            env={**os.environ, "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")},
        ),
    ]


# ── Scenario 1 ──────────────────────────────────────────────────────

async def test_cross_server():
    """Agent uses tools from mock-api AND scheduler in one conversation."""
    api_key = _env()
    orch = Orchestrator(api_key=api_key)
    await orch.connect(_mock_and_scheduler_configs())

    tool_names = [t["function"]["name"] for t in orch.openai_tools]
    print("🧪 Scenario 1: Cross-server (mock-api + scheduler)")
    print(f"   Available tools: {tool_names}")

    # Verify tools from both servers are present
    assert "get_users" in tool_names, "get_users missing"
    assert "schedule_reminder" in tool_names, "schedule_reminder missing"
    print("   ✅ Tools from both servers registered")

    # Track which tools are called
    called_tools = []

    def tracker(event, data):
        if event == "tool_call":
            called_tools.append(data["name"])
            print(f"   🔧 {data['name']}({data['arguments']})")
        elif event == "tool_result":
            preview = data["result"][:120]
            print(f"   ✅ → {preview}")

    query = (
        "First, get the list of all users. "
        "Then create a task titled 'Review PR #42' and assign it to the first user you found. "
        "Finally, schedule a reminder in 30 minutes with the message 'Check PR #42 status'."
    )
    print(f"\n   Query: {query}\n")

    answer = await orch.run(query, on_step=tracker)
    print(f"\n   💬 Answer: {answer[:300]}")

    # Verify cross-server usage
    assert "get_users" in called_tools, "get_users was not called"
    assert "create_task" in called_tools, "create_task was not called"
    assert "schedule_reminder" in called_tools, "schedule_reminder was not called"
    print("\n   ✅ Tools from BOTH servers were used")

    # Verify order: get_users must come before create_task
    assert called_tools.index("get_users") < called_tools.index("create_task"), \
        "get_users should be called before create_task"
    print("   ✅ Correct call order verified")

    try:
        await orch.disconnect()
    except BaseException:
        pass
    print("   ✅ Scenario 1 passed!\n")


# ── Scenario 2 ──────────────────────────────────────────────────────

async def test_pipeline_order():
    """Agent calls pipeline tools in correct sequence: search → summarize → save."""
    api_key = _env()
    orch = Orchestrator(api_key=api_key)
    await orch.connect(_pipeline_config())

    tool_names = [t["function"]["name"] for t in orch.openai_tools]
    print("🧪 Scenario 2: Pipeline tool ordering")
    print(f"   Available tools: {tool_names}")

    called_tools = []

    def tracker(event, data):
        if event == "tool_call":
            called_tools.append(data["name"])
            print(f"   🔧 {data['name']}")
        elif event == "tool_result":
            print(f"   ✅ → {len(data['result'])} chars")

    query = (
        "Search for information about Python asyncio, "
        "then summarize the result, "
        "and save the summary to a file called 'asyncio_summary.txt'."
    )
    print(f"\n   Query: {query}\n")

    answer = await orch.run(query, on_step=tracker)
    print(f"\n   💬 Answer: {answer[:300]}")

    assert "search" in called_tools, "search was not called"
    assert "summarize" in called_tools, "summarize was not called"
    assert "save_to_file" in called_tools, "save_to_file was not called"
    print("\n   ✅ All 3 pipeline tools were called")

    assert called_tools.index("search") < called_tools.index("summarize"), \
        "search should come before summarize"
    assert called_tools.index("summarize") < called_tools.index("save_to_file"), \
        "summarize should come before save_to_file"
    print("   ✅ Correct sequential order verified")

    try:
        await orch.disconnect()
    except BaseException:
        pass
    from pathlib import Path
    out = Path(__file__).resolve().parents[1] / "output" / "asyncio_summary.txt"
    if out.exists():
        out.unlink()
        print("   🧹 Cleaned up output file")

    print("   ✅ Scenario 2 passed!\n")


# ── main ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("🧪 MCP Orchestration Tests")
    print("=" * 60 + "\n")

    asyncio.run(test_cross_server())
    asyncio.run(test_pipeline_order())

    print("=" * 60)
    print("✅ All orchestration tests passed!")


if __name__ == "__main__":
    main()
