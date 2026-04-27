"""Minimal line-delimited JSON-RPC MCP server used by stdio integration tests."""

from __future__ import annotations

import json
import sys
from typing import Any

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_docs",
        "description": "Search local docs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
        "annotations": {
            "readOnlyHint": True,
            "concurrencySafeHint": True,
        },
    }
]

RESOURCES: list[dict[str, Any]] = [
    {
        "uri": "loom://docs/runtime",
        "name": "Runtime docs",
        "mimeType": "text/plain",
        "text": "Runtime capabilities are exposed through explicit MCP servers.",
    }
]


def _result(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id: Any, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": -32601, "message": message},
    }


def handle(message: dict[str, Any]) -> dict[str, Any]:
    method = str(message.get("method", ""))
    message_id = message.get("id")
    params = message.get("params") if isinstance(message.get("params"), dict) else {}

    if method == "tools/list":
        return _result(message_id, {"tools": TOOLS})
    if method == "resources/list":
        return _result(message_id, {"resources": RESOURCES})
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        if tool_name != "search_docs":
            return _error(message_id, f"Unknown tool: {tool_name}")
        query = str(arguments.get("query", ""))
        return _result(
            message_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": f"stdio-result:{query}",
                    }
                ]
            },
        )
    return _error(message_id, f"Unknown method: {method}")


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        response = handle(json.loads(line))
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
