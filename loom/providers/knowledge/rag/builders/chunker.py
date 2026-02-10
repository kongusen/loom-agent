"""
文本分块器
"""

import uuid
from abc import ABC, abstractmethod

from loom.providers.knowledge.rag.builders.base import Document
from loom.providers.knowledge.rag.models.chunk import TextChunk


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
        chunks = []
        start = 0

        while start < len(content):
            end = start + self.chunk_size
            chunk_content = content[start:end]

            if chunk_content.strip():
                chunks.append(
                    TextChunk(
                        id=f"{document.id}_chunk_{len(chunks)}",
                        content=chunk_content,
                        document_id=document.id,
                        metadata={"start": start, "end": end},
                    )
                )

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
        chunks = []
        current_chunk = ""
        current_start = 0

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence
            else:
                if current_chunk.strip():
                    chunks.append(
                        TextChunk(
                            id=f"{document.id}_chunk_{len(chunks)}",
                            content=current_chunk.strip(),
                            document_id=document.id,
                            metadata={"chunk_index": len(chunks)},
                        )
                    )
                # 保留重叠部分
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                current_chunk = overlap_text + sentence

        # 处理最后一个块
        if current_chunk.strip():
            chunks.append(
                TextChunk(
                    id=f"{document.id}_chunk_{len(chunks)}",
                    content=current_chunk.strip(),
                    document_id=document.id,
                    metadata={"chunk_index": len(chunks)},
                )
            )

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
