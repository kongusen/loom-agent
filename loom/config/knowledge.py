"""
外部知识库配置和接口定义

提供统一的知识库接口，支持集成各种知识源：
- 文档数据库（Notion, Confluence）
- 向量数据库（Pinecone, Weaviate）
- API文档（OpenAPI, GraphQL Schema）
- 自定义知识库
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeItem:
    """
    知识条目

    表示知识库中的一个知识单元
    """

    id: str
    content: str  # 知识内容
    source: str  # 来源（文档、API、数据库等）
    relevance: float = 0.0  # 相关度分数（0.0-1.0）
    metadata: dict[str, Any] = field(default_factory=dict)  # 附加元数据


class KnowledgeBaseProvider(ABC):
    """
    外部知识库提供者抽象接口

    用户可以实现此接口来集成各种知识源
    """

    @abstractmethod
    async def query(
        self,
        query: str,
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[KnowledgeItem]:
        """
        查询知识库

        Args:
            query: 查询文本（可以是自然语言）
            limit: 返回结果数量
            filters: 过滤条件（如类型、标签等）

        Returns:
            相关知识条目列表（按相关度排序）
        """
        pass

    @abstractmethod
    async def get_by_id(self, knowledge_id: str) -> KnowledgeItem | None:
        """
        根据ID获取知识条目

        Args:
            knowledge_id: 知识条目ID

        Returns:
            知识条目，如果不存在则返回None
        """
        pass
