"""
索引构建器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """
    文档 - 索引构建的输入单元

    Attributes:
        id: 文档ID
        content: 文档内容
        metadata: 附加元数据
    """

    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class IndexBuilder(ABC):
    """
    索引构建器抽象接口

    定义文档摄入和索引构建的标准接口
    """

    @abstractmethod
    async def add_documents(
        self,
        documents: list[Document],
        extract_entities: bool = True,
    ) -> None:
        """
        添加文档并构建索引

        Args:
            documents: 文档列表
            extract_entities: 是否抽取实体
        """
        pass

    @abstractmethod
    async def add_document(
        self,
        document: Document,
        extract_entities: bool = True,
    ) -> None:
        """
        添加单个文档

        Args:
            document: 文档
            extract_entities: 是否抽取实体
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """清空索引"""
        pass
