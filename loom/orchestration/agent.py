"""
Agent - 自主智能体基类

基于公理系统和唯一性原则：
将所有智能体能力统一到一个Agent类中，作为所有智能体的基础。

设计原则：
1. 唯一性 - 每个功能只在一个地方实现
2. 继承BaseNode - 获得观测和集体记忆能力
3. 集成LLM - 支持流式输出
4. 四范式自动能力 - LLM自主决策使用反思、工具、规划、协作能力

基础能力（继承自BaseNode）：
- 生命周期管理
- 事件发布（观测能力）
- 事件查询（集体记忆能力）
- 统计信息

自主能力（公理A6 - 四范式工作公理）：
- 反思能力：持续的思考过程（通过LLM streaming自动体现）
- 工具使用：LLM自动决策调用工具（通过tool calling）
- 规划能力：LLM检测复杂任务自动规划（通过meta-tool）
- 协作能力：LLM检测需要协作自动委派（通过meta-tool）
"""

from collections import defaultdict, deque
from typing import Any

from loom.events.queryable_event_bus import QueryableEventBus
from loom.exceptions import TaskComplete
from loom.memory.core import LoomMemory
from loom.memory.task_context import (
    EventBusContextSource,
    MemoryContextSource,
    TaskContextManager,
)
from loom.memory.tokenizer import TiktokenCounter
from loom.orchestration.base_node import BaseNode
from loom.protocol import Task, TaskStatus
from loom.providers.llm.interface import LLMProvider
from loom.tools.done_tool import create_done_tool, execute_done_tool


class Agent(BaseNode):
    """
    统一的智能体基类

    继承自BaseNode，集成了观测、记忆、上下文管理等所有基础能力。
    所有自定义智能体都应该继承此类。

    属性：
        llm_provider: LLM提供者
        system_prompt: 系统提示词
        memory: LoomMemory实例（L1-L4分层记忆）
        context_manager: TaskContextManager（智能上下文管理）
    """

    def __init__(
        self,
        node_id: str,
        llm_provider: LLMProvider,
        system_prompt: str = "",
        tools: list[dict[str, Any]] | None = None,
        available_agents: dict[str, Any] | None = None,
        event_bus: Any | None = None,  # QueryableEventBus
        enable_observation: bool = True,
        max_context_tokens: int = 4000,
        max_iterations: int = 10,
        require_done_tool: bool = True,
        skill_registry: Any | None = None,  # SkillRegistry
        tool_registry: Any | None = None,  # ToolRegistry
        memory_config: dict[str, Any] | None = None,
        **kwargs,
    ):
        """
        初始化智能体

        Args:
            node_id: 节点ID
            llm_provider: LLM提供者
            system_prompt: 系统提示词
            tools: 可用工具列表（普通工具）
            available_agents: 可用的其他agent（用于委派）
            event_bus: 事件总线（可选，用于观测和上下文管理）
            enable_observation: 是否启用观测能力
            max_context_tokens: 最大上下文token数
            max_iterations: 最大迭代次数
            require_done_tool: 是否要求显式调用done工具完成任务
            skill_registry: Skill注册表（可选，用于加载Skills）
            tool_registry: 工具注册表（可选，用于执行工具调用）
            memory_config: 记忆系统配置（可选，默认使用标准配置）
            **kwargs: 其他参数传递给BaseNode
        """
        super().__init__(
            node_id=node_id,
            node_type="agent",
            event_bus=event_bus,
            enable_observation=enable_observation,
            enable_collective_memory=True,
            **kwargs,
        )

        self.llm_provider = llm_provider
        self.system_prompt = self._build_autonomous_system_prompt(system_prompt)
        self.tools = tools or []
        self.available_agents = available_agents or {}
        self.max_iterations = max_iterations
        self.require_done_tool = require_done_tool
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry

        # 如果启用 done tool，添加到工具列表
        if self.require_done_tool:
            self.tools.append(create_done_tool())

        # 创建 LoomMemory（使用配置）
        self.memory = LoomMemory(node_id=node_id, **(memory_config or {}))

        # 创建 TaskContextManager
        from loom.memory.task_context import ContextSource

        sources: list[ContextSource] = []
        sources.append(MemoryContextSource(self.memory))
        if event_bus and isinstance(event_bus, QueryableEventBus):
            sources.append(EventBusContextSource(event_bus))

        self.context_manager = TaskContextManager(
            token_counter=TiktokenCounter(model="gpt-4"),
            sources=sources,
            max_tokens=max_context_tokens,
            system_prompt=self.system_prompt,
        )

        # 构建完整工具列表（普通工具 + 元工具）
        self.all_tools = self._build_tool_list()

        # Ephemeral 消息跟踪（用于大输出工具）
        self._ephemeral_tool_outputs: dict[str, deque] = defaultdict(lambda: deque())

        # EventBus委派处理器（用于异步委派）
        self._delegation_handler = None
        if event_bus and isinstance(event_bus, QueryableEventBus):
            from .eventbus_delegation import EventBusDelegationHandler

            self._delegation_handler = EventBusDelegationHandler(event_bus)

    def _build_autonomous_system_prompt(self, base_prompt: str) -> str:
        """
        构建自主Agent的系统提示词

        增强基础提示词，告知LLM其自主能力。

        Args:
            base_prompt: 基础系统提示词

        Returns:
            增强后的系统提示词
        """
        autonomous_capabilities = """

=== 你的自主能力（四范式工作模式）===

你是一个自主智能体，具备四种核心能力，可以根据任务自动决策使用：

1. **反思能力（Reflection）**：
   - 这是你最基础的能力，贯穿整个思考过程
   - 持续思考、分析、评估你的方法和结果
   - 无需调用工具，自然地在回复中体现你的思考

2. **工具使用（Tool Use）**：
   - 当需要执行具体操作时，调用可用的工具
   - 根据任务需求自主决定使用哪些工具
   - 可以多次调用工具直到完成任务

3. **规划能力（Planning）**：
   - 当遇到复杂任务时，使用 create_plan 工具制定计划
   - 将大任务分解为可执行的步骤
   - 按计划逐步执行

4. **协作能力（Multi-Agent）**：
   - 当任务超出你的能力范围时，使用 delegate_task 工具委派给其他agent
   - 自主判断何时需要协作
   - 整合多个agent的结果

**工作原则**：
- 始终保持反思，展现你的思考过程
- 根据任务复杂度自主决定使用哪些能力
- 不要询问是否可以使用某个能力，直接使用
- 追求高效完成任务
"""

        if base_prompt:
            return base_prompt + autonomous_capabilities
        else:
            return autonomous_capabilities.strip()

    def _build_tool_list(self) -> list[dict[str, Any]]:
        """
        构建完整工具列表（普通工具 + 元工具）

        Returns:
            完整的工具列表
        """
        tools = self.tools.copy()

        # 添加规划元工具
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "create_plan",
                    "description": "为复杂任务创建执行计划。当任务需要多个步骤或较为复杂时使用此工具。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal": {"type": "string", "description": "要实现的目标"},
                            "steps": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "执行步骤列表",
                            },
                            "reasoning": {"type": "string", "description": "为什么需要这个计划"},
                        },
                        "required": ["goal", "steps"],
                    },
                },
            }
        )

        # 添加分形委派元工具（自动创建子节点）
        from loom.orchestration.meta_tools import create_delegate_task_tool
        tools.append(create_delegate_task_tool())

        # 添加委派元工具（如果有可用的agents）
        if self.available_agents:
            agent_list = ", ".join(self.available_agents.keys())
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "delegate_task",
                        "description": f"将子任务委派给其他专业agent。可用的agents: {agent_list}",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "target_agent": {
                                    "type": "string",
                                    "description": "目标agent的ID",
                                    "enum": list(self.available_agents.keys()),
                                },
                                "subtask": {"type": "string", "description": "要委派的子任务描述"},
                                "reasoning": {
                                    "type": "string",
                                    "description": "为什么需要委派这个任务",
                                },
                            },
                            "required": ["target_agent", "subtask"],
                        },
                    },
                }
            )

        return tools

    async def _execute_single_tool(self, tool_name: str, tool_args: dict | str) -> str:
        """
        执行单个工具

        Args:
            tool_name: 工具名称
            tool_args: 工具参数（可能是dict或JSON字符串）

        Returns:
            工具执行结果
        """
        import json

        # 如果tool_args是字符串，解析为字典
        if isinstance(tool_args, str):
            try:
                tool_args = json.loads(tool_args)
            except json.JSONDecodeError:
                return f"错误：无法解析工具参数 - {tool_args}"

        # 获取工具的可调用对象
        if self.tool_registry is None:
            return "错误：工具注册表未初始化"
        tool_func = self.tool_registry.get_callable(tool_name)

        if tool_func is None:
            return f"错误：工具 '{tool_name}' 未找到"

        try:
            # 执行工具
            result = await tool_func(**tool_args)
            return str(result)
        except Exception as e:
            return f"错误：工具执行失败 - {str(e)}"

    async def _execute_impl(self, task: Task) -> Task:
        """
        执行任务 - Agent 核心循环

        核心理念：Agent is just a for loop

        Args:
            task: 任务

        Returns:
            更新后的任务
        """
        # 存储任务到记忆
        self.memory.add_task(task)

        # 加载相关的Skills（Progressive Disclosure）
        task_content = task.parameters.get("content", "")
        relevant_skills = await self._load_relevant_skills(task_content)

        # Agent 循环
        accumulated_messages: list[dict[str, Any]] = []
        final_content = ""

        try:
            for iteration in range(self.max_iterations):
                # 1. 过滤 ephemeral 消息（第一层防护）
                filtered_messages = self._filter_ephemeral_messages(accumulated_messages)

                # 2. 构建优化上下文（第二层防护）
                messages = await self.context_manager.build_context(task)

                # 添加Skills指令（如果有相关Skills）
                if relevant_skills and iteration == 0:  # 只在第一次迭代添加
                    skill_instructions = "\n\n=== Available Skills ===\n\n"
                    for skill in relevant_skills:
                        skill_instructions += skill.get_full_instructions() + "\n\n"
                    messages.append({"role": "system", "content": skill_instructions})

                # 添加过滤后的累积消息
                if filtered_messages:
                    messages.extend(filtered_messages)

                # 2. 调用 LLM（流式）
                full_content = ""
                tool_calls = []

                async for chunk in self.llm_provider.stream_chat(
                    messages, tools=self.all_tools if self.all_tools else None
                ):
                    if chunk.type == "text":
                        content_str = str(chunk.content) if isinstance(chunk.content, dict) else chunk.content
                        full_content += content_str
                        await self.publish_thinking(
                            content=content_str,
                            task_id=task.task_id,
                            metadata={"iteration": iteration},
                        )

                    elif chunk.type == "tool_call_complete":
                        if isinstance(chunk.content, dict):
                            tool_calls.append(chunk.content)
                        else:
                            # 如果不是dict，尝试解析
                            import json
                            try:
                                tool_calls.append(json.loads(str(chunk.content)))
                            except (json.JSONDecodeError, TypeError):
                                tool_calls.append({"name": "", "arguments": {}, "content": str(chunk.content)})

                    elif chunk.type == "error":
                        await self._publish_event(
                            action="node.error",
                            parameters={"error": chunk.content},
                            task_id=task.task_id,
                        )

                final_content = full_content

                # 3. 检查是否有工具调用
                if not tool_calls:
                    if self.require_done_tool:
                        # 要求 done tool，但 LLM 没有调用
                        # 提醒 LLM 调用 done
                        accumulated_messages.append(
                            {
                                "role": "system",
                                "content": "Please call the 'done' tool when you have completed the task.",
                            }
                        )
                        continue
                    else:
                        # 不要求 done tool，直接结束
                        break

                # 4. 执行工具调用
                for tool_call in tool_calls:
                    if not isinstance(tool_call, dict):
                        continue
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("arguments", {})
                    if not isinstance(tool_args, dict):
                        tool_args = {}

                    # 发布工具调用事件
                    await self.publish_tool_call(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        task_id=task.task_id,
                    )

                    # 检查是否是 done tool
                    if tool_name == "done":
                        # 执行 done tool（会抛出 TaskComplete）
                        await execute_done_tool(tool_args)

                    # 处理元工具
                    if tool_name == "create_plan":
                        result = await self._execute_plan(tool_args, task)
                    elif tool_name == "delegate_task":
                        # Check if this is fractal delegation or named agent delegation
                        if "target_agent" in tool_args:
                            # Old-style delegation to named agent
                            target_agent = tool_args.get("target_agent", "")
                            subtask = tool_args.get("subtask", "")
                            result = await self._execute_delegate_task(
                                target_agent, subtask, task.task_id
                            )
                        else:
                            # New fractal-based delegation (auto-create child)
                            from loom.orchestration.meta_tools import execute_delegate_task
                            result = await execute_delegate_task(self, tool_args, task)
                    else:
                        # 执行普通工具
                        if self.tool_registry:
                            result = await self._execute_single_tool(tool_name, tool_args)
                        else:
                            result = f"错误：未配置工具注册表，无法执行工具 '{tool_name}'"

                    # 累积消息（标记工具名称用于 ephemeral 过滤）
                    accumulated_messages.append(
                        {
                            "role": "assistant",
                            "content": full_content or "",
                        }
                    )
                    accumulated_messages.append(
                        {
                            "role": "tool",
                            "content": result,
                            "tool_call_id": tool_call.get("id", ""),
                            "tool_name": tool_name,  # 标记工具名称
                        }
                    )

                # 5. 自动反思（Reflection范式）
                # 在每次迭代后自动评估输出质量
                if iteration < self.max_iterations - 1 and full_content:
                    # 添加反思提示，让LLM自我评估
                    reflection_prompt = (
                        "Please reflect on your current response:\n"
                        "1. Is the response complete and accurate?\n"
                        "2. Are there any issues or improvements needed?\n"
                        "3. If satisfied, call the 'done' tool. If improvements needed, continue working."
                    )
                    accumulated_messages.append(
                        {
                            "role": "system",
                            "content": reflection_prompt,
                        }
                    )

        except TaskComplete as e:
            # 捕获 TaskComplete 异常，正常结束
            task.status = TaskStatus.COMPLETED
            task.result = {
                "content": e.message,
                "completed_explicitly": True,
            }
            self.memory.add_task(task)
            return task

        # 如果循环正常结束（没有调用 done）
        task.status = TaskStatus.COMPLETED
        task.result = {
            "content": final_content,
            "completed_explicitly": False,
            "iterations": iteration + 1,
        }

        # 存储完成的任务到记忆
        self.memory.add_task(task)

        return task

    # ==================== Ephemeral 消息过滤 ====================

    def _get_tool_ephemeral_count(self, tool_name: str) -> int:
        """
        获取工具的 ephemeral 设置

        Args:
            tool_name: 工具名称

        Returns:
            ephemeral 计数（0 表示不是 ephemeral 工具）
        """
        for tool in self.all_tools:
            if isinstance(tool, dict) and tool.get("function", {}).get("name") == tool_name:
                ephemeral = tool.get("_ephemeral", 0)
                return int(ephemeral) if isinstance(ephemeral, int | float) else 0
        return 0

    def _filter_ephemeral_messages(
        self,
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """
        过滤 ephemeral 消息，只保留最近的

        策略：
        1. 识别每个 ephemeral 工具的输出消息
        2. 只保留最近 N 次输出
        3. 丢弃旧的输出

        Args:
            messages: 消息列表

        Returns:
            过滤后的消息列表
        """
        if not messages:
            return messages

        # 统计每个 ephemeral 工具的出现次数
        tool_counts: dict[str, int] = defaultdict(int)
        filtered = []

        # 反向遍历（从最新到最旧）
        for msg in reversed(messages):
            tool_name = msg.get("tool_name")

            if tool_name:
                # 这是工具输出消息
                ephemeral_count = self._get_tool_ephemeral_count(tool_name)

                if ephemeral_count > 0:
                    # 这是 ephemeral 工具
                    tool_counts[tool_name] += 1

                    if tool_counts[tool_name] <= ephemeral_count:
                        # 在保留范围内
                        filtered.append(msg)
                    # else: 丢弃这条消息
                else:
                    # 普通工具，保留
                    filtered.append(msg)
            else:
                # 非工具消息，保留
                filtered.append(msg)

        # 恢复正序
        filtered.reverse()
        return filtered

    # ==================== 自动能力（内部方法）====================

    async def _load_relevant_skills(self, task_description: str) -> list[Any]:
        """
        加载与任务相关的Skills

        使用Progressive Disclosure + LLM智能判断：
        1. 第一阶段：获取所有Skills的元数据（name + description）
        2. 使用LLM判断哪些Skills相关
        3. 第二阶段：只加载相关Skills的完整定义

        Args:
            task_description: 任务描述

        Returns:
            相关的SkillDefinition列表
        """
        if not self.skill_registry:
            return []

        # 获取所有Skills的元数据
        all_metadata = await self.skill_registry.get_all_metadata()

        if not all_metadata:
            return []

        # 使用LLM智能判断相关性
        from loom.skills.activator import SkillActivator

        activator = SkillActivator(self.llm_provider)
        relevant_skill_ids = await activator.find_relevant_skills(task_description, all_metadata)

        # 加载完整的Skill定义
        relevant_skills = []
        for skill_id in relevant_skill_ids:
            skill = await self.skill_registry.get_skill(skill_id)
            if skill:
                relevant_skills.append(skill)

        return relevant_skills

    async def _execute_delegate_task(
        self,
        target_agent_id: str,
        subtask: str,
        parent_task_id: str,
    ) -> str:
        """
        执行委派任务 - 最小连接机制

        两层机制：
        1. Tier 1（默认）：直接引用 - 通过 available_agents 直接调用
        2. Tier 2（可选）：EventBus 路由 - 通过事件总线解耦

        Args:
            target_agent_id: 目标 agent ID
            subtask: 子任务描述
            parent_task_id: 父任务 ID

        Returns:
            委派结果字符串
        """
        # Tier 1: 直接引用（默认机制）
        if target_agent_id in self.available_agents:
            target_agent = self.available_agents[target_agent_id]

            # 创建委派任务
            delegated_task = Task(
                task_id=f"{parent_task_id}:delegated:{target_agent_id}",
                source_agent=self.node_id,
                target_agent=target_agent_id,
                action="execute",
                parameters={"content": subtask},
                parent_task_id=parent_task_id,
            )

            # 直接调用目标 agent
            try:
                result_task = await target_agent.execute_task(delegated_task)

                if result_task.status == TaskStatus.COMPLETED:
                    # 提取结果内容
                    if isinstance(result_task.result, dict):
                        content = result_task.result.get("content", str(result_task.result))
                        return str(content)
                    else:
                        return str(result_task.result)
                else:
                    return f"Delegation failed: {result_task.error or 'Unknown error'}"

            except Exception as e:
                return f"Delegation error: {str(e)}"

        # Tier 2: EventBus 路由（可选机制）
        elif self._delegation_handler:
            # 使用EventBusDelegationHandler进行异步委派
            result = await self._delegation_handler.delegate_task(
                source_agent_id=self.node_id,
                target_agent_id=target_agent_id,
                subtask=subtask,
                parent_task_id=parent_task_id,
            )
            return result

        # 找不到目标 agent
        else:
            return f"Error: Agent '{target_agent_id}' not found in available_agents"

    async def _execute_plan(
        self,
        plan_args: dict[str, Any],
        parent_task: Task,
    ) -> str:
        """
        执行规划 - 实现Planning范式

        将复杂任务分解为多个子任务，使用分形架构并行/顺序执行

        Args:
            plan_args: 规划参数 {goal, steps, reasoning}
            parent_task: 父任务

        Returns:
            执行结果摘要
        """
        from uuid import uuid4

        goal = plan_args.get("goal", "")
        steps = plan_args.get("steps", [])
        reasoning = plan_args.get("reasoning", "")

        if not steps:
            return "Error: No steps provided in plan"

        # 发布规划事件
        await self._publish_event(
            action="node.planning",
            parameters={
                "goal": goal,
                "steps": steps,
                "reasoning": reasoning,
                "step_count": len(steps),
            },
            task_id=parent_task.task_id,
        )

        # 执行每个步骤（分形执行）
        results = []
        for idx, step in enumerate(steps):
            # 创建子任务
            subtask = Task(
                task_id=f"{parent_task.task_id}-step-{idx+1}-{uuid4()}",
                action="execute",
                parameters={
                    "content": step,
                    "parent_task_id": parent_task.task_id,
                    "step_index": idx + 1,
                    "total_steps": len(steps),
                },
            )

            # 创建子节点并执行
            child_node = await self._create_child_node(
                subtask=subtask,
                context_hints=[],
            )

            result = await child_node.execute_task(subtask)

            # 同步记忆
            await self._sync_memory_from_child(child_node)

            # 收集结果
            if result.status == TaskStatus.COMPLETED:
                step_result = result.result.get("content", str(result.result)) if isinstance(result.result, dict) else str(result.result)
                results.append(f"Step {idx+1}: {step_result}")
            else:
                results.append(f"Step {idx+1}: Failed - {result.error or 'Unknown error'}")

        # 聚合结果
        summary = f"Plan '{goal}' completed with {len(steps)} steps:\n" + "\n".join(results)
        return summary

    async def _auto_delegate(
        self,
        args: dict[str, Any],
        parent_task: Task,
    ) -> str:
        """
        自动委派实现（框架内部）

        整合点：
        - 使用FractalMemory建立父子关系
        - 使用SmartAllocationStrategy分配记忆
        - 使用TaskContextManager构建子节点上下文

        Args:
            args: delegate_task工具参数
            parent_task: 父任务

        Returns:
            子任务执行结果
        """
        from uuid import uuid4

        # 1. 创建子任务
        subtask = Task(
            task_id=f"{parent_task.task_id}-child-{uuid4()}",
            action="execute",
            parameters={
                "content": args["subtask_description"],
                "parent_task_id": parent_task.task_id,
            },
        )

        # 2. 创建子节点（使用_create_child_node）
        child_node = await self._create_child_node(
            subtask=subtask,
            context_hints=args.get("context_hints", []),
        )

        # 3. 执行子任务
        result = await child_node.execute_task(subtask)

        # 4. 同步记忆（双向流动）
        await self._sync_memory_from_child(child_node)

        # 5. 返回结果
        if result.status == TaskStatus.COMPLETED:
            if isinstance(result.result, dict):
                return str(result.result.get("content", str(result.result)))
            else:
                return str(result.result)
        else:
            return f"Delegation failed: {result.error or 'Unknown error'}"

    async def _create_child_node(
        self,
        subtask: Task,
        context_hints: list[str],
    ) -> "Agent":
        """
        创建子节点并智能分配上下文

        整合所有组件：
        - FractalMemory（继承父节点）
        - SmartAllocationStrategy（智能分配）
        - TaskContextManager（上下文构建）

        Args:
            subtask: 子任务
            context_hints: 上下文提示（记忆ID列表）

        Returns:
            配置好的子Agent实例
        """
        from loom.fractal.allocation import SmartAllocationStrategy
        from loom.fractal.memory import FractalMemory, MemoryScope

        # 1. 创建FractalMemory（继承父节点记忆）
        child_memory = FractalMemory(
            node_id=subtask.task_id,
            parent_memory=getattr(self, "fractal_memory", None),  # type: ignore[attr-defined]
            base_memory=LoomMemory(node_id=subtask.task_id),
        )

        # 2. 使用SmartAllocationStrategy分配相关记忆
        allocation_strategy = SmartAllocationStrategy(max_inherited_memories=10)
        allocated_memories = await allocation_strategy.allocate(
            parent_memory=child_memory.parent_memory or child_memory,
            child_task=subtask,
            context_hints=context_hints,
        )

        # 3. 将分配的记忆写入子节点
        # 注意：INHERITED scope是只读的，需要直接缓存而不是通过write方法
        for scope, entries in allocated_memories.items():
            if scope == MemoryScope.INHERITED:
                # 直接缓存到INHERITED scope（不通过write方法，因为它是只读的）
                for entry in entries:
                    from loom.fractal.memory import MemoryEntry
                    inherited_entry = MemoryEntry(
                        id=entry.id,
                        content=entry.content,
                        scope=MemoryScope.INHERITED,
                        version=entry.version if hasattr(entry, 'version') else 1,
                        created_by=entry.created_by if hasattr(entry, 'created_by') else child_memory.node_id,
                        updated_by=entry.updated_by if hasattr(entry, 'updated_by') else child_memory.node_id,
                        parent_version=entry.version if hasattr(entry, 'version') else None,
                    )
                    child_memory._memory_by_scope[MemoryScope.INHERITED][entry.id] = inherited_entry
            else:
                for entry in entries:
                    await child_memory.write(entry.id, entry.content, scope=scope)

        # 4. 创建TaskContextManager (暂时不使用，保留用于将来扩展)
        # child_context_manager = TaskContextManager(...)

        # 5. 创建子Agent
        child_agent = Agent(
            node_id=subtask.task_id,
            llm_provider=self.llm_provider,
            system_prompt=self.system_prompt,
            tools=self.tools,
            event_bus=self.event_bus,
            max_iterations=self.max_iterations,
            require_done_tool=self.require_done_tool,
        )

        # 6. 设置子Agent的fractal_memory引用
        child_agent.fractal_memory = child_memory  # type: ignore[attr-defined]

        return child_agent

    async def _sync_memory_from_child(self, child_agent: "Agent") -> None:
        """
        从子节点同步记忆（双向流动）

        子节点完成任务后，将其SHARED记忆同步回父节点。

        Args:
            child_agent: 子Agent实例
        """
        from loom.fractal.memory import MemoryScope

        # 获取子节点的fractal_memory
        child_memory = getattr(child_agent, "fractal_memory", None)
        if not child_memory:
            return

        # 获取父节点的fractal_memory
        parent_memory = getattr(self, "fractal_memory", None)
        if not parent_memory:
            return

        # 使用MemorySyncManager同步SHARED记忆 (暂时直接写入，不使用sync_manager)
        # sync_manager = MemorySyncManager(parent_memory)

        # 获取子节点的SHARED记忆
        child_shared = await child_memory.list_by_scope(MemoryScope.SHARED)

        # 同步到父节点
        for entry in child_shared:
            await parent_memory.write(entry.id, entry.content, MemoryScope.SHARED)
