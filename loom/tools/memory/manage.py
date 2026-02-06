"""
Unified Memory Management Tool - 统一记忆管理工具

将 get_memory_stats, promote_task_to_l2, create_task_summary 整合为单一工具。
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.memory.core import LoomMemory


def create_unified_manage_tool() -> dict:
    """
    创建统一记忆管理工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "manage_memory",
            "description": """Manage memory layers with unified interface.

**Actions**:
- stats: Get memory usage statistics across all layers
- promote: Promote a task from L1 to L2 (important tasks)
- summarize: Create a compressed summary in L3

**Examples**:
- Check memory: action="stats"
- Promote task: action="promote", task_id="xxx"
- Summarize task: action="summarize", task_id="xxx", summary="..."
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["stats", "promote", "summarize"],
                        "description": "Action: stats/promote/summarize",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task ID (required for promote/summarize)",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Summary text (required for summarize)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for promotion (optional)",
                    },
                    "importance": {
                        "type": "number",
                        "description": "Importance score 0.0-1.0 (for summarize)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization (for summarize)",
                    },
                },
                "required": ["action"],
            },
        },
    }


async def _get_stats(memory: "LoomMemory") -> dict[str, Any]:
    """获取记忆统计信息"""
    stats = memory.get_stats()
    return {
        "action": "stats",
        "l1": {
            "current": stats["l1_size"],
            "max": stats["max_l1_size"],
            "usage_percent": round(stats["l1_size"] / stats["max_l1_size"] * 100, 1) if stats["max_l1_size"] > 0 else 0,
        },
        "l2": {
            "current": stats["l2_size"],
            "max": stats["max_l2_size"],
            "usage_percent": round(stats["l2_size"] / stats["max_l2_size"] * 100, 1) if stats["max_l2_size"] > 0 else 0,
        },
        "l3": {
            "current": stats["l3_size"],
            "max": stats["max_l3_size"],
            "usage_percent": round(stats["l3_size"] / stats["max_l3_size"] * 100, 1) if stats["max_l3_size"] > 0 else 0,
        },
        "l4_enabled": memory.enable_l4_vectorization,
    }


async def _promote_task(task_id: str, reason: str, memory: "LoomMemory") -> dict[str, Any]:
    """提升任务到L2"""
    from loom.memory.core import MemoryTier

    task = memory.get_task(task_id)
    if not task:
        return {"action": "promote", "success": False, "error": f"Task {task_id} not found"}

    l2_tasks = memory.get_l2_tasks()
    if any(t.task_id == task_id for t in l2_tasks):
        return {"action": "promote", "success": False, "error": f"Task {task_id} already in L2"}

    memory.add_task(task, tier=MemoryTier.L2_WORKING)
    stats = memory.get_stats()

    return {
        "action": "promote",
        "success": True,
        "task_id": task_id,
        "reason": reason,
        "l2_size": stats["l2_size"],
    }


async def _summarize_task(task_id: str, summary: str, importance: float, tags: list[str], memory: "LoomMemory") -> dict[str, Any]:
    """创建任务摘要"""
    from datetime import datetime

    from loom.memory.types import TaskSummary

    task = memory.get_task(task_id)
    if not task:
        return {"action": "summarize", "success": False, "error": f"Task {task_id} not found"}

    task_summary = TaskSummary(
        task_id=task.task_id,
        action=task.action,
        param_summary=str(task.parameters)[:100],
        result_summary=summary,
        importance=importance,
        tags=tags,
        created_at=task.created_at or datetime.now(),
    )

    memory._add_to_l3(task_summary)

    return {
        "action": "summarize",
        "success": True,
        "task_id": task_id,
        "summary": summary,
        "l3_size": len(memory._l3_summaries),
    }


async def execute_unified_manage_tool(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """执行统一记忆管理工具"""
    action = args.get("action", "stats")

    if action == "stats":
        return await _get_stats(memory)
    elif action == "promote":
        task_id = args.get("task_id", "")
        reason = args.get("reason", "LLM decision")
        return await _promote_task(task_id, reason, memory)
    elif action == "summarize":
        task_id = args.get("task_id", "")
        summary = args.get("summary", "")
        importance = args.get("importance", 0.5)
        tags = args.get("tags", [])
        return await _summarize_task(task_id, summary, importance, tags, memory)
    else:
        return {"error": f"Invalid action: {action}"}
