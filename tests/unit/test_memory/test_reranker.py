"""
Tests for memory/reranker.py
"""

import math
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from loom.memory.reranker import (
    DEFAULT_SIGNALS,
    AccessFrequencySignal,
    ImportanceSignal,
    InformationDensitySignal,
    MemoryReranker,
    RerankCandidate,
    RerankResult,
    TimeDecaySignal,
    VectorSimilaritySignal,
)


def _make_memory(
    mid="m1",
    content="test content",
    importance=0.5,
    info_density=0.5,
    access_count=1,
    created_at=None,
):
    mem = MagicMock()
    mem.id = mid
    mem.content = content
    mem.importance = importance
    mem.information_density = info_density
    mem.metadata = {"access_count": access_count}
    if created_at is None:
        created_at = datetime.now(tz=timezone.utc)
    mem.created_at = created_at
    return mem


def _make_vector_result(mid="m1", score=0.8):
    vr = MagicMock()
    vr.id = mid
    vr.score = score
    return vr


# ============ Dataclasses ============


class TestRerankCandidate:
    def test_defaults(self):
        mem = _make_memory()
        c = RerankCandidate(memory=mem)
        assert c.vector_score == 0.0
        assert c.rerank_score == 0.0
        assert c.signal_scores == {}


class TestRerankResult:
    def test_top_with_candidates(self):
        m1 = _make_memory("m1")
        m2 = _make_memory("m2")
        c1 = RerankCandidate(memory=m1, rerank_score=0.9)
        c2 = RerankCandidate(memory=m2, rerank_score=0.5)
        result = RerankResult(candidates=[c1, c2], recall_count=2, rerank_count=2)
        assert result.top is m1

    def test_top_empty(self):
        result = RerankResult(candidates=[], recall_count=0, rerank_count=0)
        assert result.top is None

    def test_memories_property(self):
        m1 = _make_memory("m1")
        m2 = _make_memory("m2")
        c1 = RerankCandidate(memory=m1)
        c2 = RerankCandidate(memory=m2)
        result = RerankResult(candidates=[c1, c2])
        assert result.memories == [m1, m2]


# ============ Signals ============


class TestVectorSimilaritySignal:
    def test_name_and_weight(self):
        s = VectorSimilaritySignal()
        assert s.name == "vector_similarity"
        assert s.weight == 0.30

    def test_score_normal(self):
        s = VectorSimilaritySignal()
        c = RerankCandidate(memory=_make_memory(), vector_score=0.75)
        assert s.score(c, {}) == 0.75

    def test_score_clamped_high(self):
        s = VectorSimilaritySignal()
        c = RerankCandidate(memory=_make_memory(), vector_score=1.5)
        assert s.score(c, {}) == 1.0

    def test_score_clamped_low(self):
        s = VectorSimilaritySignal()
        c = RerankCandidate(memory=_make_memory(), vector_score=-0.5)
        assert s.score(c, {}) == 0.0


class TestTimeDecaySignal:
    def test_name_and_weight(self):
        s = TimeDecaySignal()
        assert s.name == "time_decay"
        assert s.weight == 0.20

    def test_recent_memory_high_score(self):
        s = TimeDecaySignal()
        mem = _make_memory(created_at=datetime.now(tz=timezone.utc))
        c = RerankCandidate(memory=mem)
        score = s.score(c, {})
        assert score > 0.95

    def test_old_memory_low_score(self):
        s = TimeDecaySignal(half_life_hours=48.0)
        old_time = datetime.fromtimestamp(time.time() - 96 * 3600, tz=timezone.utc)
        mem = _make_memory(created_at=old_time)
        c = RerankCandidate(memory=mem)
        score = s.score(c, {})
        assert score < 0.3

    def test_half_life(self):
        s = TimeDecaySignal(half_life_hours=48.0)
        half_life_ago = datetime.fromtimestamp(time.time() - 48 * 3600, tz=timezone.utc)
        mem = _make_memory(created_at=half_life_ago)
        c = RerankCandidate(memory=mem)
        score = s.score(c, {})
        assert abs(score - 0.5) < 0.05

    def test_future_timestamp_clamped(self):
        s = TimeDecaySignal()
        future = datetime.fromtimestamp(time.time() + 3600, tz=timezone.utc)
        mem = _make_memory(created_at=future)
        c = RerankCandidate(memory=mem)
        score = s.score(c, {})
        assert score == 1.0


class TestAccessFrequencySignal:
    def test_name_and_weight(self):
        s = AccessFrequencySignal()
        assert s.name == "access_frequency"
        assert s.weight == 0.15

    def test_zero_access(self):
        s = AccessFrequencySignal()
        mem = _make_memory(access_count=0)
        c = RerankCandidate(memory=mem)
        assert s.score(c, {}) == 0.1

    def test_high_access(self):
        s = AccessFrequencySignal()
        mem = _make_memory(access_count=100)
        c = RerankCandidate(memory=mem)
        assert s.score(c, {}) == pytest.approx(1.0, abs=0.01)

    def test_moderate_access(self):
        s = AccessFrequencySignal()
        mem = _make_memory(access_count=10)
        c = RerankCandidate(memory=mem)
        score = s.score(c, {})
        assert 0.4 < score < 1.0


class TestInformationDensitySignal:
    def test_name_and_weight(self):
        s = InformationDensitySignal()
        assert s.name == "information_density"
        assert s.weight == 0.15

    def test_normal_density(self):
        s = InformationDensitySignal()
        mem = _make_memory(info_density=0.7)
        c = RerankCandidate(memory=mem)
        assert s.score(c, {}) == 0.7

    def test_clamped(self):
        s = InformationDensitySignal()
        mem = _make_memory(info_density=1.5)
        c = RerankCandidate(memory=mem)
        assert s.score(c, {}) == 1.0


class TestImportanceSignal:
    def test_name_and_weight(self):
        s = ImportanceSignal()
        assert s.name == "importance"
        assert s.weight == 0.20

    def test_normal_importance(self):
        s = ImportanceSignal()
        mem = _make_memory(importance=0.8)
        c = RerankCandidate(memory=mem)
        assert s.score(c, {}) == 0.8

    def test_clamped(self):
        s = ImportanceSignal()
        mem = _make_memory(importance=-0.5)
        c = RerankCandidate(memory=mem)
        assert s.score(c, {}) == 0.0


# ============ MemoryReranker ============


class TestMemoryReranker:
    def test_default_signals(self):
        r = MemoryReranker()
        assert len(r.signals) == 5

    def test_suggest_recall_k(self):
        r = MemoryReranker(recall_multiplier=3)
        assert r.suggest_recall_k(5) == 15

    def test_recall_top_k(self):
        r = MemoryReranker(recall_multiplier=4)
        assert r.recall_top_k == 4

    def test_rerank_basic(self):
        m1 = _make_memory("m1", importance=0.9, info_density=0.8, access_count=50)
        m2 = _make_memory("m2", importance=0.2, info_density=0.3, access_count=1)
        vr1 = _make_vector_result("m1", 0.9)
        vr2 = _make_vector_result("m2", 0.3)

        r = MemoryReranker()
        result = r.rerank([m1, m2], [vr1, vr2], top_k=2)

        assert result.recall_count == 2
        assert len(result.candidates) <= 2
        # m1 should rank higher
        if len(result.candidates) >= 2:
            assert result.candidates[0].memory.id == "m1"

    def test_rerank_min_score_threshold(self):
        m1 = _make_memory("m1", importance=0.0, info_density=0.0, access_count=0)
        vr1 = _make_vector_result("m1", 0.0)

        r = MemoryReranker(min_score_threshold=0.5)
        result = r.rerank([m1], [vr1], top_k=5)
        # Low-scoring candidate should be filtered
        assert result.rerank_count == 0 or all(
            c.rerank_score >= 0.5 for c in result.candidates
        )

    def test_rerank_top_k_limits(self):
        memories = [_make_memory(f"m{i}") for i in range(10)]
        vrs = [_make_vector_result(f"m{i}", 0.5) for i in range(10)]

        r = MemoryReranker()
        result = r.rerank(memories, vrs, top_k=3)
        assert len(result.candidates) <= 3

    def test_rerank_empty_input(self):
        r = MemoryReranker()
        result = r.rerank([], [], top_k=5)
        assert result.recall_count == 0
        assert result.candidates == []

    def test_rerank_elapsed_ms(self):
        m1 = _make_memory("m1")
        vr1 = _make_vector_result("m1", 0.5)
        r = MemoryReranker()
        result = r.rerank([m1], [vr1])
        assert result.elapsed_ms >= 0

    def test_rerank_signal_scores_populated(self):
        m1 = _make_memory("m1")
        vr1 = _make_vector_result("m1", 0.8)
        r = MemoryReranker()
        result = r.rerank([m1], [vr1])
        if result.candidates:
            scores = result.candidates[0].signal_scores
            assert "vector_similarity" in scores
            assert "time_decay" in scores
            assert "importance" in scores

    def test_custom_signals(self):
        class ConstantSignal:
            name = "constant"
            weight = 1.0
            def score(self, candidate, context):
                return 0.42

        r = MemoryReranker(signals=[ConstantSignal()])
        m1 = _make_memory("m1")
        vr1 = _make_vector_result("m1", 0.5)
        result = r.rerank([m1], [vr1])
        assert result.candidates[0].signal_scores["constant"] == 0.42


class TestDefaultSignals:
    def test_default_signals_list(self):
        assert len(DEFAULT_SIGNALS) == 5
        names = [s.name for s in DEFAULT_SIGNALS]
        assert "vector_similarity" in names
        assert "time_decay" in names
        assert "access_frequency" in names
        assert "information_density" in names
        assert "importance" in names

    def test_weights_sum_to_one(self):
        total = sum(s.weight for s in DEFAULT_SIGNALS)
        assert abs(total - 1.0) < 0.01
