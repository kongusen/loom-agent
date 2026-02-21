"""MCP stdio client — connects to MCP servers via JSON-RPC over stdin/stdout."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..types import ToolDefinition, ToolContext
from .schema import DictSchema


@dataclass
class McpServerConfig:
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None


@dataclass
class McpToolInfo:
    name: str
    description: str = ""
    input_schema: dict[str, Any] | None = None


class McpClient:
    def __init__(self, config: McpServerConfig) -> None:
        self.config = config
        self._proc: asyncio.subprocess.Process | None = None
        self._pending: dict[str, asyncio.Future] = {}
        self._buffer = ""
        self._reader_task: asyncio.Task | None = None

    async def connect(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            self.config.command, *self.config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.config.env,
        )
        self._reader_task = asyncio.create_task(self._read_loop())
        await self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "loom", "version": "0.5.7"},
        })
        await self._notify("notifications/initialized")

    async def list_tools(self) -> list[McpToolInfo]:
        res = await self._rpc("tools/list", {})
        return [McpToolInfo(
            name=t["name"],
            description=t.get("description", ""),
            input_schema=t.get("inputSchema"),
        ) for t in res.get("tools", [])]

    async def call_tool(self, name: str, args: dict[str, Any]) -> str:
        res = await self._rpc("tools/call", {"name": name, "arguments": args})
        if res.get("isError"):
            raise RuntimeError(res.get("content", [{}])[0].get("text", "MCP tool error"))
        return "".join(c.get("text", "") for c in res.get("content", []))

    async def disconnect(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
        if self._proc:
            self._proc.kill()
            await self._proc.wait()
        self._proc = None

    async def _rpc(self, method: str, params: Any) -> Any:
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("MCP client not connected")
        rid = uuid.uuid4().hex[:12]
        msg = json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}) + "\n"
        self._proc.stdin.write(msg.encode())
        await self._proc.stdin.drain()

        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[rid] = fut
        try:
            return await asyncio.wait_for(fut, timeout=30.0)
        except asyncio.TimeoutError:
            self._pending.pop(rid, None)
            raise

    async def _notify(self, method: str) -> None:
        if not self._proc or not self._proc.stdin:
            return
        msg = json.dumps({"jsonrpc": "2.0", "method": method}) + "\n"
        self._proc.stdin.write(msg.encode())
        await self._proc.stdin.drain()

    async def _read_loop(self) -> None:
        assert self._proc and self._proc.stdout
        while True:
            line = await self._proc.stdout.readline()
            if not line:
                break
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            rid = msg.get("id")
            if rid and rid in self._pending:
                fut = self._pending.pop(rid)
                if msg.get("error"):
                    fut.set_exception(RuntimeError(msg["error"].get("message", "RPC error")))
                else:
                    fut.set_result(msg.get("result", {}))


def mcp_tools_to_definitions(client: McpClient, tools: list[McpToolInfo]) -> list[ToolDefinition]:
    defs = []
    for t in tools:
        schema = DictSchema(t.input_schema or {"type": "object", "properties": {}})
        async def _exec(inp: Any, ctx: ToolContext, _c=client, _n=t.name) -> str:
            return await _c.call_tool(_n, inp if isinstance(inp, dict) else {})
        defs.append(ToolDefinition(name=t.name, description=t.description, parameters=schema, execute=_exec))
    return defs
