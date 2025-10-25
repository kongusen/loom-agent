"""
Unit tests for ToolOrchestrator

Tests intelligent tool execution orchestration with parallel/sequential execution.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from typing import Dict

from loom.core.tool_orchestrator import ToolOrchestrator, ToolCategory
from loom.core.types import ToolCall
from loom.core.events import AgentEvent, AgentEventType
from loom.interfaces.tool import BaseTool
from pydantic import BaseModel


# Mock tools for testing
class MockReadTool(BaseTool):
    name = "mock_read"
    description = "Mock read tool"
    args_schema = BaseModel

    is_read_only = True
    category = "general"

    async def run(self, **kwargs):
        return "read_result"


class MockWriteTool(BaseTool):
    name = "mock_write"
    description = "Mock write tool"
    args_schema = BaseModel

    is_read_only = False
    category = "destructive"

    async def run(self, **kwargs):
        return "write_result"


class TestToolOrchestrator:
    """Test ToolOrchestrator class."""

    def test_init(self):
        """Test initialization."""
        tools = {"read": MockReadTool(), "write": MockWriteTool()}
        orchestrator = ToolOrchestrator(tools=tools, max_parallel=3)

        assert orchestrator.tools == tools
        assert orchestrator.max_parallel == 3
        assert orchestrator.permission_manager is None

    def test_categorize_read_only_tools(self):
        """Test categorization of read-only tools."""
        tools = {
            "read1": MockReadTool(),
            "read2": MockReadTool(),
        }
        orchestrator = ToolOrchestrator(tools=tools)

        tool_calls = [
            ToolCall(id="1", name="read1", arguments={}),
            ToolCall(id="2", name="read2", arguments={}),
        ]

        read_only, write = orchestrator.categorize_tools(tool_calls)

        assert len(read_only) == 2
        assert len(write) == 0
        assert read_only[0].name == "read1"
        assert read_only[1].name == "read2"

    def test_categorize_write_tools(self):
        """Test categorization of write tools."""
        tools = {
            "write1": MockWriteTool(),
            "write2": MockWriteTool(),
        }
        orchestrator = ToolOrchestrator(tools=tools)

        tool_calls = [
            ToolCall(id="1", name="write1", arguments={}),
            ToolCall(id="2", name="write2", arguments={}),
        ]

        read_only, write = orchestrator.categorize_tools(tool_calls)

        assert len(read_only) == 0
        assert len(write) == 2
        assert write[0].name == "write1"
        assert write[1].name == "write2"

    def test_categorize_mixed_tools(self):
        """Test categorization of mixed tool calls."""
        tools = {
            "read": MockReadTool(),
            "write": MockWriteTool(),
        }
        orchestrator = ToolOrchestrator(tools=tools)

        tool_calls = [
            ToolCall(id="1", name="read", arguments={}),
            ToolCall(id="2", name="write", arguments={}),
            ToolCall(id="3", name="read", arguments={}),
        ]

        read_only, write = orchestrator.categorize_tools(tool_calls)

        assert len(read_only) == 2
        assert len(write) == 1
        assert read_only[0].name == "read"
        assert write[0].name == "write"

    @pytest.mark.asyncio
    async def test_execute_one_success(self):
        """Test single tool execution success."""
        tool = MockReadTool()
        tools = {"mock_read": tool}
        orchestrator = ToolOrchestrator(tools=tools)

        tool_call = ToolCall(id="1", name="mock_read", arguments={})

        events = []
        async for event in orchestrator.execute_one(tool_call):
            events.append(event)

        # Should emit start and result events
        assert len(events) == 2
        assert events[0].type == AgentEventType.TOOL_EXECUTION_START
        assert events[1].type == AgentEventType.TOOL_RESULT
        assert events[1].tool_result.content == "read_result"
        assert events[1].tool_result.is_error is False

    @pytest.mark.asyncio
    async def test_execute_one_error(self):
        """Test single tool execution error handling."""
        class ErrorTool(BaseTool):
            name = "error_tool"
            description = "Tool that raises error"
            args_schema = BaseModel
            is_read_only = True

            async def run(self, **kwargs):
                raise ValueError("Test error")

        tools = {"error_tool": ErrorTool()}
        orchestrator = ToolOrchestrator(tools=tools)

        tool_call = ToolCall(id="1", name="error_tool", arguments={})

        events = []
        async for event in orchestrator.execute_one(tool_call):
            events.append(event)

        # Should emit start and error events
        assert len(events) == 2
        assert events[0].type == AgentEventType.TOOL_EXECUTION_START
        assert events[1].type == AgentEventType.TOOL_ERROR
        assert events[1].tool_result.is_error is True
        assert "Test error" in events[1].tool_result.content

    @pytest.mark.asyncio
    async def test_execute_batch_mixed(self):
        """Test batch execution with mixed tools."""
        tools = {
            "read": MockReadTool(),
            "write": MockWriteTool(),
        }
        orchestrator = ToolOrchestrator(tools=tools)

        tool_calls = [
            ToolCall(id="1", name="read", arguments={}),
            ToolCall(id="2", name="write", arguments={}),
        ]

        events = []
        async for event in orchestrator.execute_batch(tool_calls):
            events.append(event)

        # Should have events for both parallel and sequential phases
        event_types = [e.type for e in events]

        # Check for key events
        assert AgentEventType.TOOL_CALLS_START in event_types
        assert AgentEventType.PHASE_START in event_types
        assert AgentEventType.PHASE_END in event_types
        assert AgentEventType.TOOL_EXECUTION_START in event_types
        assert AgentEventType.TOOL_RESULT in event_types

        # Should have 2 tool results (one for each tool)
        results = [e for e in events if e.type == AgentEventType.TOOL_RESULT]
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_execute_parallel_read_only(self):
        """Test parallel execution of read-only tools."""
        tools = {
            "read1": MockReadTool(),
            "read2": MockReadTool(),
        }
        orchestrator = ToolOrchestrator(tools=tools, max_parallel=2)

        tool_calls = [
            ToolCall(id="1", name="read1", arguments={}),
            ToolCall(id="2", name="read2", arguments={}),
        ]

        events = []
        async for event in orchestrator.execute_parallel(tool_calls):
            events.append(event)

        # Should execute both tools
        results = [e for e in events if e.type == AgentEventType.TOOL_RESULT]
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_execute_sequential_write(self):
        """Test sequential execution of write tools."""
        tools = {
            "write1": MockWriteTool(),
            "write2": MockWriteTool(),
        }
        orchestrator = ToolOrchestrator(tools=tools)

        tool_calls = [
            ToolCall(id="1", name="write1", arguments={}),
            ToolCall(id="2", name="write2", arguments={}),
        ]

        events = []
        async for event in orchestrator.execute_sequential(tool_calls):
            events.append(event)

        # Should execute both tools sequentially
        results = [e for e in events if e.type == AgentEventType.TOOL_RESULT]
        assert len(results) == 2

    def test_get_orchestration_summary(self):
        """Test orchestration summary generation."""
        tools = {
            "read": MockReadTool(),
            "write": MockWriteTool(),
        }
        orchestrator = ToolOrchestrator(tools=tools, max_parallel=5)

        tool_calls = [
            ToolCall(id="1", name="read", arguments={}),
            ToolCall(id="2", name="write", arguments={}),
            ToolCall(id="3", name="read", arguments={}),
        ]

        summary = orchestrator.get_orchestration_summary(tool_calls)

        assert summary["total_tools"] == 3
        assert summary["read_only_count"] == 2
        assert summary["write_count"] == 1
        assert "read" in summary["read_only_tools"]
        assert "write" in summary["write_tools"]
        assert summary["max_parallel"] == 5


class TestToolCategorization:
    """Test tool categorization logic."""

    def test_read_tool_is_read_only(self):
        """Verify MockReadTool is classified as read-only."""
        tool = MockReadTool()
        assert tool.is_read_only is True
        assert tool.category == "general"

    def test_write_tool_is_write(self):
        """Verify MockWriteTool is classified as write."""
        tool = MockWriteTool()
        assert tool.is_read_only is False
        assert tool.category == "destructive"


class TestBuiltinToolClassification:
    """Test built-in tools have correct classification."""

    def test_read_file_tool_classification(self):
        """Test ReadFileTool is read-only."""
        from loom.builtin.tools.read_file import ReadFileTool
        tool = ReadFileTool()
        assert tool.is_read_only is True
        assert tool.category == "general"

    def test_write_file_tool_classification(self):
        """Test WriteFileTool is write."""
        from loom.builtin.tools.write_file import WriteFileTool
        tool = WriteFileTool()
        assert tool.is_read_only is False
        assert tool.category == "destructive"

    def test_grep_tool_classification(self):
        """Test GrepTool is read-only."""
        from loom.builtin.tools.grep import GrepTool
        tool = GrepTool()
        assert tool.is_read_only is True
        assert tool.category == "general"

    def test_glob_tool_classification(self):
        """Test GlobTool is read-only."""
        from loom.builtin.tools.glob import GlobTool
        tool = GlobTool()
        assert tool.is_read_only is True
        assert tool.category == "general"

    def test_calculator_classification(self):
        """Test Calculator is read-only."""
        from loom.builtin.tools.calculator import Calculator
        tool = Calculator()
        assert tool.is_read_only is True
        assert tool.category == "general"


@pytest.mark.asyncio
class TestRaceConditionPrevention:
    """Test race condition prevention."""

    async def test_read_and_write_same_file(self):
        """Test Read and Write on same file execute safely."""
        # In real scenario, write should execute after read
        tools = {
            "read": MockReadTool(),
            "write": MockWriteTool(),
        }
        orchestrator = ToolOrchestrator(tools=tools)

        tool_calls = [
            ToolCall(id="1", name="read", arguments={"path": "test.txt"}),
            ToolCall(id="2", name="write", arguments={"path": "test.txt"}),
        ]

        # Categorize to verify separation
        read_only, write = orchestrator.categorize_tools(tool_calls)
        assert len(read_only) == 1
        assert len(write) == 1

        # Execute and verify both complete
        events = []
        async for event in orchestrator.execute_batch(tool_calls):
            events.append(event)

        results = [e for e in events if e.type == AgentEventType.TOOL_RESULT]
        assert len(results) == 2

    async def test_multiple_reads_parallel(self):
        """Test multiple Reads can execute in parallel."""
        tools = {
            "read1": MockReadTool(),
            "read2": MockReadTool(),
            "read3": MockReadTool(),
        }
        orchestrator = ToolOrchestrator(tools=tools, max_parallel=3)

        tool_calls = [
            ToolCall(id=str(i), name=f"read{i+1}", arguments={})
            for i in range(3)
        ]

        events = []
        async for event in orchestrator.execute_batch(tool_calls):
            events.append(event)

        # All should execute (in parallel)
        results = [e for e in events if e.type == AgentEventType.TOOL_RESULT]
        assert len(results) == 3
