"""
Example: Using Figma MCP Tool

This demonstrates how to:
1. Connect to Figma MCP server
2. List available tools
3. Call a tool (get file info)
4. Use the result
"""

import os
import asyncio
import json
from dotenv import load_dotenv
from aiadvent.agent.agent import Agent
from aiadvent.agent.mcp.config import MCPServerConfig


async def main():
    print("🎨 Figma MCP Tool Example")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    figma_token = os.getenv("FIGMA_PERSONAL_ACCESS_TOKEN_AI_LEARNING")
    figma_file_key = os.getenv("FIGMA_FILE_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    # Validate
    if not figma_token:
        print("❌ FIGMA_PERSONAL_ACCESS_TOKEN_AI_LEARNING not set in .env")
        return
    if not figma_file_key:
        print("❌ FIGMA_FILE_KEY not set in .env")
        return
    if not openai_key:
        print("❌ OPENAI_API_KEY not set in .env")
        return
    
    print(f"✅ Configuration loaded")
    print(f"   File Key: {figma_file_key}")
    print()
    
    # Step 1: Configure Figma MCP server
    print("1️⃣  Configuring Figma MCP server...")
    mcp_config = MCPServerConfig(
        command="npx",
        args=["-y", "figma-mcp"],
        env={"FIGMA_API_KEY": figma_token}
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
    print("4️⃣  Listing available Figma tools...")
    tools = agent.get_mcp_tools()
    print(f"✅ Found {len(tools)} tool(s):")
    for i, tool in enumerate(tools, 1):
        print(f"   {i}. {tool['name']}")
        print(f"      {tool['description'][:80]}...")
    print()
    
    # Step 5: Call a tool - Add Figma file to context
    print("5️⃣  Calling tool: add_figma_file...")
    figma_url = os.getenv("FIGMA_FILE_URL")
    print(f"   Arguments: url={figma_url}")
    
    try:
        result = await agent.call_mcp_tool(
            "add_figma_file",
            {"url": figma_url}
        )
        print("✅ Tool executed successfully!")
        print()
        
        # Step 6: Parse and display result
        print("6️⃣  Result:")
        print("-" * 60)
        
        # Result is JSON string, parse it
        if isinstance(result, str):
            result_data = json.loads(result)
        else:
            result_data = result
        
        # Display complete result
        print(json.dumps(result_data, indent=2))
        print("-" * 60)
        print()
        
        # Step 7: Use the result
        print("7️⃣  Using the result...")
        if isinstance(result_data, dict) and 'name' in result_data:
            file_name = result_data['name']
            print(f"✅ Successfully retrieved info for: '{file_name}'")
            print(f"   You can now use this data in your application!")
        
    except Exception as e:
        print(f"❌ Error calling tool: {e}")
    
    print()
    
    # Step 8: Cleanup
    print("8️⃣  Cleaning up...")
    if agent.mcp_client:
        await agent.mcp_client.disconnect()
    print("✅ Disconnected from MCP server")
    print()
    
    print("=" * 60)
    print("✅ Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
