"""Memory types."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from .messages import Message


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    content: str = ""
    tokens: int = 0
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@runtime_checkable
class MemoryLayer(Protocol):
    name: str
    token_budget: int
    current_tokens: int
    async def store(self, entry: MemoryEntry) -> None: ...
    async def retrieve(self, query: str, limit: int) -> list[MemoryEntry]: ...
    async def evict(self) -> list[MemoryEntry]: ...


@dataclass
class SearchOptions:
    limit: int = 10
    mode: Literal["semantic", "keyword", "hybrid"] = "semantic"
    filter: dict[str, Any] | None = None


@runtime_checkable
class PersistentStore(Protocol):
    async def save(self, entry: MemoryEntry) -> None: ...
    async def search(self, query: str, opts: SearchOptions) -> list[MemoryEntry]: ...
    async def delete(self, id: str) -> None: ...


@runtime_checkable
class MemoryCompressor(Protocol):
    async def compress(self, entries: list[MemoryEntry]) -> MemoryEntry: ...


@runtime_checkable
class ImportanceScorer(Protocol):
    async def score(self, entry: MemoryEntry, context: list[Message]) -> float: ...


@runtime_checkable
class Tokenizer(Protocol):
    def count(self, text: str) -> int: ...
    def truncate(self, text: str, max_tokens: int) -> str: ...
