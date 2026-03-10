"""
Test script for MCP connection functionality.

This script tests:
1. Establishing an MCP connection
2. Retrieving the list of available tools from MCP server

Usage:
    python tests/test_mcp_connection.py <command> [args...]
    
Examples:
    # Test with a Python MCP server
    python tests/test_mcp_connection.py python examples/simple_mcp_server.py
    
    # Test with npx MCP server
    python tests/test_mcp_connection.py npx -y @modelcontextprotocol/server-filesystem /tmp
"""

import asyncio
import sys
from aiadvent.agent.mcp import MCPClient


async def test_mcp_connection(command: str, args: list):
    """Test MCP connection and tool retrieval."""
    
    print(f"🔌 Testing MCP Connection")
    print(f"Command: {command}")
    print(f"Args: {args}")
    print("-" * 50)
    
    client = MCPClient()
    
    try:
        # Step 1: Establish connection
        print("\n1️⃣  Establishing connection...")
        await client.connect_stdio(command=command, args=args)
        print("✅ Connection established successfully!")
        
        # Step 2: Retrieve tools list
        print("\n2️⃣  Retrieving tools list...")
        tools = await client.list_tools()
        print(f"✅ Retrieved {len(tools)} tool(s)")
        
        # Display tools
        if tools:
            print("\n📋 Available Tools:")
            print("-" * 50)
            for i, tool in enumerate(tools, 1):
                print(f"\n{i}. {tool['name']}")
                print(f"   Description: {tool['description']}")
                print(f"   Input Schema: {tool['inputSchema']}")
        else:
            print("\n⚠️  No tools available from this server")
        
        # Step 3: Disconnect
        print("\n3️⃣  Disconnecting...")
        await client.disconnect()
        print("✅ Disconnected successfully!")
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Try to disconnect on error
        try:
            await client.disconnect()
        except:
            pass
            
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/test_mcp_connection.py <command> [args...]")
        print("\nExamples:")
        print("  python tests/test_mcp_connection.py python examples/simple_mcp_server.py")
        print("  python tests/test_mcp_connection.py npx -y @modelcontextprotocol/server-filesystem /tmp")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    success = asyncio.run(test_mcp_connection(command, args))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
