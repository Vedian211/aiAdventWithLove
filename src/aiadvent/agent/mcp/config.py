"""Configuration for MCP server connections."""

from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server connection."""
    
    command: str  # Command to start the server (e.g., "python", "node", "npx")
    args: List[str]  # Arguments for the command (e.g., ["server.py"] or ["-y", "@modelcontextprotocol/server-filesystem"])
    env: Optional[Dict[str, str]] = None  # Environment variables
    
    @classmethod
    def from_dict(cls, config: Dict) -> "MCPServerConfig":
        """Create config from dictionary."""
        return cls(
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env")
        )
