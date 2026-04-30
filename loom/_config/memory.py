"""Configuration contracts for the public Loom API."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MemoryBackend:
    """Stable memory backend definition."""

    name: str
    options: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def in_memory(
        cls,
        *,
        extensions: dict[str, Any] | None = None,
    ) -> MemoryBackend:
        return cls(name="in_memory", extensions=dict(extensions or {}))

    @classmethod
    def custom(
        cls,
        name: str,
        *,
        options: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> MemoryBackend:
        return cls(
            name=name,
            options=dict(options or {}),
            extensions=dict(extensions or {}),
        )


@dataclass(slots=True)
class MemoryQuery:
    """Stable long-term memory retrieval request."""

    text: str
    session_id: str | None = None
    top_k: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MemoryRecord:
    """One durable memory item."""

    content: str
    key: str = ""
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MemoryRecall:
    """Resolved memory records for one query."""

    query: MemoryQuery
    records: list[MemoryRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)


class MemoryStore(ABC):
    """Pluggable long-term memory storage boundary."""

    @abstractmethod
    def search(self, query: MemoryQuery) -> list[MemoryRecord]:
        """Return records relevant to the query."""

    @abstractmethod
    def upsert(self, record: MemoryRecord, query: MemoryQuery | None = None) -> None:
        """Persist or update one extracted memory record."""


@dataclass(slots=True)
class MemoryResolver:
    """Adapter for long-term memory retrieval."""

    handler: Callable[[MemoryQuery], MemoryRecall | list[MemoryRecord]]
    mode: str = "callable"
    description: str = ""
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def callable(
        cls,
        handler: Callable[[MemoryQuery], MemoryRecall | list[MemoryRecord]],
        *,
        description: str = "",
        extensions: dict[str, Any] | None = None,
    ) -> MemoryResolver:
        return cls(
            handler=handler,
            mode="callable",
            description=description,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def static(
        cls,
        records: list[str] | list[MemoryRecord],
        *,
        description: str = "",
        extensions: dict[str, Any] | None = None,
    ) -> MemoryResolver:
        normalized = _normalize_memory_records(records)

        def _handler(query: MemoryQuery) -> MemoryRecall:
            return MemoryRecall(query=query, records=normalized[: query.top_k])

        return cls(
            handler=_handler,
            mode="static",
            description=description,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def from_store(
        cls,
        store: MemoryStore,
        *,
        description: str = "",
        extensions: dict[str, Any] | None = None,
    ) -> MemoryResolver:
        def _handler(query: MemoryQuery) -> MemoryRecall:
            return MemoryRecall(query=query, records=store.search(query)[: query.top_k])

        return cls(
            handler=_handler,
            mode="store",
            description=description,
            extensions=dict(extensions or {}),
        )

    def retrieve(self, query: MemoryQuery) -> MemoryRecall:
        recall = self.handler(query)
        if isinstance(recall, MemoryRecall):
            return recall
        if isinstance(recall, list) and all(isinstance(item, MemoryRecord) for item in recall):
            return MemoryRecall(query=query, records=recall)
        raise TypeError(
            "memory resolver must return MemoryRecall or list[MemoryRecord], "
            f"got {type(recall).__name__}"
        )


@dataclass(slots=True)
class MemoryExtractor:
    """Adapter for extracting durable memories from completed turns."""

    handler: Callable[..., list[MemoryRecord]]
    mode: str = "callable"
    description: str = ""
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def callable(
        cls,
        handler: Callable[..., list[MemoryRecord]],
        *,
        description: str = "",
        extensions: dict[str, Any] | None = None,
    ) -> MemoryExtractor:
        return cls(
            handler=handler,
            mode="callable",
            description=description,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def none(cls) -> MemoryExtractor:
        def _handler(
            user_content: str,
            assistant_content: str,
            *,
            session_id: str | None = None,
        ) -> list[MemoryRecord]:
            _ = user_content, assistant_content, session_id
            return []

        return cls(handler=_handler, mode="none")

    def extract(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str | None = None,
    ) -> list[MemoryRecord]:
        records = self.handler(
            user_content,
            assistant_content,
            session_id=session_id,
        )
        if not isinstance(records, list) or not all(
            isinstance(record, MemoryRecord) for record in records
        ):
            raise TypeError("memory extractor must return list[MemoryRecord]")
        return records


@dataclass(slots=True)
class MemorySource:
    """Declarative long-term memory source for user-facing configuration."""

    name: str
    resolver: MemoryResolver
    extractor: MemoryExtractor = field(default_factory=MemoryExtractor.none)
    store: MemoryStore | None = None
    instructions: str = ""
    top_k: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def long_term(
        cls,
        name: str,
        *,
        resolver: MemoryResolver | None = None,
        extractor: MemoryExtractor | None = None,
        store: MemoryStore | None = None,
        instructions: str = "",
        top_k: int = 5,
        metadata: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> MemorySource:
        if resolver is None:
            if store is None:
                raise TypeError("MemorySource.long_term() requires resolver or store")
            resolver = MemoryResolver.from_store(store)
        return cls(
            name=name,
            resolver=resolver,
            extractor=extractor or MemoryExtractor.none(),
            store=store,
            instructions=instructions,
            top_k=top_k,
            metadata=dict(metadata or {}),
            extensions=dict(extensions or {}),
        )

    @classmethod
    def static(
        cls,
        name: str,
        records: list[str] | list[MemoryRecord],
        *,
        instructions: str = "",
        top_k: int = 5,
    ) -> MemorySource:
        return cls(
            name=name,
            resolver=MemoryResolver.static(records),
            instructions=instructions,
            top_k=top_k,
        )

    def system_prompt(self) -> str:
        return self.instructions

    def is_available(self) -> bool:
        return True

    def prefetch(self, query: str, *, session_id: str | None = None) -> str:
        recall = self.resolver.retrieve(
            MemoryQuery(
                text=query,
                session_id=session_id,
                top_k=self.top_k,
                metadata=dict(self.metadata),
            )
        )
        return "\n".join(record.content for record in recall.records if record.content)

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str | None = None,
    ) -> None:
        records = self.extractor.extract(
            user_content,
            assistant_content,
            session_id=session_id,
        )
        if self.store is None:
            return
        query = MemoryQuery(
            text=user_content,
            session_id=session_id,
            top_k=self.top_k,
            metadata=dict(self.metadata),
        )
        for record in records:
            self.store.upsert(record, query=query)


@dataclass(slots=True)
class MemoryConfig:
    """Session memory configuration."""

    enabled: bool = True
    backend: MemoryBackend = field(default_factory=MemoryBackend.in_memory)
    namespace: str | None = None
    sources: list[MemorySource] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def none(cls) -> MemoryConfig:
        """Disable runtime memory."""
        return cls(enabled=False)

    @classmethod
    def session(
        cls,
        *,
        backend: MemoryBackend | None = None,
        namespace: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> MemoryConfig:
        """Enable session-scoped memory."""
        return cls(
            enabled=True,
            backend=backend or MemoryBackend.in_memory(),
            namespace=namespace,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def with_sources(
        cls,
        sources: list[MemorySource],
        *,
        backend: MemoryBackend | None = None,
        namespace: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> MemoryConfig:
        """Enable memory with explicit long-term memory sources."""
        return cls(
            enabled=True,
            backend=backend or MemoryBackend.in_memory(),
            namespace=namespace,
            sources=list(sources),
            extensions=dict(extensions or {}),
        )

    @classmethod
    def semantic(
        cls,
        store: MemoryStore,
        *,
        name: str = "semantic",
        resolver: MemoryResolver | None = None,
        extractor: MemoryExtractor | None = None,
        instructions: str = "",
        top_k: int = 5,
    ) -> MemoryConfig:
        """Enable semantic memory backed by a memory store."""
        return cls.with_sources(
            [
                MemorySource.long_term(
                    name,
                    resolver=resolver,
                    extractor=extractor,
                    store=store,
                    instructions=instructions,
                    top_k=top_k,
                )
            ]
        )


def _normalize_memory_records(records: list[str] | list[MemoryRecord]) -> list[MemoryRecord]:
    normalized: list[MemoryRecord] = []
    for record in records:
        if isinstance(record, MemoryRecord):
            normalized.append(record)
        else:
            normalized.append(MemoryRecord(content=str(record)))
    return normalized
