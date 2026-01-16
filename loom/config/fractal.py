"""
Fractal Node Configuration

Configuration for self-organizing fractal node structures that enable
adaptive task decomposition and dynamic agent orchestration.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeRole(Enum):
    """Node roles in the fractal structure"""

    COORDINATOR = "coordinator"  # Decomposes tasks and delegates
    SPECIALIST = "specialist"  # Handles domain-specific tasks
    EXECUTOR = "executor"  # Leaf node that executes tasks directly
    AGGREGATOR = "aggregator"  # Combines results from multiple nodes


class GrowthTrigger(Enum):
    """When to trigger fractal growth"""

    COMPLEXITY = "complexity"  # When task complexity is high (formerly SYSTEM2)
    ALWAYS = "always"  # Always evaluate for growth
    MANUAL = "manual"  # Only when explicitly requested
    NEVER = "never"  # Disable fractal mode entirely


class GrowthStrategy(Enum):
    """Strategy for node growth"""

    DECOMPOSE = "decompose"  # Split into sequential subtasks (1→N chain)
    SPECIALIZE = "specialize"  # Create domain experts (1→N star)
    PARALLELIZE = "parallelize"  # Clone for parallel execution (1→N parallel)
    ITERATE = "iterate"  # Create iterative refinement loop


@dataclass
class FractalConfig:
    """Configuration for fractal node behavior"""

    # === Core Settings ===
    enabled: bool = False
    """Enable fractal mode (self-organizing structure)"""

    growth_trigger: GrowthTrigger = GrowthTrigger.COMPLEXITY
    """When to trigger automatic growth"""

    # === Structure Limits ===
    max_depth: int = 3
    """Maximum depth of the node tree (0 = root only)"""

    max_children: int = 5
    """Maximum children per node"""

    max_total_nodes: int = 20
    """Maximum total nodes in the structure (防止爆炸性增长)"""

    # === Growth Thresholds ===
    complexity_threshold: float = 0.7
    """Task complexity score (0-1) to trigger growth"""

    confidence_threshold: float = 0.6
    """Minimum confidence to NOT grow (低于此值则分解)"""

    token_threshold: int = 4000
    """Token budget threshold to trigger decomposition"""

    # === Pruning Settings ===
    enable_auto_pruning: bool = True
    """Automatically remove inefficient nodes"""

    pruning_threshold: float = 0.3
    """Minimum fitness score to keep a node"""

    min_tasks_before_pruning: int = 3
    """Minimum task count before considering pruning"""

    # === Strategy Selection ===
    default_strategy: GrowthStrategy = GrowthStrategy.DECOMPOSE
    """Default growth strategy when auto-detection fails"""

    strategy_keywords: dict[GrowthStrategy, list[str]] = field(
        default_factory=lambda: {
            GrowthStrategy.DECOMPOSE: ["step", "phase", "sequential", "order"],
            GrowthStrategy.SPECIALIZE: ["expert", "specialist", "domain", "field"],
            GrowthStrategy.PARALLELIZE: ["parallel", "concurrent", "independent", "simultaneous"],
            GrowthStrategy.ITERATE: ["iterate", "refine", "improve", "optimize"],
        }
    )
    """Keywords to detect appropriate growth strategy"""

    # === Performance Tracking ===
    track_metrics: bool = True
    """Track and record node performance metrics"""

    persist_to_memory: bool = True
    """Persist structure performance to L4 memory"""

    # === Visualization ===
    enable_visualization: bool = True
    """Enable structure visualization output"""

    visualization_format: str = "tree"  # "tree" | "graph" | "compact"
    """Format for structure visualization"""

    # === Explicit Delegation (显式委托配置) ===
    enable_explicit_delegation: bool = True
    """启用显式委托工具（delegate_subtasks）"""

    allow_recursive_delegation: bool = True
    """允许子代理再次委托（受 max_depth 限制）"""

    max_recursive_depth: int = 2
    """允许递归委托的最大深度"""

    delegation_tool_name: str = "delegate_subtasks"
    """委托工具的名称"""

    # === Synthesis Configuration (合成配置) ===
    synthesis_strategy: str = "auto"
    """默认合成策略: auto|concatenate|structured"""

    synthesis_model: str = "lightweight"
    """默认合成模型策略: lightweight|same_model|custom"""

    synthesis_model_override: str | None = None
    """自定义合成模型名称"""

    synthesis_max_tokens: int = 2000
    """合成时的最大 token 数"""

    # === Child Node Configuration (子节点配置) ===
    default_child_token_budget: int = 4000
    """子节点的默认 token 预算"""

    child_tool_blacklist: list[str] = field(default_factory=list)
    """子节点工具黑名单（额外的）"""

    max_concurrent_children: int = 5
    """最大并发子节点数"""

    # === Hybrid Mode (混合模式配置) ===
    hybrid_mode_enabled: bool = True
    """启用混合模式（显式+隐式并存）"""

    default_delegation_mode: str = "auto"
    """默认委托模式: auto|explicit_only|implicit_only"""

    def validate(self):
        """Validate configuration"""
        if self.max_depth < 0:
            raise ValueError("max_depth must be >= 0")

        if self.max_children < 1:
            raise ValueError("max_children must be >= 1")

        if not 0 <= self.complexity_threshold <= 1:
            raise ValueError("complexity_threshold must be in [0, 1]")

        if not 0 <= self.confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be in [0, 1]")

        if not 0 <= self.pruning_threshold <= 1:
            raise ValueError("pruning_threshold must be in [0, 1]")


@dataclass
class NodeMetrics:
    """Performance metrics for a single node"""

    # === Execution Metrics ===
    task_count: int = 0
    """Total number of tasks executed"""

    success_count: int = 0
    """Number of successful task completions"""

    failure_count: int = 0
    """Number of failed task executions"""

    total_tokens: int = 0
    """Total tokens consumed"""

    total_time: float = 0.0
    """Total execution time in seconds"""

    total_cost: float = 0.0
    """Total execution cost in USD"""

    # === Derived Metrics ===
    @property
    def success_rate(self) -> float:
        """Success rate (0-1)"""
        if self.task_count == 0:
            return 0.0
        return self.success_count / self.task_count

    @property
    def avg_tokens(self) -> float:
        """Average tokens per task"""
        if self.task_count == 0:
            return 0.0
        return self.total_tokens / self.task_count

    @property
    def avg_time(self) -> float:
        """Average time per task (seconds)"""
        if self.task_count == 0:
            return 0.0
        return self.total_time / self.task_count

    @property
    def avg_cost(self) -> float:
        """Average cost per task (USD)"""
        if self.task_count == 0:
            return 0.0
        return self.total_cost / self.task_count

    # === Fitness Score ===
    def fitness_score(
        self,
        success_weight: float = 0.4,
        token_weight: float = 0.3,
        time_weight: float = 0.2,
        cost_weight: float = 0.1,
    ) -> float:
        """
        Calculate composite fitness score (0-1, higher is better)

        Args:
            success_weight: Weight for success rate
            token_weight: Weight for token efficiency
            time_weight: Weight for time efficiency
            cost_weight: Weight for cost efficiency

        Returns:
            Fitness score in [0, 1]
        """
        if self.task_count == 0:
            return 0.0

        # Component 1: Success rate (0-1)
        success_component = self.success_rate

        # Component 2: Token efficiency (normalized by 4000 tokens baseline)
        token_component = 1 / (1 + self.avg_tokens / 4000)

        # Component 3: Time efficiency (normalized by 10s baseline)
        time_component = 1 / (1 + self.avg_time / 10)

        # Component 4: Cost efficiency (normalized by $0.01 baseline)
        cost_component = 1 / (1 + self.avg_cost / 0.01)

        # Weighted sum
        fitness = (
            success_component * success_weight
            + token_component * token_weight
            + time_component * time_weight
            + cost_component * cost_weight
        )

        return min(1.0, max(0.0, fitness))

    def record_execution(self, success: bool, tokens: int, time: float, cost: float = 0.0):
        """Record a task execution"""
        self.task_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        self.total_tokens += tokens
        self.total_time += time
        self.total_cost += cost

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "task_count": self.task_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_tokens": self.total_tokens,
            "total_time": self.total_time,
            "total_cost": self.total_cost,
            "success_rate": self.success_rate,
            "avg_tokens": self.avg_tokens,
            "avg_time": self.avg_time,
            "avg_cost": self.avg_cost,
            "fitness_score": self.fitness_score(),
        }
