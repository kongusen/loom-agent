"""
关键词提取单元测试
"""

import pytest

from loom.providers.knowledge.rag.builders.chunker import (
    SimpleChunker,
    SlidingWindowChunker,
    extract_chunk_keywords,
)
from loom.providers.knowledge.rag.builders.base import Document


class TestExtractChunkKeywords:
    def test_empty_text(self):
        assert extract_chunk_keywords("") == []

    def test_camel_case(self):
        keywords = extract_chunk_keywords("The GraphRAGKnowledgeBase handles retrieval")
        assert "GraphRAGKnowledgeBase" in keywords

    def test_snake_case(self):
        keywords = extract_chunk_keywords("Use chunk_store and entity_store for storage")
        assert "chunk_store" in keywords
        assert "entity_store" in keywords

    def test_all_caps(self):
        keywords = extract_chunk_keywords("The API uses CONCEPT and TOOL types")
        assert "API" in keywords
        assert "CONCEPT" in keywords
        assert "TOOL" in keywords

    def test_dotted_path(self):
        keywords = extract_chunk_keywords("Import from loom.memory.core module")
        assert "loom.memory.core" in keywords

    def test_capitalized_words(self):
        keywords = extract_chunk_keywords("The Agent uses Memory for storage")
        assert "Agent" in keywords
        assert "Memory" in keywords

    def test_stop_words_filtered(self):
        keywords = extract_chunk_keywords("The is a an are was were been")
        assert keywords == []

    def test_max_keywords_limit(self):
        text = " ".join(f"Keyword{i}" for i in range(20))
        keywords = extract_chunk_keywords(text, max_keywords=5)
        assert len(keywords) <= 5

    def test_dedup_case_insensitive(self):
        """同一个词不同大小写不重复"""
        keywords = extract_chunk_keywords("Agent agent AGENT")
        # 只应出现一次
        lower_keywords = [k.lower() for k in keywords]
        assert lower_keywords.count("agent") == 1

    def test_mixed_content(self):
        """中英混合内容"""
        text = "GraphRAG uses loom.providers.knowledge for entity_extraction with API calls"
        keywords = extract_chunk_keywords(text)
        assert len(keywords) > 0
        # 应该包含多种模式的关键词
        keyword_lower = [k.lower() for k in keywords]
        assert "graphrag" in keyword_lower or "loom.providers.knowledge" in keywords

    def test_short_words_filtered(self):
        """单字符词被过滤"""
        keywords = extract_chunk_keywords("A B C D")
        # 单字符不应出现（len > 1 过滤）
        assert all(len(k) > 1 for k in keywords)


class TestChunkerPopulatesKeywords:
    def test_simple_chunker_populates_keywords(self):
        """SimpleChunker 填充 keywords 字段"""
        doc = Document(
            id="doc_1",
            content="The GraphRAGKnowledgeBase uses chunk_store for storage. Agent handles retrieval.",
        )
        chunker = SimpleChunker(chunk_size=200)
        chunks = chunker.chunk(doc)

        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk.keywords, list)
            assert len(chunk.keywords) > 0

    def test_sliding_window_chunker_populates_keywords(self):
        """SlidingWindowChunker 填充 keywords 字段"""
        doc = Document(
            id="doc_1",
            content="The GraphRAGKnowledgeBase uses chunk_store for storage. Agent handles retrieval.",
        )
        chunker = SlidingWindowChunker(chunk_size=200)
        chunks = chunker.chunk(doc)

        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk.keywords, list)
            assert len(chunk.keywords) > 0

    def test_chunker_keywords_match_content(self):
        """关键词应来自 chunk 内容"""
        doc = Document(
            id="doc_1",
            content="The LLMEntityExtractor extracts entities using loom.providers.knowledge module",
        )
        chunker = SimpleChunker(chunk_size=500)
        chunks = chunker.chunk(doc)

        assert len(chunks) == 1
        keywords = chunks[0].keywords
        # 至少应包含一些从内容中提取的关键词
        assert any("LLMEntityExtractor" in k or "loom.providers" in k for k in keywords)
