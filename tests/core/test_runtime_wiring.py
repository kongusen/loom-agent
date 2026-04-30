from unittest.mock import MagicMock

from loom.runtime.engine import AgentEngine, EngineConfig


def test_runtime_wiring_refreshes_reassigned_engine_components() -> None:
    engine = AgentEngine(provider=MagicMock(), config=EngineConfig())
    replacement_context = MagicMock()
    replacement_provider = MagicMock()
    replacement_registry = MagicMock()
    replacement_executor = MagicMock()
    replacement_memory_store = MagicMock()
    replacement_memory_providers = [MagicMock()]
    replacement_semantic_memory = MagicMock()

    engine.context_manager = replacement_context
    engine.provider = replacement_provider
    engine.tool_registry = replacement_registry
    engine.tool_executor = replacement_executor
    engine.memory_store = replacement_memory_store
    engine.memory_providers = replacement_memory_providers
    engine.semantic_memory = replacement_semantic_memory

    engine.runtime_wiring.refresh()

    assert engine.signal_runtime.context_manager is replacement_context
    assert engine.context_runtime.context_manager is replacement_context
    assert engine.tool_runtime.context_manager is replacement_context
    assert engine.tool_runtime.tool_registry is replacement_registry
    assert engine.tool_runtime.tool_executor is replacement_executor
    assert engine.memory_runtime.context_manager is replacement_context
    assert engine.memory_runtime.memory_store is replacement_memory_store
    assert engine.memory_runtime.memory_providers is replacement_memory_providers
    assert engine.memory_runtime.semantic_memory is replacement_semantic_memory
    assert engine.provider_runtime.provider is replacement_provider
    assert engine.provider_runtime.context_manager is replacement_context
    assert engine.run_lifecycle.context_manager is replacement_context
    assert engine.loop_runner.services.context_manager is replacement_context
    assert engine.loop_runner.services.memory_runtime is engine.memory_runtime
