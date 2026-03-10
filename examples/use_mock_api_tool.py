"""
Example: Using Mock API MCP Server

This demonstrates how to:
1. Connect to our custom Mock API MCP server
2. List available tools
3. Call tools (get users, create task, etc.)
4. Use the results
"""

import os
import asyncio
import json
from dotenv import load_dotenv
from aiadvent.agent.agent import Agent
from aiadvent.agent.mcp.config import MCPServerConfig


async def main():
    print("🔧 Mock API MCP Server Example")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_key:
        print("❌ OPENAI_API_KEY not set in .env")
        return
    
    print("✅ Configuration loaded")
    print()
    
    # Step 1: Configure Mock API MCP server
    print("1️⃣  Configuring Mock API MCP server...")
    mcp_config = MCPServerConfig(
        command="python",
        args=["-m", "aiadvent.mcp_server.server"]
    )
    print("✅ MCP server configured")
    print()
    
    # Step 2: Create agent
    print("2️⃣  Creating agent...")
    agent = Agent(
        api_key=openai_key,
        model="gpt-4o-mini",
        system_prompt="You are a helpful assistant.",
        mcp_server_config=mcp_config
    )
    print("✅ Agent created")
    print()
    
    # Step 3: Initialize MCP connection
    print("3️⃣  Initializing MCP connection...")
    await agent.init_mcp()
    print("✅ MCP connection initialized")
    print()
    
    # Step 4: List available tools
    print("4️⃣  Listing available tools...")
    tools = agent.get_mcp_tools()
    print(f"✅ Found {len(tools)} tool(s):")
    for i, tool in enumerate(tools, 1):
        print(f"   {i}. {tool['name']}")
        print(f"      {tool['description']}")
    print()
    
    # Step 5: Call tools
    print("5️⃣  Testing tools...")
    print()
    
    # Test 1: Get all users
    print("   📋 Test 1: get_users")
    try:
        result = await agent.call_mcp_tool("get_users", {})
        data = json.loads(result)
        print(f"   ✅ Found {len(data)} users:")
        for user in data:
            print(f"      - {user['name']} ({user['role']})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 2: Get specific user
    print("   👤 Test 2: get_user")
    try:
        result = await agent.call_mcp_tool("get_user", {"user_id": 1})
        data = json.loads(result)
        print(f"   ✅ User details:")
        print(f"      Name: {data['name']}")
        print(f"      Email: {data['email']}")
        print(f"      Role: {data['role']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 3: List tasks
    print("   📝 Test 3: list_tasks")
    try:
        result = await agent.call_mcp_tool("list_tasks", {})
        data = json.loads(result)
        print(f"   ✅ Found {len(data)} tasks:")
        for task in data:
            print(f"      - {task['title']} (assigned to {task['assignee']}, status: {task['status']})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 4: Create new task
    print("   ➕ Test 4: create_task")
    try:
        result = await agent.call_mcp_tool(
            "create_task",
            {"title": "Write documentation", "assignee": "Alice Johnson"}
        )
        data = json.loads(result)
        print(f"   ✅ Task created:")
        print(f"      ID: {data['id']}")
        print(f"      Title: {data['title']}")
        print(f"      Assignee: {data['assignee']}")
        print(f"      Status: {data['status']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Step 6: Cleanup
    print("6️⃣  Cleaning up...")
    if agent.mcp_client:
        await agent.mcp_client.disconnect()
    print("✅ Disconnected from MCP server")
    print()
    
    print("=" * 60)
    print("✅ Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
