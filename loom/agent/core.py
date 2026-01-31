"""
Agent - 自主智能体基类

位置: loom/agent/core.py

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
from loom.memory.manager import MemoryManager
from loom.memory.orchestrator import ContextOrchestrator
from loom.memory.task_context import (
    MemoryContextSource,
    TaskContextManager,
)
from loom.memory.tokenizer import TiktokenCounter
from loom.agent.base import BaseNode
from loom.protocol import Task, TaskStatus
from loom.providers.llm.interface import LLMProvider
from loom.tools.context_tools import ContextToolExecutor, create_all_context_tools
from loom.tools.done_tool import create_done_tool, execute_done_tool
from loom.tools.tool_creation import (
    DynamicToolExecutor,
    ToolCreationError,
    create_tool_creation_tool,
)

# Optional import for SandboxToolManager
try:
    from loom.tools.sandbox_manager import SandboxToolManager
except ImportError:
    SandboxToolManager = None  # type: ignore


class Agent(BaseNode):
    """
    统一的智能体基类

    继承自BaseNode，集成了观测、记忆、上下文管理等所有基础能力。
    所有自定义智能体都应该继承此类。

    属性：
        llm_provider: LLM提供者
        system_prompt: 系统提示词
        memory: MemoryManager实例（L1-L4分层记忆 + 作用域管理）
        context_orchestrator: ContextOrchestrator（智能上下文编排）
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
        config: Any | None = None,  # AgentConfig（Phase 3: 12.5.2）
        skill_registry: Any | None = None,  # SkillRegistry
        skill_activator: Any | None = None,  # SkillActivator（Phase 2）
        tool_registry: Any | None = None,  # ToolRegistry
        sandbox_manager: "SandboxToolManager | None" = None,  # 沙盒工具管理器（NEW）
        parent_memory: "MemoryManager | None" = None,  # 父节点的 MemoryManager
        root_context_id: str | None = None,
        memory_config: dict[str, Any] | None = None,
        context_budget_config: dict[str, float | int] | None = None,
        knowledge_base: Any | None = None,  # KnowledgeBaseProvider
        knowledge_max_items: int = 3,  # 知识库查询最大条目数
        knowledge_relevance_threshold: float = 0.7,  # 知识相关度阈值
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
            skill_activator: Skill激活器（可选，Phase 2 三种激活形态）
            tool_registry: 工具注册表（可选，用于执行工具调用）
            sandbox_manager: 沙盒工具管理器（可选，用于统一管理工具和自动沙盒化）
            memory_config: 记忆系统配置（可选，默认使用标准配置）
            context_budget_config: 上下文预算配置（可选，动态调整比例）
            knowledge_base: 知识库提供者（可选，用于智能RAG）
            knowledge_max_items: 知识库查询返回的最大条目数（默认3）
            knowledge_relevance_threshold: 知识相关度阈值，0.0-1.0（默认0.7）
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

        # === Phase 3: 配置体系（12.5.2）===
        from loom.config.agent import AgentConfig

        # 1. 配置（可继承）
        self.config = config or AgentConfig()

        # 2. 共享的 Registry（全局单例）
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry

        # 3. 激活状态（独立，不继承）
        self._active_skills: set[str] = set()

        # 创建 SkillActivator（如果未提供且有 skill_registry）
        if skill_activator is None and skill_registry is not None:
            from loom.skills.activator import SkillActivator
            self.skill_activator = SkillActivator(
                llm_provider=llm_provider,
                tool_registry=tool_registry,
            )
        else:
            self.skill_activator = skill_activator  # Phase 2: Skill激活器

        self.sandbox_manager = sandbox_manager  # NEW: 存储沙盒工具管理器
        self.knowledge_base = knowledge_base  # 知识库提供者（用于智能RAG）
        self.knowledge_max_items = knowledge_max_items  # 知识库查询最大条目数
        self.knowledge_relevance_threshold = knowledge_relevance_threshold  # 知识相关度阈值
        self._root_context_id = root_context_id

        # 递归预算控制
        self._budget_tracker = budget_tracker or BudgetTracker()
        self._recursive_depth = recursive_depth

        # 如果启用 done tool，添加到工具列表
        if self.require_done_tool:
            self.tools.append(create_done_tool())

        # 创建 MemoryManager（整合 LoomMemory + FractalMemory）
        self.memory = MemoryManager(
            node_id=node_id,
            parent=parent_memory,
            event_bus=event_bus,
            **(memory_config or {})
        )

        # 创建上下文工具执行器（如果启用）
        self._context_tool_executor: ContextToolExecutor | None = None
        if self.enable_context_tools and event_bus:
            self._context_tool_executor = ContextToolExecutor(self.memory, event_bus)

        # 创建动态工具执行器（如果启用）
        self._dynamic_tool_executor: DynamicToolExecutor | None = None
        if self.enable_tool_creation:
            # 传递 sandbox_manager，使动态创建的工具自动继承父沙盒
            self._dynamic_tool_executor = DynamicToolExecutor(sandbox_manager=self.sandbox_manager)

        # 创建 ContextOrchestrator（替代 TaskContextManager）
        from loom.memory.task_context import ContextSource

        sources: list[ContextSource] = []
        sources.append(MemoryContextSource(self.memory))
        # 添加作用域记忆上下文源（MemoryManager 提供 LOCAL/SHARED/INHERITED/GLOBAL）
        from loom.memory.task_context import FractalMemoryContextSource

        sources.append(
            FractalMemoryContextSource(
                self.memory,
                include_additional=True,
                max_items=6,
                max_additional=4,
            )
        )

        # 添加知识库上下文源（如果提供）
        if self.knowledge_base:
            from loom.memory.knowledge_context import KnowledgeContextSource

            sources.append(
                KnowledgeContextSource(
                    knowledge_base=self.knowledge_base,
                    memory=self.memory,
                    max_items=self.knowledge_max_items,
                    relevance_threshold=self.knowledge_relevance_threshold,
                )
            )

        # Note: EventBusContextSource removed in Phase 3 refactoring
        # Context now only queries Memory, which automatically receives Tasks from EventBus

        self.context_orchestrator = ContextOrchestrator(
            token_counter=TiktokenCounter(model="gpt-4"),
            sources=sources,
            max_tokens=max_context_tokens,
            system_prompt=self.system_prompt,
            budget_config=context_budget_config,
        )

        # 构建完整工具列表（普通工具 + 元工具）
        self.all_tools = self._build_tool_list()

        # Ephemeral 消息跟踪（用于大输出工具）
        self._ephemeral_tool_outputs: dict[str, deque] = defaultdict(lambda: deque())

        # EventBus委派处理器已移除（使用统一的 Agent.delegate() 方法）
        # Tier 2 delegation through EventBusDelegationHandler has been removed
        # All delegation now uses Agent.delegate() which internally uses EventBus

        # AgentNode 统一抽象：节点类型
        # BaseNode 已经设置了 self.node_type = "agent"
        # 我们提供 get_node_type() 方法来获取枚举值

    def get_node_type(self) -> "NodeType":
        """
        获取节点类型（AgentNode 统一抽象）

        Returns:
            NodeType.AGENT 表示完整四范式执行
        """
        from .agent_node import NodeType
        return NodeType.AGENT

    def _build_full_system_prompt(
        self, user_prompt: str, skill_instructions: list[str] | None = None
    ) -> str:
        """
        Build complete system prompt (user prompt + skills + framework capabilities)

        Architecture:
        - user_prompt: User's business logic and task-specific instructions
        - skill_instructions: Activated Skill instructions (Form 1 - Phase 2)
        - framework_capabilities: Four-paradigm autonomous capabilities (always added, non-configurable)

        Args:
            user_prompt: User's business logic prompt
            skill_instructions: Optional list of Skill instructions to inject (Form 1)

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

        # Build prompt in layers: user_prompt + skills + framework_capabilities
        parts = []

        if user_prompt:
            parts.append(user_prompt)

        # Inject Skill instructions (Form 1 - Phase 2)
        if skill_instructions:
            skills_section = "\n\n".join(skill_instructions)
            parts.append(skills_section)

        # Framework capabilities are always added (non-configurable)
        parts.append(autonomous_capabilities.strip())

        return "\n\n".join(parts)

    async def _build_skill_context(self) -> str:
        """
        构建 Skill 上下文（用于 Discovery 层 - Phase 3: 12.5.4）

        返回所有启用 Skills 的元数据，让 LLM 知道有哪些 Skills 可用。
        这是 Progressive Disclosure 的第二层：Discovery 层。

        Returns:
            Skill 上下文字符串
        """
        if not self.skill_registry or not self.config.enabled_skills:
            return ""

        lines = ["## Available Skills\n"]

        for skill_id in self.config.enabled_skills:
            try:
                # 获取 Skill 定义
                skill_def = await self.skill_registry.get_skill(skill_id)
                if skill_def:
                    # 添加 Skill 基本信息
                    lines.append(f"- **{skill_def.name}**: {skill_def.description}")

                    # 如果有绑定的工具，显示工具列表
                    if skill_def.required_tools:
                        tools_str = ", ".join(skill_def.required_tools)
                        lines.append(f"  - Required Tools: {tools_str}")
            except Exception:
                # 跳过无法加载的 Skill
                continue

        # 如果没有可用的 Skills，返回空字符串
        if len(lines) == 1:
            return ""

        return "\n".join(lines)

    async def _activate_skills(
        self, task_description: str
    ) -> dict[str, Any]:
        """
        Activate relevant skills for the task (Phase 2 - Three Forms)

        Handles all three Skill activation forms:
        - Form 1 (INJECTION): Inject instructions into system_prompt
        - Form 2 (COMPILATION): Compile scripts to Tools
        - Form 3 (INSTANTIATION): Create SkillAgentNode instances

        Args:
            task_description: Description of the task to find relevant skills

        Returns:
            Dictionary with:
            - injected_instructions: list[str] - Form 1 instructions
            - compiled_tools: list[str] - Form 2 tool names
            - instantiated_nodes: list[SkillAgentNode] - Form 3 nodes
        """
        result = {
            "injected_instructions": [],
            "compiled_tools": [],
            "instantiated_nodes": [],
        }

        # Check if skill_activator is available
        if not self.skill_activator or not self.skill_registry:
            return result

        try:
            # Step 1: Find relevant skills (Progressive Disclosure)
            # Get skill metadata from registry
            skill_metadata = []
            if hasattr(self.skill_registry, "get_all_metadata"):
                skill_metadata = await self.skill_registry.get_all_metadata()

            # Find relevant skills using LLM
            relevant_skill_ids = await self.skill_activator.find_relevant_skills(
                task_description=task_description,
                skill_metadata=skill_metadata,
                max_skills=5,
            )

            # Step 2: Activate each relevant skill
            from loom.skills.models import SkillDefinition

            for skill_id in relevant_skill_ids:
                skill_def = await self.skill_registry.get_skill(skill_id)
                if not skill_def:
                    continue

                # Determine activation mode
                mode = self.skill_activator.determine_activation_mode(skill_def)

                # Activate based on mode
                from loom.skills.models import SkillActivationMode

                if mode == SkillActivationMode.INJECTION:
                    # Form 1: Knowledge injection
                    instructions = self.skill_activator.activate_injection(skill_def)
                    result["injected_instructions"].append(instructions)

                elif mode == SkillActivationMode.COMPILATION:
                    # Form 2: Script compilation
                    if self.sandbox_manager is not None:
                        tool_names = await self.skill_activator.activate_compilation(
                            skill_def, self.sandbox_manager
                        )
                        result["compiled_tools"].extend(tool_names)

                elif mode == SkillActivationMode.INSTANTIATION:
                    # Form 3: Instantiation as SkillAgentNode
                    skill_node = self.skill_activator.activate_instantiation(
                        skill_def, self.event_bus
                    )
                    result["instantiated_nodes"].append(skill_node)

        except Exception as e:
            # Log error but don't fail - skills are optional enhancement
            print(f"Error activating skills: {e}")

        return result

    async def _activate_skill(self, skill_id: str) -> dict[str, Any]:
        """
        激活单个 Skill 并验证依赖（Phase 3: 12.5.5）

        流程：
        1. 检查 skill 是否在 enabled_skills 中
        2. 检查是否已激活（避免重复）
        3. 验证绑定的 tools 是否可用
        4. 激活 Skill（三种形态）
        5. 记录激活状态

        Args:
            skill_id: Skill ID

        Returns:
            激活结果字典：
            {
                "success": bool,
                "already_active": bool,
                "mode": SkillActivationMode,
                "content": str,  # Form 1
                "tool_names": list[str],  # Form 2
                "node": SkillAgentNode,  # Form 3
                "error": str,
            }
        """
        # 1. 检查是否启用
        if skill_id not in self.config.enabled_skills:
            return {
                "success": False,
                "error": f"Skill '{skill_id}' not in enabled_skills",
            }

        # 2. 检查是否已激活
        if skill_id in self._active_skills:
            return {
                "success": True,
                "already_active": True,
            }

        # 3. 使用 SkillActivator 验证并激活
        if not self.skill_activator or not self.skill_registry:
            return {
                "success": False,
                "error": "SkillActivator or SkillRegistry not initialized",
            }

        try:
            # 获取 Skill 定义
            skill_def = await self.skill_registry.get_skill(skill_id)
            if not skill_def:
                return {
                    "success": False,
                    "error": f"Skill '{skill_id}' not found in registry",
                }

            # 激活（带依赖验证）
            from loom.skills.models import ActivationResult

            result: ActivationResult = await self.skill_activator.activate(
                skill=skill_def,
                tool_manager=self.sandbox_manager,
                event_bus=self.event_bus,
            )

            # 4. 记录激活状态
            if result.success:
                self._active_skills.add(skill_id)

            # 5. 转换为字典返回
            return {
                "success": result.success,
                "mode": result.mode,
                "content": result.content,
                "tool_names": result.tool_names,
                "node": result.node,
                "error": result.error,
                "missing_tools": result.missing_tools,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _get_available_tools(self) -> list[dict[str, Any]]:
        """
        获取当前可用的工具列表（动态 - Phase 3: 12.5.6）

        来源：
        1. 基础工具（self.tools）
        2. 已激活 Skills 绑定的工具（通过 sandbox_manager）
        3. 额外配置的工具（config.extra_tools）

        排除：
        - config.disabled_tools 中的工具

        Returns:
            工具定义列表（LLM 格式）
        """
        available = []
        tool_names_seen = set()

        # 1. 基础工具
        for tool in self.tools:
            # Skip non-dictionary tools (e.g., raw functions from old tests)
            if not isinstance(tool, dict):
                continue
            tool_name = tool.get("function", {}).get("name")
            if tool_name and tool_name not in tool_names_seen:
                available.append(tool)
                tool_names_seen.add(tool_name)

        # 2. 已激活 Skills 绑定的工具
        # 注意：Skills 的工具已经通过 sandbox_manager 注册，会在后面统一添加

        # 3. 额外配置的工具（从 tool_registry）
        if self.tool_registry and self.config.extra_tools:
            for tool_name in self.config.extra_tools:
                if tool_name not in tool_names_seen:
                    tool_def = self.tool_registry.get_definition(tool_name)
                    if tool_def:
                        # 转换为 LLM 格式
                        available.append({
                            "type": "function",
                            "function": {
                                "name": tool_def.name,
                                "description": tool_def.description,
                                "parameters": tool_def.input_schema,
                            },
                        })
                        tool_names_seen.add(tool_name)

        # 4. 过滤禁用的工具
        if self.config.disabled_tools:
            available = [
                tool for tool in available
                if isinstance(tool, dict) and tool.get("function", {}).get("name") not in self.config.disabled_tools
            ]

        return available

    def _build_tool_list(self) -> list[dict[str, Any]]:
        """
        构建完整工具列表（普通工具 + 元工具）

        Returns:
            完整的工具列表
        """
        # 使用动态工具列表（基于配置和已激活的 Skills）
        tools = self._get_available_tools()

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
                            "reasoning": {
                                "type": "string",
                                "description": "Why this plan is needed",
                            },
                        },
                        "required": ["goal", "steps"],
                    },
                },
            }
        )

        # 添加分形委派元工具（自动创建子节点）
        from loom.agent.meta_tools import create_delegate_task_tool

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

        # 注意：沙盒工具已经在 _get_available_tools() 中处理，不需要重复添加

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

        # 检查是否在沙盒工具管理器中（NEW）
        if self.sandbox_manager and tool_name in self.sandbox_manager:
            try:
                result = await self.sandbox_manager.execute_tool(tool_name, parsed_args)
                return str(result)
            except Exception as e:
                return f"错误：沙盒工具执行失败 - {str(e)}"

        # 获取工具的可调用对象（从 tool_registry）
        if self.tool_registry is None:
            return f"错误：工具 '{tool_name}' 未找到（工具注册表未初始化）"
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

        # 加载并激活相关的Skills（Progressive Disclosure + Phase 2 三种形态）
        task_content = task.parameters.get("content", "")
        activated_skills = await self._load_relevant_skills(task_content)

        # 提取激活结果
        injected_instructions = activated_skills.get("injected_instructions", [])
        compiled_tools = activated_skills.get("compiled_tools", [])
        instantiated_nodes = activated_skills.get("instantiated_nodes", [])

        # Form 2: 编译的工具已经注册到 SandboxToolManager，会自动可用
        # Form 3: 实例化的节点存储起来，供后续委派使用
        self._active_skill_nodes = instantiated_nodes

        # Agent 循环
        accumulated_messages: list[dict[str, Any]] = []
        final_content = ""

        try:
            for iteration in range(self.max_iterations):
                # 1. 过滤 ephemeral 消息（第一层防护）
                filtered_messages = self._filter_ephemeral_messages(accumulated_messages)

                # 2. 构建优化上下文（第二层防护）
                messages = await self.context_orchestrator.build_context(task)

                # Form 1: 添加Skills指令（知识注入）
                if injected_instructions and iteration == 0:  # 只在第一次迭代添加
                    skill_instructions = "\n\n=== Available Skills ===\n\n"
                    skill_instructions += "\n\n".join(injected_instructions)
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
                            from loom.agent.meta_tools import execute_delegate_task

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

    async def _load_relevant_skills(self, task_description: str) -> dict[str, Any]:
        """
        加载并激活与任务相关的Skills（Phase 2 - 三种形态）

        使用Progressive Disclosure + LLM智能判断：
        1. 第一阶段：获取所有Skills的元数据（name + description）
        2. 使用LLM判断哪些Skills相关
        3. 第三阶段：激活相关Skills（三种形态）

        Args:
            task_description: 任务描述

        Returns:
            激活结果字典：
            {
                "injected_instructions": list[str],  # Form 1
                "compiled_tools": list[str],         # Form 2
                "instantiated_nodes": list[Any],     # Form 3
            }
        """
        # 如果没有 skill_activator，返回空结果
        if not self.skill_activator:
            return {
                "injected_instructions": [],
                "compiled_tools": [],
                "instantiated_nodes": [],
            }

        # 调用 Phase 2 实现的 _activate_skills() 方法
        # 它会处理所有三种形态的激活
        return await self._activate_skills(task_description)

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

        # Tier 2: 检查激活的 Skill 节点（Form 3 - Phase 3）
        # 如果目标不在 available_agents 中，检查是否是激活的 SkillAgentNode
        active_skill_nodes = getattr(self, '_active_skill_nodes', [])
        for skill_node in active_skill_nodes:
            # 匹配 node_id 或 skill_id
            node_id = getattr(skill_node, 'node_id', None)
            skill_id = getattr(skill_node, 'skill_id', None)

            if node_id == target_agent_id or skill_id == target_agent_id:
                # 找到匹配的 SkillAgentNode，创建委派任务
                delegated_task = Task(
                    task_id=f"{parent_task_id}:delegated:{target_agent_id}",
                    source_agent=self.node_id,
                    target_agent=target_agent_id,
                    action="execute",
                    parameters={"content": subtask},
                    parent_task_id=parent_task_id,
                    session_id=session_id,
                )

                # 执行任务
                try:
                    result_task = await skill_node.execute_task(delegated_task)

                    if result_task.status == TaskStatus.COMPLETED:
                        # 提取结果内容
                        if isinstance(result_task.result, dict):
                            content = result_task.result.get("content", str(result_task.result))
                            return str(content)
                        else:
                            return str(result_task.result)
                    else:
                        return f"Delegation to skill node failed: {result_task.error or 'Unknown error'}"

                except Exception as e:
                    return f"Skill node delegation error: {str(e)}"

        # 找不到目标 agent（既不在 available_agents 也不在 active_skill_nodes）
        return f"Error: Agent '{target_agent_id}' not found in available_agents or active_skill_nodes"

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

        # 将计划写入 MemoryManager 的 SHARED 作用域，让子节点能看到
        from loom.fractal.memory import MemoryScope

        plan_content = f"[Parent Plan] Goal: {goal}\n"
        if reasoning:
            plan_content += f"Reasoning: {reasoning}\n"
        plan_content += f"Steps ({len(steps)}):\n"
        for idx, step in enumerate(steps, 1):
            plan_content += f"  {idx}. {step}\n"

        plan_entry_id = f"plan:{parent_task.task_id}"
        await self.memory.write(plan_entry_id, plan_content, scope=MemoryScope.SHARED)

        # DEBUG: 验证写入成功
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"[DEBUG] Plan written to SHARED: {plan_entry_id}")
        logger.info(f"[DEBUG] Plan content length: {len(plan_content)}")

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

    async def delegate(
        self,
        subtask: str,
        target_node_id: str | None = None,
        **kwargs,
    ) -> Task:
        """
        委派任务给其他节点（AgentNode 统一接口）

        遵循 A2 公理：通过 EventBus 发布任务，不直接调用子节点。

        Args:
            subtask: 子任务描述
            target_node_id: 目标节点 ID（None 表示自动选择）
            **kwargs: 额外参数

        Returns:
            委派结果任务

        Note:
            这是 AgentNode 统一接口的方法。
            与 _auto_delegate 不同，此方法通过 EventBus 进行委派。
        """
        from loom.protocol import Task, TaskAction, generate_id

        # 如果没有指定目标，使用现有的 _auto_delegate 逻辑
        if target_node_id is None:
            # 使用现有的直接委派机制（向后兼容）
            from uuid import uuid4

            # 获取当前任务（从执行上下文）
            # 这里我们需要模拟一个 parent_task，但由于此方法可能被直接调用，
            # 我们创建一个临时任务对象
            parent_task = Task(
                task_id=f"{self.node_id}-delegate-{uuid4()}",
                action=TaskAction.EXECUTE,
                parameters={
                    "content": subtask,
                    **kwargs,
                },
                source_agent="user",
                target_agent=self.node_id,
            )

            # 调用现有的 _auto_delegate 方法
            result_str = await self._auto_delegate(
                {"subtask_description": subtask, **kwargs},
                parent_task,
            )

            # 将结果转换为 Task 对象
            result_task = Task(
                task_id=parent_task.task_id + ":result",
                action=TaskAction.EXECUTE,
                parameters={"result": result_str},
                status=TaskStatus.COMPLETED,
                result={"content": result_str},
            )

            return result_task

        # 如果指定了目标，通过 EventBus 发布任务
        if not self.event_bus:
            raise RuntimeError("Cannot delegate: no event_bus available")

        # 创建委派任务
        delegation_task = Task(
            task_id=generate_id(),
            source_agent=self.node_id,
            target_agent=target_node_id,
            action=TaskAction.EXECUTE,
            parameters={"task": subtask, **kwargs},
            parent_task_id=getattr(self, "_current_task_id", None),
            session_id=getattr(self, "_session_id", None),
        )

        # 通过 EventBus 发布（遵循 A2 公理）
        result = await self.event_bus.publish(delegation_task, wait_result=True)

        return result

    async def _auto_delegate(
        self,
        args: dict[str, Any],
        parent_task: Task,
    ) -> str:
        """
        自动委派实现（框架内部）

        整合点：
        - 使用 MemoryManager 父子关系（parent_memory）
        - 使用 SmartAllocationStrategy 分配记忆
        - 子节点通过 parent_memory 继承上下文

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
        # === Phase 3: 配置继承参数（12.5.3）===
        add_skills: set[str] | None = None,
        remove_skills: set[str] | None = None,
        add_tools: set[str] | None = None,
        remove_tools: set[str] | None = None,
    ) -> "Agent":
        """
        创建子节点并智能分配上下文

        整合所有组件：
        - MemoryManager（继承父节点 parent_memory）
        - SmartAllocationStrategy（智能分配）
        - AgentConfig（配置继承 - Phase 3）

        继承规则（12.5.3）：
        - 共享：skill_registry, tool_registry, event_bus, sandbox_manager
        - 继承：config (可覆盖)
        - 独立：active_skills, memory（每个节点独立的 MemoryManager）

        Args:
            subtask: 子任务
            context_hints: 上下文提示（记忆ID列表）
            add_skills: 子节点额外启用的 Skills
            remove_skills: 子节点禁用的 Skills
            add_tools: 子节点额外启用的工具
            remove_tools: 子节点禁用的工具

        Returns:
            配置好的子Agent实例

        Raises:
            RuntimeError: 如果超出预算限制
        """
        from loom.fractal.allocation import SmartAllocationStrategy
        from loom.fractal.memory import MemoryScope

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

        # === Phase 3: 配置继承（12.5.3）===
        from loom.config.agent import AgentConfig

        child_config = AgentConfig.inherit(
            parent=self.config,
            add_skills=add_skills,
            remove_skills=remove_skills,
            add_tools=add_tools,
            remove_tools=remove_tools,
        )

        # 1. 为子节点提供上下文（不限制能力，只提供信息）
        child_system_prompt = self.system_prompt
        if subtask.parameters.get("is_plan_step"):
            parent_plan = subtask.parameters.get("parent_plan", "")
            step_index = subtask.parameters.get("step_index", "?")
            total_steps = subtask.parameters.get("total_steps", "?")

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

        # 2. 创建子 Agent（parent_memory=self.memory，子节点拥有独立 MemoryManager）
        child_agent = Agent(
            node_id=subtask.task_id,
            llm_provider=self.llm_provider,
            system_prompt=child_system_prompt,
            tools=self.tools,
            event_bus=self.event_bus,
            max_iterations=self.max_iterations,
            require_done_tool=self.require_done_tool,
            budget_tracker=self._budget_tracker,
            recursive_depth=self._recursive_depth + 1,
            parent_memory=self.memory,
            root_context_id=self._root_context_id,
            skill_registry=self.skill_registry,
            tool_registry=self.tool_registry,
            sandbox_manager=self.sandbox_manager,
            skill_activator=self.skill_activator,
            config=child_config,
        )

        # 3. 使用 SmartAllocationStrategy 分配相关记忆并预暖子节点 INHERITED 缓存
        allocation_strategy = SmartAllocationStrategy(max_inherited_memories=10)
        allocated_memories = await allocation_strategy.allocate(
            parent_memory=self.memory,
            child_task=subtask,
            context_hints=context_hints,
        )
        for entry in allocated_memories.get(MemoryScope.INHERITED, []):
            await child_agent.memory.read(
                entry.id,
                search_scopes=[MemoryScope.SHARED, MemoryScope.GLOBAL, MemoryScope.INHERITED],
            )

        return child_agent

    async def _ensure_shared_task_context(self, task: Task) -> str | None:
        """
        将当前任务内容写入 SHARED 作用域，供子节点继承
        """
        content = task.parameters.get("content", "")
        if not content:
            return None

        entry_id = f"task:{task.task_id}:content"

        from loom.fractal.memory import MemoryScope

        if self._recursive_depth == 0 and task.session_id:
            root_entry_id = f"session:{task.session_id}:goal"
            await self.memory.write(root_entry_id, content, scope=MemoryScope.SHARED)
            self._root_context_id = root_entry_id
            if "root_context_id" not in task.parameters:
                task.parameters["root_context_id"] = root_entry_id

        existing = await self.memory.read(entry_id, search_scopes=[MemoryScope.SHARED])
        if not existing:
            await self.memory.write(entry_id, content, scope=MemoryScope.SHARED)
        return entry_id

    async def _sync_memory_from_child(self, child_agent: "Agent") -> None:
        """
        从子节点同步记忆（双向流动）

        子节点完成任务后，将其SHARED记忆同步回父节点。

        Args:
            child_agent: 子Agent实例
        """
        from loom.fractal.memory import MemoryScope

        # 1. 同步 MemoryManager 的 SHARED 记忆
        child_shared = await child_agent.memory.list_by_scope(MemoryScope.SHARED)
        for entry in child_shared:
            await self.memory.write(entry.id, entry.content, MemoryScope.SHARED)

        # 2. 同步重要任务（L2）到父节点
        child_l2_tasks = child_agent.memory.get_l2_tasks(limit=5)
        for task in child_l2_tasks:
            # 提升重要性，因为这是子节点的重要发现
            task.metadata["importance"] = min(1.0, task.metadata.get("importance", 0.5) + 0.1)
            self.memory.add_task(task)
