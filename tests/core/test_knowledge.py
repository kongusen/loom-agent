"""Test knowledge pipeline."""

from collections import Counter

from loom.tools.knowledge import KnowledgePipeline


class TestKnowledgePipeline:
    """Test retrieval and rerank behavior."""

    def test_retrieve_from_string_source(self):
        """Test retrieval from simple string chunks."""
        pipeline = KnowledgePipeline()
        pipeline.register_source(
            "wiki",
            [
                "Loom is an agent runtime framework for complex tasks.",
                "Bananas are yellow fruit.",
            ],
        )

        pack = pipeline.retrieve("agent runtime", "complex task system")
        assert pack.question == "agent runtime"
        assert pack.sources == ["wiki"]
        assert pack.chunks[0]["content"].startswith("Loom is an agent runtime")
        assert pack.relevance_score > 0

    def test_retrieve_from_structured_chunks(self):
        """Test retrieval preserves chunk metadata and citations."""
        pipeline = KnowledgePipeline()
        pipeline.register_source(
            "docs",
            {
                "chunks": [
                    {"title": "Runtime", "content": "Runtime handles session task run."},
                    {"title": "Unrelated", "content": "Completely different text."},
                ]
            },
        )

        pack = pipeline.retrieve("session run", "runtime object model")
        assert pack.sources == ["docs"]
        assert pack.citations[0] == "docs: Runtime"
        assert pack.chunks[0]["title"] == "Runtime"

    def test_retrieve_from_callable_source(self):
        """Test retrieval can call dynamic sources."""
        pipeline = KnowledgePipeline()

        def source(question: str):
            return [
                {"title": "Dynamic", "content": f"Answering question about {question}."},
                {"title": "Other", "content": "No overlap here."},
            ]

        pipeline.register_source("dynamic", source)
        pack = pipeline.retrieve("question", "answering")

        assert pack.sources == ["dynamic"]
        assert pack.chunks[0]["title"] == "Dynamic"

    def test_retrieve_returns_empty_pack_when_no_match(self):
        """Test empty evidence pack when nothing matches."""
        pipeline = KnowledgePipeline()
        pipeline.register_source("wiki", ["bananas only"])

        pack = pipeline.retrieve("agent runtime", "complex task system")
        assert pack.sources == []
        assert pack.chunks == []
        assert pack.citations == []
        assert pack.relevance_score == 0.0

    def test_source_cache_reuses_previous_query_result(self):
        """Same source+query should hit LRU cache instead of reloading."""
        calls = Counter()

        def source(question: str):
            calls[question] += 1
            return [{"title": "Dynamic", "content": f"Answer about {question}"}]

        pipeline = KnowledgePipeline(source_cache_max=8)
        pipeline.register_source("dynamic", source)

        first = pipeline.retrieve("question", "answer")
        second = pipeline.retrieve("question", "answer")

        assert first.chunks[0]["title"] == "Dynamic"
        assert second.chunks[0]["title"] == "Dynamic"
        assert calls["question"] == 1

    def test_source_cache_evicts_old_entries(self):
        """LRU cache should evict least-recently used source query."""
        calls = Counter()

        def source(question: str):
            calls[question] += 1
            return [{"title": question, "content": f"content {question}"}]

        pipeline = KnowledgePipeline(source_cache_max=1)
        pipeline.register_source("dynamic", source)

        pipeline.retrieve("q1", "goal")
        pipeline.retrieve("q2", "goal")
        pipeline.retrieve("q1", "goal")

        assert calls["q1"] == 2
        assert calls["q2"] == 1
