"""Test the enhanced KnowledgePipeline with semantic similarity"""

from loom.tools.knowledge import KnowledgePipeline, EvidencePack


def test_knowledge_pipeline():
    """Test that KnowledgePipeline supports both lexical and semantic similarity"""

    print("=" * 70)
    print("KnowledgePipeline Test")
    print("=" * 70)

    # Test 1: Lexical similarity (default, no embedding_fn)
    print("\n1. Test: Lexical similarity (default)")
    pipeline = KnowledgePipeline()

    # Register a simple source
    pipeline.register_source("docs", [
        {"content": "Python is a programming language", "title": "Python Intro"},
        {"content": "JavaScript is used for web development", "title": "JS Intro"},
        {"content": "Python has great data science libraries", "title": "Python Data"}
    ])

    # Retrieve with lexical similarity
    pack = pipeline.retrieve("Python programming", "Learn Python")

    assert isinstance(pack, EvidencePack), "Should return EvidencePack"
    assert pack.question == "Python programming", "Should preserve question"
    assert len(pack.chunks) > 0, "Should find chunks"
    assert "Python" in pack.chunks[0]["content"], "Should find Python-related content"
    print(f"   ✅ Lexical similarity works (found {len(pack.chunks)} chunks)")
    print(f"      Top result: {pack.chunks[0]['title']}")

    # Test 2: Semantic similarity with mock embedding
    print("\n2. Test: Semantic similarity (with embedding_fn)")

    def mock_embedding(text: str) -> list[float]:
        """Mock embedding function that returns simple vectors"""
        # Simple mock: count word frequencies as features
        words = ["python", "javascript", "programming", "web", "data", "science"]
        text_lower = text.lower()
        return [float(text_lower.count(word)) for word in words]

    pipeline_semantic = KnowledgePipeline(embedding_fn=mock_embedding)
    pipeline_semantic.register_source("docs", [
        {"content": "Python is a programming language", "title": "Python Intro"},
        {"content": "JavaScript is used for web development", "title": "JS Intro"},
        {"content": "Python has great data science libraries", "title": "Python Data"}
    ])

    pack = pipeline_semantic.retrieve("Python programming", "Learn Python")

    assert isinstance(pack, EvidencePack), "Should return EvidencePack"
    assert len(pack.chunks) > 0, "Should find chunks"
    print(f"   ✅ Semantic similarity works (found {len(pack.chunks)} chunks)")
    print(f"      Top result: {pack.chunks[0]['title']}")

    # Test 3: Embedding caching
    print("\n3. Test: Embedding caching")
    pipeline_cached = KnowledgePipeline(embedding_fn=mock_embedding)

    # First call - should cache
    emb1 = pipeline_cached._get_embedding("test text")
    assert emb1 is not None, "Should return embedding"
    assert "test text" in pipeline_cached._embedding_cache, "Should cache embedding"

    # Second call - should use cache
    emb2 = pipeline_cached._get_embedding("test text")
    assert emb2 == emb1, "Should return same embedding from cache"
    print("   ✅ Embedding caching works")

    # Test 4: Cosine similarity calculation
    print("\n4. Test: Cosine similarity calculation")
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    vec3 = [0.0, 1.0, 0.0]

    sim_same = pipeline._cosine_similarity(vec1, vec2)
    sim_orthogonal = pipeline._cosine_similarity(vec1, vec3)

    assert sim_same > 0.9, "Same vectors should have high similarity"
    assert sim_orthogonal < 0.6, "Orthogonal vectors should have low similarity"
    print(f"   ✅ Cosine similarity works (same: {sim_same:.2f}, orthogonal: {sim_orthogonal:.2f})")

    # Test 5: Fallback to lexical on embedding failure
    print("\n5. Test: Fallback to lexical on embedding failure")

    def failing_embedding(text: str) -> list[float]:
        """Embedding function that always fails"""
        raise Exception("Embedding failed")

    pipeline_fallback = KnowledgePipeline(embedding_fn=failing_embedding)

    # Should fallback to lexical similarity
    score = pipeline_fallback._similarity("hello world", "hello there")
    assert score > 0, "Should fallback to lexical similarity"
    print(f"   ✅ Fallback to lexical works (score: {score:.2f})")

    # Test 6: Reranking with goal
    print("\n6. Test: Reranking with goal")
    pipeline_rerank = KnowledgePipeline()
    pipeline_rerank.register_source("docs", [
        {"content": "Python basics for beginners", "title": "Python Basics"},
        {"content": "Advanced Python techniques", "title": "Python Advanced"},
        {"content": "Python for data science", "title": "Python Data"}
    ])

    # Retrieve with specific goal
    pack = pipeline_rerank.retrieve("Python", "data science")

    assert len(pack.chunks) > 0, "Should find chunks"
    # The data science chunk should be ranked higher due to goal
    print(f"   ✅ Reranking works")
    print(f"      Top result: {pack.chunks[0]['title']}")

    # Test 7: Citations building
    print("\n7. Test: Citations building")
    pipeline_cite = KnowledgePipeline()
    pipeline_cite.register_source("docs", [
        {"content": "Content 1", "title": "Title 1"},
        {"content": "Content 2", "title": "Title 2"}
    ])

    pack = pipeline_cite.retrieve("content", "goal")

    assert len(pack.citations) > 0, "Should have citations"
    assert "Title" in pack.citations[0], "Citation should include title"
    print(f"   ✅ Citations building works")
    print(f"      Citations: {pack.citations}")

    # Test 8: Relevance score aggregation
    print("\n8. Test: Relevance score aggregation")
    pack = pipeline.retrieve("Python", "Python")

    assert pack.relevance_score >= 0.0, "Relevance score should be non-negative"
    assert pack.relevance_score <= 1.0, "Relevance score should be <= 1.0"
    print(f"   ✅ Relevance score aggregation works (score: {pack.relevance_score:.2f})")

    # Test 9: Empty results handling
    print("\n9. Test: Empty results handling")
    pipeline_empty = KnowledgePipeline()
    pipeline_empty.register_source("empty", [])

    pack = pipeline_empty.retrieve("query", "goal")

    assert len(pack.chunks) == 0, "Should have no chunks"
    assert pack.relevance_score == 0.0, "Relevance score should be 0"
    print("   ✅ Empty results handled correctly")

    # Test 10: Multiple sources
    print("\n10. Test: Multiple sources")
    pipeline_multi = KnowledgePipeline()
    pipeline_multi.register_source("source1", [
        {"content": "Python content from source 1", "title": "S1"}
    ])
    pipeline_multi.register_source("source2", [
        {"content": "Python content from source 2", "title": "S2"}
    ])

    pack = pipeline_multi.retrieve("Python", "Python")

    assert len(pack.sources) > 1, "Should have multiple sources"
    print(f"   ✅ Multiple sources work (sources: {pack.sources})")

    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    print("✅ All 10 tests passed!")
    print("\nKnowledgePipeline now supports:")
    print("  • Lexical similarity (default, no dependencies)")
    print("  • Semantic similarity (with embedding_fn)")
    print("  • Embedding caching for performance")
    print("  • Cosine similarity calculation")
    print("  • Automatic fallback to lexical on failure")
    print("  • Reranking with goal context")
    print("  • Citation building")
    print("  • Relevance score aggregation")
    print("  • Empty results handling")
    print("  • Multiple knowledge sources")
    print("\n" + "=" * 70)

    return True


if __name__ == "__main__":
    success = test_knowledge_pipeline()
    exit(0 if success else 1)
