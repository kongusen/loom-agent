"""
API Models - Pydantic 配置模型

参考 FastAPI 设计，使用 Pydantic 进行数据验证和配置管理。

特性：
1. 类型安全 - 完整的类型注解
2. 数据验证 - 自动验证输入数据
3. 默认值 - 合理的默认配置
4. 文档生成 - 自动生成配置文档

.. deprecated:: 0.4.7
    AgentConfig 将在 v0.5.0 中移除。请使用 Agent.from_llm() 或 Agent.create() 代替。
"""

import warnings
from pydantic import BaseModel, Field, field_validator, model_validator


class MemoryConfig(BaseModel):
    """
    Memory 配置模型

    定义 LoomMemory 的配置参数（四层记忆系统）。
    """

    max_l1_size: int = Field(
        default=50,
        description="L1层大小（最近完整任务）",
        ge=1,
        le=1000,
    )

    max_l2_size: int = Field(
        default=100,
        description="L2层大小（重要任务）",
        ge=1,
        le=1000,
    )

    max_l3_size: int = Field(
        default=500,
        description="L3层大小（任务摘要）",
        ge=1,
        le=10000,
    )

    enable_l4_vectorization: bool = Field(
        default=True,
        description="是否启用L4向量存储",
    )

    max_task_index_size: int = Field(
        default=1000,
        description="任务索引容量",
        ge=1,
        le=100000,
    )

    max_fact_index_size: int = Field(
        default=5000,
        description="事实索引容量",
        ge=1,
        le=100000,
    )


class AgentConfig(BaseModel):
    """
    Agent 配置模型

    定义创建 Agent 所需的所有配置参数。

    .. deprecated:: 0.4.7
        AgentConfig 将在 v0.5.0 中移除。请使用 Agent.from_llm() 或 Agent.create() 代替。
    """

    agent_id: str = Field(
        ...,
        description="Agent 唯一标识",
        min_length=1,
        max_length=100,
    )

    name: str = Field(
        ...,
        description="Agent 名称",
        min_length=1,
        max_length=200,
    )

    description: str = Field(
        default="",
        description="Agent 描述",
        max_length=1000,
    )

    capabilities: list[str] = Field(
        default=["tool_use"],
        description="Agent 能力列表（如 tool_use, reflection, planning, multi_agent）",
    )

    system_prompt: str = Field(
        default="",
        description="系统提示词",
    )

    max_iterations: int = Field(
        default=10,
        description="最大迭代次数",
        ge=1,
        le=100,
    )

    require_done_tool: bool = Field(
        default=True,
        description="是否要求显式调用 done 工具完成任务",
    )

    enable_observation: bool = Field(
        default=True,
        description="是否启用观测能力",
    )

    enable_context_tools: bool = Field(
        default=True,
        description="是否启用上下文查询工具",
    )

    enable_tool_creation: bool = Field(
        default=False,
        description="是否启用工具创建能力（建议禁用，优先使用delegate_task）",
    )

    max_context_tokens: int = Field(
        default=4000,
        description="最大上下文 token 数",
        ge=100,
        le=100000,
    )

    memory_config: MemoryConfig = Field(
        default_factory=MemoryConfig,
        description="记忆系统配置",
    )

    context_budget_config: dict[str, float | int] | None = Field(
        default=None,
        description="上下文预算比例配置（可选）",
    )

    # Phase 3: Skill 和工具配置
    enabled_skills: set[str] = Field(
        default_factory=set,
        description="启用的 Skills（Phase 3）",
    )

    disabled_tools: set[str] = Field(
        default_factory=set,
        description="禁用的工具（Phase 3）",
    )

    extra_tools: set[str] = Field(
        default_factory=set,
        description="额外的工具（Phase 3）",
    )

    # 知识库RAG配置
    knowledge_max_items: int = Field(
        default=3,
        description="知识库查询返回的最大条目数",
        ge=1,
        le=10,
    )

    knowledge_relevance_threshold: float = Field(
        default=0.7,
        description="知识相关度阈值（0.0-1.0）",
        ge=0.0,
        le=1.0,
    )

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, v: list[str]) -> list[str]:
        """验证能力列表"""
        valid_capabilities = {"tool_use", "reflection", "planning", "multi_agent"}
        for cap in v:
            if cap not in valid_capabilities:
                raise ValueError(
                    f"Invalid capability: {cap}. " f"Valid capabilities: {valid_capabilities}"
                )
        return v

    @model_validator(mode='after')
    def _emit_deprecation_warning(self) -> 'AgentConfig':
        """Emit deprecation warning when AgentConfig is instantiated"""
        warnings.warn(
            "AgentConfig is deprecated and will be removed in v0.5.0. "
            "Please use Agent.from_llm() or Agent.create() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "agent_id": "coding-agent",
                    "name": "Coding Assistant",
                    "description": "An agent that helps with coding tasks",
                    "capabilities": ["tool_use", "reflection"],
                    "system_prompt": "You are a helpful coding assistant.",
                    "max_iterations": 10,
                }
            ]
        }
    }
