"""Chunkers — split documents into chunks."""

from __future__ import annotations

from ..types import Document, Chunk


class FixedSizeChunker:
    def __init__(self, size: int = 512, overlap: int = 64) -> None:
        self._size = size
        self._overlap = overlap

    def chunk(self, doc: Document) -> list[Chunk]:
        text = doc.content
        chunks: list[Chunk] = []
        start = 0
        idx = 0
        while start < len(text):
            end = start + self._size
            chunks.append(Chunk(
                id=f"{doc.id}_c{idx}",
                content=text[start:end],
                document_id=doc.id,
                tokens=len(text[start:end]) // 4 + 1,
            ))
            idx += 1
            start = end - self._overlap if end < len(text) else end
        return chunks


class RecursiveChunker:
    def __init__(self, max_size: int = 1024, separators: list[str] | None = None) -> None:
        self._max = max_size
        self._seps = separators or ["\n\n", "\n", ". ", " "]

    def chunk(self, doc: Document) -> list[Chunk]:
        parts = self._split(doc.content, 0)
        return [
            Chunk(id=f"{doc.id}_c{i}", content=p, document_id=doc.id, tokens=len(p) // 4 + 1)
            for i, p in enumerate(parts)
        ]

    def _split(self, text: str, sep_idx: int) -> list[str]:
        if len(text) <= self._max or sep_idx >= len(self._seps):
            return [text] if text else []
        sep = self._seps[sep_idx]
        pieces = text.split(sep)
        result: list[str] = []
        buf = ""
        for p in pieces:
            candidate = buf + sep + p if buf else p
            if len(candidate) > self._max and buf:
                result.extend(self._split(buf, sep_idx + 1))
                buf = p
            else:
                buf = candidate
        if buf:
            result.extend(self._split(buf, sep_idx + 1))
        return result
