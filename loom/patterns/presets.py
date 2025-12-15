"""
Crew Presets - 预设配置

提供开箱即用的最佳实践配置：
- fast_prototype: 快速原型（开发阶段）
- production_ready: 生产就绪（高性能+容错）
- deep_research: 研究专用（多agent深度探索）
- conversational: 实时对话（低延迟）

基于 Anthropic 的 Multi-Agent 最佳实践
"""

from __future__ import annotations

from typing import List, Optional

from loom.core.base_agent import BaseAgent
from loom.interfaces.llm import BaseLLM
from loom.patterns.coordination import ComplexityAnalyzer, SmartCoordinator, TaskComplexity
from loom.patterns.artifact_store import ArtifactStore
from loom.patterns.parallel_executor import ParallelConfig, ParallelExecutor
from loom.patterns.error_recovery import RecoveryConfig, ErrorRecovery, CheckpointManager
from loom.patterns.observability import CrewTracer


class CrewConfig:
    """
    Crew 配置类

    封装所有配置选项，便于预设和自定义
    """

    def __init__(
        self,
        # 基础配置
        mode: str = "sequential",
        # 协调配置
        use_smart_coordinator: bool = False,
        complexity_analyzer: Optional[ComplexityAnalyzer] = None,
        coordinator: Optional[BaseAgent] = None,
        # 并行配置
        parallelism: bool = False,
        parallel_config: Optional[ParallelConfig] = None,
        # 上下文管理
        use_artifact_store: bool = False,
        artifact_store_path: str = "./crew_artifacts",
        # 容错配置
        error_recovery: bool = False,
        recovery_config: Optional[RecoveryConfig] = None,
        # Checkpoint
        use_checkpoint: bool = False,
        checkpoint_path: str = "./crew_checkpoints",
        # 可观测性
        tracing: bool = False,
        # 评估
        evaluation: bool = False,
        # 其他
        name: Optional[str] = None,
    ):
        self.mode = mode
        self.use_smart_coordinator = use_smart_coordinator
        self.complexity_analyzer = complexity_analyzer
        self.coordinator = coordinator
        self.parallelism = parallelism
        self.parallel_config = parallel_config or ParallelConfig()
        self.use_artifact_store = use_artifact_store
        self.artifact_store_path = artifact_store_path
        self.error_recovery = error_recovery
        self.recovery_config = recovery_config or RecoveryConfig()
        self.use_checkpoint = use_checkpoint
        self.checkpoint_path = checkpoint_path
        self.tracing = tracing
        self.evaluation = evaluation
        self.name = name

    def override(self, **kwargs) -> CrewConfig:
        """
        覆盖配置项（返回新实例）

        Example:
            config = CrewPresets.production_ready_config()
            custom_config = config.override(
                parallelism=True,
                parallel_config=ParallelConfig(max_parallel_agents=10)
            )
        """
        # 复制当前配置
        import copy

        new_config = copy.copy(self)

        # 应用覆盖
        for key, value in kwargs.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)

        return new_config


class CrewPresets:
    """
    Crew 预设配置

    提供常见场景的最佳实践配置
    """

    @staticmethod
    def fast_prototype(
        agents: List[BaseAgent],
        coordinator: Optional[BaseAgent] = None,
        name: Optional[str] = None,
    ) -> CrewConfig:
        """
        快速原型配置（适合开发阶段）

        特点：
        - 串行执行（方便调试）
        - 详细追踪
        - 无并行（避免复杂度）
        - 无checkpoint（快速迭代）

        Args:
            agents: Agent 列表
            coordinator: 协调器（可选）
            name: Crew 名称

        Returns:
            CrewConfig
        """
        mode = "sequential" if not coordinator else "coordinated"

        return CrewConfig(
            mode=mode,
            coordinator=coordinator,
            use_smart_coordinator=False,  # 开发阶段不需要
            parallelism=False,  # 串行方便调试
            use_artifact_store=False,  # 不需要持久化
            error_recovery=True,  # 基础错误处理
            recovery_config=RecoveryConfig(
                auto_retry=True,
                max_retries=2,
                exponential_backoff=False,  # 快速失败
            ),
            use_checkpoint=False,  # 不需要checkpoint
            tracing=True,  # 启用追踪（方便调试）
            evaluation=False,  # 开发阶段不需要
            name=name or "FastPrototypeCrew",
        )

    @staticmethod
    def production_ready(
        agents: List[BaseAgent],
        coordinator: Optional[BaseAgent] = None,
        llm: Optional[BaseLLM] = None,
        name: Optional[str] = None,
    ) -> CrewConfig:
        """
        生产就绪配置（高性能+容错）

        特点：
        - 并行执行（高性能）
        - Checkpoint 机制
        - 错误恢复
        - 监控追踪
        - Artifact 存储

        Args:
            agents: Agent 列表
            coordinator: 协调器（可选）
            llm: LLM（用于复杂度分析）
            name: Crew 名称

        Returns:
            CrewConfig
        """
        mode = "coordinated" if coordinator else "parallel"

        # 如果有 LLM，启用智能协调
        use_smart = coordinator is not None and llm is not None

        return CrewConfig(
            mode=mode,
            coordinator=coordinator,
            use_smart_coordinator=use_smart,
            complexity_analyzer=ComplexityAnalyzer(llm) if llm else None,
            # 并行配置
            parallelism=True,
            parallel_config=ParallelConfig(
                max_parallel_agents=5,
                max_parallel_tools=3,
                enable_tool_parallelism=True,
                timeout_per_agent=300,  # 5分钟超时
            ),
            # Artifact 存储
            use_artifact_store=True,
            artifact_store_path="./crew_artifacts",
            # 错误恢复
            error_recovery=True,
            recovery_config=RecoveryConfig(
                auto_retry=True,
                max_retries=3,
                exponential_backoff=True,
                enable_fallback=True,
                inform_coordinator=coordinator is not None,
            ),
            # Checkpoint
            use_checkpoint=True,
            checkpoint_path="./crew_checkpoints",
            # 监控
            tracing=True,
            evaluation=False,  # 生产环境按需启用
            name=name or "ProductionCrew",
        )

    @staticmethod
    def deep_research(
        agents: List[BaseAgent],
        coordinator: BaseAgent,
        llm: BaseLLM,
        name: Optional[str] = None,
    ) -> CrewConfig:
        """
        深度研究配置（多agent深度探索）

        特点：
        - Coordinated 模式
        - 自动工作量缩放
        - 子agent结果存文件
        - 长上下文管理
        - 并行执行

        Args:
            agents: Agent 列表
            coordinator: 协调器（必需）
            llm: LLM（用于复杂度分析）
            name: Crew 名称

        Returns:
            CrewConfig
        """
        return CrewConfig(
            mode="coordinated",
            coordinator=coordinator,
            # 智能协调
            use_smart_coordinator=True,
            complexity_analyzer=ComplexityAnalyzer(llm),
            # 并行配置（研究任务可以更激进）
            parallelism=True,
            parallel_config=ParallelConfig(
                max_parallel_agents=10,  # 更多并行
                max_parallel_tools=5,
                enable_tool_parallelism=True,
                timeout_per_agent=600,  # 10分钟超时（研究需要时间）
            ),
            # Artifact 存储（必需，研究结果通常很大）
            use_artifact_store=True,
            artifact_store_path="./research_artifacts",
            # 错误恢复
            error_recovery=True,
            recovery_config=RecoveryConfig(
                auto_retry=True,
                max_retries=3,
                enable_fallback=True,
                inform_coordinator=True,
                coordinator_decides=True,  # 让coordinator决定如何恢复
            ),
            # Checkpoint（研究任务通常很长）
            use_checkpoint=True,
            checkpoint_path="./research_checkpoints",
            # 监控
            tracing=True,
            evaluation=True,  # 研究质量很重要
            name=name or "ResearchCrew",
        )

    @staticmethod
    def conversational(
        agents: List[BaseAgent],
        name: Optional[str] = None,
    ) -> CrewConfig:
        """
        对话配置（低延迟）

        特点：
        - 快速响应模式
        - 流式输出
        - 最小化agent数量
        - 无持久化（减少I/O）

        Args:
            agents: Agent 列表（建议少于3个）
            name: Crew 名称

        Returns:
            CrewConfig
        """
        return CrewConfig(
            mode="sequential",  # 对话通常串行
            use_smart_coordinator=False,
            parallelism=False,  # 串行更快响应
            use_artifact_store=False,  # 无持久化
            error_recovery=True,
            recovery_config=RecoveryConfig(
                auto_retry=True,
                max_retries=1,  # 快速失败
                exponential_backoff=False,
            ),
            use_checkpoint=False,
            tracing=False,  # 减少开销
            evaluation=False,
            name=name or "ConversationalCrew",
        )

    @staticmethod
    def custom(
        agents: List[BaseAgent],
        **overrides,
    ) -> CrewConfig:
        """
        自定义配置（从生产配置开始，应用覆盖）

        Example:
            config = CrewPresets.custom(
                agents=agents,
                mode="parallel",
                parallelism=True,
                parallel_config=ParallelConfig(max_parallel_agents=10)
            )
        """
        base_config = CrewPresets.production_ready(agents)
        return base_config.override(**overrides)


__all__ = ["CrewConfig", "CrewPresets"]
