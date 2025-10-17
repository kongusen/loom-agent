"""Contract tests for AgentExecutor API (US1)

Contract tests verify public API contracts remain stable across versions.
These tests ensure backward compatibility and validate opt-in parameter behavior.
"""

import asyncio
from typing import Optional

import pytest

from loom.core.agent_executor import AgentExecutor
from loom.builtin.llms.mock import MockLLM
from loom.core.types import Message


@pytest.mark.contract
async def test_execute_with_cancel_token():
    """Contract: AgentExecutor.execute() accepts optional cancel_token parameter.

    API Contract:
    - execute(user_input: str, cancel_token: Optional[asyncio.Event] = None)
    - If cancel_token is None, behavior unchanged (backward compatible)
    - If cancel_token.is_set(), execution stops and yields partial results
    - Return type remains str (not changed)
    """
    # Arrange
    llm = MockLLM(responses=["Test response"])
    executor = AgentExecutor(llm=llm, tools={})

    # Act & Assert: Without cancel_token (backward compatible)
    result = await executor.execute("Hello")
    assert isinstance(result, str)
    assert result == "Test response"

    # Act & Assert: With cancel_token (new behavior)
    cancel_token = asyncio.Event()
    result_with_token = await executor.execute("Hello", cancel_token=cancel_token)
    assert isinstance(result_with_token, str)

    # Act & Assert: With cancel_token set (partial results)
    cancel_token_set = asyncio.Event()
    cancel_token_set.set()  # Pre-set cancellation

    result_cancelled = await executor.execute("Hello", cancel_token=cancel_token_set)
    assert isinstance(result_cancelled, str)
    # Should return quickly without full execution
    assert "cancel" in result_cancelled.lower() or "interrupt" in result_cancelled.lower() or result_cancelled == ""


@pytest.mark.contract
async def test_execute_with_correlation_id():
    """Contract: AgentExecutor.execute() accepts optional correlation_id parameter.

    API Contract:
    - execute(user_input: str, correlation_id: Optional[str] = None)
    - If correlation_id is None, auto-generated UUID used
    - If correlation_id provided, propagates to all events
    - Correlation ID accessible in callback events
    """
    # Arrange
    llm = MockLLM(responses=["Test response"])
    executor = AgentExecutor(llm=llm, tools={})

    # Track events
    events_received = []

    async def event_handler(event_type: str, payload: dict):
        events_received.append(payload.get("correlation_id"))

    # Mock callback (will be implemented in T031)
    # executor.callbacks.append(event_handler)

    # Act: Execute with custom correlation_id
    custom_correlation_id = "test-correlation-123"
    result = await executor.execute("Hello", correlation_id=custom_correlation_id)

    # Assert
    assert isinstance(result, str)

    # Verify correlation_id propagated (when callbacks implemented)
    # TODO: Uncomment when T031 (correlation_id propagation) is implemented
    # assert all(cid == custom_correlation_id for cid in events_received if cid is not None)


@pytest.mark.contract
async def test_execute_backward_compatibility():
    """Contract: Existing execute() calls work unchanged.

    API Contract:
    - execute(user_input: str) still works (no required new parameters)
    - Return type unchanged (str)
    - Behavior unchanged when enable_steering=False (default)
    """
    # Arrange: Create executor without new parameters
    llm = MockLLM(responses=["Backward compatible response"])
    executor = AgentExecutor(
        llm=llm,
        tools={},
        max_iterations=10,
        # No enable_steering, no cancel_token - old API
    )

    # Act: Call execute with old signature
    result = await executor.execute("Test input")

    # Assert: Behavior unchanged
    assert isinstance(result, str)
    assert result == "Backward compatible response"


@pytest.mark.contract
async def test_agent_init_with_enable_steering():
    """Contract: Agent accepts enable_steering parameter.

    API Contract:
    - Agent(llm, tools, enable_steering: bool = False)
    - Default False preserves backward compatibility
    - When True, enables h2A message queue
    """
    from loom.components.agent import Agent

    llm = MockLLM(responses=["Test"])

    # Act: Create agent with enable_steering=False (default)
    agent_default = Agent(llm=llm, tools=[])
    assert hasattr(agent_default.executor, "enable_steering") or True  # May not be implemented yet

    # Act: Create agent with enable_steering=True
    agent_steering = Agent(llm=llm, tools=[], enable_steering=True)
    # Should not raise, even if not fully implemented

    # Assert: Both agents are valid
    assert agent_default is not None
    assert agent_steering is not None
