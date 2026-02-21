"""
OpenAI Embedding Provider

基于最简实现原则的OpenAI嵌入提供者。
"""

import os
from typing import Any

from loom.memory.vector_store import EmbeddingProvider

try:
    from openai import AsyncOpenAI
except ImportError:
    raise ImportError("OpenAI SDK not installed. Install with: pip install openai") from None


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI Embedding Provider

    使用OpenAI API生成文本向量嵌入。

    使用方式：
        provider = OpenAIEmbeddingProvider(
            api_key="sk-...",
            model="text-embedding-3-small"
        )
        embedding = await provider.embed("Hello, world!")
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "text-embedding-3-small",
        timeout: float = 60.0,
        **kwargs: Any,
    ):
        """
        初始化OpenAI Embedding Provider

        Args:
            api_key: API Key（默认从环境变量读取）
            base_url: Base URL（可选）
            model: 嵌入模型名称
            timeout: 超时时间
            **kwargs: 其他参数
        """
        self.model = model

        # 创建OpenAI客户端
        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
            timeout=timeout,
            **kwargs,
        )

    async def embed(self, text: str) -> list[float]:
        """
        生成单个文本的向量嵌入

        Args:
            text: 输入文本

        Returns:
            向量嵌入
        """
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )

        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        批量生成向量嵌入

        Args:
            texts: 输入文本列表

        Returns:
            向量嵌入列表
        """
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
        )

        return [item.embedding for item in response.data]
