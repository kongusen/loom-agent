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

from loom.exceptions import TaskComplete
from loom.fractal.budget import BudgetTracker
from loom.fractal.memory import FractalMemory
from loom.memory.core import LoomMemory
from loom.memory.task_context import (
    MemoryContextSource,
    TaskContextManager,
)
from loom.memory.tokenizer import TiktokenCounter
from loom.orchestration.base_node import BaseNode
from loom.protocol import Task, TaskStatus
from loom.providers.llm.interface import LLMProvider
from loom.tools.context_tools import ContextToolExecutor, create_all_context_tools
from loom.tools.done_tool import create_done_tool, execute_done_tool
from loom.tools.tool_creation import (
    DynamicToolExecutor,
    ToolCreationError,
    create_tool_creation_tool,
)


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
        system_prompt: str = "",  # User's business logic prompt
        tools: list[dict[str, Any]] | None = None,
        available_agents: dict[str, Any] | None = None,
        event_bus: Any | None = None,  # EventBus
        enable_observation: bool = True,
        max_context_tokens: int = 4000,
        max_iterations: int = 10,
        require_done_tool: bool = True,
        enable_context_tools: bool = True,  # 是否启用上下文查询工具
        enable_tool_creation: bool = True,  # 是否启用工具创建能力
        budget_tracker: BudgetTracker | None = None,  # 递归预算跟踪器
        recursive_depth: int = 0,  # 当前递归深度
        skill_registry: Any | None = None,  # SkillRegistry
        tool_registry: Any | None = None,  # ToolRegistry
        fractal_memory: "FractalMemory | None" = None,
        root_context_id: str | None = None,
        memory_config: dict[str, Any] | None = None,
        context_budget_config: dict[str, float | int] | None = None,
        **kwargs,
    ):
        """
        初始化智能体

        Args:
            node_id: 节点ID
            llm_provider: LLM提供者
            system_prompt: User's business logic prompt (framework capabilities added automatically)
            tools: 可用工具列表（普通工具）
            available_agents: 可用的其他agent（用于委派）
            event_bus: 事件总线（可选，用于观测和上下文管理）
            enable_observation: 是否启用观测能力
            max_context_tokens: 最大上下文token数
            max_iterations: 最大迭代次数
            require_done_tool: 是否要求显式调用done工具完成任务
            enable_context_tools: 是否启用上下文查询工具（默认True）
            enable_tool_creation: 是否启用工具创建能力（默认True）
            budget_tracker: 递归预算跟踪器（可选，用于控制递归深度和资源）
            recursive_depth: 当前递归深度（内部使用）
            skill_registry: Skill注册表（可选，用于加载Skills）
            tool_registry: 工具注册表（可选，用于执行工具调用）
            memory_config: 记忆系统配置（可选，默认使用标准配置）
            context_budget_config: 上下文预算配置（可选，动态调整比例）
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

        # Build full system prompt (user prompt + framework capabilities)
        # Framework capabilities are always added automatically (non-configurable)
        self.system_prompt = self._build_full_system_prompt(system_prompt)
        self.tools = tools or []
        self.available_agents = available_agents or {}
        self.max_iterations = max_iterations
        self.require_done_tool = require_done_tool
        self.enable_context_tools = enable_context_tools
        self.enable_tool_creation = enable_tool_creation
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry
        self._root_context_id = root_context_id

        # 递归预算控制
        self._budget_tracker = budget_tracker or BudgetTracker()
        self._recursive_depth = recursive_depth

        # 如果启用 done tool，添加到工具列表
        if self.require_done_tool:
            self.tools.append(create_done_tool())

        # 创建 LoomMemory（使用配置，并连接到 EventBus）
        # Phase 2: Memory 订阅 EventBus，自动接收所有 Task
        self.memory = LoomMemory(node_id=node_id, event_bus=event_bus, **(memory_config or {}))

        # 创建 FractalMemory（用于跨节点上下文共享）
        from loom.fractal.memory import FractalMemory

        self.fractal_memory = (
            fractal_memory
            if fractal_memory is not None
            else FractalMemory(node_id=node_id, parent_memory=None, base_memory=self.memory)
        )

        # 创建上下文工具执行器（如果启用）
        self._context_tool_executor: ContextToolExecutor | None = None
        if self.enable_context_tools and event_bus:
            self._context_tool_executor = ContextToolExecutor(self.memory, event_bus)

        # 创建动态工具执行器（如果启用）
        self._dynamic_tool_executor: DynamicToolExecutor | None = None
        if self.enable_tool_creation:
            self._dynamic_tool_executor = DynamicToolExecutor()

        # 创建 TaskContextManager
        from loom.memory.task_context import ContextSource

        sources: list[ContextSource] = []
        sources.append(MemoryContextSource(self.memory))
        if self.fractal_memory:
            from loom.memory.task_context import FractalMemoryContextSource

            sources.append(
                FractalMemoryContextSource(
                    self.fractal_memory,
                    include_additional=True,
                    max_items=6,
                    max_additional=4,
                )
            )
        # Note: EventBusContextSource removed in Phase 3 refactoring
        # Context now only queries Memory, which automatically receives Tasks from EventBus

        self.context_manager = TaskContextManager(
            token_counter=TiktokenCounter(model="gpt-4"),
            sources=sources,
            max_tokens=max_context_tokens,
            system_prompt=self.system_prompt,
            node_id=self.node_id,
            budget_config=context_budget_config,
        )

        # 构建完整工具列表（普通工具 + 元工具）
        self.all_tools = self._build_tool_list()

        # Ephemeral 消息跟踪（用于大输出工具）
        self._ephemeral_tool_outputs: dict[str, deque] = defaultdict(lambda: deque())

        # EventBus委派处理器（用于异步委派）
        self._delegation_handler = None
        if event_bus and hasattr(event_bus, "query_by_task"):
            from .eventbus_delegation import EventBusDelegationHandler

            self._delegation_handler = EventBusDelegationHandler(event_bus)

    def _build_full_system_prompt(self, user_prompt: str) -> str:
        """
        Build complete system prompt (user prompt + framework capabilities)

        Architecture:
        - user_prompt: User's business logic and task-specific instructions
        - framework_capabilities: Four-paradigm autonomous capabilities (always added, non-configurable)

        Args:
            user_prompt: User's business logic prompt

        Returns:
            Complete system prompt
        """
        autonomous_capabilities = """

<autonomous_agent>
You are an autonomous agent using ReAct (Reasoning + Acting) as your PRIMARY working method.

<primary_method>
  <react>
    Your DEFAULT approach for ALL tasks:
    1. Think: Analyze the task
    2. Act: Use available tools directly
    3. Observe: See results
    4. Repeat until completion

    ALWAYS try ReAct first. Most tasks can be solved with direct tool use.
  </react>
</primary_method>

<secondary_methods>
  <planning tool="create_plan">
    ONLY use when task genuinely requires 5+ INDEPENDENT steps.
    <avoid_when>
      - Task can be solved with sequential tool calls (use ReAct instead)
      - Already executing a plan step
      - Deep recursion depth
    </avoid_when>
  </planning>

  <collaboration tool="delegate_task">
    Use when need specialized expertise beyond your tools.
  </collaboration>

  <context_query>
    Query historical information when needed:
    - query_l1_memory, query_l2_memory, query_events_by_action
  </context_query>
</secondary_methods>

<decision_framework>
  1. DEFAULT: Use ReAct - directly call tools to solve the task
  2. ONLY if task has 5+ truly independent steps: Consider planning
  3. If executing plan step: Use ReAct, avoid re-planning
</decision_framework>

<principles>
- ReAct is your primary method - use tools directly
- Planning is secondary - only for genuinely complex tasks
- Respond in the same language as the user
- Act directly without asking permission
</principles>
</autonomous_agent>
"""

        # Framework capabilities are always added (non-configurable)
        if user_prompt:
            return user_prompt + "\n\n" + autonomous_capabilities
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
                    "description": (
                        "Create execution plan for complex tasks. "
                        "Use when: task requires 3+ independent steps, multi-stage workflows, cross-domain tasks. "
                        "Avoid when: single-step tasks, already executing plan step (avoid nesting), simple operations, deep recursion. "
                        "Final decision is yours based on actual complexity."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal": {"type": "string", "description": "Goal to achieve"},
                            "steps": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of execution steps",
                            },
                            "reasoning": {"type": "string", "description": "Why this plan is needed"},
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

        # 添加上下文查询工具（如果启用）
        if self.enable_context_tools and self._context_tool_executor:
            tools.extend(create_all_context_tools())

        # 添加工具创建元工具（如果启用）
        if self.enable_tool_creation and self._dynamic_tool_executor:
            tools.append(create_tool_creation_tool())
            # 添加已创建的动态工具
            tools.extend(self._dynamic_tool_executor.get_tool_definitions())

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
                parsed_args: dict[str, Any] = json.loads(tool_args)
            except json.JSONDecodeError:
                return f"错误：无法解析工具参数 - {tool_args}"
        elif isinstance(tool_args, dict):
            parsed_args = tool_args
        else:
            parsed_args = {}

        # 检查是否是工具创建调用
        if tool_name == "create_tool" and self._dynamic_tool_executor:
            try:
                result = await self._dynamic_tool_executor.create_tool(
                    tool_name=parsed_args.get("tool_name", ""),
                    description=parsed_args.get("description", ""),
                    parameters=parsed_args.get("parameters", {}),
                    implementation=parsed_args.get("implementation", ""),
                )
                # 重建工具列表以包含新创建的工具
                self.all_tools = self._build_tool_list()
                return result
            except ToolCreationError as e:
                return f"工具创建失败: {str(e)}"
            except Exception as e:
                return f"工具创建错误: {str(e)}"

        # 检查是否是动态创建的工具
        if self._dynamic_tool_executor and tool_name in self._dynamic_tool_executor.created_tools:
            try:
                result = await self._dynamic_tool_executor.execute_tool(tool_name, **parsed_args)
                return str(result)
            except ToolCreationError as e:
                return f"动态工具执行失败: {str(e)}"
            except Exception as e:
                return f"动态工具执行错误: {str(e)}"

        # 检查是否是上下文查询工具
        context_tool_names = {
            "query_l1_memory",
            "query_l2_memory",
            "query_l3_memory",
            "query_l4_memory",
            "query_events_by_action",
            "query_events_by_node",
            "query_events_by_target",
            "query_recent_events",
            "query_thinking_process",
        }
        if tool_name in context_tool_names and self._context_tool_executor:
            try:
                result = await self._context_tool_executor.execute(tool_name, parsed_args)  # type: ignore[assignment]
                return json.dumps(result, ensure_ascii=False, default=str)
            except Exception as e:
                return f"错误：上下文工具执行失败 - {str(e)}"

        # 获取工具的可调用对象
        if self.tool_registry is None:
            return "错误：工具注册表未初始化"
        tool_func = self.tool_registry.get_callable(tool_name)

        if tool_func is None:
            return f"错误：工具 '{tool_name}' 未找到"

        try:
            # 执行工具
            result = await tool_func(**parsed_args)
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

        # 记录任务到分形共享记忆（用于子节点继承上下文）
        await self._ensure_shared_task_context(task)

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
                        content_str = (
                            str(chunk.content) if isinstance(chunk.content, dict) else chunk.content
                        )
                        full_content += content_str
                        await self.publish_thinking(
                            content=content_str,
                            task_id=task.task_id,
                            metadata={"iteration": iteration},
                            session_id=task.session_id,
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
                                tool_calls.append(
                                    {"name": "", "arguments": {}, "content": str(chunk.content)}
                                )

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
                    if isinstance(tool_args, str):
                        import json

                        try:
                            tool_args = json.loads(tool_args)
                        except json.JSONDecodeError:
                            tool_args = {}
                    if not isinstance(tool_args, dict):
                        tool_args = {}

                    # 发布工具调用事件
                    await self.publish_tool_call(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        task_id=task.task_id,
                        session_id=task.session_id,
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
                                target_agent, subtask, task.task_id, session_id=task.session_id
                            )
                        else:
                            # New fractal-based delegation (auto-create child)
                            from loom.orchestration.meta_tools import execute_delegate_task

                            result = await execute_delegate_task(self, tool_args, task)
                    else:
                        # 执行普通工具
                        result = await self._execute_single_tool(tool_name, tool_args)

                    # 发布工具执行结果事件
                    await self.publish_tool_result(
                        tool_name=tool_name,
                        result=result,
                        task_id=task.task_id,
                        session_id=task.session_id,
                    )

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

        except TaskComplete as e:
            # 捕获 TaskComplete 异常，正常结束
            task.status = TaskStatus.COMPLETED
            task.result = {
                "content": e.message,
                "completed_explicitly": True,
            }
            # 自我评估
            await self._self_evaluate(task)
            self.memory.add_task(task)
            # 触发异步记忆升级（L3→L4向量化）
            await self.memory.promote_tasks_async()
            return task

        # 如果循环正常结束（没有调用 done）
        if not final_content:
            tool_outputs = [
                m.get("content", "")
                for m in accumulated_messages
                if m.get("role") == "tool" and m.get("content")
            ]
            if tool_outputs:
                final_content = "\n".join(tool_outputs)

        task.status = TaskStatus.COMPLETED
        task.result = {
            "content": final_content,
            "completed_explicitly": False,
            "iterations": iteration + 1,
        }

        # 自我评估
        await self._self_evaluate(task)

        # 存储完成的任务到记忆
        self.memory.add_task(task)
        # 触发异步记忆升级（L3→L4向量化）
        await self.memory.promote_tasks_async()

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

    # ==================== 自我评估 ====================

    async def _self_evaluate(self, task: Task) -> None:
        """
        自我评估任务执行结果

        Agent完成任务后，用自己的LLM评估结果质量，
        将质量指标附加到task.result中。

        Args:
            task: 已完成的任务
        """
        if not isinstance(task.result, dict):
            return

        task_content = task.parameters.get("content", "")
        result_content = task.result.get("content", "")

        if not task_content or not result_content:
            return

        prompt = f"""请评估以下任务执行结果的质量。

任务：{task_content}

结果：{result_content[:1000]}

请从三个维度评估（0-1分）：
1. confidence: 结果是否准确完整
2. coverage: 是否完整回答任务要求
3. novelty: 提供了多少有价值的信息

返回JSON：{{"confidence": 0.X, "coverage": 0.X, "novelty": 0.X}}"""

        try:
            response = await self.llm_provider.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            # 解析响应
            import json
            import re

            json_match = re.search(r"\{[^}]+\}", response.content)
            if json_match:
                metrics = json.loads(json_match.group())
                task.result["quality_metrics"] = {
                    "confidence": float(metrics.get("confidence", 0.5)),
                    "coverage": float(metrics.get("coverage", 0.5)),
                    "novelty": float(metrics.get("novelty", 0.5)),
                }
        except Exception:
            # 评估失败不影响任务结果
            pass

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
        session_id: str | None = None,
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
                session_id=session_id,
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
                session_id=session_id,
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
            session_id=parent_task.session_id,
        )

        # 将计划写入FractalMemory的SHARED作用域，让子节点能看到
        fractal_memory = getattr(self, "fractal_memory", None)
        if fractal_memory:
            from loom.fractal.memory import MemoryScope

            plan_content = f"[Parent Plan] Goal: {goal}\n"
            if reasoning:
                plan_content += f"Reasoning: {reasoning}\n"
            plan_content += f"Steps ({len(steps)}):\n"
            for idx, step in enumerate(steps, 1):
                plan_content += f"  {idx}. {step}\n"

            plan_entry_id = f"plan:{parent_task.task_id}"
            await fractal_memory.write(plan_entry_id, plan_content, scope=MemoryScope.SHARED)

            # DEBUG: 验证写入成功
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[DEBUG] Plan written to SHARED: {plan_entry_id}")
            logger.info(f"[DEBUG] Plan content length: {len(plan_content)}")
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[DEBUG] No fractal_memory available for task {parent_task.task_id}")

        # 确保父任务上下文可继承
        parent_context_id = await self._ensure_shared_task_context(parent_task)
        root_context_id = parent_task.parameters.get("root_context_id") or self._root_context_id
        context_hints = [cid for cid in [root_context_id, parent_context_id] if cid]

        # 执行每个步骤（分形执行）
        results = []

        # 构建父计划摘要（用于注入子节点）
        parent_plan_summary = f"Goal: {goal}\n"
        if reasoning:
            parent_plan_summary += f"Reasoning: {reasoning}\n"
        parent_plan_summary += f"Steps ({len(steps)}):\n"
        for idx_summary, step_summary in enumerate(steps, 1):
            parent_plan_summary += f"  {idx_summary}. {step_summary}\n"

        for idx, step in enumerate(steps):
            # 创建子任务（标记为计划步骤，并传递父计划）
            subtask = Task(
                task_id=f"{parent_task.task_id}-step-{idx+1}-{uuid4()}",
                action="execute",
                parameters={
                    "content": step,
                    "parent_task_id": parent_task.task_id,
                    "step_index": idx + 1,
                    "total_steps": len(steps),
                    "is_plan_step": True,  # 标记这是一个计划步骤
                    "parent_plan": parent_plan_summary,  # 传递父计划
                    "root_context_id": root_context_id,
                },
                session_id=parent_task.session_id,
            )

            # 创建子节点并执行
            child_node = await self._create_child_node(
                subtask=subtask,
                context_hints=context_hints,
            )

            result = await child_node.execute_task(subtask)

            # 同步记忆
            await self._sync_memory_from_child(child_node)

            # 收集结果
            if result.status == TaskStatus.COMPLETED:
                step_result = (
                    result.result.get("content", str(result.result))
                    if isinstance(result.result, dict)
                    else str(result.result)
                )
                results.append(f"Step {idx+1}: {step_result}")
            else:
                results.append(f"Step {idx+1}: Failed - {result.error or 'Unknown error'}")

        # 聚合结果 - 使用LLM综合生成最终答案
        # 构建步骤执行结果的上下文
        steps_context = "\n".join(results)

        # 获取用户的原始问题
        original_question = parent_task.parameters.get("content", goal)

        # 调用LLM综合生成最终答案
        # 简化语言处理：在提示词中要求使用用户的语言回答
        synthesis_prompt = f"""You have executed a plan to answer the user's question. Now provide a direct, comprehensive answer based on the execution results.

User's Original Question: {original_question}

Plan Execution Results:
{steps_context}

IMPORTANT:
- Provide a DIRECT answer to the user's question
- Do NOT describe the plan or say "I created a plan"
- Synthesize insights from the execution results
- Focus on actionable recommendations and analysis
- Write as if you're directly answering the question, not summarizing a process
- MUST respond in the same language as the user's original question"""

        try:
            synthesis_response = await self.llm_provider.chat(
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=1000,
            )
            final_answer = synthesis_response.content
        except Exception:
            # 如果综合失败，返回步骤摘要作为后备
            final_answer = f"Plan '{goal}' completed with {len(steps)} steps:\n" + steps_context

        # 直接抛出 TaskComplete，让 synthesis 结果成为最终答案
        # 这样避免 LLM 再次处理并生成错误的总结
        raise TaskComplete(message=final_answer)

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

        # 验证必需参数（支持两种参数名）
        subtask_description = args.get("subtask_description") or args.get("subtask")
        if not subtask_description:
            return "Error: subtask_description (or subtask) is required for delegation. Please provide a clear description of the subtask."

        # 1. 创建子任务
        root_context_id = parent_task.parameters.get("root_context_id") or self._root_context_id
        subtask = Task(
            task_id=f"{parent_task.task_id}-child-{uuid4()}",
            action="execute",
            parameters={
                "content": subtask_description,
                "parent_task_id": parent_task.task_id,
                "root_context_id": root_context_id,
            },
            session_id=parent_task.session_id,
        )

        # 2. 创建子节点（使用_create_child_node）
        parent_context_id = await self._ensure_shared_task_context(parent_task)
        context_hints = list(args.get("context_hints", []) or [])
        for cid in (root_context_id, parent_context_id):
            if cid and cid not in context_hints:
                context_hints.append(cid)

        child_node = await self._create_child_node(
            subtask=subtask,
            context_hints=context_hints,
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

        Raises:
            RuntimeError: 如果超出预算限制
        """
        from loom.fractal.allocation import SmartAllocationStrategy
        from loom.fractal.memory import FractalMemory, MemoryScope

        # 0. 预算检查（在创建子节点前强制执行）
        violation = self._budget_tracker.check_can_create_child(
            parent_node_id=self.node_id,
            current_depth=self._recursive_depth,
        )
        if violation:
            raise RuntimeError(f"预算违规: {violation.message}. 建议: {violation.suggestion}")

        # 记录子节点创建和深度
        self._budget_tracker.record_child_created(self.node_id)
        self._budget_tracker.record_depth(self._recursive_depth + 1)

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
                        version=entry.version if hasattr(entry, "version") else 1,
                        created_by=entry.created_by
                        if hasattr(entry, "created_by")
                        else child_memory.node_id,
                        updated_by=entry.updated_by
                        if hasattr(entry, "updated_by")
                        else child_memory.node_id,
                        parent_version=entry.version if hasattr(entry, "version") else None,
                    )
                    child_memory._memory_by_scope[MemoryScope.INHERITED][entry.id] = inherited_entry
            else:
                for entry in entries:
                    await child_memory.write(entry.id, entry.content, scope=scope)

        # 4. 创建TaskContextManager (暂时不使用，保留用于将来扩展)
        # child_context_manager = TaskContextManager(...)

        # 5. 为子节点提供上下文（不限制能力，只提供信息）
        child_system_prompt = self.system_prompt
        if subtask.parameters.get("is_plan_step"):
            parent_plan = subtask.parameters.get("parent_plan", "")
            step_index = subtask.parameters.get('step_index', '?')
            total_steps = subtask.parameters.get('total_steps', '?')

            # 简化的上下文提示：提供信息，不限制能力
            step_context = f"""

<context>
You are executing step {step_index}/{total_steps} of a parent plan.
Parent plan: {parent_plan}
Your task: {subtask.parameters.get('content', '')}

You have full capabilities including planning if genuinely needed.
Prefer ReAct (direct tool use) for most tasks.
</context>
"""
            child_system_prompt = self.system_prompt + step_context

        # 6. 创建子Agent（传递预算跟踪器和递增的深度）
        child_agent = Agent(
            node_id=subtask.task_id,
            llm_provider=self.llm_provider,
            system_prompt=child_system_prompt,
            tools=self.tools,
            event_bus=self.event_bus,
            max_iterations=self.max_iterations,
            require_done_tool=self.require_done_tool,
            budget_tracker=self._budget_tracker,  # 共享预算跟踪器
            recursive_depth=self._recursive_depth + 1,  # 递增深度
            fractal_memory=child_memory,
            root_context_id=self._root_context_id,
        )

        # 6. 设置子Agent的fractal_memory引用
        child_agent.fractal_memory = child_memory  # type: ignore[attr-defined]

        return child_agent

    async def _ensure_shared_task_context(self, task: Task) -> str | None:
        """
        将当前任务内容写入 SHARED 作用域，供子节点继承
        """
        fractal_memory = getattr(self, "fractal_memory", None)
        if not fractal_memory:
            return None

        content = task.parameters.get("content", "")
        if not content:
            return None

        entry_id = f"task:{task.task_id}:content"

        from loom.fractal.memory import MemoryScope

        if self._recursive_depth == 0 and task.session_id:
            root_entry_id = f"session:{task.session_id}:goal"
            await fractal_memory.write(root_entry_id, content, scope=MemoryScope.SHARED)
            self._root_context_id = root_entry_id
            if "root_context_id" not in task.parameters:
                task.parameters["root_context_id"] = root_entry_id

        existing = await fractal_memory.read(entry_id, search_scopes=[MemoryScope.SHARED])
        if not existing:
            await fractal_memory.write(entry_id, content, scope=MemoryScope.SHARED)
        return entry_id

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

        # 1. 同步FractalMemory的SHARED记忆
        child_shared = await child_memory.list_by_scope(MemoryScope.SHARED)
        for entry in child_shared:
            await parent_memory.write(entry.id, entry.content, MemoryScope.SHARED)

        # 2. 同步LoomMemory的重要任务（L2）到父节点
        child_loom_memory = getattr(child_agent, "memory", None)
        if child_loom_memory and self.memory:
            # 获取子节点L2中的重要任务
            child_l2_tasks = child_loom_memory.get_l2_tasks(limit=5)
            for task in child_l2_tasks:
                # 提升重要性，因为这是子节点的重要发现
                task.metadata["importance"] = min(1.0, task.metadata.get("importance", 0.5) + 0.1)
                self.memory.add_task(task)
