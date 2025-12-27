"""
Loom Quick Start API

提供简化的 API，让新用户无需理解底层架构即可快速上手。

示例：
    from loom.quick import create_agent, run

    agent = create_agent("研究员", role="Researcher")
    result = run(agent, "研究量子计算的最新进展")
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps

from loom.api.main import LoomApp
from loom.node.agent import AgentNode
from loom.node.tool import ToolNode
from loom.node.crew import CrewNode
from loom.protocol.mcp import MCPToolDefinition
from loom.interfaces.llm import LLMProvider
from loom.interfaces.memory import MemoryInterface


# ============================================================================
# 全局 App 管理器
# ============================================================================

_global_app: Optional[LoomApp] = None
_global_app_lock = asyncio.Lock()


def _get_or_create_app(control_config: Optional[Dict[str, Any]] = None) -> LoomApp:
    """
    获取或创建全局 LoomApp 实例。

    这个函数管理一个全局单例 App，用户不需要显式创建和管理。
    """
    global _global_app

    if _global_app is None:
        _global_app = LoomApp(control_config=control_config)

    return _global_app


def reset_app():
    """
    重置全局 App（主要用于测试）。
    """
    global _global_app
    _global_app = None


def get_app() -> Optional[LoomApp]:
    """
    获取当前的全局 App 实例。

    Returns:
        当前的 LoomApp 实例，如果还未创建则返回 None
    """
    return _global_app


def configure_app(control_config: Dict[str, Any]):
    """
    配置全局 App。

    必须在创建任何 Agent/Tool/Crew 之前调用。

    Args:
        control_config: 控制配置，例如 {"budget": 5000, "depth": 10}

    Example:
        configure_app({"budget": 5000, "depth": 10})
        agent = create_agent("researcher")
    """
    global _global_app

    if _global_app is not None:
        raise RuntimeError(
            "Cannot configure app after it has been created. "
            "Call configure_app() before creating any agents/tools/crews."
        )

    _global_app = LoomApp(control_config=control_config)


# ============================================================================
# 快速创建函数
# ============================================================================

def create_agent(
    name: str,
    role: str = "Assistant",
    tools: Optional[List[Union[str, ToolNode]]] = None,
    provider: Optional[LLMProvider] = None,
    memory: Optional[MemoryInterface] = None
) -> AgentNode:
    """
    快速创建一个 Agent。

    Args:
        name: Agent 的名称/ID
        role: Agent 的角色描述
        tools: 工具列表，可以是字符串名称或 ToolNode 实例
        provider: LLM 提供商（可选，默认使用 Mock）
        memory: 记忆接口（可选，默认使用分层记忆）

    Returns:
        创建的 AgentNode 实例

    Example:
        agent = create_agent("研究员", role="Researcher")
        agent = create_agent("编码员", role="Coder", tools=["file-ops"])
    """
    app = _get_or_create_app()

    # 解析工具列表
    tool_nodes = []
    if tools:
        for tool in tools:
            if isinstance(tool, str):
                # TODO: 从标准库解析工具名称
                # 目前先跳过字符串工具
                pass
            elif isinstance(tool, ToolNode):
                tool_nodes.append(tool)

    return AgentNode(
        node_id=name,
        dispatcher=app.dispatcher,
        role=role,
        tools=tool_nodes if tool_nodes else None,
        provider=provider,
        memory=memory
    )


def create_tool(
    name: str,
    func: Callable[..., Any],
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None
) -> ToolNode:
    """
    快速创建一个 Tool。

    Args:
        name: 工具名称
        func: 工具函数（可以是同步或异步函数）
        description: 工具描述（可选，会从函数文档字符串自动生成）
        parameters: 参数 schema（可选，会从函数签名自动生成）

    Returns:
        创建的 ToolNode 实例

    Example:
        def search_web(query: str) -> str:
            return f"搜索结果: {query}"

        tool = create_tool("web-search", search_web, "搜索网络")
    """
    app = _get_or_create_app()

    # 使用工厂函数自动生成 schema
    from loom.adapters.converters import FunctionToMCP

    auto_def = FunctionToMCP.convert(func, name=name)

    final_desc = description or auto_def.description
    final_input_schema = parameters or auto_def.input_schema

    tool_def = MCPToolDefinition(
        name=name,
        description=final_desc,
        input_schema=final_input_schema
    )

    return ToolNode(
        node_id=name,
        dispatcher=app.dispatcher,
        tool_def=tool_def,
        func=func
    )


def create_crew(
    name: str,
    agents: List[AgentNode],
    pattern: str = "sequential"
) -> CrewNode:
    """
    快速创建一个 Crew（Agent 团队）。

    Args:
        name: Crew 名称
        agents: Agent 列表
        pattern: 协作模式（目前支持 "sequential"）

    Returns:
        创建的 CrewNode 实例

    Example:
        researcher = create_agent("researcher", role="Researcher")
        writer = create_agent("writer", role="Writer")
        crew = create_crew("research-team", [researcher, writer])
    """
    app = _get_or_create_app()

    return CrewNode(
        node_id=name,
        dispatcher=app.dispatcher,
        agents=agents
    )


# ============================================================================
# 运行函数
# ============================================================================

async def run_async(
    node: Union[AgentNode, CrewNode],
    task: str,
    timeout: float = 30.0
) -> Any:
    """
    异步运行一个 Agent 或 Crew。

    Args:
        node: Agent 或 Crew 实例
        task: 任务描述
        timeout: 超时时间（秒）

    Returns:
        任务执行结果

    Example:
        agent = create_agent("researcher")
        result = await run_async(agent, "研究量子计算")
    """
    app = _get_or_create_app()

    # 确保节点已订阅事件（如果还没有订阅）
    if not node._subscribed:
        await node._subscribe_to_events()

    return await app.run(task, target=node.source_uri)


def run(
    node: Union[AgentNode, CrewNode],
    task: str,
    timeout: float = 30.0
) -> Any:
    """
    同步运行一个 Agent 或 Crew（自动处理 asyncio）。

    Args:
        node: Agent 或 Crew 实例
        task: 任务描述
        timeout: 超时时间（秒）

    Returns:
        任务执行结果

    Example:
        agent = create_agent("researcher")
        result = run(agent, "研究量子计算")
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已经在事件循环中，抛出错误提示使用 run_async
            raise RuntimeError(
                "Cannot use run() inside an async context. "
                "Use 'await run_async()' instead."
            )
    except RuntimeError:
        # 没有事件循环，创建新的
        pass

    return asyncio.run(run_async(node, task, timeout))
