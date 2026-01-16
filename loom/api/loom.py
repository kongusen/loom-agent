"""
Loom Agent Framework - 统一 API 入口

提供简洁、体系化的能力暴露接口。
"""

from dataclasses import dataclass
from typing import Any, cast

from loom.config.cognitive import CognitiveConfig
from loom.config.execution import ExecutionConfig
from loom.config.fractal import FractalConfig
from loom.config.memory import ContextConfig

# 配置类导入
from loom.config.models import AgentConfig as AgentMetaConfig
from loom.kernel.core import Dispatcher
from loom.kernel.core.bus import UniversalEventBus
from loom.llm import LLMProvider
from loom.node.agent import AgentNode
from loom.node.tool import ToolNode


@dataclass
class LoomConfig:
    """
    Loom Agent 统一配置

    整合所有配置项，提供一站式配置能力。
    """

    agent: AgentMetaConfig | None = None
    """Agent 元配置（角色、提示词等）"""

    fractal: FractalConfig | None = None
    """分型配置（自动分解、委托等）"""

    execution: ExecutionConfig | None = None
    """执行配置（并行、超时等）"""

    memory: ContextConfig | None = None
    """Memory 和 Context 配置"""

    @staticmethod
    def from_pattern(name: str) -> 'LoomConfig':
        """
        从模式创建配置

        Args:
            name: 模式名称 (analytical|creative|collaborative|iterative|execution)

        Returns:
            LoomConfig 实例
        """
        from loom.patterns import get_pattern

        pattern = get_pattern(name)
        return cast(LoomConfig, pattern.get_config())

    @staticmethod
    def from_preset(name: str) -> 'LoomConfig':
        """
        从预设创建配置（已弃用，使用 from_pattern 代替）

        Args:
            name: 预设名称

        Returns:
            LoomConfig 实例
        """
        import warnings
        warnings.warn(
            "from_preset() is deprecated, use from_pattern() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return LoomConfig.from_pattern(name)

    def validate(self):
        """验证配置的一致性"""
        if self.fractal:
            self.fractal.validate()


class Loom:
    """
    Loom Agent Framework 统一入口

    提供简洁的 API 来创建和管理 Agent。
    """

    @staticmethod
    def create_agent(
        node_id: str,
        *,
        pattern: str | None = None,
        preset: str | None = None,  # 已弃用，使用 pattern 代替
        llm: LLMProvider | None = None,
        tools: list[ToolNode] | None = None,
        config: LoomConfig | None = None,
        dispatcher: Dispatcher | None = None,
        **kwargs
    ) -> AgentNode:
        """
        创建 Agent（主入口）

        Args:
            node_id: Agent 唯一标识
            pattern: 模式名称 (analytical|creative|collaborative|iterative|execution)
            preset: 预设名称（已弃用，使用 pattern 代替）
            llm: LLM Provider
            tools: 工具列表
            config: 完整配置对象（优先级最高）
            dispatcher: 消息总线
            **kwargs: 其他参数

        Returns:
            AgentNode 实例

        Examples:
            >>> # 使用模式
            >>> agent = Loom.create_agent("my-agent", pattern="analytical")

            >>> # 使用配置对象
            >>> config = LoomConfig(...)
            >>> agent = Loom.create_agent("my-agent", config=config)
        """
        # 1. 确定配置来源（优先级：config > pattern > preset > default）
        if config is None:
            if pattern:
                config = LoomConfig.from_pattern(pattern)
            elif preset:
                import warnings
                warnings.warn(
                    "preset parameter is deprecated, use pattern instead",
                    DeprecationWarning,
                    stacklevel=2
                )
                config = LoomConfig.from_preset(preset)
            else:
                config = LoomConfig()

        # 2. 验证配置
        config.validate()

        # 3. 创建 Dispatcher
        if dispatcher is None:
            bus = UniversalEventBus()
            dispatcher = Dispatcher(bus)

        # 4. 准备参数
        agent_params: dict[str, Any] = {
            "node_id": node_id,
            "dispatcher": dispatcher,
            "provider": llm,
            "tools": tools or [],
        }

        # 5. 应用配置
        if config.agent:
            agent_params["role"] = config.agent.role
            agent_params["system_prompt"] = config.agent.system_prompt

        if config.fractal:
            agent_params["fractal_config"] = config.fractal

        if config.execution:
            agent_params["execution_config"] = config.execution

        # Prepare Cognitive Configuration
        cognitive_config = CognitiveConfig.default()
        if config.memory:
            cognitive_config.context_max_tokens = config.memory.max_context_tokens
            cognitive_config.context_strategy = config.memory.strategy
            # Map other fields if possible

        agent_params["cognitive_config"] = cognitive_config

        # 6. 应用 kwargs 覆盖
        agent_params.update(kwargs)

        # 7. 创建 Agent
        return AgentNode(**agent_params)

    @staticmethod
    def builder():
        """返回 Builder 实例"""
        from loom.builder import LoomBuilder
        return LoomBuilder()

    @staticmethod
    def get_preset(name: str) -> LoomConfig:
        """获取预设配置"""
        return LoomConfig.from_preset(name)

    @staticmethod
    def list_presets() -> list[str]:
        """列出所有可用的预设"""
        from loom.presets import PRESETS
        return list(PRESETS.keys())
