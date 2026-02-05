"""
Base Node - 节点基类

位置: loom/agent/base.py

基于公理系统和唯一性原则：
将观测和集体记忆能力集成到BaseNode中，作为所有节点的基础能力。

设计原则：
1. 唯一性 - 每个功能只在一个地方实现
2. 分层 - 基础能力在BaseNode，高级功能在子类
3. 可选 - 功能可以按需启用/禁用

基础能力：
- 生命周期管理（on_start, on_complete, on_error）
- 事件发布（观测能力）
- 事件查询（集体记忆能力）
- 统计信息
"""

import time
from datetime import datetime
from enum import StrEnum
from typing import Any

from loom.protocol import AgentCard, Task, TaskStatus


class NodeState(StrEnum):
    """节点状态枚举"""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseNode:
    """
    节点基类

    集成了观测和集体记忆能力，作为所有节点的基础。
    所有自定义节点都应该继承此类。

    属性：
        node_id: 节点唯一标识
        node_type: 节点类型（agent, tool, pipeline, container）
        agent_card: 能力声明
        event_bus: 事件总线（用于观测和集体记忆）
        enable_observation: 是否启用观测能力
        enable_collective_memory: 是否启用集体记忆能力
        state: 当前状态
        metadata: 节点元数据
        stats: 执行统计信息
    """

    def __init__(
        self,
        node_id: str,
        node_type: str = "base",
        agent_card: AgentCard | None = None,
        event_bus: Any | None = None,  # EventBus
        enable_observation: bool = True,
        enable_collective_memory: bool = True,
    ):
        """
        初始化基础节点

        Args:
            node_id: 节点ID
            node_type: 节点类型
            agent_card: 能力声明
            event_bus: 事件总线（可选）
            enable_observation: 是否启用观测能力
            enable_collective_memory: 是否启用集体记忆能力
        """
        self.node_id = node_id
        self.source_uri = f"node://{node_id}"
        self.node_type = node_type
        self.agent_card = agent_card or AgentCard(
            agent_id=node_id,
            name=node_id,
            description=f"Base node: {node_id}",
            capabilities=[],
        )

        # 事件总线（用于观测和集体记忆）
        self.event_bus = event_bus
        self.enable_observation = enable_observation
        self.enable_collective_memory = enable_collective_memory

        # 状态管理
        self.state = NodeState.IDLE
        self.metadata: dict[str, Any] = {}

        # 执行统计
        self.stats: dict[str, Any] = {
            "execution_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_duration": 0.0,
            "last_execution": None,
        }

        # 拦截器链
        from loom.runtime.interceptor import InterceptorChain

        self.interceptor_chain = InterceptorChain()

    # ==================== 事件发布（观测能力）====================

    async def _publish_event(
        self,
        action: str,
        parameters: dict[str, Any],
        task_id: str,
        session_id: str | None = None,
    ) -> None:
        """
        发布节点事件（观测能力）

        Args:
            action: 事件动作
            parameters: 事件参数
            task_id: 关联的任务ID
        """
        if not self.enable_observation or not self.event_bus:
            return

        # 创建事件Task
        event_task = Task(
            taskId=f"{task_id}:event:{action}",
            sourceAgent=self.node_id,
            targetAgent="observer",
            action=action,
            parameters={
                "node_id": self.node_id,
                "node_type": self.node_type,
                "parent_task_id": task_id,
                **parameters,
            },
            status=TaskStatus.COMPLETED,
            sessionId=session_id,
            parentTaskId=task_id,
        )

        # 发布事件（fire-and-forget）
        await self.event_bus.publish(event_task, wait_result=False)

    async def publish_thinking(
        self,
        content: str,
        task_id: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> None:
        """
        发布思考过程事件

        Args:
            content: 思考内容
            task_id: 关联的任务ID
            metadata: 额外的元数据
        """
        await self._publish_event(
            action="node.thinking",
            parameters={
                "content": content,
                "metadata": metadata or {},
            },
            task_id=task_id,
            session_id=session_id,
        )

    async def publish_tool_call(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        task_id: str,
        session_id: str | None = None,
    ) -> None:
        """
        发布工具调用事件

        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            task_id: 关联的任务ID
        """
        await self._publish_event(
            action="node.tool_call",
            parameters={
                "tool_name": tool_name,
                "tool_args": tool_args,
            },
            task_id=task_id,
            session_id=session_id,
        )

    async def publish_tool_result(
        self,
        tool_name: str,
        result: str,
        task_id: str,
        session_id: str | None = None,
    ) -> None:
        """
        发布工具执行结果事件

        Args:
            tool_name: 工具名称
            result: 工具执行结果
            task_id: 关联的任务ID
        """
        await self._publish_event(
            action="node.tool_result",
            parameters={
                "tool_name": tool_name,
                "result": result,
            },
            task_id=task_id,
            session_id=session_id,
        )

    async def publish_message(
        self,
        content: str,
        task_id: str,
        target_agent: str,
        target_node_id: str | None = None,
        priority: float = 0.5,
        ttl_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> None:
        """
        发布点对点消息（Direct Message）

        Args:
            content: 消息内容
            task_id: 关联的任务ID
            target_agent: 目标Agent ID
            target_node_id: 目标节点ID（可选）
            priority: 优先级（0-1）
            ttl_seconds: 生存时间（秒，可选）
            metadata: 额外元数据
        """
        if not self.enable_observation or not self.event_bus:
            return

        event_task = Task(
            taskId=f"{task_id}:event:node.message",
            sourceAgent=self.node_id,
            targetAgent=target_agent,
            action="node.message",
            parameters={
                "content": content,
                "priority": priority,
                "ttl_seconds": ttl_seconds,
                "target_node_id": target_node_id,
                "parent_task_id": task_id,
                "metadata": metadata or {},
            },
            status=TaskStatus.COMPLETED,
            sessionId=session_id,
            parentTaskId=task_id,
        )

        await self.event_bus.publish(event_task, wait_result=False)

    # ==================== 事件查询（集体记忆能力）====================

    def query_collective_memory(
        self,
        action_filter: str | None = None,
        node_filter: str | None = None,
        limit: int = 10,
    ) -> list[Task]:
        """
        查询集体记忆

        Args:
            action_filter: 可选的动作过滤
            node_filter: 可选的节点过滤
            limit: 最大结果数量

        Returns:
            事件列表
        """
        if not self.enable_collective_memory or not self.event_bus:
            return []

        # 检查event_bus是否有query方法
        if not hasattr(self.event_bus, "query_recent"):
            return []

        # 类型断言：query_recent 返回 list[Task]
        # mypy 无法推断动态属性的返回类型，需要类型忽略
        result = self.event_bus.query_recent(  # type: ignore[attr-defined]
            limit=limit,
            action_filter=action_filter,
            node_filter=node_filter,
        )
        # 确保返回类型正确
        if isinstance(result, list):
            return result  # type: ignore[return-value]
        return []

    def query_sibling_insights(
        self,
        task_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        查询兄弟节点的洞察

        Args:
            task_id: 任务ID
            limit: 最大结果数量

        Returns:
            兄弟节点洞察列表
        """
        if not self.enable_collective_memory or not self.event_bus:
            return []

        # 检查event_bus是否有query_by_task方法
        if not hasattr(self.event_bus, "query_by_task"):
            return []

        # 查询同一任务下的所有thinking事件
        task_events = self.event_bus.query_by_task(
            task_id,
            action_filter="node.thinking",
        )

        # 过滤掉自己的事件
        sibling_events = [e for e in task_events if e.parameters.get("node_id") != self.node_id]

        # 限制数量
        sibling_events = sibling_events[-limit:]

        # 提取洞察
        insights = []
        for event in sibling_events:
            insights.append(
                {
                    "node_id": event.parameters.get("node_id"),
                    "content": event.parameters.get("content", ""),
                    "timestamp": event.created_at.isoformat() if event.created_at else None,
                }
            )

        return insights

    # ==================== 生命周期钩子 ====================

    async def on_start(self, task: Task) -> None:
        """
        任务开始前的钩子

        Args:
            task: 要执行的任务
        """
        self.state = NodeState.RUNNING
        self.stats["last_execution"] = datetime.now()

        # 发布开始事件
        await self._publish_event(
            action="node.start",
            parameters={
                "action": task.action,
                "parameters": task.parameters,
            },
            task_id=task.task_id,
        )

    async def on_planning(self, task: Task, plan: dict[str, Any]) -> bool:
        """
        规划阶段的钩子（可能需要用户审查）

        Args:
            task: 任务
            plan: 规划内容

        Returns:
            是否继续执行（True=继续，False=中止）
        """
        # 发布规划事件
        await self._publish_event(
            action="node.planning",
            parameters={
                "plan": plan,
            },
            task_id=task.task_id,
        )
        return True

    async def on_tool_call_request(
        self,
        task: Task,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> bool:
        """
        工具调用请求钩子（可能需要用户审查）

        Args:
            task: 任务
            tool_name: 工具名称
            tool_args: 工具参数

        Returns:
            是否允许调用（True=允许，False=拒绝）
        """
        # 发布工具调用请求事件
        await self._publish_event(
            action="node.tool_call_request",
            parameters={
                "tool_name": tool_name,
                "tool_args": tool_args,
            },
            task_id=task.task_id,
        )
        return True

    async def on_delegation_request(
        self,
        task: Task,
        target_agent: str,
        subtask: str,
    ) -> bool:
        """
        委派请求钩子（可能需要用户审查）

        Args:
            task: 任务
            target_agent: 目标agent
            subtask: 子任务描述

        Returns:
            是否允许委派（True=允许，False=拒绝）
        """
        # 发布委派请求事件
        await self._publish_event(
            action="node.delegation_request",
            parameters={
                "target_agent": target_agent,
                "subtask": subtask,
            },
            task_id=task.task_id,
        )
        return True

    async def on_complete(self, task: Task) -> None:
        """
        任务成功完成后的钩子

        Args:
            task: 已完成的任务
        """
        self.state = NodeState.COMPLETED
        self.stats["success_count"] += 1

        # 发布完成事件
        await self._publish_event(
            action="node.complete",
            parameters={
                "result": task.result,
                "status": task.status.value,
            },
            task_id=task.task_id,
        )

    async def on_error(self, task: Task, error: Exception) -> None:
        """
        任务执行出错后的钩子

        Args:
            task: 失败的任务
            error: 错误信息
        """
        self.state = NodeState.FAILED
        self.stats["failure_count"] += 1
        task.error = str(error)

        # 发布错误事件
        await self._publish_event(
            action="node.error",
            parameters={
                "error": str(error),
                "error_type": type(error).__name__,
            },
            task_id=task.task_id,
        )

    # ==================== NodeProtocol 实现 ====================

    async def process(self, _event: Any) -> Any:
        """
        处理事件（默认实现）

        Args:
            _event: 事件对象

        Returns:
            处理结果
        """
        return {"status": "processed", "node_id": self.node_id}

    async def execute_task(self, task: Task) -> Task:
        """
        执行任务（带拦截器支持）

        Args:
            task: 要执行的任务

        Returns:
            更新后的任务
        """
        # 使用拦截器链包装执行
        return await self.interceptor_chain.execute(task, self._execute_task_with_lifecycle)

    async def _execute_task_with_lifecycle(self, task: Task) -> Task:
        """
        执行任务（带生命周期管理）

        Args:
            task: 要执行的任务

        Returns:
            更新后的任务
        """
        start_time = time.time()
        self.stats["execution_count"] += 1

        try:
            # 1. 开始钩子
            await self.on_start(task)

            # 2. 执行任务（子类实现）
            result_task = await self._execute_impl(task)

            # 3. 完成钩子
            await self.on_complete(result_task)

            # 4. 更新统计
            duration = time.time() - start_time
            self.stats["total_duration"] += duration

            return result_task

        except Exception as e:
            # 错误钩子
            await self.on_error(task, e)

            # 更新统计
            duration = time.time() - start_time
            self.stats["total_duration"] += duration

            # 更新任务状态
            task.status = TaskStatus.FAILED
            task.error = str(e)
            return task

    async def _execute_impl(self, task: Task) -> Task:
        """
        任务执行的实际实现

        子类必须覆盖此方法来实现具体的任务执行逻辑。

        Args:
            task: 要执行的任务

        Returns:
            更新后的任务
        """
        # 默认实现：标记为完成
        task.status = TaskStatus.COMPLETED
        task.result = {"message": "Task executed by base node", "node_id": self.node_id}
        return task

    def get_capabilities(self) -> AgentCard:
        """
        获取节点能力声明

        Returns:
            AgentCard对象
        """
        return self.agent_card

    # ==================== 状态管理 ====================

    def get_state(self) -> NodeState:
        """获取当前状态"""
        return self.state

    def reset_state(self) -> None:
        """重置节点状态为空闲"""
        self.state = NodeState.IDLE

    # ==================== 统计信息 ====================

    def get_stats(self) -> dict[str, Any]:
        """
        获取执行统计信息

        Returns:
            统计信息字典
        """
        stats = self.stats.copy()

        # 计算成功率
        if stats["execution_count"] > 0:
            stats["success_rate"] = stats["success_count"] / stats["execution_count"]
        else:
            stats["success_rate"] = 0.0

        # 计算平均耗时
        if stats["execution_count"] > 0:
            stats["avg_duration"] = stats["total_duration"] / stats["execution_count"]
        else:
            stats["avg_duration"] = 0.0

        return stats

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            "execution_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_duration": 0.0,
            "last_execution": None,
        }
