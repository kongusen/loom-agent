"""Semantic memory with embeddings"""

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MemoryEntry:
    """Memory entry with embedding"""
    content: str
    embedding: list[float] | None = None
    metadata: dict | None = None


class SemanticMemory:
    """Semantic memory with vector search, max-size eviction, and optional persistence."""

    def __init__(self, max_size: int = 10_000, persist_path: str | None = None):
        self.max_size = max_size
        self.persist_path = persist_path
        self.entries: list[MemoryEntry] = []
        if persist_path and os.path.exists(persist_path):
            self._load(persist_path)

    def add(self, entry: MemoryEntry):
        """Add memory entry, evicting oldest if over max_size."""
        self.entries.append(entry)
        if len(self.entries) > self.max_size:
            self.entries = self.entries[-self.max_size:]
        if self.persist_path:
            self._save(self.persist_path)

    def search(
        self,
        query: str,
        top_k: int = 5,
        query_embedding: list[float] | None = None,
    ) -> list[MemoryEntry]:
        """Search similar memories using embeddings or lexical fallback."""
        if top_k <= 0 or not self.entries:
            return []

        scored = [
            (
                self._score_entry(query, entry, query_embedding=query_embedding),
                index,
                entry,
            )
            for index, entry in enumerate(self.entries)
        ]
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [entry for _, _, entry in scored[:top_k]]

    def _score_entry(
        self,
        query: str,
        entry: MemoryEntry,
        query_embedding: list[float] | None = None,
    ) -> float:
        if query_embedding is not None and entry.embedding is not None:
            return self._cosine_similarity(query_embedding, entry.embedding)
        return self._lexical_similarity(query, entry.content)

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)

    def _lexical_similarity(self, query: str, content: str) -> float:
        query_tokens = self._tokenize(query)
        content_tokens = self._tokenize(content)
        if not query_tokens or not content_tokens:
            return 0.0
        overlap = len(query_tokens & content_tokens)
        union = len(query_tokens | content_tokens)
        return overlap / union if union else 0.0

    def _tokenize(self, text: str) -> set[str]:
        return {token.strip(".,:;!?()[]{}\"'").lower() for token in text.split() if token.strip()}

    def _save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = [
            {"content": e.content, "embedding": e.embedding, "metadata": e.metadata}
            for e in self.entries
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def _load(self, path: str) -> None:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.entries = [
                MemoryEntry(content=d["content"], embedding=d.get("embedding"), metadata=d.get("metadata"))
                for d in data
            ]
        except Exception:
            self.entries = []
