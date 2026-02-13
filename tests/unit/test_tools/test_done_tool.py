"""
Tests for Done Tool
"""

import pytest

from loom.exceptions import TaskComplete
from loom.tools.builtin.done import create_done_tool, execute_done_tool


class TestCreateDoneTool:
    """Test suite for create_done_tool"""

    def test_create_done_tool(self):
        """Test creating done tool definition"""
        tool = create_done_tool()

        assert tool["type"] == "function"
        assert tool["function"]["name"] == "done"
        assert "parameters" in tool["function"]

    def test_done_tool_parameters(self):
        """Test done tool has correct parameters"""
        tool = create_done_tool()

        params = tool["function"]["parameters"]
        assert params["type"] == "object"
        assert "message" in params["properties"]
        assert params["properties"]["message"]["type"] == "string"
        assert params["required"] == []  # message is optional (signal-only semantics)

    def test_done_tool_description(self):
        """Test done tool description"""
        tool = create_done_tool()

        description = tool["function"]["description"]
        assert "completion" in description.lower()


class TestExecuteDoneTool:
    """Test suite for execute_done_tool"""

    @pytest.mark.asyncio
    async def test_execute_done_tool_with_message(self):
        """Test executing done tool with message"""
        with pytest.raises(TaskComplete) as exc_info:
            await execute_done_tool({"message": "Task completed successfully"})

        assert exc_info.value.message == "Task completed successfully"

    @pytest.mark.asyncio
    async def test_execute_done_tool_default_message(self):
        """Test executing done tool with default message"""
        with pytest.raises(TaskComplete) as exc_info:
            await execute_done_tool({})

        assert exc_info.value.message == "Task completed"

    @pytest.mark.asyncio
    async def test_execute_done_tool_empty_message(self):
        """Test executing done tool with empty message"""
        with pytest.raises(TaskComplete) as exc_info:
            await execute_done_tool({"message": ""})

        assert exc_info.value.message == ""

    @pytest.mark.asyncio
    async def test_execute_done_tool_always_raises(self):
        """Test that execute_done_tool always raises TaskComplete"""
        with pytest.raises(TaskComplete):
            await execute_done_tool({"message": "Any message"})

    @pytest.mark.asyncio
    async def test_task_complete_exception_attributes(self):
        """Test TaskComplete exception has correct attributes"""
        test_message = "Test result message"

        with pytest.raises(TaskComplete) as exc_info:
            await execute_done_tool({"message": test_message})

        exception = exc_info.value
        assert exception.message == test_message
        assert test_message in str(exception)

    @pytest.mark.asyncio
    async def test_execute_done_tool_unicode_message(self):
        """Test executing done tool with unicode characters"""
        message = "任务完成 🎉"

        with pytest.raises(TaskComplete) as exc_info:
            await execute_done_tool({"message": message})

        assert exc_info.value.message == message

    @pytest.mark.asyncio
    async def test_execute_done_tool_long_message(self):
        """Test executing done tool with long message"""
        long_message = "x" * 1000

        with pytest.raises(TaskComplete) as exc_info:
            await execute_done_tool({"message": long_message})

        assert exc_info.value.message == long_message
