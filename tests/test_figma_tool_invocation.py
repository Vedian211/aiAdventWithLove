"""
Test: Figma Tool Invocation

Tests the complete flow:
1. Tool registration (list tools)
2. Tool invocation (call tool)
3. Result handling (parse and use result)
"""

import os
import asyncio
import json
from dotenv import load_dotenv
from aiadvent.agent.agent import Agent
from aiadvent.agent.mcp.config import MCPServerConfig


async def test_figma_tool_invocation():
    """Test complete Figma tool invocation flow."""
    
    print("🧪 Testing Figma Tool Invocation")
    print("=" * 60)
    
    # Load configuration
    load_dotenv()
    figma_token = os.getenv("FIGMA_PERSONAL_ACCESS_TOKEN_AI_LEARNING")
    figma_url = os.getenv("FIGMA_FILE_URL")
    figma_file_key = os.getenv("FIGMA_FILE_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not all([figma_token, figma_url, openai_key]):
        print("❌ Missing configuration in .env")
        return False
    
    try:
        # Test 1: Initialize agent with MCP
        print("\n✅ Test 1: Initialize Agent with MCP")
        mcp_config = MCPServerConfig(
            command="npx",
            args=["-y", "figma-mcp"],
            env={"FIGMA_API_KEY": figma_token}
        )
        
        agent = Agent(
            api_key=openai_key,
            mcp_server_config=mcp_config
        )
        await agent.init_mcp()
        print("   ✓ Agent initialized with MCP connection")
        
        # Test 2: Tool Registration
        print("\n✅ Test 2: Tool Registration")
        tools = agent.get_mcp_tools()
        assert len(tools) > 0, "No tools found"
        print(f"   ✓ Found {len(tools)} tool(s)")
        
        # Verify tool structure
        for tool in tools:
            assert "name" in tool, "Tool missing 'name'"
            assert "description" in tool, "Tool missing 'description'"
            assert "inputSchema" in tool, "Tool missing 'inputSchema'"
        print("   ✓ All tools have correct structure")
        
        # Print all tools
        print("\n   📋 All Available Tools:")
        for i, tool in enumerate(tools, 1):
            print(f"\n   {i}. {tool['name']}")
            print(f"      Description: {tool['description']}")
            print(f"      Input Schema: {json.dumps(tool['inputSchema'], indent=6)}")
        
        # Test 3: Input Parameters Description
        print("\n✅ Test 3: Input Parameters Description")
        add_file_tool = next((t for t in tools if t["name"] == "add_figma_file"), None)
        assert add_file_tool is not None, "add_figma_file tool not found"
        
        schema = add_file_tool["inputSchema"]
        assert "properties" in schema, "Input schema missing properties"
        assert "url" in schema["properties"], "Input schema missing 'url' parameter"
        print("   ✓ Tool has correct input parameter description")
        print(f"   ✓ Parameters: {list(schema['properties'].keys())}")
        
        # Test 4: Tool Invocation
        print("\n✅ Test 4: Tool Invocation")
        # print("   ⏳ Waiting 60 seconds to avoid rate limit...")
        # await asyncio.sleep(60)
        
        try:
            result = await agent.call_mcp_tool(
                "add_figma_file",
                {"url": figma_url}
            )
            assert result is not None, "Tool returned no result"
            print("   ✓ Tool executed successfully")
        except RuntimeError as e:
            if "429" in str(e):
                print("   ⚠️  Rate limit hit (429). Figma API limits exceeded.")
                print("   ℹ️  This is expected when running tests frequently.")
                print("   ℹ️  Wait 5-10 minutes before running again.")
            else:
                raise
        
        # Test 5: Result Handling
        print("\n✅ Test 5: Result Handling")
        if isinstance(result, str):
            result_data = json.loads(result)
        else:
            result_data = result
        
        assert isinstance(result_data, dict), "Result is not a dictionary"
        assert "name" in result_data, "Result missing 'name' field"
        print(f"   ✓ Result parsed successfully")
        print(f"\n   📋 Complete Result Data:")
        print(json.dumps(result_data, indent=4))
        
        # Test 6: Use Result
        print("\n✅ Test 6: Use Result")
        file_name = result_data["name"]
        assert len(file_name) > 0, "File name is empty"
        print(f"   ✓ Successfully extracted file name: '{file_name}'")
        print(f"   ✓ Result can be used in application")
        
        # Cleanup
        await agent.mcp_client.disconnect()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    success = asyncio.run(test_figma_tool_invocation())
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
