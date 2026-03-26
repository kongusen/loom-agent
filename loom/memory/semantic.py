"""Semantic search utilities."""

from __future__ import annotations

import time


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def hybrid_score(
    semantic_sim: float,
    recency: float,
    importance: float,
    weights: tuple[float, float, float] = (0.6, 0.2, 0.2),
) -> float:
    """Compute hybrid score from semantic, recency, and importance."""
    return weights[0] * semantic_sim + weights[1] * recency + weights[2] * importance


def recency_score(created_at: float, decay_hours: float = 24.0) -> float:
    """Compute recency score with exponential decay."""
    age_hours = (time.time() - created_at) / 3600
    return max(0.0, 1.0 - age_hours / decay_hours)
