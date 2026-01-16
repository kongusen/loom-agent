"""
Delegation Protocol

定义显式委托机制的协议和数据结构，支持 Agent 通过工具调用显式请求子代理协助。
"""

from dataclasses import dataclass, field
from typing import Any

from loom.config.fractal import GrowthStrategy
from loom.protocol.mcp import MCPToolDefinition


@dataclass
class SubtaskSpecification:
    """
    单个子任务的规格说明

    定义了子任务的描述、角色、工具限制和资源预算。
    """

    description: str
    """任务描述（必需）"""

    role: str | None = None
    """节点角色: specialist|executor|researcher|aggregator"""

    tools: list[str] | None = None
    """工具白名单（None 表示继承父节点工具）"""

    max_tokens: int | None = None
    """Token 预算限制"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """额外的元数据"""

    def __post_init__(self):
        """验证字段"""
        if not self.description or not self.description.strip():
            raise ValueError("SubtaskSpecification.description 不能为空")

        if self.role and self.role not in ["specialist", "executor", "researcher", "aggregator"]:
            raise ValueError(f"无效的角色: {self.role}")

        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("max_tokens 必须大于 0")


@dataclass
class DelegationRequest:
    """
    委托请求

    包含子任务列表、执行模式、合成策略等配置。
    """

    subtasks: list[SubtaskSpecification]
    """子任务列表"""

    execution_mode: str = "parallel"
    """执行模式: parallel|sequential|adaptive"""

    synthesis_strategy: str = "auto"
    """合成策略: auto|concatenate|structured"""

    reasoning: str | None = None
    """分解理由（可选）"""

    def __post_init__(self):
        """验证字段"""
        if not self.subtasks:
            raise ValueError("subtasks 不能为空")

        if self.execution_mode not in ["parallel", "sequential", "adaptive"]:
            raise ValueError(f"无效的执行模式: {self.execution_mode}")

        if self.synthesis_strategy not in ["auto", "concatenate", "structured"]:
            raise ValueError(f"无效的合成策略: {self.synthesis_strategy}")


@dataclass
class DelegationResult:
    """
    委托结果

    包含合成后的结果、各子任务的详细结果和执行元数据。
    """

    success: bool
    """是否成功"""

    synthesized_result: str
    """合成后的最终结果"""

    subtask_results: list[dict[str, Any]]
    """各子任务的详细结果"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """执行元数据（如执行时间、token 使用等）"""


# MCP 工具定义
DELEGATE_SUBTASKS_TOOL = MCPToolDefinition(
    name="delegate_subtasks",
    description="将复杂任务分解为子任务并委托给专门的子代理并行执行。适用于需要多个专家协作或并行处理的复杂任务。",
    input_schema={
        "type": "object",
        "properties": {
            "subtasks": {
                "type": "array",
                "description": "子任务列表，每个子任务可以指定角色、工具和资源限制",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "子任务的详细描述"},
                        "role": {
                            "type": "string",
                            "enum": ["specialist", "executor", "researcher", "aggregator"],
                            "description": "子代理的角色类型",
                        },
                        "tools": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "子代理可用的工具白名单（不指定则继承父代理工具）",
                        },
                        "max_tokens": {"type": "integer", "description": "子任务的 token 预算限制"},
                    },
                    "required": ["description"],
                },
                "minItems": 1,
            },
            "execution_mode": {
                "type": "string",
                "enum": ["parallel", "sequential", "adaptive"],
                "default": "parallel",
                "description": "执行模式：parallel（并行）、sequential（顺序）、adaptive（自适应）",
            },
            "synthesis_strategy": {
                "type": "string",
                "enum": ["auto", "concatenate", "structured"],
                "default": "auto",
                "description": "结果合成策略：auto（LLM合成）、concatenate（简单拼接）、structured（结构化输出）",
            },
            "reasoning": {"type": "string", "description": "任务分解的理由说明（可选）"},
        },
        "required": ["subtasks"],
    },
)


@dataclass
class TaskDecomposition:
    """Result of task decomposition"""

    subtasks: list[str]
    """List of subtasks"""

    strategy: GrowthStrategy
    """Strategy used for decomposition"""

    reasoning: str
    """Explanation of decomposition"""

    estimated_complexity: float
    """Estimated complexity (0-1) of original task"""
