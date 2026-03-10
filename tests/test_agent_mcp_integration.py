"""
Integration test: Agent with MCP connection.

This demonstrates how to initialize the Agent with MCP support.
"""

import os
import asyncio
from aiadvent.agent.agent import Agent
from aiadvent.agent.mcp.config import MCPServerConfig


async def test_agent_with_mcp():
    """Test Agent initialization with MCP server."""
    
    print("🤖 Testing Agent with MCP Integration")
    print("=" * 50)
    
    # Configure MCP server (using filesystem server as example)
    mcp_config = MCPServerConfig(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    )
    
    print("\n1️⃣  Creating Agent with MCP configuration...")
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return False
    
    # Create agent with MCP config (but don't connect yet)
    agent = Agent(
        api_key=api_key,
        model="gpt-4o-mini",
        system_prompt="You are a helpful assistant.",
        mcp_server_config=mcp_config
    )
    
    print("✅ Agent created successfully!")
    
    # Initialize MCP connection
    print("\n2️⃣  Initializing MCP connection...")
    await agent.init_mcp()
    print("✅ MCP connection initialized!")
    
    # Check MCP tools
    print("\n3️⃣  Checking MCP tools...")
    tools = agent.get_mcp_tools()
    print(f"✅ Agent has access to {len(tools)} MCP tool(s)")
    
    if tools:
        print("\n📋 Available MCP Tools:")
        for i, tool in enumerate(tools, 1):
            print(f"\n{i}. {tool['name']}")
            print(f"   Description: {tool['description']}")
            print(f"   Input Schema: {tool['inputSchema']}")
    
    # Cleanup
    print("\n4️⃣  Cleaning up...")
    if agent.mcp_client:
        await agent.mcp_client.disconnect()
    print("✅ Cleanup complete!")
    
    print("\n" + "=" * 50)
    print("✅ Integration test passed!")
    return True


def main():
    success = asyncio.run(test_agent_with_mcp())
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
