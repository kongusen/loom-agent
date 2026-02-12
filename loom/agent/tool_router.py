"""
ToolRouter - 工具路由器

从 Agent.core 提取的工具执行路由逻辑。
负责将工具调用分发到正确的执行器。
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from loom.events.actions import KnowledgeAction
from loom.exceptions import PermissionDenied
from loom.observability.metrics import LoomMetrics
from loom.observability.tracing import SpanKind
from loom.runtime import Task, TaskStatus
from loom.tools.builtin.creation import ToolCreationError
from loom.tools.memory.browse import execute_unified_browse_tool
from loom.tools.memory.events import execute_unified_events_tool
from loom.tools.memory.manage import execute_unified_manage_tool

if TYPE_CHECKING:
    from loom.agent.core import Agent

logger = logging.getLogger(__name__)


class ToolRouter:
    """
    工具路由器

    将工具调用分发到正确的执行器：
    - 权限检查 → 参数解析 → 路由到具体执行器
    - 支持：动态工具、统一检索、内存工具、沙盒工具、注册表工具
    """

    def __init__(self, agent: Agent):
        self._agent = agent

    async def route(self, tool_name: str, tool_args: dict | str) -> str:
        """
        路由并执行工具调用

        Args:
            tool_name: 工具名称
            tool_args: 工具参数（dict 或 JSON 字符串）

        Returns:
            工具执行结果字符串
        """
        agent = self._agent

        # 权限检查
        if agent.tool_policy:
            context = {"tool_name": tool_name, "tool_args": tool_args}
            if not agent.tool_policy.is_allowed(tool_name, context):
                reason = agent.tool_policy.get_denial_reason(tool_name)
                raise PermissionDenied(tool_name=tool_name, reason=reason)

        # 参数解析
        parsed_args = self._parse_args(tool_args)

        # 动态工具创建
        if tool_name == "create_tool" and agent._dynamic_tool_executor:
            return await self._handle_create_tool(parsed_args)

        # 动态工具执行
        if agent._dynamic_tool_executor and tool_name in agent._dynamic_tool_executor.created_tools:
            return await self._handle_dynamic_tool(tool_name, parsed_args)

        # 统一检索
        if tool_name == "query":
            return await self._handle_query(parsed_args)

        # 统一内存/事件工具
        unified_result = await self._handle_unified_tools(tool_name, parsed_args)
        if unified_result is not None:
            return unified_result

        # 沙盒工具
        if agent.sandbox_manager and tool_name in agent.sandbox_manager:
            return await self._handle_sandbox_tool(tool_name, parsed_args)

        # 注册表工具
        return await self._handle_registry_tool(tool_name, parsed_args)

    @staticmethod
    def _parse_args(tool_args: dict | str) -> dict[str, Any]:
        if isinstance(tool_args, str):
            try:
                parsed: dict[str, Any] = json.loads(tool_args)
                return parsed
            except json.JSONDecodeError:
                return {}
        elif isinstance(tool_args, dict):
            return tool_args
        return {}

    async def _handle_create_tool(self, parsed_args: dict[str, Any]) -> str:
        agent = self._agent
        try:
            result = await agent._dynamic_tool_executor.create_tool(
                tool_name=parsed_args.get("tool_name", ""),
                description=parsed_args.get("description", ""),
                parameters=parsed_args.get("parameters", {}),
                implementation=parsed_args.get("implementation", ""),
            )
            agent.all_tools = agent._build_tool_list()
            return str(result)
        except ToolCreationError as e:
            return f"工具创建失败: {e}"
        except Exception as e:
            return f"工具创建错误: {e}"

    async def _handle_dynamic_tool(self, tool_name: str, parsed_args: dict[str, Any]) -> str:
        try:
            result = await self._agent._dynamic_tool_executor.execute_tool(
                tool_name, **parsed_args,
            )
            return str(result)
        except ToolCreationError as e:
            return f"动态工具执行失败: {e}"
        except Exception as e:
            return f"动态工具执行错误: {e}"

    async def _handle_query(self, parsed_args: dict[str, Any]) -> str:
        agent = self._agent
        session_id = getattr(agent, "_current_session_id", None)
        search_query = parsed_args.get("query", "")

        agent._metrics.increment(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL)
        _search_start = time.monotonic()

        # 创建 SearchTask 并发布到 EventBus
        search_task = Task(
            taskId=f"{agent.node_id}-search-{uuid4()}",
            sourceAgent=agent.node_id,
            action=KnowledgeAction.SEARCH,
            parameters=parsed_args,
            sessionId=session_id,
            parentTaskId=getattr(agent, "_current_task_id", None),
        )
        if agent.event_bus:
            await agent.event_bus.publish(search_task, wait_result=False)

        # 执行检索
        try:
            with agent._tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, search_query) as span:
                span.set_attribute("scope", parsed_args.get("scope", "auto"))
                result = await agent._search_executor.execute(
                    query=search_query,
                    scope=parsed_args.get("scope", "auto"),
                    source=parsed_args.get("source"),
                    intent=parsed_args.get("intent"),
                    filters=parsed_args.get("filters"),
                    layer=parsed_args.get("layer", "auto"),
                    session_id=session_id,
                )
                _elapsed = (time.monotonic() - _search_start) * 1000
                agent._metrics.observe(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY, _elapsed)
                _result_count = result.count("\n[") if result else 0
                agent._metrics.observe(LoomMetrics.KNOWLEDGE_RESULTS_COUNT, _result_count)
                has_results = result and "未找到" not in result
                agent._metrics.set_gauge(
                    LoomMetrics.KNOWLEDGE_HIT_RATE,
                    1.0 if has_results else 0.0,
                )
                span.set_attribute("results_count", _result_count)
                span.set_attribute("latency_ms", round(_elapsed, 1))
        except Exception as e:
            search_task.status = TaskStatus.FAILED
            search_task.error = str(e)
            if agent.event_bus:
                await agent.event_bus.publish(search_task, wait_result=False)
            return f"检索失败: {e}"

        # 发布结果 Task
        result_task = Task(
            taskId=f"{agent.node_id}-search-result-{uuid4()}",
            sourceAgent=agent.node_id,
            action=KnowledgeAction.SEARCH_RESULT,
            parameters={"query": search_query, "scope": parsed_args.get("scope", "auto")},
            result={"formatted_output": result},
            status=TaskStatus.COMPLETED,
            sessionId=session_id,
            parentTaskId=search_task.taskId,
        )
        if agent.event_bus:
            await agent.event_bus.publish(result_task, wait_result=False)

        return result

    async def _handle_unified_tools(
        self, tool_name: str, parsed_args: dict[str, Any],
    ) -> str | None:
        agent = self._agent
        unified_tool_executors = {
            "browse_memory": (execute_unified_browse_tool, "memory"),
            "manage_memory": (execute_unified_manage_tool, "memory"),
            "query_events": (execute_unified_events_tool, "event_bus"),
        }
        if tool_name not in unified_tool_executors:
            return None

        executor_func, resource_type = unified_tool_executors[tool_name]
        try:
            if resource_type == "memory" and agent.memory:
                result = await executor_func(parsed_args, agent.memory)  # type: ignore[operator]
            elif resource_type == "event_bus" and agent.event_bus:
                result = await executor_func(parsed_args, agent.event_bus)  # type: ignore[operator]
            else:
                return f"错误：{resource_type} 未初始化"
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return f"错误：统一工具执行失败 - {e}"

    async def _handle_sandbox_tool(self, tool_name: str, parsed_args: dict[str, Any]) -> str:
        try:
            assert self._agent.sandbox_manager is not None
            result = await self._agent.sandbox_manager.execute_tool(tool_name, parsed_args)
            return str(result)
        except Exception as e:
            return f"错误：沙盒工具执行失败 - {e}"

    async def _handle_registry_tool(self, tool_name: str, parsed_args: dict[str, Any]) -> str:
        agent = self._agent
        if agent.tool_registry is None:
            return f"错误：工具 '{tool_name}' 未找到（工具注册表未初始化）"
        tool_func = agent.tool_registry.get_callable(tool_name)
        if tool_func is None:
            return f"错误：工具 '{tool_name}' 未找到"
        try:
            result = await tool_func(**parsed_args)
            return str(result)
        except Exception as e:
            return f"错误：工具执行失败 - {e}"
