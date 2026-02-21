"""
图知识库实现

基于知识图谱的增强检索，支持混合搜索（向量+图谱）
"""

from typing import Any

from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem


class GraphKnowledgeBase(KnowledgeBaseProvider):
    """
    基于知识图谱的知识库实现

    特点：
    - 支持图谱多跳扩展
    - 混合搜索（向量+图谱）
    - 自动重排序
    - 灵活的权重配置
    """

    def __init__(
        self,
        graph_rag_service: Any,
        search_mode: str = "hybrid",
        max_hops: int = 2,
        vector_weight: float = 0.5,
        graph_weight: float = 0.5,
        rerank_enabled: bool = True,
    ):
        """
        初始化图知识库

        Args:
            graph_rag_service: GraphRAGSearchService实例
            search_mode: 搜索模式（'vector'/'graph'/'hybrid'）
            max_hops: 图谱最大跳数
            vector_weight: 向量搜索权重
            graph_weight: 图搜索权重
            rerank_enabled: 是否启用重排序
        """
        self.graph_rag = graph_rag_service
        self.search_mode = search_mode
        self.max_hops = max_hops
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
        self.rerank_enabled = rerank_enabled

    async def query(
        self,
        query: str,
        limit: int = 5,
        _filters: dict[str, Any] | None = None,
    ) -> list[KnowledgeItem]:
        """
        查询知识库（使用图谱增强检索）

        Args:
            query: 查询文本
            limit: 返回结果数量
            _filters: 过滤条件（暂未使用）

        Returns:
            匹配的知识条目列表
        """
        # 调用GraphRAG搜索
        result = await self.graph_rag.search(
            query=query,
            top_k=limit,
            max_hops=self.max_hops,
            search_mode=self.search_mode,
            rerank_enabled=self.rerank_enabled,
            vector_weight=self.vector_weight,
            graph_weight=self.graph_weight,
        )

        # 转换为KnowledgeItem列表
        knowledge_items = []
        for idx, item in enumerate(result.get("results", [])):
            knowledge_items.append(
                KnowledgeItem(
                    id=item.get("id", f"graph_{idx}"),
                    content=item.get("content", ""),
                    source=item.get("source", "graph_rag"),
                    relevance=item.get("score", 0.0),
                    metadata=item,
                )
            )

        return knowledge_items

    async def get_by_id(self, _knowledge_id: str) -> KnowledgeItem | None:
        """
        根据ID获取知识条目

        注意：图谱搜索主要用于语义查询，不支持按ID精确查询

        Args:
            _knowledge_id: 知识条目ID

        Returns:
            None（不支持按ID查询）
        """
        return None
