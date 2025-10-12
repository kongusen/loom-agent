"""简单的内存检索器 - 无需外部依赖"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loom.interfaces.retriever import BaseRetriever, Document


class InMemoryRetriever(BaseRetriever):
    """
    简单的内存检索器 - 基于关键词匹配

    特点:
    - 无需外部依赖
    - 适用于开发/测试
    - 基于简单的关键词匹配 (非向量检索)

    示例:
        retriever = InMemoryRetriever()
        await retriever.add_texts([
            "Python is a programming language",
            "JavaScript is used for web development"
        ])

        docs = await retriever.retrieve("programming")
        # 返回包含 "programming" 的文档
    """

    def __init__(self):
        self.documents: List[Document] = []

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        基于关键词匹配检索文档

        简单算法:
        1. 将查询分词
        2. 计算每个文档包含的关键词数量
        3. 按匹配度排序
        """
        if not self.documents:
            return []

        # 简单分词 (按空格)
        query_terms = set(query.lower().split())

        # 计算每个文档的匹配分数
        scored_docs = []
        for doc in self.documents:
            # 应用过滤器
            if filters and not self._match_filters(doc, filters):
                continue

            # 计算匹配分数
            doc_terms = set(doc.content.lower().split())
            matches = query_terms.intersection(doc_terms)
            score = len(matches) / len(query_terms) if query_terms else 0.0

            if score > 0:
                # 创建副本并设置分数
                doc_with_score = Document(
                    content=doc.content,
                    metadata=doc.metadata,
                    score=score,
                    doc_id=doc.doc_id
                )
                scored_docs.append(doc_with_score)

        # 按分数排序
        scored_docs.sort(key=lambda d: d.score or 0, reverse=True)

        return scored_docs[:top_k]

    async def add_documents(self, documents: List[Document]) -> None:
        """添加文档到内存"""
        for doc in documents:
            # 分配 ID (如果没有)
            if doc.doc_id is None:
                doc.doc_id = str(len(self.documents))

            self.documents.append(doc)

    def _match_filters(self, doc: Document, filters: Dict[str, Any]) -> bool:
        """检查文档是否匹配过滤条件"""
        if not doc.metadata:
            return False

        for key, value in filters.items():
            if doc.metadata.get(key) != value:
                return False

        return True

    def clear(self) -> None:
        """清空所有文档"""
        self.documents.clear()

    def __len__(self) -> int:
        """返回文档数量"""
        return len(self.documents)
