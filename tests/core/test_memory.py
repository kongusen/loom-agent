"""Test memory components"""

from unittest.mock import MagicMock

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


# ── SemanticMemory + WorkingMemory engine integration ──


class TestSemanticMemoryEngineIntegration:
    def test_semantic_memory_created_when_enabled(self):
        from loom.memory.semantic import SemanticMemory
        from loom.runtime.engine import AgentEngine, EngineConfig

        engine = AgentEngine(provider=MagicMock(), config=EngineConfig(enable_memory=True))
        assert isinstance(engine.semantic_memory, SemanticMemory)

    def test_semantic_memory_none_when_disabled(self):
        from loom.runtime.engine import AgentEngine, EngineConfig

        engine = AgentEngine(provider=MagicMock(), config=EngineConfig(enable_memory=False))
        assert engine.semantic_memory is None

    def test_inject_recalls_relevant_entry(self):
        from loom.memory.semantic import MemoryEntry
        from loom.runtime.engine import AgentEngine, EngineConfig

        engine = AgentEngine(provider=MagicMock(), config=EngineConfig(enable_memory=True))
        engine.semantic_memory.add(MemoryEntry(content="Python is a programming language"))
        engine._inject_semantic_memories("What programming language should I use?")
        contents = [
            m.content
            for m in engine.context_manager.partitions.memory
            if isinstance(m.content, str)
        ]
        assert any("[recalled]" in c for c in contents)

    def test_inject_noop_when_no_entries(self):
        from loom.runtime.engine import AgentEngine, EngineConfig

        engine = AgentEngine(provider=MagicMock(), config=EngineConfig(enable_memory=True))
        before = len(engine.context_manager.partitions.memory)
        engine._inject_semantic_memories("some goal")
        assert len(engine.context_manager.partitions.memory) == before


class TestWorkingMemoryEngineIntegration:
    def test_working_memory_always_created(self):
        from loom.memory.working import WorkingMemory
        from loom.runtime.engine import AgentEngine, EngineConfig

        engine = AgentEngine(provider=MagicMock(), config=EngineConfig())
        assert isinstance(engine.working_memory, WorkingMemory)

    def test_working_memory_dashboard_bound_to_partition(self):
        from loom.runtime.engine import AgentEngine, EngineConfig

        engine = AgentEngine(provider=MagicMock(), config=EngineConfig())
        assert engine.working_memory.dashboard is engine.context_manager.partitions.working

    def test_scratchpad_read_write(self):
        from loom.runtime.engine import AgentEngine, EngineConfig

        engine = AgentEngine(provider=MagicMock(), config=EngineConfig())
        engine.working_memory.set_scratch("step", 3)
        assert engine.working_memory.get_scratch("step") == 3

    def test_agent_working_memory_none_before_build(self):
        from loom.agent import Agent
        from loom.config import AgentConfig, ModelRef

        agent = Agent(
            config=AgentConfig(
                model=ModelRef(provider="anthropic", name="claude-3-5-sonnet-20241022"),
            )
        )
        assert agent.working_memory is None

    def test_agent_working_memory_available_after_build(self):
        from loom.agent import Agent
        from loom.config import AgentConfig, ModelRef
        from loom.memory.working import WorkingMemory

        agent = Agent(
            config=AgentConfig(
                model=ModelRef(provider="anthropic", name="claude-3-5-sonnet-20241022"),
            )
        )
        agent._build_engine(MagicMock())
        assert isinstance(agent.working_memory, WorkingMemory)
