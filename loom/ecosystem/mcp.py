"""MCP (Model Context Protocol) integration - 参考 Claude Code MCP

MCP 特性：
1. 支持 stdio/sse/http/ws 多种传输协议
2. 环境变量替换（${VAR}, ${CLAUDE_PLUGIN_ROOT}）
3. 支持 MCPB (MCP Bundle) 格式
4. 支持 user config 配置
5. 作用域隔离（plugin:name:server）
"""

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MCPTransportType(Enum):
    """MCP transport types"""
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    WS = "ws"


@dataclass
class MCPServerConfig:
    """MCP server configuration"""
    type: MCPTransportType = MCPTransportType.STDIO

    # stdio config
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None

    # remote config (sse/http/ws)
    url: str | None = None
    headers: dict[str, str] | None = None

    # metadata
    disabled: bool = False
    auto_approve: list[str] | None = None
    instructions: str = ""

    # mock / local integration hooks for the current implementation stage
    mock_tools: list[dict[str, Any]] = field(default_factory=list)
    mock_resources: list[dict[str, Any]] = field(default_factory=list)
    mock_tool_results: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPServer:
    """MCP server instance"""
    name: str
    config: MCPServerConfig
    scope: str = "user"  # user | plugin | dynamic
    plugin_source: str | None = None

    # Runtime state
    connected: bool = False
    tools: list[dict] | None = None
    resources: list[dict] | None = None

    def __post_init__(self):
        if self.tools is None:
            self.tools = []
        if self.resources is None:
            self.resources = []


class MCPBridge:
    """Bridge to MCP servers"""

    def __init__(self):
        self.servers: dict[str, MCPServer] = {}
        self._instructions_cache: dict[str, str] = {}

    def register_server(self, name: str, config: MCPServerConfig,
                       scope: str = "user", plugin_source: str | None = None):
        """Register MCP server"""
        server = MCPServer(
            name=name,
            config=config,
            scope=scope,
            plugin_source=plugin_source,
        )
        self.servers[name] = server
        if config.instructions:
            self._instructions_cache[name] = config.instructions

    def resolve_env_vars(self, value: str, plugin_path: str | None = None) -> str:
        """Resolve environment variables in config"""
        import os
        import re

        # Replace ${CLAUDE_PLUGIN_ROOT}
        if plugin_path:
            value = value.replace('${CLAUDE_PLUGIN_ROOT}', plugin_path)

        # Replace ${VAR}
        def replace_var(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))

        return re.sub(r'\$\{([^}]+)\}', replace_var, value)

    def connect(self, server_name: str) -> bool:
        """Connect to MCP server (stdio subprocess or mock fallback)"""
        server = self.servers.get(server_name)
        if not server or server.config.disabled:
            return False

        if server.config.type == MCPTransportType.STDIO and server.config.command:
            try:
                self._connect_stdio(server)
            except Exception:
                # fallback to mock
                server.tools = [dict(t) for t in server.config.mock_tools]
                server.resources = [dict(r) for r in server.config.mock_resources]
        else:
            server.tools = [dict(t) for t in server.config.mock_tools]
            server.resources = [dict(r) for r in server.config.mock_resources]

        server.connected = True
        if server.config.instructions:
            self._instructions_cache[server_name] = server.config.instructions
        return True

    _RPC_TIMEOUT = 10.0  # seconds for stdio readline

    def _connect_stdio(self, server: "MCPServer") -> None:
        """Launch stdio MCP subprocess and fetch tools/resources via JSON-RPC."""
        import json
        import os
        import subprocess

        if not server.config.command:
            raise ValueError(f"MCP server {server.name} has no command configured")

        cmd = [server.config.command] + (server.config.args or [])
        env = {**os.environ, **(server.config.env or {})}
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=env,
        )

        def rpc(method: str, params: dict | None = None) -> dict:
            if proc.poll() is not None:
                raise RuntimeError("MCP subprocess has exited")
            msg = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
            # Type guard: ensure stdin is not None
            if proc.stdin is None:
                raise RuntimeError("MCP subprocess stdin is None")
            proc.stdin.write((json.dumps(msg) + "\n").encode())
            proc.stdin.flush()
            # readline with timeout via select
            import select
            # Type guard: ensure stdout is not None
            if proc.stdout is None:
                raise RuntimeError("MCP subprocess stdout is None")
            ready, _, _ = select.select([proc.stdout], [], [], self._RPC_TIMEOUT)
            if not ready:
                proc.kill()
                raise TimeoutError(f"MCP server timed out on {method}")
            raw = proc.stdout.readline()
            result = json.loads(raw)
            # Type guard: ensure result is dict
            if isinstance(result, dict):
                result_data = result.get("result", {})
                if isinstance(result_data, dict):
                    return result_data
            return {}

        server.tools = rpc("tools/list").get("tools", [])
        server.resources = rpc("resources/list").get("resources", [])

        if not hasattr(self, "_stdio_procs"):
            self._stdio_procs: dict[str, Any] = {}
        self._stdio_procs[server.name] = proc

    def list_tools(self, server_name: str) -> list[dict]:
        """List tools from MCP server"""
        server = self.servers.get(server_name)
        if not server or not server.connected:
            return []
        # Type guard: ensure tools is not None
        if server.tools is None:
            return []
        return [dict(tool) for tool in server.tools]

    def list_resources(self, server_name: str) -> list[dict]:
        """List resources from MCP server."""
        server = self.servers.get(server_name)
        if not server or not server.connected:
            return []
        # Type guard: ensure resources is not None
        if server.resources is None:
            return []
        return [dict(resource) for resource in server.resources]

    def read_resource(self, server_name: str, uri: str) -> dict[str, Any] | None:
        """Read one resource from MCP server."""
        server = self.servers.get(server_name)
        if not server or not server.connected:
            raise RuntimeError(f"Server {server_name} not connected")

        # Type guard: ensure resources is not None
        if server.resources is None:
            return None
        for resource in server.resources:
            if resource.get("uri") == uri:
                return dict(resource)
        return None

    def execute_tool(self, server_name: str, tool_name: str, **kwargs) -> Any:
        """Execute MCP tool via stdio subprocess or mock fallback"""
        server = self.servers.get(server_name)
        if not server or not server.connected:
            raise RuntimeError(f"Server {server_name} not connected")

        # Try real stdio execution
        procs = getattr(self, "_stdio_procs", {})
        if server_name in procs:
            import json
            import select
            proc = procs[server_name]
            # Reconnect if process has died
            if proc.poll() is not None:
                try:
                    self._connect_stdio(server)
                    proc = self._stdio_procs[server_name]
                except Exception:
                    del self._stdio_procs[server_name]
                    proc = None
            if proc is not None:
                msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool_name, "arguments": kwargs}}
                proc.stdin.write((json.dumps(msg) + "\n").encode())
                proc.stdin.flush()
                ready, _, _ = select.select([proc.stdout], [], [], self._RPC_TIMEOUT)
                if not ready:
                    proc.kill()
                    del self._stdio_procs[server_name]
                    raise TimeoutError(f"Tool call '{tool_name}' timed out")
                raw = proc.stdout.readline()
                result = json.loads(raw).get("result", {})
                content = result.get("content", [])
                if content and isinstance(content, list):
                    return content[0].get("text", result)
                return result

        # Mock fallback
        if tool_name in server.config.mock_tool_results:
            configured = server.config.mock_tool_results[tool_name]
            if callable(configured):
                return configured(**kwargs)
            return configured

        # Type guard: ensure tools is not None
        if server.tools is None:
            raise RuntimeError(f"Server {server_name} has no tools")
        for tool in server.tools:
            if tool.get("name") == tool_name:
                return {"tool": tool_name, "arguments": kwargs, "server": server_name}

        raise KeyError(f"Tool {tool_name} not found on server {server_name}")

    def get_instructions(self, server_name: str) -> str:
        """Get instructions for system prompt injection"""
        return self._instructions_cache.get(server_name, "")

    def set_instructions(self, server_name: str, instructions: str):
        """Set instructions for server"""
        self._instructions_cache[server_name] = instructions


_DEFAULT_BRIDGE: MCPBridge | None = None
_DEFAULT_BRIDGE_LOCK = threading.Lock()


def get_default_mcp_bridge() -> MCPBridge:
    """Return a process-local default MCP bridge (thread-safe)."""
    global _DEFAULT_BRIDGE
    if _DEFAULT_BRIDGE is None:
        with _DEFAULT_BRIDGE_LOCK:
            if _DEFAULT_BRIDGE is None:
                _DEFAULT_BRIDGE = MCPBridge()
    return _DEFAULT_BRIDGE
