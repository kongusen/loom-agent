"""MCP 工具"""

from typing import Any

from ...ecosystem.mcp import get_default_mcp_bridge


async def mcp_list_resources(server: str | None = None) -> dict[str, Any]:
    """列出 MCP 资源"""
    bridge = get_default_mcp_bridge()
    if server is None:
        resources = {
            name: bridge.list_resources(name)
            for name in bridge.servers
            if bridge.servers[name].connected
        }
        return {
            "server": None,
            "resources": resources,
            "message": "ok",
        }

    return {
        "server": server,
        "resources": bridge.list_resources(server),
        "message": "ok",
    }


async def mcp_read_resource(server: str, uri: str) -> dict[str, Any]:
    """读取 MCP 资源"""
    bridge = get_default_mcp_bridge()
    try:
        resource = bridge.read_resource(server, uri)
    except RuntimeError:
        resource = None
    return {
        "server": server,
        "uri": uri,
        "content": None if resource is None else resource.get("content"),
        "resource": resource,
        "message": "ok" if resource is not None else "not_connected",
    }


async def mcp_call_tool(server: str, tool_name: str, arguments: dict) -> dict[str, Any]:
    """调用 MCP 工具"""
    bridge = get_default_mcp_bridge()
    try:
        result = bridge.execute_tool(server, tool_name, **arguments)
        message = "ok"
    except (RuntimeError, KeyError) as e:
        result = None
        message = str(e)
    return {
        "server": server,
        "tool": tool_name,
        "result": result,
        "message": message,
    }
