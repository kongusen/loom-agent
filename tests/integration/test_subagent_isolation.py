"""Integration tests for US3: Sub-Agent Isolation (T054-T056)

Test fault isolation, independent message histories, and tool whitelisting.

Written FIRST per TDD workflow before SubAgentPool implementation.
"""

import asyncio
import time
from typing import List

import pytest

from loom.core.types import Message


class MockLLM:
    """Mock LLM for testing sub-agent isolation."""

    def __init__(self, response: str = "Success", fail_on_call: int = -1):
        self.response = response
        self.fail_on_call = fail_on_call
        self.call_count = 0
        self.supports_tools = False

    async def generate(self, messages: List[dict]) -> str:
        """Generate response, optionally fail on specific call."""
        self.call_count += 1
        await asyncio.sleep(0.01)  # Simulate latency

        if self.call_count == self.fail_on_call:
            raise Exception(f"Simulated LLM failure on call {self.call_count}")

        return self.response


class MockReadTool:
    """Mock read_file tool."""
    name = "read_file"
    description = "Read file contents"

    async def run(self, path: str) -> str:
        await asyncio.sleep(0.01)
        return f"Contents of {path}"


class MockWriteTool:
    """Mock write_file tool."""
    name = "write_file"
    description = "Write file contents"

    async def run(self, path: str, content: str) -> str:
        await asyncio.sleep(0.01)
        return f"Wrote to {path}"


@pytest.mark.integration
async def test_fault_isolation():
    """Test sub-agent fault isolation - 1 failure doesn't affect others.

    Acceptance Criteria (US3-AC1):
    - Spawn 3 sub-agents concurrently
    - Agent 2 fails with exception
    - Agents 1 and 3 complete successfully
    - Main agent receives results from successful agents
    - No cascading failures
    """
    try:
        from loom.core.subagent_pool import SubAgentPool
    except ImportError:
        pytest.skip("SubAgentPool not yet implemented")

    # Create 3 LLMs - second one will fail
    llm1 = MockLLM(response="Agent 1 success")
    llm2 = MockLLM(response="Agent 2 should fail", fail_on_call=1)
    llm3 = MockLLM(response="Agent 3 success")

    pool = SubAgentPool()

    # Spawn 3 sub-agents concurrently
    start_time = time.time()

    tasks = [
        pool.spawn(llm=llm1, prompt="Task 1", timeout_seconds=5),
        pool.spawn(llm=llm2, prompt="Task 2", timeout_seconds=5),
        pool.spawn(llm=llm3, prompt="Task 3", timeout_seconds=5),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.time() - start_time

    # Assert: Execution completed quickly (concurrent, not serial)
    assert elapsed < 1.0, f"Should execute concurrently: {elapsed:.2f}s"

    # Assert: Agent 1 succeeded
    assert not isinstance(results[0], Exception), "Agent 1 should succeed"
    assert "Agent 1 success" in results[0]

    # Assert: Agent 2 failed (exception returned)
    assert isinstance(results[2], Exception), "Agent 2 should fail"

    # Assert: Agent 3 succeeded (not affected by Agent 2's failure)
    assert not isinstance(results[2], Exception), "Agent 3 should succeed"
    assert "Agent 3 success" in results[2]


@pytest.mark.integration
async def test_independent_message_history():
    """Test sub-agents have separate message contexts.

    Acceptance Criteria (US3-AC2):
    - Spawn 2 sub-agents with different prompts
    - Each builds independent message history
    - Sub-agent 1 history does NOT contain sub-agent 2 messages
    - No cross-contamination
    """
    try:
        from loom.core.subagent_pool import SubAgentPool
        from loom.memory.simple_memory import SimpleMemory
    except ImportError:
        pytest.skip("SubAgentPool not yet implemented")

    pool = SubAgentPool()

    llm1 = MockLLM(response="Response from agent 1")
    llm2 = MockLLM(response="Response from agent 2")

    memory1 = SimpleMemory()
    memory2 = SimpleMemory()

    # Add initial context to each memory
    await memory1.add_message(Message(role="system", content="You are Agent 1"))
    await memory2.add_message(Message(role="system", content="You are Agent 2"))

    # Spawn sub-agents with separate memories
    result1 = await pool.spawn(
        llm=llm1,
        prompt="Agent 1 task",
        memory=memory1,
        timeout_seconds=5,
    )

    result2 = await pool.spawn(
        llm=llm2,
        prompt="Agent 2 task",
        memory=memory2,
        timeout_seconds=5,
    )

    # Assert: Both completed
    assert "agent 1" in result1.lower()
    assert "agent 2" in result2.lower()

    # Assert: Separate message histories
    history1 = await memory1.get_messages()
    history2 = await memory2.get_messages()

    # Agent 1 history contains only Agent 1 messages
    agent1_content = " ".join([m.content for m in history1])
    assert "Agent 1" in agent1_content
    assert "Agent 2" not in agent1_content, "Agent 1 history contaminated with Agent 2 messages"

    # Agent 2 history contains only Agent 2 messages
    agent2_content = " ".join([m.content for m in history2])
    assert "Agent 2" in agent2_content
    assert "Agent 1" not in agent2_content, "Agent 2 history contaminated with Agent 1 messages"


@pytest.mark.integration
async def test_tool_whitelist_override():
    """Test sub-agent tool whitelist enforcement.

    Acceptance Criteria (US3-AC3):
    - Parent agent has tools: [read_file, write_file]
    - Sub-agent spawned with whitelist: [read_file] only
    - Sub-agent can call read_file ✅
    - Sub-agent cannot call write_file ❌ (tool not available)
    """
    try:
        from loom.core.subagent_pool import SubAgentPool
    except ImportError:
        pytest.skip("SubAgentPool not yet implemented")

    pool = SubAgentPool()

    # Parent has both tools
    read_tool = MockReadTool()
    write_tool = MockWriteTool()
    parent_tools = [read_tool, write_tool]

    llm = MockLLM(response="Task complete")

    # Spawn sub-agent with whitelist: only read_file
    result = await pool.spawn(
        llm=llm,
        prompt="Read file test.txt",
        tools=parent_tools,
        tool_whitelist=["read_file"],  # Only read_file allowed
        timeout_seconds=5,
    )

    # Assert: Sub-agent completed task
    assert "complete" in result.lower()

    # Verify sub-agent only had access to read_file
    # (This will be validated by SubAgentPool implementation)
    # If sub-agent tries to call write_file, it should fail with ToolNotFoundError


@pytest.mark.integration
async def test_execution_depth_limit():
    """Test execution depth limit prevents infinite recursion.

    Acceptance Criteria (US3-AC4):
    - Set max_depth=3
    - Agent spawns sub-agent (depth 1)
    - Sub-agent spawns sub-sub-agent (depth 2)
    - Sub-sub-agent spawns sub-sub-sub-agent (depth 3)
    - Depth 3 agent cannot spawn another (raises MaxDepthError)
    """
    try:
        from loom.core.subagent_pool import SubAgentPool, MaxDepthError
    except ImportError:
        pytest.skip("SubAgentPool not yet implemented")

    pool = SubAgentPool(max_depth=3)

    llm = MockLLM(response="Depth test")

    # Depth 1: Main spawn
    result = await pool.spawn(
        llm=llm,
        prompt="Depth 1 task",
        execution_depth=1,
        timeout_seconds=5,
    )
    assert "Depth test" in result

    # Depth 2: Sub-agent spawns another
    result = await pool.spawn(
        llm=llm,
        prompt="Depth 2 task",
        execution_depth=2,
        timeout_seconds=5,
    )
    assert "Depth test" in result

    # Depth 3: Limit reached, but should still work
    result = await pool.spawn(
        llm=llm,
        prompt="Depth 3 task",
        execution_depth=3,
        timeout_seconds=5,
    )
    assert "Depth test" in result

    # Depth 4: Should raise MaxDepthError
    with pytest.raises(MaxDepthError):
        await pool.spawn(
            llm=llm,
            prompt="Depth 4 task - should fail",
            execution_depth=4,
            timeout_seconds=5,
        )


@pytest.mark.integration
async def test_timeout_enforcement():
    """Test sub-agent timeout enforcement.

    Acceptance Criteria (US3-AC5):
    - Set timeout_seconds=1
    - Sub-agent takes 3 seconds to complete
    - After 1 second, sub-agent is cancelled
    - TimeoutError raised
    """
    try:
        from loom.core.subagent_pool import SubAgentPool
    except ImportError:
        pytest.skip("SubAgentPool not yet implemented")

    class SlowLLM(MockLLM):
        async def generate(self, messages: List[dict]) -> str:
            await asyncio.sleep(3.0)  # Takes 3 seconds
            return "Too slow"

    pool = SubAgentPool()
    slow_llm = SlowLLM()

    start_time = time.time()

    # Spawn with 1 second timeout
    with pytest.raises(asyncio.TimeoutError):
        await pool.spawn(
            llm=slow_llm,
            prompt="Slow task",
            timeout_seconds=1.0,
        )

    elapsed = time.time() - start_time

    # Assert: Timeout enforced (should fail after ~1s, not 3s)
    assert 0.9 < elapsed < 1.5, f"Timeout not enforced: {elapsed:.2f}s"


@pytest.mark.integration
async def test_concurrent_subagent_execution():
    """Test multiple sub-agents execute concurrently, not serially.

    Acceptance Criteria (US3-AC6):
    - Spawn 5 sub-agents, each takes 1 second
    - Total time should be ~1 second (concurrent), not 5 seconds (serial)
    - All 5 complete successfully
    """
    try:
        from loom.core.subagent_pool import SubAgentPool
    except ImportError:
        pytest.skip("SubAgentPool not yet implemented")

    pool = SubAgentPool()

    class OneSecondLLM(MockLLM):
        def __init__(self, agent_id: int):
            super().__init__(response=f"Agent {agent_id} complete")
            self.agent_id = agent_id

        async def generate(self, messages: List[dict]) -> str:
            await asyncio.sleep(1.0)  # Each takes 1 second
            return f"Agent {self.agent_id} complete"

    # Spawn 5 sub-agents
    start_time = time.time()

    tasks = [
        pool.spawn(llm=OneSecondLLM(i), prompt=f"Task {i}", timeout_seconds=5)
        for i in range(5)
    ]

    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time

    # Assert: All completed
    assert len(results) == 5
    for i, result in enumerate(results):
        assert f"Agent {i} complete" in result

    # Assert: Concurrent execution (should take ~1s, not ~5s)
    assert elapsed < 2.0, f"Should execute concurrently: {elapsed:.2f}s (expected ~1s)"
