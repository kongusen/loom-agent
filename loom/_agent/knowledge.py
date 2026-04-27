"""Knowledge aggregation helpers for Agent runs."""

from __future__ import annotations

from typing import Any

from ..config import KnowledgeBundle, KnowledgeEvidence, KnowledgeQuery


def _build_knowledge_bundle(
    query: KnowledgeQuery,
    evidences: list[KnowledgeEvidence],
) -> KnowledgeBundle:
    items: list[Any] = []
    citations: list[Any] = []
    relevance_values: list[float] = []

    for evidence in evidences:
        items.extend(evidence.items)
        citations.extend(evidence.citations)
        if evidence.relevance_score is not None:
            relevance_values.append(evidence.relevance_score)

    items.sort(key=lambda item: item.score if item.score is not None else 0.0, reverse=True)

    relevance_score = sum(relevance_values) / len(relevance_values) if relevance_values else None
    return KnowledgeBundle(
        query=query,
        evidences=evidences,
        items=items,
        citations=citations,
        relevance_score=relevance_score,
    )
