"""
文本分块器
"""

import re
from abc import ABC, abstractmethod

from loom.providers.knowledge.rag.builders.base import Document
from loom.providers.knowledge.rag.models.chunk import TextChunk

# 英文停用词
_STOP_WORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "dare",
        "ought",
        "used",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "because",
        "but",
        "and",
        "or",
        "if",
        "while",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "they",
        "them",
        "their",
        "what",
        "which",
        "who",
        "whom",
        "none",
        "also",
        "about",
        "up",
    }
)

# 关键词提取模式
_CAMEL_CASE_RE = re.compile(
    r"[A-Z][a-z]+(?:[A-Z]+[a-z]*)+"
)  # handles acronyms like GraphRAGKnowledgeBase
_SNAKE_CASE_RE = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+")
_ALL_CAPS_RE = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
_DOTTED_PATH_RE = re.compile(r"[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)+")
_CAPITALIZED_RE = re.compile(r"\b[A-Z][a-z]{2,}\b")


def extract_chunk_keywords(text: str, max_keywords: int = 10) -> list[str]:
    """
    从文本中提取关键词（轻量文本处理，不调用 LLM）

    提取策略：CamelCase、snake_case、ALL_CAPS、dotted.path、大写开头词
    过滤停用词，返回 top-N 关键词。
    """
    if not text:
        return []

    seen: set[str] = set()
    keywords: list[str] = []

    def _add(word: str) -> None:
        lower = word.lower()
        if lower not in seen and lower not in _STOP_WORDS and len(word) > 1:
            seen.add(lower)
            keywords.append(word)

    # 高优先级：dotted path（如 loom.memory.core）
    for m in _DOTTED_PATH_RE.findall(text):
        _add(m)

    # CamelCase（如 GraphRAGKnowledgeBase）
    for m in _CAMEL_CASE_RE.findall(text):
        _add(m)

    # snake_case（如 chunk_store）
    for m in _SNAKE_CASE_RE.findall(text):
        _add(m)

    # ALL_CAPS（如 API, CONCEPT）
    for m in _ALL_CAPS_RE.findall(text):
        _add(m)

    # 大写开头词（如 Agent, Memory）
    for m in _CAPITALIZED_RE.findall(text):
        _add(m)

    return keywords[:max_keywords]


class ChunkingStrategy(ABC):
    """分块策略抽象接口"""

    @abstractmethod
    def chunk(self, document: Document) -> list[TextChunk]:
        """
        将文档分块

        Args:
            document: 输入文档

        Returns:
            文本块列表
        """
        pass


class SimpleChunker(ChunkingStrategy):
    """
    简单分块器

    按固定大小分块，不考虑语义边界
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document: Document) -> list[TextChunk]:
        """按固定大小分块"""
        content = document.content
        chunks: list[TextChunk] = []
        start = 0

        while start < len(content):
            end = start + self.chunk_size
            chunk_content = content[start:end]

            if chunk_content.strip():
                tc = TextChunk(
                    id=f"{document.id}_chunk_{len(chunks)}",
                    content=chunk_content,
                    document_id=document.id,
                    metadata={"start": start, "end": end},
                )
                tc.keywords = extract_chunk_keywords(chunk_content)
                chunks.append(tc)

            start = end - self.chunk_overlap
            if start >= len(content):
                break

        return chunks


class SlidingWindowChunker(ChunkingStrategy):
    """
    滑动窗口分块器

    按句子边界分块，保持语义完整性
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: list[str] | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["。", "！", "？", ".", "!", "?", "\n\n", "\n"]

    def chunk(self, document: Document) -> list[TextChunk]:
        """按句子边界分块"""
        content = document.content
        sentences = self._split_sentences(content)
        chunks: list[TextChunk] = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence
            else:
                if current_chunk.strip():
                    stripped = current_chunk.strip()
                    tc = TextChunk(
                        id=f"{document.id}_chunk_{len(chunks)}",
                        content=stripped,
                        document_id=document.id,
                        metadata={"chunk_index": len(chunks)},
                    )
                    tc.keywords = extract_chunk_keywords(stripped)
                    chunks.append(tc)
                # 保留重叠部分
                overlap_text = (
                    current_chunk[-self.chunk_overlap :]
                    if len(current_chunk) > self.chunk_overlap
                    else ""
                )
                current_chunk = overlap_text + sentence

        # 处理最后一个块
        if current_chunk.strip():
            stripped = current_chunk.strip()
            tc = TextChunk(
                id=f"{document.id}_chunk_{len(chunks)}",
                content=stripped,
                document_id=document.id,
                metadata={"chunk_index": len(chunks)},
            )
            tc.keywords = extract_chunk_keywords(stripped)
            chunks.append(tc)

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """按分隔符切分句子"""
        sentences = [text]
        for sep in self.separators:
            new_sentences = []
            for s in sentences:
                parts = s.split(sep)
                for i, part in enumerate(parts):
                    if i < len(parts) - 1:
                        new_sentences.append(part + sep)
                    elif part:
                        new_sentences.append(part)
            sentences = new_sentences
        return sentences
