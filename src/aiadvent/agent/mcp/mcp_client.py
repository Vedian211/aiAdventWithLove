"""MCP (Model Context Protocol) client for connecting to MCP servers and retrieving tools."""

from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """Client for connecting to MCP servers via stdio transport."""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
        
    async def connect_stdio(self, command: str, args: List[str] = None, env: Dict[str, str] = None) -> None:
        """
        Connect to an MCP server using stdio transport.
        
        Args:
            command: Command to start the MCP server (e.g., "python", "node")
            args: Arguments for the command (e.g., ["server.py"])
            env: Environment variables for the server process
        """
        if args is None:
            args = []
            
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        
        self.exit_stack = AsyncExitStack()
        read_stream, write_stream = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.session = ClientSession(read_stream, write_stream)
        await self.exit_stack.enter_async_context(self.session)
        
        # Initialize the connection
        await self.session.initialize()
        
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Retrieve the list of available tools from the connected MCP server.
        
        Returns:
            List of tool definitions with name, description, and input schema
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect_stdio() first.")
            
        response = await self.session.list_tools()
        
        # Convert tools to dict format
        tools = []
        for tool in response.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            })
            
        return tools
    
    async def disconnect(self) -> None:
        """Close the connection to the MCP server."""
        if self.exit_stack:
            await self.exit_stack.aclose()
            self.session = None
            self.exit_stack = None
