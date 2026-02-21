"""Unit tests for agent module (core, strategy, interceptor)."""

import pytest
from unittest.mock import AsyncMock
from loom.agent import Agent, InterceptorChain, InterceptorContext, ToolUseStrategy, ReactStrategy, LoopContext
from loom.types import (
    UserMessage, DoneEvent, TextDeltaEvent, ErrorEvent,
    CompletionParams, CompletionResult, TokenUsage, ToolCall,
)
from loom.config import AgentConfig
from loom.tools import ToolRegistry
from tests.conftest import MockLLMProvider


class TestInterceptorChain:
    async def test_empty_chain(self):
        chain = InterceptorChain()
        ctx = InterceptorContext(messages=[UserMessage(content="hi")])
        await chain.run(ctx)
        assert len(ctx.messages) == 1

    async def test_interceptor_modifies_messages(self):
        chain = InterceptorChain()

        class Upper:
            name = "upper"
            async def intercept(self, ctx, next):
                ctx.messages = [type(m)(content=m.content.upper()) for m in ctx.messages]
                await next()

        chain.use(Upper())
        ctx = InterceptorContext(messages=[UserMessage(content="hello")])
        await chain.run(ctx)
        assert ctx.messages[0].content == "HELLO"

    async def test_chain_order(self):
        chain = InterceptorChain()
        order = []

        class A:
            name = "a"
            async def intercept(self, ctx, next):
                order.append("a")
                await next()

        class B:
            name = "b"
            async def intercept(self, ctx, next):
                order.append("b")
                await next()

        chain.use(A())
        chain.use(B())
        await chain.run(InterceptorContext(messages=[]))
        assert order == ["a", "b"]


class TestAgent:
    async def test_run_returns_done_event(self):
        llm = MockLLMProvider(["Hello world"])
        agent = Agent(provider=llm, config=AgentConfig(max_steps=1, stream=False))
        result = await agent.run("hi")
        assert isinstance(result, DoneEvent)
        assert "Hello world" in result.content

    async def test_stream_yields_events(self):
        llm = MockLLMProvider(["streamed"])
        agent = Agent(provider=llm, config=AgentConfig(max_steps=1, stream=False))
        events = [e async for e in agent.stream("hi")]
        assert any(isinstance(e, DoneEvent) for e in events)

    async def test_on_registers_handler(self):
        llm = MockLLMProvider(["ok"])
        agent = Agent(provider=llm)
        received = []
        async def handler(e): received.append(e)
        agent.on("done", handler)
        await agent.run("hi")
        assert len(received) >= 1


class TestToolUseStrategy:
    async def test_no_tools_completes_immediately(self):
        llm = MockLLMProvider(["done"])
        ctx = LoopContext(
            messages=[UserMessage(content="hi")], provider=llm,
            tools=[], tool_registry=ToolRegistry(),
            max_steps=3, streaming=False, temperature=0.7, max_tokens=1024,
            agent_id="t1", interceptors=InterceptorChain(), events=None, signal=None,
            tool_config=None,
        )
        strategy = ToolUseStrategy()
        events = [e async for e in strategy.execute(ctx)]
        assert any(isinstance(e, DoneEvent) for e in events)

    async def test_max_steps_error(self):
        """Provider always returns tool calls → hits max steps."""
        class ToolCallProvider:
            async def complete(self, params):
                return CompletionResult(
                    content="", usage=TokenUsage(total_tokens=5),
                    tool_calls=[ToolCall(id="t1", name="nope", arguments="{}")]
                )
        reg = ToolRegistry()
        ctx = LoopContext(
            messages=[UserMessage(content="hi")], provider=ToolCallProvider(),
            tools=[], tool_registry=reg,
            max_steps=2, streaming=False, temperature=0.7, max_tokens=1024,
            agent_id="t1", interceptors=InterceptorChain(), events=None, signal=None,
            tool_config=None,
        )
        events = [e async for e in ToolUseStrategy().execute(ctx)]
        assert any(isinstance(e, ErrorEvent) and "Max steps" in e.error for e in events)
