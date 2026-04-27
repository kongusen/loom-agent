"""Configuration contracts for the public Loom API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class KnowledgeDocument:
    """Stable declarative knowledge document."""

    content: str
    title: str = ""
    uri: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_context_payload(self) -> dict[str, Any]:
        payload = {
            "content": self.content,
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.title:
            payload["title"] = self.title
        if self.uri:
            payload["uri"] = self.uri
        return payload


@dataclass(slots=True)
class KnowledgeQuery:
    """Stable retrieval request for one execution."""

    text: str
    goal: str = ""
    top_k: int = 5
    source_names: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_context_payload(self) -> dict[str, Any]:
        payload = {
            "text": self.text,
            "top_k": self.top_k,
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.goal:
            payload["goal"] = self.goal
        if self.source_names:
            payload["source_names"] = list(self.source_names)
        return payload


@dataclass(slots=True)
class KnowledgeCitation:
    """Stable citation attached to evidence."""

    source_name: str
    title: str = ""
    uri: str = ""
    snippet: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_context_payload(self) -> dict[str, Any]:
        payload = {
            "source_name": self.source_name,
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.title:
            payload["title"] = self.title
        if self.uri:
            payload["uri"] = self.uri
        if self.snippet:
            payload["snippet"] = self.snippet
        return payload


@dataclass(slots=True)
class KnowledgeEvidenceItem:
    """Stable evidence item used at execution time."""

    source_name: str
    content: str
    title: str = ""
    uri: str = ""
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_context_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_name": self.source_name,
            "content": self.content,
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.title:
            payload["title"] = self.title
        if self.uri:
            payload["uri"] = self.uri
        if self.score is not None:
            payload["score"] = self.score
        return payload


@dataclass(slots=True)
class KnowledgeEvidence:
    """Stable retrieval evidence contract."""

    query: KnowledgeQuery
    items: list[KnowledgeEvidenceItem] = field(default_factory=list)
    citations: list[KnowledgeCitation] = field(default_factory=list)
    relevance_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_context_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": self.query.to_context_payload(),
            "items": [item.to_context_payload() for item in self.items],
            "citations": [citation.to_context_payload() for citation in self.citations],
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.relevance_score is not None:
            payload["relevance_score"] = self.relevance_score
        return payload


@dataclass(slots=True)
class KnowledgeBundle:
    """Stable aggregated knowledge bundle for one run."""

    query: KnowledgeQuery
    evidences: list[KnowledgeEvidence] = field(default_factory=list)
    items: list[KnowledgeEvidenceItem] = field(default_factory=list)
    citations: list[KnowledgeCitation] = field(default_factory=list)
    relevance_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_context_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": self.query.to_context_payload(),
            "evidences": [evidence.to_context_payload() for evidence in self.evidences],
            "items": [item.to_context_payload() for item in self.items],
            "citations": [citation.to_context_payload() for citation in self.citations],
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.relevance_score is not None:
            payload["relevance_score"] = self.relevance_score
        return payload


@dataclass(slots=True)
class KnowledgeResolver:
    """Adapter for dynamic knowledge access."""

    handler: Callable[[KnowledgeQuery], KnowledgeEvidence]
    mode: str = "callable"
    description: str = ""
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def callable(
        cls,
        handler: Callable[[KnowledgeQuery], KnowledgeEvidence],
        *,
        description: str = "",
        extensions: dict[str, Any] | None = None,
    ) -> KnowledgeResolver:
        return cls(
            handler=handler,
            mode="callable",
            description=description,
            extensions=dict(extensions or {}),
        )

    def resolve(self, query: KnowledgeQuery) -> KnowledgeEvidence:
        evidence = self.handler(query)
        if not isinstance(evidence, KnowledgeEvidence):
            raise TypeError(
                f"knowledge resolver must return KnowledgeEvidence, got {type(evidence).__name__}"
            )
        return evidence

    def to_context_payload(self) -> dict[str, Any]:
        payload = {
            "mode": self.mode,
            "description": self.description,
            "extensions": dict(self.extensions),
        }
        return payload


@dataclass(slots=True)
class KnowledgeSource:
    """Public declarative knowledge source definition."""

    name: str
    description: str = ""
    documents: list[KnowledgeDocument] = field(default_factory=list)
    resolver: KnowledgeResolver | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def inline(
        cls,
        name: str,
        documents: list[str] | list[KnowledgeDocument],
        *,
        description: str = "",
        metadata: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> KnowledgeSource:
        normalized_documents: list[KnowledgeDocument] = []
        for document in documents:
            if isinstance(document, KnowledgeDocument):
                normalized_documents.append(document)
            else:
                normalized_documents.append(KnowledgeDocument(content=document))
        return cls(
            name=name,
            description=description,
            documents=normalized_documents,
            metadata=dict(metadata or {}),
            extensions=dict(extensions or {}),
        )

    @classmethod
    def dynamic(
        cls,
        name: str,
        resolver: KnowledgeResolver,
        *,
        description: str = "",
        metadata: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> KnowledgeSource:
        return cls(
            name=name,
            description=description,
            resolver=resolver,
            metadata=dict(metadata or {}),
            extensions=dict(extensions or {}),
        )

    def resolve(self, query: KnowledgeQuery) -> KnowledgeEvidence:
        if query.source_names and self.name not in query.source_names:
            return KnowledgeEvidence(query=query)

        if self.resolver is not None:
            return self.resolver.resolve(query)

        items = [
            KnowledgeEvidenceItem(
                source_name=self.name,
                content=document.content,
                title=document.title,
                uri=document.uri,
                metadata=dict(document.metadata),
                extensions=dict(document.extensions),
            )
            for document in self.documents[: query.top_k]
        ]
        citations = [
            KnowledgeCitation(
                source_name=self.name,
                title=item.title,
                uri=item.uri,
                metadata=dict(item.metadata),
            )
            for item in items
        ]
        return KnowledgeEvidence(
            query=query,
            items=items,
            citations=citations,
            metadata=dict(self.metadata),
            relevance_score=1.0 if items else 0.0,
        )

    def to_context_payload(self) -> dict[str, Any]:
        """Serialize a knowledge source for prompt/runtime context."""
        payload: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.documents:
            payload["documents"] = [document.to_context_payload() for document in self.documents]
        if self.resolver is not None:
            payload["resolver"] = self.resolver.to_context_payload()
        return payload
