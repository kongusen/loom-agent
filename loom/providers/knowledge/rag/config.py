"""
RAG 配置类
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractionConfig:
    """
    实体/关系提取配置

    用户通过此配置指定提取方向（Skill 模式），
    框架内置 LLMEntityExtractor 负责具体提取逻辑。
    """

    entity_types: list[str] = field(default_factory=lambda: ["CONCEPT", "TOOL", "API"])
    relation_types: list[str] = field(default_factory=lambda: ["DEPENDS_ON", "IMPLEMENTS", "USES"])
    hints: str = ""  # 领域提示（如 "关注技术架构和API设计模式"）
    max_entities_per_chunk: int = 10
    max_relations_per_chunk: int = 10
    enabled: bool = True  # False 时跳过提取，纯向量模式


@dataclass
class RAGConfig:
    """
    RAG 配置

    统一的配置对象，支持快速配置
    """

    # 策略配置
    strategy: str = "hybrid"  # graph_first | vector_first | hybrid
    n_hop: int = 2
    graph_weight: float = 0.5
    vector_weight: float = 0.5

    # 分块配置
    chunk_size: int = 512
    chunk_overlap: int = 50

    # 检索配置
    default_limit: int = 10
    vector_threshold: float = 0.0

    # 提取配置
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)

    # 额外配置
    extra: dict[str, Any] = field(default_factory=dict)
