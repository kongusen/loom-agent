"""
RAG 配置类
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StorageType(Enum):
    """存储类型"""

    MEMORY = "memory"
    POSTGRES = "postgres"
    QDRANT = "qdrant"


@dataclass
class RAGConfig:
    """
    RAG 配置

    统一的配置对象，支持快速配置
    """

    # 存储配置
    storage_type: StorageType = StorageType.MEMORY
    connection_string: str | None = None

    # 策略配置
    strategy: str = "graph_first"  # graph_first | vector_first | hybrid
    n_hop: int = 2
    graph_weight: float = 0.5
    vector_weight: float = 0.5

    # 分块配置
    chunk_size: int = 512
    chunk_overlap: int = 50

    # 检索配置
    default_limit: int = 10
    vector_threshold: float = 0.0

    # 额外配置
    extra: dict[str, Any] = field(default_factory=dict)
