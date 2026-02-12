"""
DelegatorMixin - 委派逻辑

处理任务委派、子节点创建、记忆同步等功能。

从 core.py 拆分，遵循单一职责原则。
"""

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from loom.runtime import Task, TaskStatus

if TYPE_CHECKING:
    from .core import Agent


def create_delegate_task_tool() -> dict[str, Any]:
    """
    创建 delegate_task 元工具定义

    允许 Agent 将子任务委派给子节点执行。
    """
    return {
        "type": "function",
        "function": {
            "name": "delegate_task",
            "description": (
                "Delegate a subtask to a specialized child agent. "
                "Use this when a task can be broken down into independent subtasks "
                "or when specialized expertise is needed. "
                "The child agent will have access to relevant context from the parent."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subtask_description": {
                        "type": "string",
                        "description": "Clear description of the subtask to delegate",
                    },
                    "required_capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of capabilities needed",
                    },
                    "context_hints": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Memory IDs that should be passed to the child agent",
                    },
                },
                "required": ["subtask_description"],
            },
        },
    }


class DelegatorMixin:
    """
    委派处理混入类

    提供委派相关的所有功能：
    - 任务委派
    - 子节点创建
    - 记忆同步
    """

    # 类型提示（由 Agent 类提供）
    node_id: str
    llm_provider: Any
    memory: Any
    event_bus: Any
    available_agents: dict[str, Any]
    tools: list[dict[str, Any]]
    system_prompt: str
    max_iterations: int
    require_done_tool: bool
    skill_registry: Any
    tool_registry: Any
    sandbox_manager: Any
    skill_activator: Any
    config: Any
    _root_context_id: str | None
    _recursive_depth: int

    # 方法声明移到 TYPE_CHECKING 块中，避免覆盖 BaseNode 的实际实现
    if TYPE_CHECKING:

        async def _publish_event(
            self,
            action: str,
            parameters: dict[str, Any],
            task_id: str,
            session_id: str | None = None,
        ) -> None: ...

    async def delegate(
        self,
        subtask: str,
        target_node_id: str | None = None,
        **kwargs,
    ) -> Task:
        """
        委派任务给其他节点（AgentNode 统一接口）

        遵循 A2 公理：通过 EventBus 发布任务。
        """
        if target_node_id is None:
            parent_task = Task(
                taskId=f"{self.node_id}-delegate-{uuid4()}",
                action="execute",
                parameters={"content": subtask, **kwargs},
                sourceAgent="user",
                targetAgent=self.node_id,
            )

            result_str = await self._auto_delegate(
                {"subtask_description": subtask, **kwargs},
                parent_task,
            )

            return Task(
                taskId=parent_task.taskId + ":result",
                action="execute",
                parameters={"result": result_str},
                status=TaskStatus.COMPLETED,
                result={"content": result_str},
            )

        if not self.event_bus:
            raise RuntimeError("Cannot delegate: no event_bus available")

        delegation_task = Task(
            taskId=str(uuid4()),
            sourceAgent=self.node_id,
            targetAgent=target_node_id,
            action="execute",
            parameters={"task": subtask, **kwargs},
        )

        from typing import cast

        result = await self.event_bus.publish(delegation_task, wait_result=True)
        return cast(Task, result)

    async def _auto_delegate(
        self,
        args: dict[str, Any],
        parent_task: Task,
    ) -> str:
        """
        自动委派 - 创建子节点执行子任务

        由 delegate_task 元工具调用。
        """
        subtask_description = args.get("subtask_description", "")
        context_hints = args.get("context_hints", [])

        # 准备上下文
        parent_context_id = await self._ensure_shared_task_context(parent_task)
        root_context_id = parent_task.parameters.get("root_context_id") or self._root_context_id
        if root_context_id and root_context_id not in context_hints:
            context_hints = [root_context_id] + list(context_hints)
        if parent_context_id and parent_context_id not in context_hints:
            context_hints.append(parent_context_id)

        # 创建子任务
        subtask = Task(
            taskId=f"{parent_task.taskId}-sub-{uuid4()}",
            action="execute",
            parameters={
                "content": subtask_description,
                "parent_task_id": parent_task.taskId,
                "root_context_id": root_context_id,
            },
            sessionId=parent_task.sessionId,
        )

        # 发布委派开始事件
        await self._publish_event(
            action="delegation.started",
            parameters={
                "subtask_id": subtask.taskId,
                "subtask_description": subtask_description,
                "parent_task_id": parent_task.taskId,
                "context_hints": context_hints,
            },
            task_id=parent_task.taskId,
            session_id=parent_task.sessionId,
        )

        # 创建子节点
        child_node = await self._create_child_node(
            context_hints=context_hints,
        )

        # 执行子任务
        result = await child_node.execute_task(subtask)
        await self._sync_memory_from_child(child_node)

        # 发布委派完成事件
        success = result.status == TaskStatus.COMPLETED
        # 提取子任务的 output 字段（如果有）
        child_output = None
        if success and isinstance(result.result, dict):
            child_output = result.result.get("output")

        await self._publish_event(
            action="delegation.completed",
            parameters={
                "subtask_id": subtask.taskId,
                "success": success,
                "child_node_id": child_node.node_id,
                "error": result.error if not success else None,
                "output": child_output,  # 传递子任务的结构化输出
            },
            task_id=parent_task.taskId,
            session_id=parent_task.sessionId,
        )

        if success:
            return (
                result.result.get("content", str(result.result))
                if isinstance(result.result, dict)
                else str(result.result)
            )
        return f"Subtask failed: {result.error or 'Unknown error'}"

    async def _create_child_node(
        self,
        context_hints: list[str] | None = None,
    ) -> "Agent":
        """
        创建子节点（分形架构）

        子节点继承父节点的：
        - LLM Provider
        - 工具注册表
        - 技能注册表
        - EventBus
        """
        from .core import Agent

        child_node_id = f"{self.node_id}:child:{uuid4().hex[:8]}"

        child = Agent(
            node_id=child_node_id,
            llm_provider=self.llm_provider,
            system_prompt=self.system_prompt,
            tools=self.tools.copy(),
            event_bus=self.event_bus,
            max_iterations=self.max_iterations,
            require_done_tool=self.require_done_tool,
            skill_registry=self.skill_registry,
            tool_registry=self.tool_registry,
            sandbox_manager=self.sandbox_manager,
            skill_activator=self.skill_activator,
            config=self.config,
            parent_memory=self.memory,
        )

        child._root_context_id = self._root_context_id
        child._recursive_depth = self._recursive_depth + 1

        # 加载上下文提示到子节点
        if context_hints:
            for hint_id in context_hints:
                entry = await self.memory.read(hint_id)
                if entry:
                    # 直接写入子节点 memory（新架构不使用 scope）
                    await child.memory.add_context(hint_id, entry.content)

        return child

    async def _ensure_shared_task_context(self, task: Task) -> str | None:
        """确保任务上下文写入记忆"""
        context_id = f"task_context:{task.taskId}"
        content = task.parameters.get("content", "")
        if content:
            await self.memory.add_context(context_id, content)
            return context_id
        return None

    async def _sync_memory_from_child(self, child_agent: "Agent") -> None:
        """从子节点同步重要记忆到父节点（通过 L2 任务）"""
        # 新架构：通过 parent_memory 关系自动继承，无需手动同步
        pass
