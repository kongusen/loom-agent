"""
Unified Memory Query Tool - 统一记忆查询工具

提供单一接口查询 L1-L4 记忆层，支持自动层级选择和渐进式查询。

基于 Session-EventBus 架构：
- L1/L2: Session 私有，通过 Session 访问
- L3: Agent 级聚合，通过 ContextController 访问
- L4: 全局持久化，通过 ContextController 访问

参考: loom/events/CONTEXT_ARCHITECTURE.md
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.events.context_controller import ContextController
    from loom.events.session import Session


def _select_layer_auto(query: str | None, session_id: str | None) -> str:
    """自动选择最合适的记忆层级"""
    if query and len(query) > 20:
        return "L4"
    if not session_id:
        return "L4" if query else "L3"
    return "L1"


def _is_result_sufficient(count: int, layer: str) -> bool:
    """判断结果是否充足"""
    thresholds = {"L1": 3, "L2": 5, "L3": 10, "L4": 1}
    return count >= thresholds.get(layer, 1)


def _get_next_layer(current_layer: str) -> str | None:
    """获取下一个层级"""
    layer_sequence = ["L1", "L2", "L3", "L4"]
    try:
        idx = layer_sequence.index(current_layer)
        if idx < len(layer_sequence) - 1:
            return layer_sequence[idx + 1]
    except ValueError:
        pass
    return None


async def _query_l1(args: dict, session: "Session") -> dict[str, Any]:
    """查询L1记忆（最近任务，Session私有）"""
    limit = args.get("limit", 10)
    tasks = session.get_l1_tasks(limit=limit)
    return {
        "layer": "L1",
        "count": len(tasks),
        "tasks": [
            {
                "task_id": t.task_id,
                "action": t.action,
                "parameters": t.parameters,
                "result": t.result,
                "status": t.status.value if t.status else None,
            }
            for t in tasks
        ],
    }


async def _query_l2(args: dict, session: "Session") -> dict[str, Any]:
    """查询L2记忆（重要任务，Session级别）"""
    limit = args.get("limit", 10)
    tasks = session.get_l2_tasks(limit=limit)
    statements = []
    for task in tasks:
        params_str = str(task.parameters)[:50] + "..." if len(str(task.parameters)) > 50 else str(task.parameters)
        result_str = str(task.result)[:100] + "..." if task.result and len(str(task.result)) > 100 else str(task.result or "")
        statements.append({
            "task_id": task.task_id,
            "statement": f"{task.action}: {params_str} -> {result_str}",
            "importance": task.metadata.get("importance", 0.5),
        })
    return {"layer": "L2", "count": len(statements), "statements": statements}


async def _query_l3(args: dict, context_controller: "ContextController", session_id: str | None = None) -> dict[str, Any]:
    """查询L3记忆（Agent级聚合，ContextController管理）"""
    limit = args.get("limit", 20)
    summaries = context_controller.get_l3_summaries(limit=limit)
    if session_id:
        summaries = [s for s in summaries if session_id in s.get("session_ids", []) or not s.get("session_ids")]
    statements = []
    for s in summaries:
        content = s.get("content", "")[:100]
        statements.append({
            "timestamp": s.get("timestamp", ""),
            "statement": content + "..." if len(s.get("content", "")) > 100 else content,
            "source_count": s.get("source_count", 0),
        })
    return {"layer": "L3", "count": len(statements), "statements": statements}


async def _query_l4(args: dict, context_controller: "ContextController") -> dict[str, Any]:
    """查询L4记忆（全局持久化，ContextController管理）"""
    query = args.get("query", "")
    limit = args.get("limit", 5)
    l4_summaries = await context_controller.load_from_l4()
    statements = []
    for s in l4_summaries[-limit:]:
        content = s.get("content", "")[:100]
        statements.append({
            "agent_id": s.get("agent_id", ""),
            "statement": content + "..." if len(s.get("content", "")) > 100 else content,
        })
    return {"layer": "L4", "query": query, "count": len(statements), "statements": statements}


def create_unified_memory_tool() -> dict:
    """创建统一记忆查询工具定义"""
    return {
        "type": "function",
        "function": {
            "name": "query_memory",
            "description": """Query memory with automatic layer selection.

**Memory Layers**:
- L1: Recent tasks (Session private, full details)
- L2: Important tasks (Session level, compressed)
- L3: Agent summaries (cross-Session aggregation)
- L4: Global persistent (EventBus level)

**Usage**:
- layer="auto": Auto-select and cascade
- layer="L1/L2/L3/L4": Direct query""",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (for L4)",
                    },
                    "layer": {
                        "type": "string",
                        "enum": ["auto", "L1", "L2", "L3", "L4"],
                        "default": "auto",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                    },
                    "auto_cascade": {
                        "type": "boolean",
                        "default": True,
                    },
                },
                "required": [],
            },
        },
    }


async def execute_unified_memory_tool(
    args: dict,
    session: "Session",
    context_controller: "ContextController",
) -> dict[str, Any]:
    """
    执行统一记忆查询工具

    Args:
        args: 工具参数
        session: Session 实例（L1/L2）
        context_controller: ContextController 实例（L3/L4）
    """
    query = args.get("query")
    layer = args.get("layer", "auto")
    limit = args.get("limit", 10)
    auto_cascade = args.get("auto_cascade", True)
    session_id = session.session_id

    if layer == "auto":
        layer = _select_layer_auto(query, session_id)

    results = []
    current_layer = layer

    while current_layer:
        layer_args = {"limit": limit}
        if current_layer == "L4":
            if not query:
                break
            layer_args["query"] = query

        if current_layer == "L1":
            result = await _query_l1(layer_args, session)
        elif current_layer == "L2":
            result = await _query_l2(layer_args, session)
        elif current_layer == "L3":
            result = await _query_l3(layer_args, context_controller, session_id)
        elif current_layer == "L4":
            result = await _query_l4(layer_args, context_controller)
        else:
            break

        results.append(result)

        if not auto_cascade or _is_result_sufficient(result.get("count", 0), current_layer):
            break

        current_layer = _get_next_layer(current_layer)

    return {
        "query_type": "unified",
        "requested_layer": layer,
        "layers_queried": [r["layer"] for r in results],
        "total_results": sum(r.get("count", 0) for r in results),
        "results": results,
    }
