"""Tests for runtime memory coordination extraction."""

from loom.memory.semantic import MemoryEntry, SemanticMemory
from loom.runtime.memory_runtime import MemoryRuntime


class _MemoryPartition(list):
    pass


class _Partitions:
    def __init__(self) -> None:
        self.memory = _MemoryPartition()


class _ContextManager:
    def __init__(self) -> None:
        self.partitions = _Partitions()
        self.current_goal = "ship safely"


class _Store:
    def __init__(self) -> None:
        self.saved = None

    def load(self, _session_id: str):
        return {"memory": [{"role": "system", "content": "persisted note"}]}

    def save(self, _session_id: str, data):
        self.saved = data


class _Provider:
    name = "recorder"

    def __init__(self) -> None:
        self.synced = []

    def is_available(self) -> bool:
        return True

    def system_prompt(self) -> str:
        return "Use provider memory."

    def prefetch(self, query: str, *, session_id=None) -> str:
        return f"remembered {query} in {session_id}"

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id=None) -> None:
        self.synced.append((user_content, assistant_content, session_id))


def test_memory_runtime_session_load_save_and_provider_flow() -> None:
    context = _ContextManager()
    store = _Store()
    provider = _Provider()
    runtime = MemoryRuntime(
        context_manager=context,
        memory_store=store,
        memory_providers=[provider],
        semantic_memory=None,
    )

    runtime.load_session_memory("s1")
    runtime.save_session_memory("s1")
    runtime.inject_provider_memories("goal", "s1")
    runtime.sync_memory_providers("user", "assistant", "s1")

    assert str(context.partitions.memory[0].content) == "persisted note"
    assert str(context.partitions.memory[1].content).startswith("[memory:recorder] remembered goal")
    assert store.saved is not None
    assert provider.synced == [("user", "assistant", "s1")]


def test_memory_runtime_semantic_inject_and_remember_tool_result() -> None:
    context = _ContextManager()
    semantic = SemanticMemory()
    semantic.add(MemoryEntry(content="prior fix"))
    runtime = MemoryRuntime(
        context_manager=context,
        memory_store=_Store(),
        memory_providers=[],
        semantic_memory=semantic,
    )

    runtime.inject_semantic_memories("prior")
    runtime.remember_tool_result(content="new evidence", tool_name="search", iteration=2)

    assert any("prior fix" in str(message.content) for message in context.partitions.memory)
    assert any(entry.content == "new evidence" for entry in semantic.search("new evidence", top_k=5))
