"""Integration tests for US1: Real-Time Steering

Test Plan:
- test_interrupt_during_multi_step_task: Analyze 100 files, interrupt at 50%, verify <2s stop + partial results
- test_prioritization_change: Queue 5 tasks with priority, change priority mid-execution, verify reordering
- test_cancel_llm_call: Start LLM request, cancel mid-flight, verify resource cleanup

Independent Test: Agent processes 100-file analysis, receives interrupt signal mid-execution,
stops within 2s and returns partial results.
"""

import asyncio
import time
from pathlib import Path
from typing import List

import pytest

from loom.components.agent import Agent
from loom.builtin.llms.mock import MockLLM
from loom.builtin.tools.read_file import ReadFileTool
from loom.core.types import Message


@pytest.mark.integration
async def test_interrupt_during_multi_step_task():
    """Test agent stops within 2s on interrupt and returns partial results.

    Acceptance Criteria:
    - Agent analyzes 100 files (simulated with slow ReadFileTool)
    - Interrupt signal sent after ~50 files processed
    - Agent stops within 2000ms of interrupt
    - Partial results returned (at least 40-60 files analyzed)
    - No resource leaks (file handles, async tasks)
    """
    # Arrange: Create agent with steering enabled
    llm = MockLLM(responses=[
        "I'll analyze all 100 files systematically.",
        "Analysis complete for batch 1-50.",
        "Continuing with batch 51-100...",
    ])

    read_tool = ReadFileTool()
    agent = Agent(
        llm=llm,
        tools=[read_tool],
        enable_steering=True,  # NEW: Enable h2A message queue
        max_iterations=100,
    )

    # Create cancel token
    cancel_token = asyncio.Event()

    # Act: Start long-running task
    task = asyncio.create_task(
        agent.run(
            "Analyze all 100 Python files in this directory",
            cancel_token=cancel_token,  # NEW parameter
        )
    )

    # Simulate interrupt after 1 second (should process ~50 files)
    await asyncio.sleep(1.0)
    interrupt_time = time.time()
    cancel_token.set()  # Signal cancellation

    # Assert: Agent stops within 2s
    try:
        result = await asyncio.wait_for(task, timeout=2.0)
        stop_time = time.time()

        # Verify stop time
        elapsed_ms = (stop_time - interrupt_time) * 1000
        assert elapsed_ms < 2000, f"Agent took {elapsed_ms}ms to stop (expected <2000ms)"

        # Verify partial results returned
        assert result is not None
        assert "partial" in result.lower() or "interrupted" in result.lower()

        # Verify no resource leaks (check open tasks)
        pending_tasks = [t for t in asyncio.all_tasks() if not t.done()]
        assert len(pending_tasks) <= 1, f"Resource leak: {len(pending_tasks)} tasks still running"

    except asyncio.TimeoutError:
        pytest.fail("Agent failed to stop within 2s timeout")


@pytest.mark.integration
async def test_prioritization_change():
    """Test dynamic priority reordering mid-execution.

    Acceptance Criteria:
    - Queue 5 tasks with different priorities
    - Change priority of low-priority task to high mid-execution
    - Verify task execution order reflects new priority
    """
    # Arrange: Create message queue directly
    from loom.core.message_queue import MessageQueue  # Will be created in T026
    from loom.core.types import MessageQueueItem

    queue = MessageQueue()

    # Add 5 tasks with priorities
    tasks = [
        MessageQueueItem(role="user", content="Task A", priority=5),
        MessageQueueItem(role="user", content="Task B", priority=3),
        MessageQueueItem(role="user", content="Task C", priority=8),
        MessageQueueItem(role="user", content="Task D", priority=1),
        MessageQueueItem(role="user", content="Task E", priority=6),
    ]

    for task in tasks:
        await queue.put(task)

    # Act: Get first task (should be highest priority: Task C, priority 8)
    first_task = await queue.get()
    assert first_task.content == "Task C", "Expected highest priority task first"

    # Change Task D priority from 1 to 10 (highest)
    new_task_d = MessageQueueItem(role="user", content="Task D", priority=10)
    await queue.put(new_task_d)

    # Assert: Next task should be updated Task D
    second_task = await queue.get()
    assert second_task.content == "Task D", "Priority change not reflected"


@pytest.mark.integration
async def test_cancel_llm_call():
    """Test LLM call cancellation and resource cleanup.

    Acceptance Criteria:
    - Start LLM request (simulated with slow MockLLM)
    - Cancel mid-flight
    - Verify LLM call terminated
    - Verify agent returns gracefully
    - No hanging HTTP connections or async tasks
    """
    # Arrange: MockLLM with artificial delay
    async def slow_response(*args, **kwargs):
        await asyncio.sleep(5.0)  # Simulate slow LLM
        return "This should never be returned"

    llm = MockLLM(responses=["Placeholder"])
    llm.generate = slow_response  # Override with slow version

    agent = Agent(
        llm=llm,
        tools=[],
        enable_steering=True,
    )

    cancel_token = asyncio.Event()

    # Act: Start request and cancel immediately
    task = asyncio.create_task(
        agent.run("Ask a question", cancel_token=cancel_token)
    )

    await asyncio.sleep(0.5)  # Let LLM call start
    cancel_time = time.time()
    cancel_token.set()

    # Assert: Task completes quickly (not waiting for 5s LLM response)
    try:
        result = await asyncio.wait_for(task, timeout=2.0)
        stop_time = time.time()

        elapsed = stop_time - cancel_time
        assert elapsed < 2.0, f"LLM cancellation took {elapsed}s (expected <2s)"

        # Verify graceful return (not exception)
        assert isinstance(result, str)
        assert "cancel" in result.lower() or "interrupt" in result.lower()

    except asyncio.TimeoutError:
        pytest.fail("LLM cancellation timed out - resource leak suspected")
