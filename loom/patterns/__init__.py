"""
高级模式 - 多智能体协作 & 递归控制

v0.1.7 - 完整的 Agent 推理、协作和路由框架

核心组件：
## 多智能体协作（Multi-Agent）
- Crew: 基础多智能体协作
- CrewRole: 角色定义
- SmartCoordinator: 智能任务分解
- ArtifactStore: 上下文管理
- ParallelExecutor: 并行执行
- ErrorRecovery: 容错机制
- CrewTracer: 可观测性
- CrewPresets: 预设配置

## 递归控制（Recursive Control）- 基于吴恩达 Agent 四大范式
- ReflectionLoop: 反思循环（Reflection）
- TreeOfThoughts: 思维树（Planning）
- PlanExecutor: 规划-执行（Planning）
- SelfConsistency: 自洽性检查（Quality Assurance）

## 智能路由（Intelligent Routing）- v0.1.7
- Router: 智能路由器
- AgentCapability: Agent 能力描述
- TaskClassifier: 任务分类器
- RoutingStrategy: 路由策略
"""

# ============================================================================
# 多智能体协作
# ============================================================================

# 基础 Crew
from loom.patterns.crew import (
    Crew,
    sequential_crew,
    parallel_crew,
    coordinated_crew,
)
from loom.patterns.crew_role import CrewRole

# 智能协调
from loom.patterns.coordination import (
    TaskComplexity,
    SubTask,
    TaskDecomposition,
    ComplexityAnalyzer,
    SmartCoordinator,
)

# 上下文管理
from loom.patterns.artifact_store import (
    SubAgentResult,
    ArtifactStore,
)

# 并行执行
from loom.patterns.parallel_executor import (
    ParallelConfig,
    ParallelExecutor,
    DependencyAnalyzer,
)

# 容错和恢复
from loom.patterns.error_recovery import (
    RecoveryAction,
    ErrorContext,
    RecoveryConfig,
    ErrorRecovery,
    CheckpointData,
    CheckpointManager,
)

# 可观测性和评估
from loom.patterns.observability import (
    DecisionLogEntry,
    CrewTracer,
    EvalMetrics,
    CrewEvaluator,
)

# 预设配置
from loom.patterns.presets import (
    CrewConfig,
    CrewPresets,
)

# ============================================================================
# 递归控制模式（Recursive Control）
# ============================================================================

from loom.patterns.recursive_control import (
    # 思维模式
    ThinkingMode,
    ThoughtNode,
    # 反思循环
    ReflectionLoop,
    # 思维树
    TreeOfThoughts,
    # 规划-执行
    PlanExecutor,
    Plan,
    ExecutionResult,
    # 自洽性检查
    SelfConsistency,
)

# ============================================================================
# 智能路由（Intelligent Routing）- v0.1.7
# ============================================================================

from loom.patterns.routing import (
    # 路由器
    Router,
    RoutingStrategy,
    RoutingResult,
    # Agent 能力
    AgentCapability,
    AgentType,
    ComplexityLevel,
    # 任务分类
    TaskClassifier,
    TaskCharacteristics,
)

__all__ = [
    # ========================================================================
    # 多智能体协作
    # ========================================================================
    # 基础
    "Crew",
    "CrewRole",
    "sequential_crew",
    "parallel_crew",
    "coordinated_crew",
    # 协调
    "TaskComplexity",
    "SubTask",
    "TaskDecomposition",
    "ComplexityAnalyzer",
    "SmartCoordinator",
    # 上下文
    "SubAgentResult",
    "ArtifactStore",
    # 并行
    "ParallelConfig",
    "ParallelExecutor",
    "DependencyAnalyzer",
    # 容错
    "RecoveryAction",
    "ErrorContext",
    "RecoveryConfig",
    "ErrorRecovery",
    "CheckpointData",
    "CheckpointManager",
    # 可观测性
    "DecisionLogEntry",
    "CrewTracer",
    "EvalMetrics",
    "CrewEvaluator",
    # 预设
    "CrewConfig",
    "CrewPresets",
    # ========================================================================
    # 递归控制模式
    # ========================================================================
    # 思维模式
    "ThinkingMode",
    "ThoughtNode",
    # 反思循环
    "ReflectionLoop",
    # 思维树
    "TreeOfThoughts",
    # 规划-执行
    "PlanExecutor",
    "Plan",
    "ExecutionResult",
    # 自洽性检查
    "SelfConsistency",
    # ========================================================================
    # 智能路由（v0.1.7）
    # ========================================================================
    # 路由器
    "Router",
    "RoutingStrategy",
    "RoutingResult",
    # Agent 能力
    "AgentCapability",
    "AgentType",
    "ComplexityLevel",
    # 任务分类
    "TaskClassifier",
    "TaskCharacteristics",
]
