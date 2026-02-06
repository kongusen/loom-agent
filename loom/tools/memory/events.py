"""
Unified Event Query Tool - 统一事件查询工具

将 query_events_by_action, query_events_by_node, query_events_by_target,
query_recent_events, query_thinking_process 整合为单一工具。
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.events.event_bus import EventBus


def create_unified_events_tool() -> dict:
    """
    创建统一事件查询工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "query_events",
            "description": """Query events with unified interface.

**Filter Types**:
- action: Filter by action type (e.g., 'node.thinking', 'node.tool_call')
- node: Filter by node/agent ID
- target: Filter by target agent (direct messages)
- recent: Get recent events across all nodes
- thinking: Get thinking process events

**Examples**:
- By action: filter_by="action", action="node.tool_call"
- By node: filter_by="node", node_id="agent-1"
- Recent: filter_by="recent"
- Thinking: filter_by="thinking"
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_by": {
                        "type": "string",
                        "enum": ["action", "node", "target", "recent", "thinking"],
                        "description": "Filter type: action/node/target/recent/thinking",
                    },
                    "action": {
                        "type": "string",
                        "description": "Action type (for filter_by='action')",
                    },
                    "node_id": {
                        "type": "string",
                        "description": "Node ID (for filter_by='node' or 'thinking')",
                    },
                    "target_agent": {
                        "type": "string",
                        "description": "Target agent ID (for filter_by='target')",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task ID filter (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum events to retrieve (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["filter_by"],
            },
        },
    }


def _format_events(events: list) -> list[dict[str, Any]]:
    """格式化事件列表"""
    return [
        {
            "task_id": e.task_id,
            "action": e.action,
            "parameters": e.parameters,
            "result": e.result,
            "status": e.status.value if e.status else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


async def execute_unified_events_tool(args: dict, event_bus: "EventBus") -> dict[str, Any]:
    """执行统一事件查询工具"""
    filter_by = args.get("filter_by", "recent")
    limit = args.get("limit", 10)

    # 获取最近事件（EventBus 只提供 get_recent_events 方法）
    # 获取足够多的事件用于过滤
    all_events = event_bus.get_recent_events(limit=100)

    if filter_by == "action":
        action = args.get("action", "")
        node_filter = args.get("node_id")
        events = [
            e for e in all_events
            if e.action == action
            and (node_filter is None or getattr(e, "source_node", None) == node_filter)
        ][:limit]
        return {"filter_by": "action", "action": action, "count": len(events), "events": _format_events(events)}

    elif filter_by == "node":
        node_id = args.get("node_id", "")
        action_filter = args.get("action")
        events = [
            e for e in all_events
            if getattr(e, "source_node", None) == node_id
            and (action_filter is None or e.action == action_filter)
        ][:limit]
        return {"filter_by": "node", "node_id": node_id, "count": len(events), "events": _format_events(events)}

    elif filter_by == "target":
        target_agent = args.get("target_agent")
        target_node_id = args.get("node_id")
        if not target_agent and not target_node_id:
            return {"error": "target_agent or node_id required for filter_by='target'"}
        events = [
            e for e in all_events
            if (target_agent and getattr(e, "target_agent", None) == target_agent)
            or (target_node_id and getattr(e, "target_node", None) == target_node_id)
        ][:limit]
        return {"filter_by": "target", "target_agent": target_agent, "count": len(events), "events": _format_events(events)}

    elif filter_by == "recent":
        action_filter = args.get("action")
        node_filter = args.get("node_id")
        events = [
            e for e in all_events
            if (action_filter is None or e.action == action_filter)
            and (node_filter is None or getattr(e, "source_node", None) == node_filter)
        ][:limit]
        return {"filter_by": "recent", "count": len(events), "events": _format_events(events)}

    elif filter_by == "thinking":
        # 过滤思考相关事件
        node_id = args.get("node_id")
        task_id = args.get("task_id")
        thinking_actions = {"node.thinking", "agent.thinking", "thinking"}
        events = [
            e for e in all_events
            if e.action in thinking_actions
            and (node_id is None or getattr(e, "source_node", None) == node_id)
            and (task_id is None or e.task_id == task_id)
        ][:limit]
        thoughts = [
            {"task_id": e.task_id, "content": e.parameters.get("content", ""), "action": e.action}
            for e in events
        ]
        return {"filter_by": "thinking", "count": len(thoughts), "thoughts": thoughts}

    return {"error": f"Invalid filter_by: {filter_by}"}
