"""
Loom App - FastAPI 风格的应用接口

参考 FastAPI 设计，提供直观、类型安全的 API。

特性：
1. Pydantic 验证 - 使用 Pydantic 模型进行参数验证
2. 类型安全 - 完整的类型注解
3. 依赖注入 - 自动管理组件依赖
4. 简洁 API - 直观易用的接口
"""

from typing import Any

from loom.api.models import AgentConfig
from loom.events import EventBus
from loom.orchestration import Agent
from loom.providers.llm.interface import LLMProvider
from loom.runtime import Dispatcher


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
        """
        # 创建或使用提供的事件总线
        self.event_bus = event_bus or EventBus()

        # 创建或使用提供的调度器
        self.dispatcher = dispatcher or Dispatcher(self.event_bus)

        # 存储全局配置
        self._llm_provider: LLMProvider | None = None
        self._default_tools: list[dict[str, Any]] = []
        self._agents: dict[str, Agent] = {}

    def set_llm_provider(self, provider: LLMProvider) -> "LoomApp":
        """
        设置全局 LLM 提供者

        Args:
            provider: LLM 提供者

        Returns:
            self（支持链式调用）
        """
        self._llm_provider = provider
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

    def create_agent(
        self,
        config: AgentConfig,
        llm_provider: LLMProvider | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> Agent:
        """
        创建 Agent（使用 Pydantic 配置）

        Args:
            config: Agent 配置（Pydantic 模型）
            llm_provider: LLM 提供者（可选，默认使用全局配置）
            tools: 工具列表（可选，默认使用全局工具）

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

        # 创建 Agent
        agent = Agent(
            node_id=config.agent_id,
            llm_provider=provider,
            system_prompt=config.system_prompt,
            tools=agent_tools,
            event_bus=self.event_bus,
            enable_observation=config.enable_observation,
            max_context_tokens=config.max_context_tokens,
            max_iterations=config.max_iterations,
            require_done_tool=config.require_done_tool,
            memory_config=config.memory_config.model_dump(),
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
