# MCP Integration

Loom connects to external tool servers via the [Model Context Protocol](https://modelcontextprotocol.io) over stdio JSON-RPC.

## Connecting a Server

```python
from loom.ecosystem.mcp import get_default_mcp_bridge

bridge = get_default_mcp_bridge()  # thread-safe singleton
bridge.register_server("filesystem", {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
})
bridge.connect("filesystem")
```

## Calling Tools

```python
result = bridge.execute_tool("filesystem", "read_file", path="/tmp/notes.txt")
resources = bridge.list_resources("filesystem")
```

## Reliability Features

- **Timeout**: 10s per RPC call via `select`-based I/O
- **Reconnect**: auto-reconnects if subprocess dies
- **Thread-safe singleton**: `get_default_mcp_bridge()` uses double-checked locking

**Code:** `loom/ecosystem/mcp.py`
