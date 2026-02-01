"""
Loom App - FastAPI 风格的应用接口

参考 FastAPI 设计，提供直观、类型安全的 API。

特性：
1. Pydantic 验证 - 使用 Pydantic 模型进行参数验证
2. 类型安全 - 完整的类型注解
3. 依赖注入 - 自动管理组件依赖
4. 简洁 API - 直观易用的接口

.. deprecated:: 0.4.7
    LoomApp 将在 v0.5.0 中移除。请使用 Agent.from_llm() 或 Agent.create() 代替。
"""

import warnings
from typing import TYPE_CHECKING, Any

from loom.api.models import AgentConfig
from loom.events import EventBus
from loom.agent import Agent
from loom.providers.llm.interface import LLMProvider
from loom.runtime import Dispatcher
from loom.tools.registry import ToolRegistry
from loom.skills.skill_registry import SkillRegistry
from loom.skills.activator import SkillActivator

if TYPE_CHECKING:
    from loom.providers.knowledge.base import KnowledgeBaseProvider


class LoomApp:
    """
    Loom 应用主类

    参考 FastAPI 设计，提供类型安全、易用的 API。

    Examples:
        >>> from loom.api import LoomApp
        >>> from loom.providers.llm import OpenAIProvider
        >>>
        >>> # 创建应用
        >>> app = LoomApp()
        >>>
        >>> # 配置 LLM
        >>> llm = OpenAIProvider(api_key="...")
        >>> app.set_llm_provider(llm)
        >>>
        >>> # 创建 Agent（使用 Pydantic 模型）
        >>> config = AgentConfig(
        ...     agent_id="assistant",
        ...     name="AI Assistant",
        ...     capabilities=["tool_use", "reflection"],
        ... )
        >>> agent = app.create_agent(config)
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        dispatcher: Dispatcher | None = None,
    ):
        """
        初始化 Loom 应用

        Args:
            event_bus: 事件总线（可选，默认创建新的）
            dispatcher: 调度器（可选，默认创建新的）

        .. deprecated:: 0.4.7
            LoomApp 将在 v0.5.0 中移除。请使用 Agent.from_llm() 或 Agent.create() 代替。
        """
        warnings.warn(
            "LoomApp is deprecated and will be removed in v0.5.0. "
            "Please use Agent.from_llm() or Agent.create() instead.",
            DeprecationWarning,
            stacklevel=2
        )

        # 创建或使用提供的事件总线
        self.event_bus = event_bus or EventBus()

        # 创建或使用提供的调度器
        self.dispatcher = dispatcher or Dispatcher(self.event_bus)

        # 存储全局配置
        self._llm_provider: LLMProvider | None = None
        self._default_tools: list[dict[str, Any]] = []
        self._agents: dict[str, Agent] = {}
        self._knowledge_base: "KnowledgeBaseProvider | None" = None

        # 创建工具注册表
        self._tool_registry = ToolRegistry()

        # 创建Skill注册表
        self._skill_registry = SkillRegistry()

        # Skill激活器（延迟初始化，需要LLM provider）
        self._skill_activator: SkillActivator | None = None

    def set_llm_provider(self, provider: LLMProvider) -> "LoomApp":
        """
        设置全局 LLM 提供者

        Args:
            provider: LLM 提供者

        Returns:
            self（支持链式调用）
        """
        self._llm_provider = provider

        # 初始化Skill激活器（需要LLM provider）
        self._skill_activator = SkillActivator(
            llm_provider=provider,
            tool_registry=self._tool_registry
        )

        return self

    def set_knowledge_base(self, knowledge_base: "KnowledgeBaseProvider") -> "LoomApp":
        """
        设置全局知识库提供者

        Args:
            knowledge_base: 知识库提供者

        Returns:
            self（支持链式调用）
        """
        self._knowledge_base = knowledge_base
        return self

    def add_tools(self, tools: list[dict[str, Any]]) -> "LoomApp":
        """
        添加全局工具

        Args:
            tools: 工具列表

        Returns:
            self（支持链式调用）
        """
        self._default_tools.extend(tools)
        return self

    def register_tool(self, func: Any, name: str | None = None) -> "LoomApp":
        """
        注册工具实现

        Args:
            func: Python 函数（工具的实际实现）
            name: 工具名称（可选，默认使用函数名）

        Returns:
            self（支持链式调用）
        """
        self._tool_registry.register_function(func, name)
        return self

    def register_skill(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Any,
        source: str = "python",
        **metadata: Any,
    ) -> "LoomApp":
        """
        注册Skill

        Args:
            name: Skill名称
            description: Skill描述
            parameters: 参数定义（OpenAI格式）
            handler: 处理函数
            source: 来源类型（python/mcp/http）
            **metadata: 其他元数据

        Returns:
            self（支持链式调用）
        """
        self._skill_registry.register_skill(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            source=source,
            **metadata,
        )
        return self

    def create_agent(
        self,
        config: AgentConfig,
        llm_provider: LLMProvider | None = None,
        tools: list[dict[str, Any]] | None = None,
        knowledge_base: "KnowledgeBaseProvider | None" = None,
    ) -> Agent:
        """
        创建 Agent（使用 Pydantic 配置）

        Args:
            config: Agent 配置（Pydantic 模型）
            llm_provider: LLM 提供者（可选，默认使用全局配置）
            tools: 工具列表（可选，默认使用全局工具）
            knowledge_base: 知识库提供者（可选，默认使用全局配置）

        Returns:
            创建的 Agent 实例

        Raises:
            ValueError: 如果缺少必需的配置
        """
        # 使用提供的或全局的 LLM provider
        provider = llm_provider or self._llm_provider
        if not provider:
            raise ValueError(
                "LLM provider is required. "
                "Set it globally with set_llm_provider() or pass it to create_agent()"
            )

        # 合并工具列表
        agent_tools = self._default_tools.copy()
        if tools:
            agent_tools.extend(tools)

        # 使用提供的或全局的知识库
        kb = knowledge_base or self._knowledge_base

        # 创建 Agent
        agent = Agent(
            node_id=config.agent_id,
            llm_provider=provider,
            system_prompt=config.system_prompt,
            tools=agent_tools,
            event_bus=self.event_bus,
            enable_observation=config.enable_observation,
            enable_context_tools=config.enable_context_tools,
            enable_tool_creation=config.enable_tool_creation,
            max_context_tokens=config.max_context_tokens,
            max_iterations=config.max_iterations,
            require_done_tool=config.require_done_tool,
            memory_config=config.memory_config.model_dump(),
            context_budget_config=config.context_budget_config,
            knowledge_base=kb,
            knowledge_max_items=config.knowledge_max_items,
            knowledge_relevance_threshold=config.knowledge_relevance_threshold,
            tool_registry=self._tool_registry,
            skill_registry=self._skill_registry,
            skill_activator=self._skill_activator,
        )

        # 存储 Agent
        self._agents[config.agent_id] = agent

        return agent

    def get_agent(self, agent_id: str) -> Agent | None:
        """
        获取已创建的 Agent

        Args:
            agent_id: Agent ID

        Returns:
            Agent 实例，如果不存在则返回 None
        """
        return self._agents.get(agent_id)

    def list_agents(self) -> list[str]:
        """
        列出所有已创建的 Agent ID

        Returns:
            Agent ID 列表
        """
        return list(self._agents.keys())
