"""Test memory components"""

from loom.memory.semantic import MemoryEntry, SemanticMemory
from loom.memory.session import SessionMemory
from loom.memory.working import WorkingMemory


class TestWorkingMemory:
    """Test WorkingMemory"""

    def test_working_memory_creation(self):
        """Test WorkingMemory creation"""
        wm = WorkingMemory()
        assert wm is not None


class TestSemanticMemory:
    """Test SemanticMemory"""

    def test_semantic_memory_creation(self):
        """Test SemanticMemory creation"""
        sm = SemanticMemory()
        assert sm is not None

    def test_semantic_memory_search_lexical(self):
        """Test lexical fallback search."""
        sm = SemanticMemory()
        sm.add(MemoryEntry(content="python async framework"))
        sm.add(MemoryEntry(content="golang web server"))
        sm.add(MemoryEntry(content="python testing patterns"))

        results = sm.search("python framework", top_k=2)
        assert len(results) == 2
        assert results[0].content == "python async framework"

    def test_semantic_memory_search_with_embeddings(self):
        """Test cosine similarity search when embeddings are present."""
        sm = SemanticMemory()
        sm.add(MemoryEntry(content="entry-a", embedding=[1.0, 0.0]))
        sm.add(MemoryEntry(content="entry-b", embedding=[0.0, 1.0]))
        sm.add(MemoryEntry(content="entry-c", embedding=[0.8, 0.2]))

        results = sm.search("ignored", top_k=2, query_embedding=[1.0, 0.0])
        assert [entry.content for entry in results] == ["entry-a", "entry-c"]

    def test_semantic_memory_search_handles_empty(self):
        """Test empty and zero top_k cases."""
        sm = SemanticMemory()
        assert sm.search("python") == []

        sm.add(MemoryEntry(content="python async framework"))
        assert sm.search("python", top_k=0) == []


class TestSessionMemory:
    """Test SessionMemory"""

    def test_session_memory_creation(self):
        """Test SessionMemory creation"""
        session = SessionMemory()
        assert session is not None
