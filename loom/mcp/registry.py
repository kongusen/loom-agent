from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .client import MCPClient, MCPServerConfig
from .tool_adapter import MCPTool


class MCPToolRegistry:
    """MCP 工具注册中心 - 负责发现/连接 server 并加载工具。"""

    def __init__(self, config_path: Optional[str] = None) -> None:
        self.config_path = Path(config_path) if config_path else Path.home() / ".loom" / "mcp.json"
        self.servers: Dict[str, MCPClient] = {}
        self.tools: Dict[str, MCPTool] = {}

    async def discover_local_servers(self) -> None:
        if not self.config_path.exists():
            return
        config = json.loads(self.config_path.read_text())
        for name, scfg in config.get("mcpServers", {}).items():
            await self.add_server(name, scfg)

    async def add_server(self, name: str, cfg: Dict) -> None:
        client = MCPClient(
            MCPServerConfig(command=cfg["command"], args=cfg.get("args", []), env=cfg.get("env"))
        )
        await client.connect()
        self.servers[name] = client
        await self._load_server_tools(name, client)

    async def _load_server_tools(self, server_name: str, client: MCPClient) -> None:
        for spec in await client.list_tools():
            tool = MCPTool(mcp_tool_spec=spec, mcp_client=client)
            self.tools[f"{server_name}:{tool.name}"] = tool

    async def load_from_server(self, server_name: str) -> List[MCPTool]:
        return [tool for key, tool in self.tools.items() if key.startswith(f"{server_name}:")]

    async def load_servers(self, server_names: List[str]) -> List[MCPTool]:
        tools: List[MCPTool] = []
        for s in server_names:
            tools.extend(await self.load_from_server(s))
        return tools

    async def list_all_tools(self) -> Dict[str, List[str]]:
        grouped: Dict[str, List[str]] = {}
        for key in self.tools.keys():
            server, tname = key.split(":", 1)
            grouped.setdefault(server, []).append(tname)
        return grouped

    async def close(self) -> None:
        for client in self.servers.values():
            await client.disconnect()

