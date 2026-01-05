"""
Loom Agent Builder - 流式构建接口

提供链式调用的 Builder 模式，支持细粒度配置。
"""

from typing import Optional, List, Dict, Any
from loom.node.agent import AgentNode
from loom.node.tool import ToolNode
from loom.llm import LLMProvider
from loom.kernel.core import Dispatcher, UniversalEventBus

# Interceptors
from loom.kernel.control import (
    BudgetInterceptor,
    DepthInterceptor,
    TimeoutInterceptor,
    HITLInterceptor,
    TracingInterceptor,
    AuthInterceptor,
)

# 配置类
from loom.config.models import AgentConfig as AgentMetaConfig
from loom.config.fractal import FractalConfig
from loom.config.execution import ExecutionConfig
from loom.config.router import RouterConfig
from loom.config.memory import ContextConfig, CurationConfig
from loom.config.interceptor import InterceptorConfig
from loom.config.optimization import OptimizationConfig


class LoomBuilder:
    """
    Loom Agent Builder

    提供流式的链式调用接口，支持细粒度配置。

    Example:
        >>> agent = (Loom.builder()
        ...     .with_id("my-agent")
        ...     .with_llm(provider)
        ...     .with_tools([tool1, tool2])
        ...     .with_fractal(enabled=True, max_depth=3)
        ...     .build())
    """

    def __init__(self):
        """初始化 Builder"""
        self._node_id: Optional[str] = None
        self._llm: Optional[LLMProvider] = None
        self._tools: List[ToolNode] = []
        self._dispatcher: Optional[Dispatcher] = None

        # 配置对象
        self._agent_config: Optional[AgentMetaConfig] = None
        self._fractal_config: Optional[FractalConfig] = None
        self._router_config: Optional[RouterConfig] = None
        self._execution_config: Optional[ExecutionConfig] = None
        self._memory_config: Optional[ContextConfig] = None
        self._interceptor_config: Optional[InterceptorConfig] = None
        self._optimization_config: Optional[OptimizationConfig] = None

        # 其他参数
        self._extra_params: Dict[str, Any] = {}

    def with_id(self, node_id: str) -> 'LoomBuilder':
        """
        设置 Agent ID

        Args:
            node_id: Agent 唯一标识

        Returns:
            self（支持链式调用）
        """
        self._node_id = node_id
        return self

    def with_llm(self, provider: LLMProvider) -> 'LoomBuilder':
        """
        设置 LLM Provider

        Args:
            provider: LLM Provider 实例

        Returns:
            self（支持链式调用）
        """
        self._llm = provider
        return self

    def with_tools(self, tools: List[ToolNode]) -> 'LoomBuilder':
        """
        设置工具列表

        Args:
            tools: 工具列表

        Returns:
            self（支持链式调用）
        """
        self._tools = tools
        return self

    def with_dispatcher(self, dispatcher: Dispatcher) -> 'LoomBuilder':
        """
        设置 Dispatcher（消息总线）

        Args:
            dispatcher: Dispatcher 实例

        Returns:
            self（支持链式调用）
        """
        self._dispatcher = dispatcher
        return self

    def with_agent(
        self,
        role: str = "Assistant",
        system_prompt: str = "You are a helpful assistant."
    ) -> 'LoomBuilder':
        """
        配置 Agent 基本信息

        Args:
            role: Agent 角色
            system_prompt: 系统提示词

        Returns:
            self（支持链式调用）
        """
        self._agent_config = AgentMetaConfig(
            role=role,
            system_prompt=system_prompt
        )
        return self

    def with_memory(
        self,
        max_tokens: int = 8000,
        strategy: str = "system2"
    ) -> 'LoomBuilder':
        """
        配置 Memory 系统

        Args:
            max_tokens: 最大 token 数
            strategy: 策略 (system1|system2)

        Returns:
            self（支持链式调用）
        """
        self._memory_config = ContextConfig(
            strategy=strategy,
            curation_config=CurationConfig(max_tokens=max_tokens)
        )
        return self

    def with_fractal(
        self,
        enabled: bool = True,
        max_depth: int = 3,
        enable_explicit_delegation: bool = True,
        synthesis_model: str = "lightweight",
        **kwargs
    ) -> 'LoomBuilder':
        """
        配置分型能力

        Args:
            enabled: 是否启用分型
            max_depth: 最大深度
            enable_explicit_delegation: 是否启用显式委托
            synthesis_model: 合成模型策略
            **kwargs: 其他 FractalConfig 参数

        Returns:
            self（支持链式调用）
        """
        self._fractal_config = FractalConfig(
            enabled=enabled,
            max_depth=max_depth,
            enable_explicit_delegation=enable_explicit_delegation,
            synthesis_model=synthesis_model,
            **kwargs
        )
        return self

    def with_system12_routing(
        self,
        complexity_threshold: float = 0.7,
        confidence_threshold: float = 0.6,
        **kwargs
    ) -> 'LoomBuilder':
        """
        配置 System 1/2 路由

        Args:
            complexity_threshold: 复杂度阈值
            confidence_threshold: 信心阈值
            **kwargs: 其他 RouterConfig 参数

        Returns:
            self（支持链式调用）
        """
        self._router_config = RouterConfig(
            complexity_threshold=complexity_threshold,
            confidence_threshold=confidence_threshold,
            **kwargs
        )
        return self

    def with_execution(
        self,
        parallel_execution: bool = True,
        max_concurrent: int = 5,
        **kwargs
    ) -> 'LoomBuilder':
        """
        配置执行引擎

        Args:
            parallel_execution: 是否并行执行
            max_concurrent: 最大并发数
            **kwargs: 其他 ExecutionConfig 参数

        Returns:
            self（支持链式调用）
        """
        self._execution_config = ExecutionConfig(
            parallel_execution=parallel_execution,
            max_concurrent=max_concurrent,
            **kwargs
        )
        return self

    # ============================================================================
    # Layer 2: Interceptor Configuration (Control Capabilities)
    # ============================================================================

    def with_budget(self, max_tokens: int) -> 'LoomBuilder':
        """
        启用预算控制（Token 限制）

        Args:
            max_tokens: 最大 Token 数量

        Returns:
            self（支持链式调用）
        """
        if self._interceptor_config is None:
            self._interceptor_config = InterceptorConfig()
        self._interceptor_config.enable_budget = True
        self._interceptor_config.max_tokens = max_tokens
        return self

    def with_depth_limit(self, max_depth: int) -> 'LoomBuilder':
        """
        启用深度限制（防止无限递归）

        Args:
            max_depth: 最大递归深度

        Returns:
            self（支持链式调用）
        """
        if self._interceptor_config is None:
            self._interceptor_config = InterceptorConfig()
        self._interceptor_config.enable_depth_limit = True
        self._interceptor_config.max_depth = max_depth
        return self

    def with_timeout(self, seconds: float) -> 'LoomBuilder':
        """
        启用超时控制

        Args:
            seconds: 超时时间（秒）

        Returns:
            self（支持链式调用）
        """
        if self._interceptor_config is None:
            self._interceptor_config = InterceptorConfig()
        self._interceptor_config.enable_timeout = True
        self._interceptor_config.timeout_seconds = seconds
        return self

    def with_hitl(self, patterns: List[str]) -> 'LoomBuilder':
        """
        启用人机交互审批（HITL）

        Args:
            patterns: 需要人工审批的模式列表

        Returns:
            self（支持链式调用）
        """
        if self._interceptor_config is None:
            self._interceptor_config = InterceptorConfig()
        self._interceptor_config.enable_hitl = True
        self._interceptor_config.hitl_patterns = patterns
        return self

    def with_interceptor_config(self, config: InterceptorConfig) -> 'LoomBuilder':
        """
        直接设置 Interceptor 配置

        Args:
            config: InterceptorConfig 实例

        Returns:
            self（支持链式调用）
        """
        self._interceptor_config = config
        return self

    # ============================================================================
    # Layer 4: Optimization Configuration
    # ============================================================================

    def with_optimization(
        self,
        enabled: bool = True,
        strategy: str = "adaptive"
    ) -> 'LoomBuilder':
        """
        启用结构优化

        Args:
            enabled: 是否启用
            strategy: 优化策略（adaptive, aggressive, conservative）

        Returns:
            self（支持链式调用）
        """
        if self._optimization_config is None:
            self._optimization_config = OptimizationConfig()
        self._optimization_config.enabled = enabled
        self._optimization_config.evolution_strategy = strategy
        return self

    def with_optimization_config(self, config: OptimizationConfig) -> 'LoomBuilder':
        """
        直接设置优化配置

        Args:
            config: OptimizationConfig 实例

        Returns:
            self（支持链式调用）
        """
        self._optimization_config = config
        return self

    def build(self) -> AgentNode:
        """
        构建 Agent

        Returns:
            AgentNode 实例

        Raises:
            ValueError: 如果缺少必需参数
        """
        # 验证必需参数
        if self._node_id is None:
            raise ValueError("node_id is required. Use with_id() to set it.")

        # 创建 Dispatcher（如果未提供）
        if self._dispatcher is None:
            bus = UniversalEventBus()
            self._dispatcher = Dispatcher(bus)

        # 配置 Interceptors（Layer 2 - Control Capabilities）
        if self._interceptor_config:
            config = self._interceptor_config

            # Budget Control
            if config.enable_budget and config.max_tokens:
                self._dispatcher.add_interceptor(
                    BudgetInterceptor(max_tokens=config.max_tokens)
                )

            # Depth Limiting
            if config.enable_depth_limit and config.max_depth:
                self._dispatcher.add_interceptor(
                    DepthInterceptor(max_depth=config.max_depth)
                )

            # Timeout Control
            if config.enable_timeout and config.timeout_seconds:
                self._dispatcher.add_interceptor(
                    TimeoutInterceptor(timeout_seconds=config.timeout_seconds)
                )

            # Human-in-the-Loop
            if config.enable_hitl and config.hitl_patterns:
                self._dispatcher.add_interceptor(
                    HITLInterceptor(patterns=config.hitl_patterns)
                )

            # Tracing
            if config.enable_tracing:
                self._dispatcher.add_interceptor(TracingInterceptor())

            # Auth
            if config.enable_auth and config.allowed_sources:
                self._dispatcher.add_interceptor(
                    AuthInterceptor(allowed_prefixes=set(config.allowed_sources))
                )

        # 准备参数
        params = {
            "node_id": self._node_id,
            "dispatcher": self._dispatcher,
            "provider": self._llm,
            "tools": self._tools,
        }

        # 应用配置
        if self._agent_config:
            params["role"] = self._agent_config.role
            params["system_prompt"] = self._agent_config.system_prompt

        if self._fractal_config:
            params["fractal_config"] = self._fractal_config

        if self._router_config:
            params["router_config"] = self._router_config

        if self._execution_config:
            params["execution_config"] = self._execution_config

        if self._memory_config:
            params["context_config"] = self._memory_config

        # 应用额外参数
        params.update(self._extra_params)

        # 创建 Agent
        return AgentNode(**params)

