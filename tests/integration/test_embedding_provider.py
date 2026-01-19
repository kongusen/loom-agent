"""
Embedding Provider 集成测试

测试真实API调用。需要配置环境变量才能运行：
- OPENAI_API_KEY: OpenAI API密钥
- ENABLE_REAL_API_TESTS=true: 启用真实API测试

运行方式：
    pytest tests/integration/test_embedding_provider.py -v
"""

import pytest

from loom.providers.embedding.openai import OpenAIEmbeddingProvider
from tests.api_config import requires_real_api


class TestOpenAIEmbeddingProviderIntegration:
    """OpenAI Embedding Provider 真实API集成测试"""

    @requires_real_api
    @pytest.mark.asyncio
    async def test_embed_single_text(self, embedding_config):
        """测试单个文本的embedding生成"""
        provider = OpenAIEmbeddingProvider(
            api_key=embedding_config["api_key"],
            base_url=embedding_config["base_url"],
            model=embedding_config["model"],
            timeout=embedding_config["timeout"],
        )

        text = "Hello, world!"
        embedding = await provider.embed(text)

        # 验证embedding
        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    @requires_real_api
    @pytest.mark.asyncio
    async def test_embed_chinese_text(self, embedding_config):
        """测试中文文本的embedding生成"""
        provider = OpenAIEmbeddingProvider(
            api_key=embedding_config["api_key"],
            base_url=embedding_config["base_url"],
            model=embedding_config["model"],
        )

        text = "你好，世界！"
        embedding = await provider.embed(text)

        # 验证embedding
        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) > 0

    @requires_real_api
    @pytest.mark.asyncio
    async def test_embed_batch(self, embedding_config):
        """测试批量embedding生成"""
        provider = OpenAIEmbeddingProvider(
            api_key=embedding_config["api_key"],
            base_url=embedding_config["base_url"],
            model=embedding_config["model"],
        )

        texts = ["First text", "Second text", "Third text"]
        embeddings = await provider.embed_batch(texts)

        # 验证embeddings
        assert embeddings is not None
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3

        for embedding in embeddings:
            assert isinstance(embedding, list)
            assert len(embedding) > 0
            assert all(isinstance(x, float) for x in embedding)

    @requires_real_api
    @pytest.mark.asyncio
    async def test_embed_consistency(self, embedding_config):
        """测试相同文本生成的embedding一致性"""
        provider = OpenAIEmbeddingProvider(
            api_key=embedding_config["api_key"],
            base_url=embedding_config["base_url"],
            model=embedding_config["model"],
        )

        text = "Consistency test"

        # 生成两次embedding
        embedding1 = await provider.embed(text)
        embedding2 = await provider.embed(text)

        # 验证两次结果应该相同或非常接近
        assert len(embedding1) == len(embedding2)

        # 计算余弦相似度应该接近1
        import numpy as np

        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        assert similarity > 0.99  # 应该非常相似
