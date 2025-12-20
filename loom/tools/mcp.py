"""
Loom MCP (Model Context Protocol) Integration

This module provides support for consuming tools from MCP servers.
It implements a lightweight JSON-RPC client over Stdio.

Usage:
    from loom.tools.mcp import load_mcp_tools

    tools = await load_mcp_tools(
        server_name="filesystem",
        command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "/path/to/allow"]
    )
    
    agent = loom.agent(..., tools=tools)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from asyncio.subprocess import Process
from typing import Any, Dict, List, Optional, Union, Callable

from pydantic import BaseModel, Field, create_model

from loom.interfaces.tool import BaseTool

logger = logging.getLogger(__name__)


# ============================================================================
# JSON-RPC Protocol
# ============================================================================


class JsonRpcMessage(BaseModel):
    jsonrpc: str = "2.0"


class JsonRpcRequest(JsonRpcMessage):
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Union[str, int, None] = None


class JsonRpcResponse(JsonRpcMessage):
    result: Any = None
    error: Optional[Dict[str, Any]] = None
    id: Union[str, int, None] = None


class JsonRpcNotification(JsonRpcMessage):
    method: str
    params: Optional[Dict[str, Any]] = None


# ============================================================================
# MCP Client (Stdio)
# ============================================================================


class MCPClient:
    """
    Lightweight MCP Client using Stdio transport
    """

    def __init__(self, command: List[str], cwd: Optional[str] = None, env: Optional[Dict] = None):
        self.command = command
        self.cwd = cwd
        self.env = env or os.environ.copy()
        
        self.process: Optional[Process] = None
        self._request_id = 0
        self._pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._connected = False

    async def connect(self):
        """Start the server and initialize connection"""
        if self._connected:
            return

        logger.info(f"Starting MCP server: {self.command}")
        
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=sys.stderr, # Forward stderr to host stderr
            cwd=self.cwd,
            env=self.env
        )

        # Start reader loop
        self._reader_task = asyncio.create_task(self._read_loop())

        # Initialize Protocol
        init_result = await self.request("initialize", {
            "protocolVersion": "2024-11-05",  # Use latest known draft version
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {},
            },
            "clientInfo": {
                "name": "loom-agent",
                "version": "0.2.0"
            }
        })
        
        logger.info(f"MCP Initialized: {init_result}")

        # Send initialized notification
        await self.notify("notifications/initialized")
        self._connected = True

    async def _read_loop(self):
        """Read stdout from server line by line"""
        assert self.process and self.process.stdout
        
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                
                line_str = line.decode().strip()
                if not line_str:
                    continue
                    
                try:
                    message = json.loads(line_str)
                    await self._handle_message(message)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from MCP server: {line_str}")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}")
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"MCP Reader error: {e}")

    async def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming JSON-RPC message"""
        # Response
        if "id" in message and ("result" in message or "error" in message):
            req_id = message["id"]
            if req_id in self._pending_requests:
                future = self._pending_requests.pop(req_id)
                if "error" in message and message["error"]:
                    future.set_exception(Exception(f"MCP Error: {message['error']}"))
                else:
                    future.set_result(message.get("result"))
        
        # Request (from server to client, e.g. sampling) - Not supported yet
        elif "method" in message and "id" in message:
            logger.warning(f"Received request from server (not supported): {message['method']}")
        
        # Notification
        elif "method" in message:
            logger.debug(f"Received notification: {message['method']}")

    async def request(self, method: str, params: Optional[Dict] = None) -> Any:
        """Send a JSON-RPC request"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP Client not connected")

        self._request_id += 1
        req_id = self._request_id
        
        # Create future
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending_requests[req_id] = future

        # Send request
        req = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": req_id
        }
        
        input_data = json.dumps(req) + "\n"
        self.process.stdin.write(input_data.encode())
        await self.process.stdin.drain()

        # Wait for response with timeout
        try:
            return await asyncio.wait_for(future, timeout=60.0)
        except asyncio.TimeoutError:
            if req_id in self._pending_requests:
                self._pending_requests.pop(req_id)
            raise

    async def notify(self, method: str, params: Optional[Dict] = None):
        """Send a JSON-RPC notification"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP Client not connected")

        req = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        input_data = json.dumps(req) + "\n"
        self.process.stdin.write(input_data.encode())
        await self.process.stdin.drain()

    async def list_tools(self) -> List[Dict]:
        """List available tools"""
        result = await self.request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: Dict) -> Any:
        """Call a tool"""
        result = await self.request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        
        # Extract content from result
        # MCP spec: result = { content: [{type: "text", text: "..."}], isError: bool }
        if result and "content" in result:
            content_list = result["content"]
            text_parts = []
            for item in content_list:
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif item.get("type") == "image":
                    text_parts.append(f"[Image: {item.get('resource', {}).get('uri', 'unknown')}]")
            
            output = "\n".join(text_parts)
            
            if result.get("isError"):
                raise Exception(f"Tool execution failed: {output}")
                
            return output
            
        return result

    async def close(self):
        """Close connection"""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception:
                pass


# ============================================================================
# Loom Tool Adapter
# ============================================================================

def _json_schema_to_pydantic(name: str, schema: Dict[str, Any]) -> type[BaseModel]:
    """
    Convert JSON Schema to Pydantic Model
    (Simplified version, mostly handling basic types)
    """
    fields = {}
    
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None)
    }

    for prop_name, prop_schema in properties.items():
        prop_type_str = prop_schema.get("type", "string")
        prop_type = type_map.get(prop_type_str, str)
        prop_desc = prop_schema.get("description", "")
        
        # Determine if optional
        if prop_name in required:
            fields[prop_name] = (prop_type, Field(description=prop_desc))
        else:
            fields[prop_name] = (Optional[prop_type], Field(default=None, description=prop_desc))
            
    return create_model(f"{name}Args", **fields)


class MCPTool(BaseTool):
    """
    Adapter to wrap an MCP tool as a Loom BaseTool
    """
    
    def __init__(
        self, 
        client: MCPClient, 
        tool_def: Dict[str, Any]
    ):
        self.client = client
        self.name = tool_def["name"]
        self.description = tool_def.get("description", "")
        
        # Parse schema
        self.input_schema = tool_def.get("inputSchema", {})
        self.args_schema = _json_schema_to_pydantic(self.name, self.input_schema)
        
        # Inherit standard attributes
        super().__init__()

    async def run(self, **kwargs) -> Any:
        # Call the tool via client
        return await self.client.call_tool(self.name, kwargs)


async def load_mcp_tools(
    command: List[str], 
    cwd: Optional[str] = None,
    server_name: str = "mcp-server"
) -> List[BaseTool]:
    """
    Connect to an MCP server and load all its tools
    
    Args:
        command: Command to run the server (e.g. ["npx", "-y", ...])
        cwd: Working directory
        server_name: Name for logging
        
    Returns:
        List of Loom Tools
    """
    # Create and connect client
    client = MCPClient(command, cwd)
    try:
        await client.connect()
    except Exception as e:
        logger.error(f"Failed to connect to MCP server {server_name}: {e}")
        await client.close()
        raise

    # Fetch tools
    try:
        mcp_tools_defs = await client.list_tools()
    except Exception as e:
        logger.error(f"Failed to list tools from {server_name}: {e}")
        await client.close()
        raise

    # Convert to Loom tools
    loom_tools = []
    for tool_def in mcp_tools_defs:
        try:
            tool = MCPTool(client, tool_def)
            loom_tools.append(tool)
        except Exception as e:
            logger.warning(f"Skipping invalid tool {tool_def.get('name')}: {e}")

    logger.info(f"Loaded {len(loom_tools)} tools from {server_name}")
    return loom_tools
