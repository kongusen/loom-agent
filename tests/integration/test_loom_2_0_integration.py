"""
Integration tests for loom-agent 2.0 architecture.

Tests the new features:
- ExecutionFrame
- EventJournal and crash recovery
- LifecycleHooks (including HITL)
- ContextDebugger
- StateReconstructor
"""

import asyncio
import pytest
from pathlib import Path
import tempfile
import shutil
from typing import List, Dict, Any

from loom.core.agent_executor import AgentExecutor
from loom.core.execution_context import ExecutionContext
from loom.core.execution_frame import ExecutionFrame, ExecutionPhase
from loom.core.event_journal import EventJournal
from loom.core.context_debugger import ContextDebugger
from loom.core.state_reconstructor import StateReconstructor
from loom.core.lifecycle_hooks import (
    LifecycleHook,
    HITLHook,
    LoggingHook,
    MetricsHook,
    InterruptException,
)
from loom.core.turn_state import TurnState
from loom.core.types import Message
from loom.core.events import AgentEventType
from loom.builtin.llms import MockLLM
from loom import tool


# ==========================================
# Test Fixtures
# ==========================================

@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for logs."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    return MockLLM(
        responses=[
            "I'll search for that.",
            "Here's what I found: Test result.",
        ]
    )


@pytest.fixture
def test_tool():
    """Create a simple test tool."""
    @tool(description="Search for information")
    async def search(query: str) -> str:
        return f"Found results for: {query}"

    return search()


# ==========================================
# Test: Basic Execution with Hooks
# ==========================================

@pytest.mark.asyncio
async def test_basic_execution_with_logging_hook(mock_llm, test_tool, temp_log_dir):
    """Test basic execution with LoggingHook."""

    # Create hooks
    logging_hook = LoggingHook(verbose=True)
    metrics_hook = MetricsHook()

    # Create executor
    executor = AgentExecutor(
        llm=mock_llm,
        tools={"search": test_tool},
        max_iterations=5,
        hooks=[logging_hook, metrics_hook],
    )

    # Execute
    turn_state = TurnState.initial(max_iterations=5)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Search for Python docs")]

    events = []
    async for event in executor.tt(messages, turn_state, context):
        events.append(event)
        if event.type == AgentEventType.AGENT_FINISH:
            break

    # Verify events were emitted
    assert len(events) > 0
    assert any(e.type == AgentEventType.ITERATION_START for e in events)
    assert any(e.type == AgentEventType.LLM_COMPLETE for e in events)
    assert any(e.type == AgentEventType.AGENT_FINISH for e in events)

    # Verify metrics were collected
    metrics = metrics_hook.get_metrics()
    assert metrics["llm_calls"] >= 1
    assert metrics["iterations"] >= 1


# ==========================================
# Test: EventJournal Recording and Replay
# ==========================================

@pytest.mark.asyncio
async def test_event_journal_recording(mock_llm, test_tool, temp_log_dir):
    """Test EventJournal records all events."""

    # Create journal
    journal = EventJournal(storage_path=temp_log_dir)
    await journal.start()

    # Create executor
    executor = AgentExecutor(
        llm=mock_llm,
        tools={"search": test_tool},
        max_iterations=5,
        event_journal=journal,
        thread_id="test-thread-1",
    )

    # Execute
    turn_state = TurnState.initial(max_iterations=5)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Search for Python docs")]

    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.AGENT_FINISH:
            break

    await journal.stop()

    # Replay events
    replayed_events = await journal.replay(thread_id="test-thread-1")

    # Verify events were recorded
    assert len(replayed_events) > 0
    assert any(e.type == AgentEventType.ITERATION_START for e in replayed_events)
    assert any(e.type == AgentEventType.LLM_COMPLETE for e in replayed_events)
    assert any(e.type == AgentEventType.AGENT_FINISH for e in replayed_events)


# ==========================================
# Test: StateReconstructor
# ==========================================

@pytest.mark.asyncio
async def test_state_reconstruction(mock_llm, test_tool, temp_log_dir):
    """Test StateReconstructor can rebuild state from events."""

    # Create journal
    journal = EventJournal(storage_path=temp_log_dir)
    await journal.start()

    # Create executor
    executor = AgentExecutor(
        llm=mock_llm,
        tools={"search": test_tool},
        max_iterations=5,
        event_journal=journal,
        thread_id="test-thread-2",
    )

    # Execute
    turn_state = TurnState.initial(max_iterations=5)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Search for Python docs")]

    final_depth = 0
    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.RECURSION:
            final_depth = event.metadata.get("depth", 0)
        if event.type == AgentEventType.AGENT_FINISH:
            break

    await journal.stop()

    # Reconstruct state
    events = await journal.replay(thread_id="test-thread-2")
    reconstructor = StateReconstructor()
    frame, metadata = await reconstructor.reconstruct(events)

    # Verify reconstruction
    assert frame is not None
    assert metadata.total_events > 0
    # Check if final_phase is a string or enum
    if isinstance(metadata.final_phase, str):
        assert metadata.final_phase in ["llm_call", "completed", "decision"]
    else:
        assert metadata.final_phase in [ExecutionPhase.LLM_CALL, ExecutionPhase.COMPLETED, ExecutionPhase.DECISION]
    assert frame.depth >= 0


# ==========================================
# Test: Crash Recovery with resume()
# ==========================================

@pytest.mark.asyncio
async def test_crash_recovery_resume(mock_llm, test_tool, temp_log_dir):
    """Test resume() can recover from crash."""

    # Create journal
    journal = EventJournal(storage_path=temp_log_dir)
    await journal.start()

    # First execution (simulate crash)
    executor1 = AgentExecutor(
        llm=mock_llm,
        tools={"search": test_tool},
        max_iterations=5,
        event_journal=journal,
        thread_id="test-thread-crash",
    )

    turn_state = TurnState.initial(max_iterations=5)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Search for Python docs")]

    # Execute partially (simulate crash after first event)
    event_count = 0
    async for event in executor1.tt(messages, turn_state, context):
        event_count += 1
        if event_count >= 5:  # Stop early to simulate crash
            break

    await journal.stop()

    # Verify events were recorded before crash
    events = await journal.replay(thread_id="test-thread-crash")
    assert len(events) >= 5

    # Resume execution
    executor2 = AgentExecutor(
        llm=mock_llm,
        tools={"search": test_tool},
        max_iterations=5,
        event_journal=journal,
        thread_id="test-thread-crash",
    )

    resumed = False
    async for event in executor2.resume(thread_id="test-thread-crash"):
        if event.type == AgentEventType.PHASE_START and event.phase == "resume":
            resumed = True
        if event.type == AgentEventType.AGENT_FINISH:
            break

    # Verify resumption worked
    assert resumed, "Resume phase should have started"


# ==========================================
# Test: HITL Hook with Interruption
# ==========================================

class MockLLMWithToolCalls(MockLLM):
    """Mock LLM that generates tool calls."""

    def __init__(self, tool_calls_to_generate, **kwargs):
        super().__init__(**kwargs)
        self.tool_calls_to_generate = tool_calls_to_generate

    async def generate_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        """Generate response with tool calls."""
        if self.tool_calls_to_generate:
            tool_calls = self.tool_calls_to_generate
            self.tool_calls_to_generate = []  # Only generate once
            return {
                "content": "I'll use the tool.",
                "tool_calls": tool_calls
            }
        return await super().generate_with_tools(messages, tools)


@pytest.mark.asyncio
async def test_hitl_hook_interruption(temp_log_dir):
    """Test HITLHook can interrupt execution."""

    # Create a dangerous tool
    @tool(description="Delete file")
    async def delete_file(path: str) -> str:
        return f"Deleted: {path}"

    # Create tool calls that the mock will generate
    tool_calls_to_generate = [
        {
            "id": "call_1",
            "name": "delete_file",
            "arguments": {"path": "/old/logs"}
        }
    ]

    # Create HITL hook that always rejects
    hitl_hook = HITLHook(
        dangerous_tools=["delete_file"],
        ask_user_callback=lambda msg: False  # Always reject
    )

    # Create journal to capture checkpoint
    journal = EventJournal(storage_path=temp_log_dir)
    await journal.start()

    # Create executor with mock that generates tool calls
    executor = AgentExecutor(
        llm=MockLLMWithToolCalls(
            tool_calls_to_generate=tool_calls_to_generate,
            responses=["I'll delete that file."]
        ),
        tools={"delete_file": delete_file()},
        max_iterations=5,
        hooks=[hitl_hook],
        event_journal=journal,
        thread_id="test-thread-hitl",
    )

    # Execute
    turn_state = TurnState.initial(max_iterations=5)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Delete old logs")]

    interrupted = False
    checkpoint_saved = False

    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.EXECUTION_CANCELLED:
            if event.metadata.get("interrupt"):
                interrupted = True
        if event.type == AgentEventType.PHASE_START and event.phase == "checkpoint":
            checkpoint_saved = True
            break  # Exit as expected

    await journal.stop()

    # Verify interruption occurred
    assert interrupted, "Execution should have been interrupted by HITL"
    assert checkpoint_saved, "Checkpoint should have been saved"


# ==========================================
# Test: ContextDebugger
# ==========================================

@pytest.mark.asyncio
async def test_context_debugger_recording(mock_llm, test_tool):
    """Test ContextDebugger records context decisions."""

    # Create debugger
    debugger = ContextDebugger(enable_auto_export=False)

    # Create executor
    executor = AgentExecutor(
        llm=mock_llm,
        tools={"search": test_tool},
        max_iterations=5,
        context_debugger=debugger,
        system_instructions="You are a helpful assistant.",
    )

    # Execute
    turn_state = TurnState.initial(max_iterations=5)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Search for Python docs")]

    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.AGENT_FINISH:
            break

    # Verify debugger recorded decisions
    summary = debugger.generate_summary()
    assert "Context Management Summary" in summary
    assert "Total iterations" in summary


# ==========================================
# Test: Complete Workflow
# ==========================================

@pytest.mark.asyncio
async def test_complete_workflow_integration(mock_llm, test_tool, temp_log_dir):
    """Test complete workflow with all features enabled."""

    # Create all components
    journal = EventJournal(storage_path=temp_log_dir)
    await journal.start()

    debugger = ContextDebugger(enable_auto_export=False)
    logging_hook = LoggingHook(verbose=False)
    metrics_hook = MetricsHook()

    # Create executor with all features
    executor = AgentExecutor(
        llm=mock_llm,
        tools={"search": test_tool},
        max_iterations=5,
        system_instructions="You are a helpful assistant.",
        hooks=[logging_hook, metrics_hook],
        event_journal=journal,
        context_debugger=debugger,
        thread_id="test-thread-complete",
    )

    # Execute
    turn_state = TurnState.initial(max_iterations=5)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Search for Python docs")]

    completed = False
    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.AGENT_FINISH:
            completed = True
            break

    await journal.stop()

    # Verify all components worked
    assert completed, "Execution should have completed"

    # Verify journal recorded events
    events = await journal.replay(thread_id="test-thread-complete")
    assert len(events) > 0

    # Verify debugger recorded
    summary = debugger.generate_summary()
    assert "Context Management Summary" in summary

    # Verify metrics
    metrics = metrics_hook.get_metrics()
    assert metrics["llm_calls"] >= 1


# ==========================================
# Test: Custom Hook
# ==========================================

class CustomHook:
    """Custom hook for testing."""

    def __init__(self):
        self.calls = []

    async def before_iteration_start(self, frame):
        self.calls.append(("before_iteration_start", frame.depth))
        return frame

    async def after_context_assembly(self, frame, context_snapshot, context_metadata):
        self.calls.append(("after_context_assembly", frame.depth))
        return None

    async def before_llm_call(self, frame, messages):
        self.calls.append(("before_llm_call", len(messages)))
        return None

    async def after_tool_execution(self, frame, tool_result):
        self.calls.append(("after_tool_execution", tool_result["tool_name"]))
        return None


@pytest.mark.asyncio
async def test_custom_hook_integration(mock_llm, test_tool):
    """Test custom hook is called at appropriate points."""

    custom_hook = CustomHook()

    # Create executor
    executor = AgentExecutor(
        llm=mock_llm,
        tools={"search": test_tool},
        max_iterations=5,
        hooks=[custom_hook],
    )

    # Execute
    turn_state = TurnState.initial(max_iterations=5)
    context = ExecutionContext.create()
    messages = [Message(role="user", content="Search for Python docs")]

    async for event in executor.tt(messages, turn_state, context):
        if event.type == AgentEventType.AGENT_FINISH:
            break

    # Verify hook was called
    assert len(custom_hook.calls) > 0
    assert any(call[0] == "before_iteration_start" for call in custom_hook.calls)
    assert any(call[0] == "after_context_assembly" for call in custom_hook.calls)
    assert any(call[0] == "before_llm_call" for call in custom_hook.calls)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
