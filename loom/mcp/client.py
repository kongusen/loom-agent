from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MCPServerConfig:
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None


class MCPError(Exception):
    pass


class MCPClient:
    """最小 MCP 客户端：JSON-RPC over stdio。"""

    def __init__(self, server_config: MCPServerConfig) -> None:
        self.config = server_config
        self.process: Optional[asyncio.subprocess.Process] = None
        self.request_id = 0
        self._response_futures: Dict[int, asyncio.Future] = {}

    async def connect(self) -> None:
        self.process = await asyncio.create_subprocess_exec(
            self.config.command,
            *self.config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.config.env,
        )
        asyncio.create_task(self._read_responses())
        await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "loom-framework", "version": "0.1.0"},
            },
        )

    async def disconnect(self) -> None:
        if self.process:
            self.process.terminate()
            await self.process.wait()

    async def list_tools(self) -> List[Dict]:
        result = await self._send_request("tools/list", {})
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: Dict) -> Dict:
        return await self._send_request("tools/call", {"name": name, "arguments": arguments})

    async def _send_request(self, method: str, params: Dict) -> Dict:
        assert self.process and self.process.stdin and self.process.stdout
        self.request_id += 1
        req = {"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params}
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._response_futures[self.request_id] = fut
        self.process.stdin.write((json.dumps(req) + "\n").encode())
        await self.process.stdin.drain()
        return await fut

    async def _read_responses(self) -> None:
        assert self.process and self.process.stdout
        while True:
            line = await self.process.stdout.readline()
            if not line:
                break
            resp = json.loads(line.decode())
            if "id" in resp:
                rid = resp["id"]
                fut = self._response_futures.pop(rid, None)
                if fut is None:
                    continue
                if "error" in resp:
                    fut.set_exception(MCPError(str(resp["error"])))
                else:
                    fut.set_result(resp.get("result", {}))

