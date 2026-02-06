"""
Unified Browse Memory Tool - 统一记忆浏览工具

将 list_l2_memory, list_l3_memory, select_memory_by_index 整合为单一工具。
支持两阶段查询：列出索引 → 选择内容
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.memory.core import LoomMemory


def create_unified_browse_tool() -> dict:
    """
    创建统一记忆浏览工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "browse_memory",
            "description": """Browse memory with two-phase query: list indices first, then select content.

**Actions**:
- list: Show indexed preview of memory items (saves tokens)
- select: Get full content for selected indices

**Layers**:
- L2: Important tasks (medium compression)
- L3: Task summaries (high compression)

**Workflow**:
1. First call with action="list" to see available items
2. Then call with action="select" and indices=[1,3,5] to get full content

**Examples**:
- List L2 items: action="list", layer="L2"
- Select items: action="select", layer="L2", indices=[1,3,5]""",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "select"],
                        "description": "Action to perform: 'list' for preview, 'select' for full content",
                    },
                    "layer": {
                        "type": "string",
                        "enum": ["L2", "L3"],
                        "default": "L2",
                        "description": "Memory layer to browse (L2: important tasks, L3: summaries)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum items to list (default: 10 for L2, 20 for L3)",
                        "default": 10,
                    },
                    "indices": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Indices to select (required for action='select')",
                    },
                },
                "required": ["action"],
            },
        },
    }


async def _list_memory(layer: str, limit: int, memory: "LoomMemory") -> dict[str, Any]:
    """列出记忆索引"""
    if layer == "L2":
        tasks = memory.get_l2_tasks(limit=limit)
        items = []
        for idx, task in enumerate(tasks, start=1):
            preview = f"{task.action}"
            if task.parameters:
                first_param = list(task.parameters.keys())[0] if task.parameters else ""
                if first_param:
                    preview += f"({first_param}=...)"
            items.append({
                "index": idx,
                "task_id": task.task_id,
                "preview": preview,
                "importance": task.metadata.get("importance", 0.5),
            })
        return {
            "layer": "L2",
            "action": "list",
            "count": len(items),
            "items": items,
            "hint": "Use action='select' with indices=[1,3,5] to get full content",
        }

    elif layer == "L3":
        summaries = memory.get_l3_summaries(limit=limit)
        items = []
        for idx, summary in enumerate(summaries, start=1):
            items.append({
                "index": idx,
                "task_id": summary.task_id,
                "preview": summary.action,
                "tags": summary.tags[:2] if summary.tags else [],
            })
        return {
            "layer": "L3",
            "action": "list",
            "count": len(items),
            "items": items,
            "hint": "Use action='select' with indices=[1,3,5] to get full content",
        }

    return {"error": f"Invalid layer: {layer}"}


async def _select_memory(layer: str, indices: list[int], memory: "LoomMemory") -> dict[str, Any]:
    """根据索引选择记忆内容"""

    if not indices:
        return {"error": "No indices provided", "selected": []}

    selected: list[dict[str, Any]] = []

    if layer == "L2":
        tasks = memory.get_l2_tasks(limit=100)
        for idx in indices:
            if 1 <= idx <= len(tasks):
                task = tasks[idx - 1]
                params_str = str(task.parameters)[:50] + "..." if len(str(task.parameters)) > 50 else str(task.parameters)
                result_str = str(task.result)[:100] + "..." if task.result and len(str(task.result)) > 100 else str(task.result or "无结果")
                selected.append({
                    "index": idx,
                    "task_id": task.task_id,
                    "statement": f"执行了{task.action}操作，参数{params_str}，结果{result_str}",
                })

    elif layer == "L3":
        summaries = memory.get_l3_summaries(limit=100)
        for idx in indices:
            if 1 <= idx <= len(summaries):
                summary = summaries[idx - 1]
                result_brief = summary.result_summary[:50] + "..." if len(summary.result_summary) > 50 else summary.result_summary
                selected.append({
                    "index": idx,
                    "task_id": summary.task_id,
                    "statement": f"{summary.action}: {result_brief}",
                })
    else:
        return {"error": f"Invalid layer: {layer}"}

    return {
        "layer": layer,
        "action": "select",
        "count": len(selected),
        "selected": selected,
    }


async def execute_unified_browse_tool(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """
    执行统一记忆浏览工具

    Args:
        args: 工具参数
        memory: LoomMemory实例

    Returns:
        查询结果
    """
    action = args.get("action", "list")
    layer = args.get("layer", "L2")
    limit = args.get("limit", 10 if layer == "L2" else 20)
    indices = args.get("indices", [])

    if action == "list":
        return await _list_memory(layer, limit, memory)
    elif action == "select":
        return await _select_memory(layer, indices, memory)
    else:
        return {"error": f"Invalid action: {action}"}
