"""
Unified Browse Memory Tool - 统一记忆浏览工具

基于 Session-EventBus 架构：
- L2: Session 级别，通过 Session 访问
- L3: Agent 级聚合，通过 ContextController 访问
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.events.context_controller import ContextController
    from loom.events.session import Session


def create_unified_browse_tool() -> dict:
    """创建统一记忆浏览工具定义"""
    return {
        "type": "function",
        "function": {
            "name": "browse_memory",
            "description": """Browse memory: list indices, then select content.

- L2: Important tasks (Session)
- L3: Agent summaries (ContextController)""",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "select"]},
                    "layer": {"type": "string", "enum": ["L2", "L3"], "default": "L2"},
                    "limit": {"type": "integer", "default": 10},
                    "indices": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["action"],
            },
        },
    }


async def _list_l2(session: "Session", limit: int) -> dict[str, Any]:
    """列出 L2 记忆"""
    tasks = session.get_l2_tasks(limit=limit)
    items = []
    for idx, task in enumerate(tasks, start=1):
        preview = task.action
        if task.parameters:
            first_key = next(iter(task.parameters), "")
            if first_key:
                preview += f"({first_key}=...)"
        items.append({
            "index": idx,
            "task_id": task.task_id,
            "preview": preview,
        })
    return {"layer": "L2", "action": "list", "count": len(items), "items": items}


async def _list_l3(cc: "ContextController", limit: int) -> dict[str, Any]:
    """列出 L3 记忆"""
    summaries = cc.get_l3_summaries(limit=limit)
    items = []
    for idx, s in enumerate(summaries, start=1):
        content = s.get("content", "")[:50]
        items.append({
            "index": idx,
            "timestamp": s.get("timestamp", ""),
            "preview": content + "..." if len(s.get("content", "")) > 50 else content,
        })
    return {"layer": "L3", "action": "list", "count": len(items), "items": items}


async def _select_l2(session: "Session", indices: list[int]) -> dict[str, Any]:
    """选择 L2 记忆"""
    tasks = session.get_l2_tasks(limit=100)
    selected = []
    for idx in indices:
        if 1 <= idx <= len(tasks):
            t = tasks[idx - 1]
            selected.append({
                "index": idx,
                "task_id": t.task_id,
                "action": t.action,
                "parameters": t.parameters,
                "result": t.result,
            })
    return {"layer": "L2", "action": "select", "count": len(selected), "selected": selected}


async def _select_l3(cc: "ContextController", indices: list[int]) -> dict[str, Any]:
    """选择 L3 记忆"""
    summaries = cc.get_l3_summaries(limit=100)
    selected = []
    for idx in indices:
        if 1 <= idx <= len(summaries):
            s = summaries[idx - 1]
            selected.append({
                "index": idx,
                "content": s.get("content", ""),
                "timestamp": s.get("timestamp", ""),
            })
    return {"layer": "L3", "action": "select", "count": len(selected), "selected": selected}


async def execute_unified_browse_tool(
    args: dict,
    session: "Session",
    context_controller: "ContextController",
) -> dict[str, Any]:
    """执行统一记忆浏览工具"""
    action = args.get("action", "list")
    layer = args.get("layer", "L2")
    limit = args.get("limit", 10)
    indices = args.get("indices", [])

    if action == "list":
        if layer == "L2":
            return await _list_l2(session, limit)
        return await _list_l3(context_controller, limit)
    elif action == "select":
        if not indices:
            return {"error": "No indices provided"}
        if layer == "L2":
            return await _select_l2(session, indices)
        return await _select_l3(context_controller, indices)
    return {"error": f"Invalid action: {action}"}
