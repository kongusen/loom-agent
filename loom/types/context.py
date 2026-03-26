"""Context types."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class ContextSource(str, Enum):
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"
    SKILL = "skill"
    CLUSTER = "cluster"
    MITOSIS = "mitosis"


@dataclass
class ContextFragment:
    source: ContextSource
    content: str
    tokens: int
    relevance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ContextProvider(Protocol):
    source: ContextSource

    async def provide(self, query: str, budget: int) -> list[ContextFragment]: ...


@dataclass
class TokenBudget:
    total: int = 4096
    reserved_output: int = 1024
    system_prompt_tokens: int = 0
    available: int = 0


BudgetRatios = dict[ContextSource, float]


# --- Axiom 1: Context Partition ---


@dataclass
class ContextPartition:
    """单个上下文分区（公理一）"""
    name: str
    content: str
    tokens: int
    priority: int  # 5=system, 4=working, 3=memory, 2=skill, 1=history
    writable: bool
    compressible: bool


# --- Knowledge types ---


@dataclass
class Document:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    content: str = ""
    document_id: str = ""
    tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    chunk: Chunk
    score: float = 0.0


@dataclass
class RetrieverOptions:
    limit: int = 10
    filter: dict[str, Any] | None = None


@runtime_checkable
class Chunker(Protocol):
    def chunk(self, doc: Document) -> list[Chunk]: ...


@runtime_checkable
class Retriever(Protocol):
    async def retrieve(
        self, query: str, opts: RetrieverOptions | None = None
    ) -> list[RetrievalResult]: ...


# --- Skill types (removed trigger mechanism for Claude standard alignment) ---
