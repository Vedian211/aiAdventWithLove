"""MCP Orchestrator: connects to multiple MCP servers, lets the model pick tools."""

import json
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from aiadvent.agent.mcp import MCPClient
from aiadvent.agent.mcp.config import MCPServerConfig


class Orchestrator:
    """Connects to N MCP servers, exposes all tools to OpenAI, runs tool-call loop."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini",
                 system_prompt: str = "You are a helpful assistant with access to tools."):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt

        self.mcp_clients: Dict[str, MCPClient] = {}
        # tool_name -> server_name for direct routing
        self.tool_map: Dict[str, str] = {}
        # OpenAI function-calling format
        self.openai_tools: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    async def connect(self, configs: List[MCPServerConfig]) -> None:
        """Connect to all MCP servers and build the tool map."""
        for cfg in configs:
            server_name = cfg.args[1] if len(cfg.args) > 1 else cfg.args[0] if cfg.args else cfg.command
            client = MCPClient()
            await client.connect_stdio(command=cfg.command, args=cfg.args, env=cfg.env)
            self.mcp_clients[server_name] = client

            for tool in await client.list_tools():
                self.tool_map[tool["name"]] = server_name
                self.openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["inputSchema"],
                    },
                })

    async def disconnect(self) -> None:
        for c in self.mcp_clients.values():
            try:
                await c.disconnect()
            except BaseException:
                pass

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------
    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        server = self.tool_map.get(name)
        if not server:
            return json.dumps({"error": f"Unknown tool: {name}"})
        result = await self.mcp_clients[server].call_tool(name, arguments)
        return result if isinstance(result, str) else json.dumps(result)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    async def run(self, user_message: str, on_step=None) -> str:
        """
        Send user_message, loop until the model stops calling tools.

        on_step(event, data) — optional callback for logging:
            event="tool_call"  data={"name", "arguments"}
            event="tool_result" data={"name", "result"}
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        while True:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.openai_tools if self.openai_tools else None,
            )
            choice = resp.choices[0]

            if choice.finish_reason == "stop":
                return choice.message.content

            # Model wants to call tool(s)
            messages.append(choice.message)

            for tc in choice.message.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)

                if on_step:
                    on_step("tool_call", {"name": name, "arguments": args})

                result = await self._call_tool(name, args)

                if on_step:
                    on_step("tool_result", {"name": name, "result": result})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
