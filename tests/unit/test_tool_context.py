"""Tests for ToolContext extension mechanism."""

import json
import pytest

from loom.agent import Agent, LoopContext
from loom.config import AgentConfig
from loom.tools import ToolRegistry
from loom.types import (
    DoneEvent,
    ToolContext,
    ToolDefinition,
)
from tests.conftest import MockLLMProvider


# ── ToolContext __getattr__ ──


class TestToolContextExtension:
    def test_metadata_access_via_getattr(self):
        ctx = ToolContext(agent_id="a", metadata={"documentContext": [1, 2, 3]})
        assert ctx.documentContext == [1, 2, 3]

    def test_getattr_raises_for_missing_key(self):
        ctx = ToolContext(agent_id="a")
        with pytest.raises(AttributeError, match="no attribute 'foo'"):
            _ = ctx.foo

    def test_normal_fields_still_work(self):
        ctx = ToolContext(agent_id="x", session_id="s1", tenant_id="t1")
        assert ctx.agent_id == "x"
        assert ctx.session_id == "s1"
        assert ctx.tenant_id == "t1"

    def test_metadata_does_not_shadow_real_fields(self):
        ctx = ToolContext(agent_id="real", metadata={"agent_id": "fake"})
        assert ctx.agent_id == "real"


# ── AgentConfig tool_context ──


class TestAgentConfigToolContext:
    def test_default_empty(self):
        c = AgentConfig()
        assert c.tool_context == {}

    def test_custom_tool_context(self):
        c = AgentConfig(tool_context={"documentContext": ["block1"]})
        assert c.tool_context["documentContext"] == ["block1"]


# ── LoopContext passthrough ──


class TestLoopContextToolContext:
    def test_tool_context_stored(self):
        ctx = LoopContext(tool_context={"selectedText": "hello"})
        assert ctx.tool_context == {"selectedText": "hello"}

    def test_tool_context_defaults_none(self):
        ctx = LoopContext()
        assert ctx.tool_context is None


# ── End-to-end: _exec_tool merges tool_context into ToolContext.metadata ──


class TestExecToolMergesContext:
    @pytest.mark.asyncio
    async def test_tool_receives_custom_context(self):
        """Verify tool_context flows from LoopContext → ToolContext.metadata."""
        captured_ctx = {}

        class _Schema:
            def parse(self, raw):
                return raw
            def to_json_schema(self):
                return {"type": "object"}

        async def my_tool(inp, ctx: ToolContext):
            captured_ctx["documentContext"] = ctx.metadata.get("documentContext")
            captured_ctx["attr_access"] = ctx.documentContext  # via __getattr__
            return "ok"

        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="my_tool", description="test", parameters=_Schema(), execute=my_tool,
        ))

        from loom.agent.strategy import _exec_tool
        from loom.types import ToolCall

        tc = ToolCall(id="c1", name="my_tool", arguments="{}")
        ctx = LoopContext(
            tool_registry=registry,
            tool_config=None,
            tool_context={"documentContext": ["block-A", "block-B"]},
            agent_id="test",
        )
        result = await _exec_tool(tc, ctx)
        assert result == "ok"
        assert captured_ctx["documentContext"] == ["block-A", "block-B"]
        assert captured_ctx["attr_access"] == ["block-A", "block-B"]
