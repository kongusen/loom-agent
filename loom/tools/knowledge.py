"""外部知识检索治理链 - RAG as Evidence"""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class EvidencePack:
    """证据包"""
    question: str
    sources: list[str] = field(default_factory=list)
    chunks: list[dict] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    relevance_score: float = 0.0


class KnowledgePipeline:
    """知识检索治理链

    支持两种相似度计算方式：
    1. 词法相似度（默认，无需外部依赖）
    2. 语义相似度（使用 embedding，需要提供 embedding_fn）
    """

    def __init__(
        self,
        embedding_fn: Callable[[str], list[float]] | None = None,
        rerank_retrieval_weight: float = 0.7,
        rerank_goal_weight: float = 0.3,
        embedding_cache_max: int = 1000,
    ):
        self.sources: dict[str, Any] = {}
        self.embedding_fn = embedding_fn
        self.rerank_retrieval_weight = rerank_retrieval_weight
        self.rerank_goal_weight = rerank_goal_weight
        self._embedding_cache: dict[str, list[float]] = {}
        self._embedding_cache_max = embedding_cache_max

    def register_source(self, source_id: str, source: Any) -> None:
        """Register a knowledge source."""
        self.sources[source_id] = source

    def retrieve(self, question: str, goal: str, top_k: int = 5) -> EvidencePack:
        """检索知识并生成证据包"""
        candidates = self._retrieve_candidates(question)
        ranked = self._rerank(candidates, goal)
        top_chunks = ranked[:top_k]
        return EvidencePack(
            question=question,
            sources=self._collect_sources(top_chunks),
            chunks=top_chunks,
            citations=self._build_citations(top_chunks),
            relevance_score=self._aggregate_relevance(top_chunks),
        )

    def _retrieve_candidates(self, question: str) -> list[dict]:
        """召回候选片段"""
        candidates: list[dict] = []
        for source_id, source in self.sources.items():
            for chunk in self._load_chunks(source_id, source, question):
                content = chunk.get("content", "")
                score = self._similarity(question, content)
                if score <= 0:
                    continue

                candidate = dict(chunk)
                candidate["source"] = chunk.get("source", source_id)
                candidate["retrieval_score"] = score
                candidates.append(candidate)

        candidates.sort(
            key=lambda item: item.get("retrieval_score", 0.0),
            reverse=True,
        )
        return candidates

    def _rerank(self, candidates: list[dict], goal: str) -> list[dict]:
        """重排序"""
        ranked = []
        for candidate in candidates:
            goal_score = self._similarity(goal, candidate.get("content", ""))
            final_score = (candidate.get("retrieval_score", 0.0) * self.rerank_retrieval_weight
                           + goal_score * self.rerank_goal_weight)
            reranked = dict(candidate)
            reranked["goal_score"] = goal_score
            reranked["score"] = final_score
            ranked.append(reranked)

        ranked.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return ranked

    def _load_chunks(self, source_id: str, source: Any, question: str) -> list[dict]:
        """Normalize source data into chunk dictionaries."""
        data = source(question) if callable(source) else source

        if isinstance(data, dict):
            if "chunks" in data:
                data = data["chunks"]
            else:
                data = [data]

        if not isinstance(data, list):
            return []

        normalized: list[dict] = []
        for item in data:
            if isinstance(item, str):
                normalized.append({"content": item, "source": source_id})
            elif isinstance(item, dict):
                chunk = dict(item)
                chunk.setdefault("source", source_id)
                normalized.append(chunk)
        return normalized

    def _collect_sources(self, chunks: list[dict]) -> list[str]:
        """Collect unique source ids in ranked order."""
        sources: list[str] = []
        for chunk in chunks:
            source = chunk.get("source", "")
            if source and source not in sources:
                sources.append(source)
        return sources

    def _build_citations(self, chunks: list[dict]) -> list[str]:
        """Build lightweight citation strings."""
        citations: list[str] = []
        for chunk in chunks:
            source = chunk.get("source", "")
            title = chunk.get("title", "")
            citation = f"{source}: {title}".strip(": ").strip()
            citations.append(citation or source)
        return citations

    def _aggregate_relevance(self, chunks: list[dict]) -> float:
        """Aggregate overall relevance score."""
        if not chunks:
            return 0.0
        return sum(chunk.get("score", 0.0) for chunk in chunks) / len(chunks)

    def _similarity(self, left: str, right: str) -> float:
        """Compute similarity between two texts

        Uses semantic similarity if embedding_fn is provided,
        otherwise falls back to lexical similarity.

        Args:
            left: First text
            right: Second text

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if self.embedding_fn:
            return self._semantic_similarity(left, right)
        else:
            return self._lexical_similarity(left, right)

    def _semantic_similarity(self, left: str, right: str) -> float:
        """Compute semantic similarity using embeddings

        Args:
            left: First text
            right: Second text

        Returns:
            Cosine similarity between 0.0 and 1.0
        """
        try:
            # Get embeddings (with caching)
            left_emb = self._get_embedding(left)
            right_emb = self._get_embedding(right)

            if not left_emb or not right_emb:
                # Fallback to lexical if embedding fails
                return self._lexical_similarity(left, right)

            # Compute cosine similarity
            return self._cosine_similarity(left_emb, right_emb)

        except Exception:
            # Fallback to lexical if any error
            return self._lexical_similarity(left, right)

    def _get_embedding(self, text: str) -> list[float] | None:
        """Get embedding for text with caching

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if failed
        """
        if not text or not self.embedding_fn:
            return None

        # Check cache
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        try:
            embedding = self.embedding_fn(text)
            if len(self._embedding_cache) >= self._embedding_cache_max:
                # evict oldest entry
                oldest = next(iter(self._embedding_cache))
                del self._embedding_cache[oldest]
            self._embedding_cache[text] = embedding
            return embedding

        except Exception:
            return None

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity between 0.0 and 1.0
        """
        if len(vec1) != len(vec2):
            return 0.0

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Magnitudes
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5

        if mag1 == 0 or mag2 == 0:
            return 0.0

        # Cosine similarity
        cosine = dot_product / (mag1 * mag2)

        # Normalize to [0, 1] range (cosine is in [-1, 1])
        return (cosine + 1) / 2

    def _lexical_similarity(self, left: str, right: str) -> float:
        """Compute lexical similarity by token overlap (fallback)

        Args:
            left: First text
            right: Second text

        Returns:
            Jaccard similarity between 0.0 and 1.0
        """
        left_tokens = self._tokenize(left)
        right_tokens = self._tokenize(right)
        if not left_tokens or not right_tokens:
            return 0.0

        overlap = len(left_tokens & right_tokens)
        union = len(left_tokens | right_tokens)
        return overlap / union if union else 0.0

    def _tokenize(self, text: str) -> set[str]:
        """Tokenize text into lowercase terms."""
        return {
            token.strip(".,:;!?()[]{}\"'").lower()
            for token in text.split()
            if token.strip()
        }
