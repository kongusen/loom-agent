"""Unit tests for tools module."""

import pytest
from pydantic import BaseModel
from loom.tools import ToolRegistry, define_tool
from loom.types import ToolCall, ToolContext


class SearchInput(BaseModel):
    query: str

async def _search(inp, ctx):
    return f"found: {inp.query}"


class TestDefineTool:
    def test_creates_tool_definition(self):
        tool = define_tool("search", "Search", SearchInput, _search)
        assert tool.name == "search"

class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = define_tool("search", "Search", SearchInput, _search)
        reg.register(tool)
        assert reg.get("search") is tool

    def test_list(self):
        reg = ToolRegistry()
        reg.register(define_tool("a", "A", SearchInput, _search))
        reg.register(define_tool("b", "B", SearchInput, _search))
        assert len(reg.list()) == 2

    async def test_execute(self):
        reg = ToolRegistry()
        reg.register(define_tool("search", "Search", SearchInput, _search))
        result = await reg.execute(
            ToolCall(id="tc1", name="search", arguments='{"query":"test"}'),
            ToolContext(agent_id="a1"),
        )
        assert "found: test" in result

    async def test_execute_missing_tool(self):
        reg = ToolRegistry()
        result = await reg.execute(
            ToolCall(id="tc1", name="nope", arguments="{}"),
        )
        assert "error" in result
