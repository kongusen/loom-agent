"""
Crew - 增强的多 Agent 协作系统 (Loom Agent v0.1.7)

核心多智能体协作框架，支持四种协作模式：
- Sequential: 顺序执行（A → B → C）
- Parallel: 并行执行（A + B + C）
- Coordinated: 智能协调分配（v0.1.6增强）
- Routed: 智能路由分配（v0.1.7新增）

v0.1.7 新特性：
- 智能路由系统（Router）
- Agent 能力匹配（AgentCapability）
- 任务分类器（TaskClassifier）
- 多种路由策略（AUTO, RULE_BASED, LLM_BASED等）

v0.1.6 特性：
- 智能任务分解（SmartCoordinator）
- 并行执行（ParallelExecutor）
- 容错机制（ErrorRecovery）
- 上下文管理（ArtifactStore）
- 可观测性（CrewTracer）
- 预设配置（CrewPresets）
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import List, Dict, Optional, Callable, Tuple, Any, Union, AsyncGenerator

from loom.core.base_agent import BaseAgent
from loom.core.message import Message, create_user_message
from loom.interfaces.llm import BaseLLM

# v0.1.6: Import new components
from loom.patterns.coordination import (
    ComplexityAnalyzer,
    SmartCoordinator,
    TaskDecomposition,
)
from loom.patterns.artifact_store import ArtifactStore, SubAgentResult
from loom.patterns.parallel_executor import ParallelExecutor, ParallelConfig
from loom.patterns.error_recovery import ErrorRecovery, RecoveryConfig, CheckpointManager
from loom.patterns.observability import CrewTracer, CrewEvaluator

# v0.1.7: Import Router
from loom.patterns.routing import (
    Router,
    AgentCapability,
    TaskClassifier,
    RoutingStrategy,
)


class Crew(BaseAgent):
    """
    增强的多 Agent 协作系统

    特性：
    - 基于 Pipeline 的高效实现
    - 支持 Message 接口和追溯
    - 四种协作模式：Sequential、Parallel、Coordinated、Routed (v0.1.7)
    - 智能任务分解和调度
    - 智能路由和能力匹配 (v0.1.7)
    - 执行历史管理
    - 灵活的角色配置（工具、记忆、知识库）

    支持两种使用方式：

    1. 简单模式 - 直接传入 Agent：
        crew = Crew(
            agents=[agent1, agent2, agent3],
            mode="sequential"
        )

    2. 灵活模式 - 使用 CrewRole 定义：
        from loom.patterns import CrewRole

        roles = [
            CrewRole(
                name="researcher",
                goal="Research information",
                tools=[search_tool, read_tool],
                memory=InMemoryMemory()
            ),
            CrewRole(
                name="writer",
                goal="Write content"
            )
        ]

        crew = Crew(
            roles=roles,  # 使用 roles 而不是 agents
            mode="sequential",
            llm=OpenAILLM()  # 为所有角色提供默认 LLM
        )
    """

    @classmethod
    def from_config(cls, config: "CrewConfig", agents: List[BaseAgent]) -> "Crew":
        """
        从 CrewConfig 创建 Crew（v0.1.6工厂方法）

        Args:
            config: CrewConfig 配置对象
            agents: Agent 列表

        Returns:
            配置好的 Crew 实例

        Example:
            ```python
            from loom.patterns import CrewPresets

            config = CrewPresets.production_ready(
                agents=[researcher, analyst],
                coordinator=coordinator,
                llm=llm
            )

            crew = Crew.from_config(config, agents=[researcher, analyst])
            result = await crew.run("任务")
            ```
        """
        # Import here to avoid circular dependency
        from loom.patterns.presets import CrewConfig

        # 创建 artifact store
        artifact_store = None
        if config.use_artifact_store:
            artifact_store = ArtifactStore(path=config.artifact_store_path)

        # 创建 checkpoint manager
        checkpoint_manager = None
        if config.use_checkpoint:
            checkpoint_manager = CheckpointManager(
                path=config.checkpoint_path, enabled=True
            )

        # 创建 complexity analyzer 和 smart coordinator
        complexity_analyzer = config.complexity_analyzer
        use_smart_coordinator = config.use_smart_coordinator

        # 创建 Crew
        return cls(
            agents=agents,
            mode=config.mode,
            coordinator=config.coordinator,
            # v0.1.6 参数
            use_smart_coordinator=use_smart_coordinator,
            complexity_analyzer=complexity_analyzer,
            enable_parallel=config.parallelism,
            parallel_config=config.parallel_config,
            artifact_store=artifact_store,
            enable_error_recovery=config.error_recovery,
            recovery_config=config.recovery_config,
            enable_checkpoint=config.use_checkpoint,
            checkpoint_manager=checkpoint_manager,
            enable_tracing=config.tracing,
            name=config.name,
        )

    def __init__(
        self,
        agents: Optional[List[BaseAgent]] = None,
        roles: Optional[List] = None,  # List[CrewRole]
        mode: str = "sequential",
        coordinator: Optional[BaseAgent] = None,
        aggregator: Optional[Callable[[List[str]], str]] = None,
        llm: Optional[BaseLLM] = None,  # 默认 LLM（用于 roles）
        name: Optional[str] = None,
        # v0.1.6: Enhanced coordination
        use_smart_coordinator: bool = False,
        complexity_analyzer: Optional[ComplexityAnalyzer] = None,
        # v0.1.6: Parallel execution
        enable_parallel: bool = False,
        parallel_config: Optional[ParallelConfig] = None,
        # v0.1.6: Context management
        artifact_store: Optional[ArtifactStore] = None,
        # v0.1.6: Error recovery
        enable_error_recovery: bool = False,
        recovery_config: Optional[RecoveryConfig] = None,
        enable_checkpoint: bool = False,
        checkpoint_manager: Optional[CheckpointManager] = None,
        # v0.1.6: Observability
        enable_tracing: bool = False,
        tracer: Optional[CrewTracer] = None,
        evaluator: Optional[CrewEvaluator] = None,
        # v0.1.7: Routing
        router: Optional[Router] = None,
        routing_strategy: RoutingStrategy = RoutingStrategy.AUTO,
        agent_capabilities: Optional[Dict[BaseAgent, AgentCapability]] = None,
        **config
    ):
        """
        初始化 Crew

        Args:
            agents: Agent 列表（简单模式）
            roles: CrewRole 列表（灵活模式）
            mode: 协作模式
                - "sequential": 顺序执行（A → B → C）
                - "parallel": 并行执行（A + B + C）
                - "coordinated": 协调器智能分配
                - "routed": 路由器智能分配 (v0.1.7)
            coordinator: 协调器 Agent（coordinated 模式必需）
            aggregator: 结果聚合函数（parallel 模式可选）
            llm: 默认 LLM（用于从 roles 创建 agents）
            name: Crew 名称

            # v0.1.6 新参数
            use_smart_coordinator: 是否使用智能协调器（coordinated模式）
            complexity_analyzer: 复杂度分析器（配合智能协调器）
            enable_parallel: 是否启用并行执行
            parallel_config: 并行配置
            artifact_store: Artifact存储（用于大型结果）
            enable_error_recovery: 是否启用错误恢复
            recovery_config: 恢复配置
            enable_checkpoint: 是否启用checkpoint
            checkpoint_manager: Checkpoint管理器
            enable_tracing: 是否启用追踪
            tracer: 追踪器
            evaluator: 评估器

            # v0.1.7 新参数
            router: 路由器实例（routed模式使用）
            routing_strategy: 路由策略（如果未提供router，将自动创建）
            agent_capabilities: Agent 能力映射（用于路由决策）
            **config: 其他配置参数
        """
        # 处理 agents 和 roles
        if agents is None and roles is None:
            raise ValueError("Either 'agents' or 'roles' must be provided")

        if agents is not None and roles is not None:
            raise ValueError("Cannot provide both 'agents' and 'roles'")

        # 如果提供了 roles，创建 agents
        if roles is not None:
            if llm is None:
                raise ValueError("'llm' is required when using 'roles'")

            agents = []
            for role in roles:
                agent = role.create_agent(llm=llm)
                agents.append(agent)

        if not agents:
            raise ValueError("Crew requires at least one agent")

        if mode not in ["sequential", "parallel", "coordinated", "routed"]:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be 'sequential', 'parallel', 'coordinated', or 'routed'"
            )

        if mode == "coordinated" and coordinator is None:
            raise ValueError("Coordinated mode requires a coordinator agent")

        if mode == "routed" and router is None and len(agents) < 2:
            raise ValueError("Routed mode requires at least 2 agents or a pre-configured router")

        # 生成默认名称
        if name is None:
            if mode == "sequential":
                agent_names = " -> ".join([a.name for a in agents])
                name = f"Crew[{agent_names}]"
            elif mode == "parallel":
                agent_names = " + ".join([a.name for a in agents])
                name = f"Crew[{agent_names}]"
            elif mode == "routed":
                name = f"Crew[routed, {len(agents)} agents]"
            else:
                name = f"Crew[coordinated, {len(agents)} agents]"

        super().__init__(name=name, **config)

        self.agents = agents
        self.mode = mode
        self.coordinator = coordinator

        # 默认聚合器
        if aggregator is None:
            aggregator = lambda results: "\n\n".join(results)
        self.aggregator = aggregator

        # 执行历史
        self._execution_history: List[Dict[str, Any]] = []

        # ===== v0.1.6: Initialize new components =====

        # Smart Coordinator
        self.use_smart_coordinator = use_smart_coordinator and mode == "coordinated"
        self.complexity_analyzer = complexity_analyzer
        if self.use_smart_coordinator and coordinator:
            self.smart_coordinator = SmartCoordinator(
                base_agent=coordinator,
                complexity_analyzer=complexity_analyzer,
                detect_duplicate_tasks=True,
                auto_scale_agents=True,
            )
        else:
            self.smart_coordinator = None

        # Parallel Executor
        self.enable_parallel = enable_parallel
        self.parallel_config = parallel_config or ParallelConfig()
        if enable_parallel:
            self.parallel_executor = ParallelExecutor(
                config=self.parallel_config,
                artifact_store=artifact_store,
            )
        else:
            self.parallel_executor = None

        # Artifact Store
        self.artifact_store = artifact_store

        # Error Recovery
        self.enable_error_recovery = enable_error_recovery
        self.recovery_config = recovery_config or RecoveryConfig()
        if enable_error_recovery:
            self.error_recovery = ErrorRecovery(
                config=self.recovery_config,
                coordinator=coordinator,
            )
        else:
            self.error_recovery = None

        # Checkpoint
        self.enable_checkpoint = enable_checkpoint
        if enable_checkpoint:
            self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        else:
            self.checkpoint_manager = None

        # Tracing
        self.enable_tracing = enable_tracing
        if enable_tracing:
            self.tracer = tracer or CrewTracer(enabled=True)
        else:
            self.tracer = None

        # Evaluator
        self.evaluator = evaluator

        # ===== v0.1.7: Initialize Router =====
        self.router = router
        self.routing_strategy = routing_strategy

        if mode == "routed":
            if self.router is None:
                # 自动创建路由器
                self.router = Router(
                    strategy=routing_strategy,
                    classifier=TaskClassifier(),
                    llm=coordinator,  # 如果有 coordinator，可用于 LLM_BASED 路由
                )

                # 注册所有 agents
                for agent in self.agents:
                    capability = None
                    if agent_capabilities and agent in agent_capabilities:
                        capability = agent_capabilities[agent]
                    # router 会自动推断能力
                    self.router.register_agent(agent, capability)
        else:
            self.router = None

    async def run(self, input: str) -> str:
        """
        执行任务（字符串接口）

        Args:
            input: 任务描述

        Returns:
            执行结果
        """
        # 记录开始时间
        start_time = time.time()

        if self.mode == "sequential":
            result = await self._sequential_run(input)
        elif self.mode == "parallel":
            result = await self._parallel_run(input)
        elif self.mode == "routed":
            # v0.1.7: Routed 模式
            result = await self._routed_run(input)
        else:
            # Coordinated 模式
            result = await self._coordinated_run(input)

        # 记录执行历史
        self._execution_history.append(
            {
                "task_content": input[:100],  # 记录前100个字符
                "result_preview": result[:100] if result else "",
                "mode": self.mode,
                "duration": time.time() - start_time,
                "timestamp": start_time,
            }
        )

        return result

    async def reply(self, message: Message) -> Message:
        """
        执行任务（Message 接口）

        Args:
            message: 任务消息

        Returns:
            结果消息
        """
        if self.mode == "sequential":
            return await self._sequential_reply(message)
        elif self.mode == "parallel":
            return await self._parallel_reply(message)
        elif self.mode == "routed":
            # v0.1.7: Routed 模式
            return await self._routed_reply(message)
        else:
            # Coordinated 模式
            return await self._coordinated_reply(message)

    async def run_stream(self, input: str) -> AsyncGenerator[str, None]:
        """
        流式执行

        Args:
            input: 任务描述

        Yields:
            文本块
        """
        if self.mode == "sequential":
            # Sequential: 前 N-1 个 agent 正常执行，最后一个流式执行
            current_input = input
            for agent in self.agents[:-1]:
                current_input = await agent.run(current_input)

            # 最后一个 Agent 流式执行
            async for chunk in self.agents[-1].run_stream(current_input):
                yield chunk
        elif self.mode == "parallel":
            # Parallel: 等待所有完成后一次性返回
            results = await asyncio.gather(*[
                agent.run(input) for agent in self.agents
            ])
            aggregated = self.aggregator(list(results))
            yield aggregated
        else:
            # Coordinated: 降级为非流式
            result = await self._coordinated_run(input)
            yield result

    async def execute_with_history(
        self, task: Message
    ) -> Tuple[Message, List[Message]]:
        """
        执行任务并返回完整消息历史

        Args:
            task: 任务消息

        Returns:
            (结果消息, 消息历史列表)
        """
        # 记录开始时间
        start_time = time.time()

        # 执行任务
        result = await self.reply(task)

        # 收集消息历史
        history = self._collect_message_history(task, result)

        # 记录执行
        self._execution_history.append(
            {
                "task_id": task.id,
                "result_id": result.id,
                "mode": self.mode,
                "duration": time.time() - start_time,
                "timestamp": start_time,
            }
        )

        return result, history

    def _collect_message_history(
        self, task: Message, result: Message
    ) -> List[Message]:
        """收集消息历史"""
        from loom.core.message import trace_message_chain

        # 构建消息字典
        messages = {task.id: task, result.id: result}

        # 如果有中间消息，也收集
        current = result
        while current.parent_id:
            if current.parent_id in messages:
                break
            # 这里简化处理，实际可能需要更复杂的追溯
            current = messages.get(current.parent_id, task)

        # 追溯完整链
        return trace_message_chain(result, messages)

    # ===== Sequential Mode Implementation =====

    async def _sequential_run(self, input: str) -> str:
        """顺序执行（字符串接口）"""
        current_input = input
        for agent in self.agents:
            current_input = await agent.run(current_input)
        return current_input

    async def _sequential_reply(self, message: Message) -> Message:
        """顺序执行（Message 接口）"""
        current_msg = message
        for agent in self.agents:
            current_msg = await agent.reply(current_msg)
        return current_msg

    # ===== Parallel Mode Implementation =====

    async def _parallel_run(self, input: str) -> str:
        """并行执行（字符串接口）"""
        # 并行执行所有 Agent
        results = await asyncio.gather(*[
            agent.run(input) for agent in self.agents
        ])
        # 聚合结果
        return self.aggregator(list(results))

    async def _parallel_reply(self, message: Message) -> Message:
        """并行执行（Message 接口）"""
        # 并行执行所有 Agent
        replies = await asyncio.gather(*[
            agent.reply(message) for agent in self.agents
        ])
        # 聚合内容
        combined_content = self.aggregator([r.get_text_content() for r in replies])
        # 创建聚合消息
        return message.reply(combined_content, name=self.name)

    # ===== Coordinated Mode Implementation =====

    async def _coordinated_run(self, input: str) -> str:
        """协调模式执行（字符串接口）"""
        # 转换为 Message
        task_msg = create_user_message(input)
        task_msg.metadata["mode"] = "coordinated"
        task_msg.metadata["crew_name"] = self.name

        # 执行
        result_msg = await self._coordinated_reply(task_msg)

        return result_msg.content

    async def _coordinated_reply(self, message: Message) -> Message:
        """
        协调模式执行（Message 接口）

        v0.1.6 增强：
        - 支持 SmartCoordinator（智能任务分解）
        - 支持 ParallelExecutor（并行执行）
        - 支持 ErrorRecovery（容错）
        - 支持 CrewTracer（追踪）
        """
        # Start tracing
        if self.tracer:
            self.tracer.start()

        # === 步骤1：任务分解 ===
        if self.use_smart_coordinator and self.smart_coordinator:
            # v0.1.6: 使用 SmartCoordinator（智能分解）
            task_decomposition = await self.smart_coordinator.decompose_task(
                task=message.content, available_agents=self.agents
            )

            # Log coordinator decision
            if self.tracer:
                self.tracer.log_coordinator_decision(
                    original_task=message.content,
                    complexity=task_decomposition.complexity,
                    num_subtasks=len(task_decomposition.subtasks),
                    estimated_agents=task_decomposition.estimated_agents,
                    reasoning=task_decomposition.reasoning,
                )

            subtasks = task_decomposition.subtasks
        else:
            # 旧版：使用简单的 coordinator prompt
            decompose_msg = await self._decompose_task_with_coordinator(message)
            subtasks_dict = self._parse_subtasks(decompose_msg.content)

            if not subtasks_dict:
                # 降级：如果分解失败，使用 sequential 模式
                return await self._sequential_reply(message)

            # 转换为 SubTask 对象
            from loom.patterns.coordination import SubTask

            subtasks = [SubTask.from_dict(st) for st in subtasks_dict]

        # === 步骤2：执行子任务 ===
        if self.enable_parallel and self.parallel_executor:
            # v0.1.6: 使用 ParallelExecutor（并行执行 + 错误恢复）
            results = await self.parallel_executor.execute_agents_parallel(
                agents=[self._get_agent_by_name(st.agent) for st in subtasks],
                subtasks=subtasks,
                original_task=message.content,
            )

            # Log executions
            if self.tracer:
                for subtask, result in zip(subtasks, results):
                    self.tracer.log_sub_agent_execution(
                        agent_id=result.agent_id,
                        task_id=result.task_id,
                        task_description=subtask.task,
                        result=result,
                    )

            # Convert SubAgentResult to results dict
            results_dict = {res.task_id: res.summary for res in results if res.success}

        else:
            # 旧版：使用依赖关系执行
            dependencies = self._analyze_dependencies_from_subtasks(subtasks)
            layers = self._build_execution_layers_from_subtasks(subtasks, dependencies)
            results_dict = await self._execute_layers(
                layers, subtasks, message
            )

        # End tracing
        if self.tracer:
            self.tracer.end()

        # === 步骤3：聚合结果 ===
        aggregated = self._aggregate_coordinated_results_v2(results_dict, subtasks)

        # === 步骤4：评估（可选） ===
        if self.evaluator:
            metrics = await self.evaluator.evaluate(
                task=message.content, result=aggregated
            )
            # 将评估结果添加到metadata
            message.metadata["evaluation"] = {
                "overall": metrics.overall,
                "pass": metrics.pass_,
                "feedback": metrics.feedback,
            }

        # 创建结果消息
        return message.reply(aggregated, name=self.name)

    # ===== Routed Mode Implementation (v0.1.7) =====

    async def _routed_run(self, input: str) -> str:
        """
        路由模式执行（字符串接口）

        v0.1.7: 使用 Router 智能路由任务到最合适的 Agent
        """
        # 转换为 Message
        task_msg = create_user_message(input)
        task_msg.metadata["mode"] = "routed"
        task_msg.metadata["crew_name"] = self.name

        # 执行
        result_msg = await self._routed_reply(task_msg)

        return result_msg.content

    async def _routed_reply(self, message: Message) -> Message:
        """
        路由模式执行（Message 接口）

        v0.1.7: 智能路由
        - 分析任务特征
        - 匹配 Agent 能力
        - 选择最合适的 Agent 执行
        - 支持多种路由策略
        """
        if not self.router:
            raise ValueError("Router not initialized for routed mode")

        # Start tracing
        if self.tracer:
            self.tracer.start()

        # === 步骤1：路由任务 ===
        routing_result = await self.router.route(message.content)

        selected_agent = routing_result.agent
        capability = routing_result.capability
        score = routing_result.score
        reason = routing_result.reason

        # Log routing decision
        if self.tracer:
            self.tracer.log_coordinator_decision(
                original_task=message.content,
                complexity=capability.complexity_level.value,
                num_subtasks=1,
                estimated_agents=1,
                reasoning=f"Routed to {selected_agent.name} ({capability.agent_type.value}), score: {score:.2f}, reason: {reason}",
            )

        # === 步骤2：执行任务 ===
        try:
            result_msg = await selected_agent.reply(message)

            # Log execution
            if self.tracer:
                self.tracer.log_sub_agent_execution(
                    agent_id=selected_agent.name,
                    task_id="routed_task",
                    task_description=message.content,
                    result=SubAgentResult(
                        agent_id=selected_agent.name,
                        task_id="routed_task",
                        summary=result_msg.content[:200],
                        full_result=result_msg.content,
                        success=True,
                    ),
                )

            # 添加路由元数据
            result_msg.metadata["routing"] = {
                "selected_agent": selected_agent.name,
                "agent_type": capability.agent_type.value,
                "score": score,
                "reason": reason,
                "strategy": self.routing_strategy.value,
            }

        except Exception as e:
            # 路由失败，记录错误
            if self.tracer:
                self.tracer.end()

            # 如果启用了错误恢复，尝试恢复
            if self.enable_error_recovery and self.error_recovery:
                # TODO: Implement error recovery for routed mode
                pass

            # 否则重新抛出异常
            raise RuntimeError(f"Routed execution failed: {e}") from e

        # End tracing
        if self.tracer:
            self.tracer.end()

        # === 步骤3：评估（可选） ===
        if self.evaluator:
            metrics = await self.evaluator.evaluate(
                task=message.content, result=result_msg.content
            )
            # 将评估结果添加到metadata
            result_msg.metadata["evaluation"] = {
                "overall": metrics.overall,
                "pass": metrics.pass_,
                "feedback": metrics.feedback,
            }

        return result_msg

    def _analyze_dependencies_from_subtasks(
        self, subtasks: List["SubTask"]
    ) -> Dict[str, List[str]]:
        """从 SubTask 列表分析依赖关系"""
        dependencies = {}
        for subtask in subtasks:
            task_id = subtask.id
            depends_on = subtask.depends_on
            dependencies[task_id] = depends_on
        return dependencies

    def _build_execution_layers_from_subtasks(
        self, subtasks: List["SubTask"], dependencies: Dict[str, List[str]]
    ) -> List[List[str]]:
        """从 SubTask 列表构建执行层次"""
        layers = []
        remaining = set(subtask.id for subtask in subtasks)
        completed = set()

        while remaining:
            # 找出当前可以执行的任务（所有依赖都已完成）
            current_layer = []
            for task_id in remaining:
                deps = dependencies.get(task_id, [])
                if all(dep in completed for dep in deps):
                    current_layer.append(task_id)

            if not current_layer:
                # 检测到循环依赖，将剩余任务都放入当前层
                current_layer = list(remaining)

            layers.append(current_layer)
            remaining -= set(current_layer)
            completed.update(current_layer)

        return layers

    def _aggregate_coordinated_results_v2(
        self, results: Dict[str, str], subtasks: List["SubTask"]
    ) -> str:
        """
        聚合协调模式的结果（v0.1.6）

        支持 SubAgentResult 格式
        """
        if self.aggregator and callable(self.aggregator):
            # 使用自定义聚合器
            result_list = [results.get(st.id, "") for st in subtasks]
            return self.aggregator(result_list)

        # 默认聚合：按子任务顺序格式化
        lines = ["## Crew Execution Results\n"]
        for subtask in subtasks:
            task_id = subtask.id
            result = results.get(task_id, "[No result]")
            lines.append(f"### Subtask: {subtask.task[:100]}...")
            lines.append(f"**Agent**: {subtask.agent}")
            lines.append(f"**Result**: {result}")
            lines.append("")

        return "\n".join(lines)

    async def _decompose_task_with_coordinator(
        self, task: Message
    ) -> Message:
        """使用协调器分解任务"""
        # 构建分解提示
        agent_info = "\n".join(
            [f"- {a.name}: {(getattr(a, 'system_prompt', None) or 'General purpose agent')[:100]}" for a in self.agents]
        )

        decompose_prompt = f"""You are a task coordinator for a multi-agent crew.

Available agents:
{agent_info}

Task: {task.content}

Decompose this task into subtasks and assign each to the most appropriate agent.
Consider dependencies between subtasks.

Return ONLY a JSON array (no markdown, no explanation):
[
  {{"id": "task1", "agent": "agent_name", "task": "subtask description", "depends_on": []}},
  {{"id": "task2", "agent": "agent_name", "task": "subtask description", "depends_on": ["task1"]}},
  ...
]

Requirements:
- Each subtask must have a unique id
- Agent name must match one from the available agents
- depends_on should list task ids that must complete first
- If no dependencies, use empty array []
"""

        decompose_task_msg = task.reply(decompose_prompt, role="user")

        # 协调器分析
        return await self.coordinator.reply(decompose_task_msg)

    def _parse_subtasks(self, content: str) -> List[Dict]:
        """解析子任务"""
        try:
            # 尝试提取 JSON（可能被包裹在 markdown 代码块中）
            content = content.strip()

            # 移除 markdown 代码块标记
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])  # 移除首尾的 ```

            # 解析 JSON
            subtasks = json.loads(content)

            if not isinstance(subtasks, list):
                return []

            # 验证每个子任务的结构
            valid_subtasks = []
            for subtask in subtasks:
                if all(key in subtask for key in ["id", "agent", "task"]):
                    if "depends_on" not in subtask:
                        subtask["depends_on"] = []
                    valid_subtasks.append(subtask)

            return valid_subtasks

        except Exception as e:
            # 解析失败
            return []

    def _analyze_dependencies(self, subtasks: List[Dict]) -> Dict[str, List[str]]:
        """分析任务依赖关系"""
        dependencies = {}
        for subtask in subtasks:
            task_id = subtask["id"]
            depends_on = subtask.get("depends_on", [])
            dependencies[task_id] = depends_on
        return dependencies

    def _build_execution_layers(
        self, subtasks: List[Dict], dependencies: Dict[str, List[str]]
    ) -> List[List[str]]:
        """
        构建执行层次（拓扑排序）

        Returns:
            [[task_id, ...], ...] 每层的任务可以并行执行
        """
        layers = []
        remaining = set(subtask["id"] for subtask in subtasks)
        completed = set()

        while remaining:
            # 找出当前可以执行的任务（所有依赖都已完成）
            current_layer = []
            for task_id in remaining:
                deps = dependencies.get(task_id, [])
                if all(dep in completed for dep in deps):
                    current_layer.append(task_id)

            if not current_layer:
                # 检测到循环依赖，将剩余任务都放入当前层
                current_layer = list(remaining)

            layers.append(current_layer)
            remaining -= set(current_layer)
            completed.update(current_layer)

        return layers

    async def _execute_layers(
        self,
        layers: List[List[str]],
        subtasks: Union[List[Dict], List["SubTask"]],
        original_task: Message,
    ) -> Dict[str, str]:
        """
        执行各层任务（混合 Sequential 和 Parallel）

        支持两种格式：
        - List[Dict]: 旧版格式
        - List[SubTask]: v0.1.6 格式
        """
        # 转换为统一格式
        if subtasks and hasattr(subtasks[0], "id"):
            # SubTask 对象
            subtasks_dict = {s.id: s for s in subtasks}
            is_subtask_obj = True
        else:
            # Dict 格式
            subtasks_dict = {s["id"]: s for s in subtasks}
            is_subtask_obj = False

        results = {}

        for layer in layers:
            if len(layer) == 1:
                # 单个任务：直接执行
                task_id = layer[0]
                subtask = subtasks_dict[task_id]

                if is_subtask_obj:
                    agent_name = subtask.agent
                    task_content = subtask.task
                else:
                    agent_name = subtask["agent"]
                    task_content = subtask["task"]

                agent = self._get_agent_by_name(agent_name)

                if agent:
                    # 创建子任务消息
                    subtask_msg = original_task.reply(
                        task_content,
                        role="user",
                        name=f"{self.name}_coordinator",
                    )
                    result_msg = await agent.reply(subtask_msg)
                    results[task_id] = result_msg.content
                else:
                    results[task_id] = f"[Error: Agent '{agent_name}' not found]"

            else:
                # 多个任务：并行执行
                tasks = [subtasks_dict[task_id] for task_id in layer]

                if is_subtask_obj:
                    agents = [self._get_agent_by_name(t.agent) for t in tasks]
                    task_contents = [t.task for t in tasks]
                else:
                    agents = [self._get_agent_by_name(t["agent"]) for t in tasks]
                    task_contents = [t["task"] for t in tasks]

                # 并行执行
                layer_results = await asyncio.gather(
                    *[
                        agent.run(task_content) if agent else f"[Error: Agent not found]"
                        for agent, task_content in zip(agents, task_contents)
                    ]
                )

                for task_id, result in zip(layer, layer_results):
                    results[task_id] = result

        return results

    def _get_agent_by_name(self, name: str) -> Optional[BaseAgent]:
        """根据名称获取 Agent"""
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None

    def _aggregate_coordinated_results(
        self, results: Dict[str, str], subtasks: List[Dict]
    ) -> str:
        """聚合协调模式的结果"""
        if self.aggregator:
            # 使用自定义聚合器
            result_list = [results.get(s["id"], "") for s in subtasks]
            return self.aggregator(result_list)

        # 默认聚合：按子任务顺序格式化
        lines = ["## Crew Execution Results\n"]
        for subtask in subtasks:
            task_id = subtask["id"]
            result = results.get(task_id, "[No result]")
            lines.append(f"### Subtask: {subtask['task']}")
            lines.append(f"**Agent**: {subtask['agent']}")
            lines.append(f"**Result**: {result}")
            lines.append("")

        return "\n".join(lines)

    # ===== Utility Methods =====

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self._execution_history.copy()

    def get_execution_graph(self) -> Dict[str, Any]:
        """
        获取执行图（用于可视化）

        Returns:
            {
                "nodes": [{"id": "agent1", "name": "...", "type": "agent"}, ...],
                "edges": [{"from": "...", "to": "..."}, ...]
            }
        """
        nodes = []
        edges = []

        if self.mode == "sequential":
            # Sequential: 线性图
            for i, agent in enumerate(self.agents):
                nodes.append({"id": agent.name, "name": agent.name, "type": "agent"})
                if i > 0:
                    edges.append(
                        {"from": self.agents[i - 1].name, "to": agent.name}
                    )

        elif self.mode == "parallel":
            # Parallel: 星形图
            nodes.append({"id": "input", "name": "Input", "type": "input"})
            nodes.append({"id": "output", "name": "Output", "type": "output"})

            for agent in self.agents:
                nodes.append({"id": agent.name, "name": agent.name, "type": "agent"})
                edges.append({"from": "input", "to": agent.name})
                edges.append({"from": agent.name, "to": "output"})

        else:  # coordinated
            # Coordinated: 复杂图（需要实际执行后才能确定）
            nodes.append(
                {"id": "coordinator", "name": self.coordinator.name, "type": "coordinator"}
            )
            for agent in self.agents:
                nodes.append({"id": agent.name, "name": agent.name, "type": "agent"})
                edges.append({"from": "coordinator", "to": agent.name})

        return {"nodes": nodes, "edges": edges}

    def __repr__(self) -> str:
        return f"Crew(name={self.name}, mode={self.mode}, agents={len(self.agents)})"


# ===== Convenience Functions =====


def sequential_crew(
    *agents: BaseAgent, name: Optional[str] = None, **config
) -> Crew:
    """
    创建顺序 Crew 的便捷函数

    Example:
        crew = sequential_crew(researcher, writer, reviewer)
        result = await crew.run("任务")
    """
    return Crew(list(agents), mode="sequential", name=name, **config)


def parallel_crew(
    *agents: BaseAgent,
    name: Optional[str] = None,
    aggregator: Optional[Callable] = None,
    **config,
) -> Crew:
    """
    创建并行 Crew 的便捷函数

    Example:
        crew = parallel_crew(analyst1, analyst2, analyst3)
        result = await crew.run("任务")
    """
    return Crew(
        list(agents), mode="parallel", name=name, aggregator=aggregator, **config
    )


def coordinated_crew(
    *agents: BaseAgent,
    coordinator: BaseAgent,
    name: Optional[str] = None,
    aggregator: Optional[Callable] = None,
    # v0.1.6: Enhanced coordination
    use_smart_coordinator: bool = False,
    complexity_analyzer: Optional[ComplexityAnalyzer] = None,
    # v0.1.6: Parallel execution
    enable_parallel: bool = False,
    parallel_config: Optional[ParallelConfig] = None,
    # v0.1.6: Context management
    artifact_store: Optional[ArtifactStore] = None,
    # v0.1.6: Error recovery
    enable_error_recovery: bool = False,
    recovery_config: Optional[RecoveryConfig] = None,
    enable_checkpoint: bool = False,
    checkpoint_manager: Optional[CheckpointManager] = None,
    # v0.1.6: Observability
    enable_tracing: bool = False,
    tracer: Optional[CrewTracer] = None,
    evaluator: Optional[CrewEvaluator] = None,
    **config,
) -> Crew:
    """
    创建协调 Crew 的便捷函数（v0.1.6 增强）

    Args:
        *agents: 工作 agents
        coordinator: 协调器 agent
        name: Crew名称
        aggregator: 自定义结果聚合函数

        # v0.1.6 新增参数
        use_smart_coordinator: 启用智能任务分解（需要提供complexity_analyzer）
        complexity_analyzer: 复杂度分析器
        enable_parallel: 启用并行执行
        parallel_config: 并行配置（如不提供则使用默认配置）
        artifact_store: 上下文存储（用于大文件内容管理）
        enable_error_recovery: 启用错误恢复
        recovery_config: 恢复配置（如不提供则使用默认配置）
        enable_checkpoint: 启用断点续传
        checkpoint_manager: Checkpoint管理器
        enable_tracing: 启用执行追踪
        tracer: 自定义追踪器
        evaluator: 质量评估器

    Example (基础用法):
        crew = coordinated_crew(
            specialist1, specialist2, specialist3,
            coordinator=coordinator_agent
        )
        result = await crew.run("复杂任务")

    Example (v0.1.6 完整功能):
        from loom.patterns import (
            ComplexityAnalyzer, ParallelConfig,
            ArtifactStore, RecoveryConfig, CrewTracer
        )

        crew = coordinated_crew(
            researcher1, researcher2, analyst,
            coordinator=coordinator_agent,
            # 启用智能协调
            use_smart_coordinator=True,
            complexity_analyzer=ComplexityAnalyzer(llm=llm),
            # 启用并行执行
            enable_parallel=True,
            parallel_config=ParallelConfig(max_parallel_agents=5),
            # 启用上下文管理
            artifact_store=ArtifactStore(path="./artifacts"),
            # 启用错误恢复
            enable_error_recovery=True,
            recovery_config=RecoveryConfig(max_retries=3),
            # 启用追踪
            enable_tracing=True,
        )
        result = await crew.run("分析全球AI芯片市场")
    """
    return Crew(
        list(agents),
        mode="coordinated",
        coordinator=coordinator,
        name=name,
        aggregator=aggregator,
        # v0.1.6 参数
        use_smart_coordinator=use_smart_coordinator,
        complexity_analyzer=complexity_analyzer,
        enable_parallel=enable_parallel,
        parallel_config=parallel_config,
        artifact_store=artifact_store,
        enable_error_recovery=enable_error_recovery,
        recovery_config=recovery_config,
        enable_checkpoint=enable_checkpoint,
        checkpoint_manager=checkpoint_manager,
        enable_tracing=enable_tracing,
        tracer=tracer,
        evaluator=evaluator,
        **config,
    )
