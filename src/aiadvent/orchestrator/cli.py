"""CLI for MCP Orchestrator — multi-server tool routing demo."""

import os
import sys
import asyncio
from aiadvent.agent.mcp.config import MCPServerConfig
from aiadvent.orchestrator.orchestrator import Orchestrator


def _make_configs():
    """Build configs for mock-api + scheduler servers."""
    return [
        MCPServerConfig(
            command="python",
            args=["-m", "aiadvent.mcp_server.server"],
        ),
        MCPServerConfig(
            command="python",
            args=["-m", "aiadvent.mcp_server.scheduler_server"],
        ),
    ]


def _step_printer(event, data):
    if event == "tool_call":
        print(f"  🔧 Calling: {data['name']}({data['arguments']})")
    elif event == "tool_result":
        preview = data["result"][:200] + ("..." if len(data["result"]) > 200 else "")
        print(f"  ✅ Result:  {preview}")


async def run(query: str):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        sys.exit(1)

    orch = Orchestrator(api_key=api_key)
    configs = _make_configs()

    print("🔗 Connecting to MCP servers...")
    await orch.connect(configs)
    tools = [t["function"]["name"] for t in orch.openai_tools]
    print(f"   Tools: {tools}")
    print()
    print(f"📝 Query: {query}")
    print("-" * 60)

    answer = await orch.run(query, on_step=_step_printer)

    print("-" * 60)
    print(f"💬 Answer:\n{answer}")

    await orch.disconnect()


def main():
    if len(sys.argv) < 2:
        print('Usage: orchestrator "your request here"')
        sys.exit(1)
    query = " ".join(sys.argv[1:])
    asyncio.run(run(query))


if __name__ == "__main__":
    main()
