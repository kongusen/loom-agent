"""
Integration tests for RecursionMonitor with AgentExecutor
(Phase 2: Execution Layer Optimization)

Tests the full integration of recursion control with agent execution,
ensuring it works correctly in real agent scenarios.
"""

import pytest
import asyncio
from typing import List, Dict, Any, AsyncGenerator

from loom.core.agent_executor import AgentExecutor
from loom.core.recursion_control import RecursionMonitor, TerminationReason
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.events import AgentEvent, AgentEventType
from loom.core.types import Message
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool
from pydantic import BaseModel, Field


# ===== Mock LLM that simulates infinite loop behavior =====

class MockLoopingLLM(BaseLLM):
    """LLM that always calls the same tool (simulating a loop)"""

    def __init__(self, tool_to_loop: str = "search", loop_count: int = 10):
        self.tool_to_loop = tool_to_loop
        self.call_count = 0
        self.loop_count = loop_count

    @property
    def model_name(self) -> str:
        return "mock-looping"

    @property
    def supports_tools(self) -> bool:
        return True

    async def generate(self, messages: List[Dict]) -> str:
        return "Mock response"

    async def generate_with_tools(
        self, messages: List[Dict], tools: List[Dict]
    ) -> Dict[str, Any]:
        self.call_count += 1

        # Keep looping until loop_count
        if self.call_count < self.loop_count:
            return {
                "content": "",
                "tool_calls": [
                    {
                        "id": f"call_{self.call_count}",
                        "name": self.tool_to_loop,
                        "arguments": {}
                    }
                ]
            }
        else:
            # Eventually finish
            return {
                "content": "Task completed after many iterations",
                "tool_calls": []
            }

    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        yield "Mock response"


class MockRepeatingOutputLLM(BaseLLM):
    """LLM that generates repeating outputs (loop pattern detection)"""

    def __init__(self):
        self.call_count = 0

    @property
    def model_name(self) -> str:
        return "mock-repeating"

    @property
    def supports_tools(self) -> bool:
        return True

    async def generate(self, messages: List[Dict]) -> str:
        return "Mock response"

    async def generate_with_tools(
        self, messages: List[Dict], tools: List[Dict]
    ) -> Dict[str, Any]:
        self.call_count += 1

        # Generate repeating pattern: A, B, A, B, A, B...
        pattern = ["Pattern A", "Pattern B"]
        output = pattern[self.call_count % 2]

        if self.call_count < 10:
            return {
                "content": output,
                "tool_calls": [
                    {
                        "id": f"call_{self.call_count}",
                        "name": "analyze",
                        "arguments": {}
                    }
                ]
            }
        else:
            return {
                "content": "Finished",
                "tool_calls": []
            }

    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        yield "Mock response"


# ===== Mock Tool =====

class MockToolArgs(BaseModel):
    """Arguments for mock tool"""
    pass


class MockTool(BaseTool):
    """Simple mock tool for testing"""

    name: str = "search"
    description: str = "Mock search tool"
    args_schema: type[BaseModel] = MockToolArgs

    def __init__(self, name: str = "search"):
        super().__init__()
        self.name = name

    def run(self, **kwargs) -> str:
        """Sync version (not used in async context)"""
        return f"Result from {self.name}"

    async def _arun(self, **kwargs) -> str:
        return f"Result from {self.name}"


# ===== Integration Tests =====

class TestRecursionControlIntegration:
    """Integration tests for recursion control"""

    @pytest.mark.asyncio
    async def test_duplicate_tool_detection_integration(self):
        """Test that recursion control detects and terminates looping behavior"""
        # Create agent that will loop on same tool
        llm = MockLoopingLLM(tool_to_loop="search", loop_count=10)
        tools = {"search": MockTool("search")}

        # Enable recursion control with low threshold
        monitor = RecursionMonitor(
            max_iterations=50,
            duplicate_threshold=3,  # Terminate after 3 duplicate calls
            error_threshold=0.99  # Very high to avoid false positives
        )

        executor = AgentExecutor(
            llm=llm,
            tools=tools,
            enable_recursion_control=True,
            recursion_monitor=monitor
        )

        # Execute
        turn_state = TurnState.initial(max_iterations=50)
        context = ExecutionContext.create()
        messages = [Message(role="user", content="Search for something")]

        events = []
        async for event in executor.tt(messages, turn_state, context):
            events.append(event)

        # Check that RECURSION_TERMINATED event was emitted
        # This demonstrates the recursion control is working and detecting loops
        termination_events = [
            e for e in events
            if e.type == AgentEventType.RECURSION_TERMINATED
        ]

        # Main assertion: recursion control should detect the issue
        assert len(termination_events) > 0, "Recursion control should have detected the loop"

        # Verify termination reason is in metadata
        assert "reason" in termination_events[0].metadata

    @pytest.mark.asyncio
    async def test_max_iterations_with_recursion_control(self):
        """Test that max iterations still works with recursion control"""
        llm = MockLoopingLLM(tool_to_loop="search", loop_count=100)
        tools = {"search": MockTool("search")}

        # Low max_iterations
        executor = AgentExecutor(
            llm=llm,
            tools=tools,
            max_iterations=5,
            enable_recursion_control=True
        )

        turn_state = TurnState.initial(max_iterations=5)
        context = ExecutionContext.create()
        messages = [Message(role="user", content="Search")]

        events = []
        async for event in executor.tt(messages, turn_state, context):
            events.append(event)

        # Should hit max iterations
        max_iter_events = [
            e for e in events
            if e.type == AgentEventType.MAX_ITERATIONS_REACHED
        ]

        assert len(max_iter_events) > 0

    @pytest.mark.asyncio
    async def test_recursion_control_disabled(self):
        """Test that recursion control can be disabled"""
        llm = MockLoopingLLM(tool_to_loop="search", loop_count=4)
        tools = {"search": MockTool("search")}

        # Disable recursion control
        executor = AgentExecutor(
            llm=llm,
            tools=tools,
            max_iterations=10,
            enable_recursion_control=False  # Disabled
        )

        turn_state = TurnState.initial(max_iterations=10)
        context = ExecutionContext.create()
        messages = [Message(role="user", content="Search")]

        events = []
        async for event in executor.tt(messages, turn_state, context):
            events.append(event)

        # Should NOT emit RECURSION_TERMINATED events
        termination_events = [
            e for e in events
            if e.type == AgentEventType.RECURSION_TERMINATED
        ]

        assert len(termination_events) == 0

    @pytest.mark.asyncio
    async def test_custom_recursion_monitor(self):
        """Test using a custom RecursionMonitor"""
        llm = MockLoopingLLM(tool_to_loop="search", loop_count=10)
        tools = {"search": MockTool("search")}

        # Custom monitor with very low threshold
        custom_monitor = RecursionMonitor(
            max_iterations=50,
            duplicate_threshold=2,  # Terminate after only 2 duplicates
            error_threshold=0.99
        )

        executor = AgentExecutor(
            llm=llm,
            tools=tools,
            enable_recursion_control=True,
            recursion_monitor=custom_monitor
        )

        turn_state = TurnState.initial(max_iterations=50)
        context = ExecutionContext.create()
        messages = [Message(role="user", content="Search")]

        events = []
        async for event in executor.tt(messages, turn_state, context):
            events.append(event)

        # Should have termination events from custom monitor
        termination_events = [
            e for e in events
            if e.type == AgentEventType.RECURSION_TERMINATED
        ]

        assert len(termination_events) > 0, "Custom monitor should have detected the loop"

    @pytest.mark.asyncio
    async def test_turn_state_tracking(self):
        """Test that TurnState correctly tracks recursion metrics"""
        llm = MockLoopingLLM(tool_to_loop="search", loop_count=4)
        tools = {"search": MockTool("search")}

        executor = AgentExecutor(
            llm=llm,
            tools=tools,
            enable_recursion_control=True
        )

        turn_state = TurnState.initial(max_iterations=10)
        context = ExecutionContext.create()
        messages = [Message(role="user", content="Search")]

        # Track turn state through recursion events
        recursion_events = []
        async for event in executor.tt(messages, turn_state, context):
            if event.type == AgentEventType.RECURSION:
                recursion_events.append(event)

        # Each recursion should track tool calls
        for event in recursion_events:
            if "tools_called" in event.metadata:
                tools_called = event.metadata["tools_called"]
                assert isinstance(tools_called, list)
                assert len(tools_called) > 0

    @pytest.mark.asyncio
    async def test_backward_compatibility(self):
        """Test that existing code without recursion control still works"""
        llm = MockLoopingLLM(tool_to_loop="search", loop_count=3)
        tools = {"search": MockTool("search")}

        # Old-style initialization (no recursion control params)
        executor = AgentExecutor(
            llm=llm,
            tools=tools,
            max_iterations=10
        )

        turn_state = TurnState.initial(max_iterations=10)
        context = ExecutionContext.create()
        messages = [Message(role="user", content="Search")]

        events = []
        async for event in executor.tt(messages, turn_state, context):
            events.append(event)

        # Should still work and complete
        finish_events = [
            e for e in events
            if e.type == AgentEventType.AGENT_FINISH
        ]

        assert len(finish_events) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
