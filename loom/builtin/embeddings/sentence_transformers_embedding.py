"""Sentence Transformers Embedding 适配器（本地模型）"""

from __future__ import annotations

from typing import List

from loom.interfaces.embedding import BaseEmbedding

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class SentenceTransformersEmbedding(BaseEmbedding):
    """
    Sentence Transformers 本地 Embedding 适配器

    特点:
    - ✅ 完全本地运行，无需 API
    - ✅ 支持多种预训练模型
    - ✅ 支持多语言
    - ✅ GPU 加速支持

    推荐模型:
    - all-MiniLM-L6-v2 (384 维, 快速)
    - all-mpnet-base-v2 (768 维, 平衡)
    - paraphrase-multilingual-MiniLM-L12-v2 (384 维, 多语言)

    示例:
        from loom.builtin.embeddings import SentenceTransformersEmbedding

        # 英文模型
        embedding = SentenceTransformersEmbedding(
            model_name="all-MiniLM-L6-v2"
        )

        # 多语言模型
        embedding = SentenceTransformersEmbedding(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
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
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        batch_size: int = 32,
        normalize_embeddings: bool = True,
    ):
        """
        Parameters:
            model_name: 模型名称（HuggingFace 模型 ID）
            device: 设备 ('cpu', 'cuda', 'mps')
            batch_size: 批处理大小
            normalize_embeddings: 是否归一化向量
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "Sentence Transformers is not installed. "
                "Install with: pip install sentence-transformers"
            )

        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.normalize_embeddings = normalize_embeddings

        # 加载模型
        self.model = SentenceTransformer(model_name, device=device)

    async def embed_query(self, text: str) -> List[float]:
        """
        对单个查询文本进行向量化

        Parameters:
            text: 查询文本

        Returns:
            向量（列表）
        """
        # Sentence Transformers 的 encode 是同步的
        # 在 async 函数中直接调用（小型模型通常很快）
        embedding = self.model.encode(
            text,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True
        )
        return embedding.tolist()

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
            dimension = self.get_dimension()
            return [[0.0] * dimension] * len(texts)

        # 批量编码
        embeddings = self.model.encode(
            non_empty_texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=False
        )

        vectors = embeddings.tolist()

        # 处理空文本位置
        result = []
        non_empty_idx = 0
        dimension = len(vectors[0])

        for text in texts:
            if text.strip():
                result.append(vectors[non_empty_idx])
                non_empty_idx += 1
            else:
                result.append([0.0] * dimension)

        return result

    def get_dimension(self) -> int:
        """返回向量维度"""
        return self.model.get_sentence_embedding_dimension()
