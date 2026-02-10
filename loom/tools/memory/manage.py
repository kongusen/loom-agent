"""
Unified Memory Management Tool - 统一记忆管理工具

基于 Session-EventBus 架构：
- stats: 获取 Session 和 ContextController 的统计
- promote: 触发 L1→L2 提升 (Session)
- aggregate: 触发 L2→L3 聚合 (ContextController)
- persist: 触发 L3→L4 持久化 (ContextController)
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.events.context_controller import ContextController
    from loom.events.session import Session


def create_unified_manage_tool() -> dict:
    """创建统一记忆管理工具定义"""
    return {
        "type": "function",
        "function": {
            "name": "manage_memory",
            "description": """Manage memory layers.

**Actions**:
- stats: Get memory statistics
- promote: Trigger L1→L2 promotion (Session)
- aggregate: Trigger L2→L3 aggregation (ContextController)
- persist: Trigger L3→L4 persistence (ContextController)""",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["stats", "promote", "aggregate", "persist"],
                    },
                },
                "required": ["action"],
            },
        },
    }


async def _get_stats(session: "Session", cc: "ContextController") -> dict[str, Any]:
    """获取记忆统计"""
    session_stats = session.get_stats()
    return {
        "action": "stats",
        "session": {
            "id": session.session_id,
            "status": session_stats.get("status"),
            "l1_count": len(session.get_l1_tasks()),
            "l2_count": len(session.get_l2_tasks()),
        },
        "controller": {
            "l3_count": cc.l3_count,
            "l3_tokens": cc.l3_token_usage,
            "sessions": len(cc.session_ids),
        },
    }


async def _promote(session: "Session") -> dict[str, Any]:
    """触发 L1→L2 提升"""
    session.promote_tasks()
    return {
        "action": "promote",
        "success": True,
        "l2_count": len(session.get_l2_tasks()),
    }


async def _aggregate(cc: "ContextController") -> dict[str, Any]:
    """触发 L2→L3 聚合"""
    result = await cc.aggregate_to_l3()
    return {
        "action": "aggregate",
        "success": result is not None,
        "l3_count": cc.l3_count,
    }


async def _persist(cc: "ContextController") -> dict[str, Any]:
    """触发 L3→L4 持久化"""
    success = await cc.persist_to_l4()
    return {"action": "persist", "success": success}


async def execute_unified_manage_tool(
    args: dict,
    session: "Session",
    context_controller: "ContextController",
) -> dict[str, Any]:
    """执行统一记忆管理工具"""
    action = args.get("action", "stats")

    if action == "stats":
        return await _get_stats(session, context_controller)
    elif action == "promote":
        return await _promote(session)
    elif action == "aggregate":
        return await _aggregate(context_controller)
    elif action == "persist":
        return await _persist(context_controller)
    return {"error": f"Invalid action: {action}"}
