"""OpenAI Embedding 适配器"""

from __future__ import annotations

from typing import List

from loom.interfaces.embedding import BaseEmbedding

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIEmbedding(BaseEmbedding):
    """
    OpenAI Embedding 适配器

    支持模型:
    - text-embedding-3-small (1536 维, 最便宜)
    - text-embedding-3-large (3072 维, 最强)
    - text-embedding-ada-002 (1536 维, 旧版)

    示例:
        from loom.builtin.embeddings import OpenAIEmbedding

        embedding = OpenAIEmbedding(
            api_key="your-api-key",
            model="text-embedding-3-small"
        )

        # 单个文本
        vector = await embedding.embed_query("Hello world")

        # 批量文本
        vectors = await embedding.embed_documents([
            "Hello world",
            "Loom framework"
        ])
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ):
        """
        Parameters:
            api_key: OpenAI API Key
            model: 模型名称
            dimensions: 向量维度（可选，text-embedding-3-* 支持）
            base_url: API 基础 URL（可选，用于代理）
            timeout: 请求超时时间（秒）
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI client is not installed. "
                "Install with: pip install openai"
            )

        self.model = model
        self.dimensions = dimensions
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )

    async def embed_query(self, text: str) -> List[float]:
        """
        对单个查询文本进行向量化

        Parameters:
            text: 查询文本

        Returns:
            向量（列表）
        """
        vectors = await self.embed_documents([text])
        return vectors[0]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量向量化文档

        Parameters:
            texts: 文本列表

        Returns:
            向量列表
        """
        # 过滤空文本
        non_empty_texts = [t for t in texts if t.strip()]

        if not non_empty_texts:
            return [[0.0] * (self.dimensions or 1536)] * len(texts)

        # 调用 OpenAI Embedding API
        kwargs = {"input": non_empty_texts, "model": self.model}
        if self.dimensions:
            kwargs["dimensions"] = self.dimensions

        response = await self.client.embeddings.create(**kwargs)

        # 提取向量
        vectors = [item.embedding for item in response.data]

        # 处理空文本位置
        result = []
        non_empty_idx = 0
        for text in texts:
            if text.strip():
                result.append(vectors[non_empty_idx])
                non_empty_idx += 1
            else:
                result.append([0.0] * len(vectors[0]))

        return result

    def get_dimension(self) -> int:
        """返回向量维度"""
        if self.dimensions:
            return self.dimensions

        # 默认维度
        dimension_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dimension_map.get(self.model, 1536)
