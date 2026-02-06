"""
Unified Memory Query Tool - 统一记忆查询工具

提供单一接口查询 L1-L4 记忆层，支持自动层级选择和渐进式查询。
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.memory.core import LoomMemory


def _select_layer_auto(query: str | None, session_id: str | None) -> str:
    """
    自动选择最合适的记忆层级

    Args:
        query: 查询字符串
        session_id: 会话ID

    Returns:
        选择的层级 (L1/L2/L3/L4)
    """
    # 如果有明确的语义查询，优先使用 L4
    if query and len(query) > 20:  # 较长的查询通常是语义搜索
        return "L4"

    # 如果没有 session_id，使用 L4 跨会话搜索
    if not session_id:
        return "L4" if query else "L3"

    # 默认从 L1 开始（最近任务）
    return "L1"


def _is_result_sufficient(count: int, layer: str) -> bool:
    """
    判断结果是否充足

    Args:
        count: 结果数量
        layer: 当前层级

    Returns:
        是否充足
    """
    # 不同层级的充足阈值
    thresholds = {
        "L1": 3,   # L1 至少需要 3 个结果
        "L2": 5,   # L2 至少需要 5 个结果
        "L3": 10,  # L3 至少需要 10 个结果
        "L4": 1,   # L4 语义搜索至少需要 1 个结果
    }
    return count >= thresholds.get(layer, 1)


def _get_next_layer(current_layer: str) -> str | None:
    """
    获取下一个层级

    Args:
        current_layer: 当前层级

    Returns:
        下一个层级，如果没有则返回 None
    """
    layer_sequence = ["L1", "L2", "L3", "L4"]
    try:
        current_index = layer_sequence.index(current_layer)
        if current_index < len(layer_sequence) - 1:
            return layer_sequence[current_index + 1]
    except ValueError:
        pass
    return None


async def _query_l1(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """查询L1记忆"""
    limit = args.get("limit", 10)
    session_id = args.get("session_id")
    tasks = memory.get_l1_tasks(limit=limit, session_id=session_id)
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


async def _query_l2(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """查询L2记忆"""
    limit = args.get("limit", 10)
    session_id = args.get("session_id")
    tasks = memory.get_l2_tasks(limit=limit, session_id=session_id)
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


async def _query_l3(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """查询L3记忆"""
    limit = args.get("limit", 20)
    session_id = args.get("session_id")
    summaries = memory.get_l3_summaries(limit=limit, session_id=session_id)
    statements = []
    for s in summaries:
        result_brief = s.result_summary[:50] + "..." if len(s.result_summary) > 50 else s.result_summary
        statements.append({
            "task_id": s.task_id,
            "statement": f"{s.action}: {result_brief}",
            "tags": s.tags[:3] if s.tags else [],
        })
    return {"layer": "L3", "count": len(statements), "statements": statements}


async def _query_l4(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """查询L4记忆（语义搜索）"""
    query = args.get("query", "")
    limit = args.get("limit", 5)
    session_id = args.get("session_id")
    tasks = await memory.search_tasks(query=query, limit=limit, session_id=session_id)
    statements = []
    for t in tasks:
        status = "完成" if t.status and t.status.value == "completed" else "执行"
        statements.append({"task_id": t.task_id, "statement": f"{t.action}{status}"})
    return {"layer": "L4", "query": query, "count": len(statements), "statements": statements}


def create_unified_memory_tool() -> dict:
    """
    创建统一记忆查询工具定义

    Returns:
        OpenAI格式的工具定义字典
    """
    return {
        "type": "function",
        "function": {
            "name": "query_memory",
            "description": """Query memory with automatic layer selection and progressive disclosure.

**Memory Layers**:
- L1: Recent tasks (full details, ~10 items, current session)
- L2: Important tasks (compressed, ~50 items, current session)
- L3: Session summaries (highly compressed, ~200 items)
- L4: Semantic search (minimal, cross-session, vector-based)

**Usage**:
- Default (layer="auto"): Automatically selects best layer and cascades if needed
- Specific layer: Directly query L1/L2/L3/L4
- Auto cascade: If results insufficient, automatically queries next layer

**Examples**:
- Recent tasks: layer="auto" or layer="L1"
- Important history: layer="L2"
- Broad overview: layer="L3"
- Semantic search: layer="L4" with query parameter""",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (required for L4 semantic search, optional for others)",
                    },
                    "layer": {
                        "type": "string",
                        "enum": ["auto", "L1", "L2", "L3", "L4"],
                        "default": "auto",
                        "description": """Target memory layer:
- auto: Automatically select best layer (default)
- L1: Recent tasks with full details
- L2: Important tasks with compression
- L3: Session summaries
- L4: Semantic search (requires query parameter)""",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of items to retrieve (default varies by layer)",
                        "default": 10,
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID filter (L1-L3 only, L4 is cross-session)",
                    },
                    "auto_cascade": {
                        "type": "boolean",
                        "description": "If true, automatically query next layer when results insufficient (default: true)",
                        "default": True,
                    },
                },
                "required": [],
            },
        },
    }


async def execute_unified_memory_tool(args: dict, memory: "LoomMemory") -> dict[str, Any]:
    """
    执行统一记忆查询工具

    Args:
        args: 工具参数
        memory: LoomMemory实例

    Returns:
        查询结果（可能包含多层级的结果）
    """
    query = args.get("query")
    layer = args.get("layer", "auto")
    limit = args.get("limit", 10)
    session_id = args.get("session_id")
    auto_cascade = args.get("auto_cascade", True)

    # 自动选择层级
    if layer == "auto":
        layer = _select_layer_auto(query, session_id)

    # 存储所有查询结果
    results = []
    current_layer = layer

    # 查询当前层级
    while current_layer:
        layer_args = {"limit": limit, "session_id": session_id}
        if current_layer == "L4":
            if not query:
                break
            layer_args["query"] = query

        # 执行查询（内联实现）
        if current_layer == "L1":
            result = await _query_l1(layer_args, memory)
        elif current_layer == "L2":
            result = await _query_l2(layer_args, memory)
        elif current_layer == "L3":
            result = await _query_l3(layer_args, memory)
        elif current_layer == "L4":
            result = await _query_l4(layer_args, memory)
        else:
            break

        results.append(result)

        if not auto_cascade:
            break

        count = result.get("count", 0)
        if _is_result_sufficient(count, current_layer):
            break

        next_layer = _get_next_layer(current_layer)
        if not next_layer:
            break

        current_layer = next_layer

    return {
        "query_type": "unified",
        "requested_layer": layer,
        "layers_queried": [r["layer"] for r in results],
        "total_results": sum(r.get("count", 0) for r in results),
        "results": results,
    }
