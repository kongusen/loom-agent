"""Tests for Mode B streaming (typed StreamEvent pipeline)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

# ── StreamEvent type tests ────────────────────────────────────────────────────


class TestStreamEventTypes:
    def test_text_delta(self):
        from loom.types.stream import TextDelta

        ev = TextDelta(delta="hello")
        assert ev.type == "text_delta"
        assert ev.delta == "hello"

    def test_thinking_delta(self):
        from loom.types.stream import ThinkingDelta

        ev = ThinkingDelta(delta="reasoning...")
        assert ev.type == "thinking"
        assert ev.delta == "reasoning..."

    def test_tool_call_event(self):
        from loom.types.stream import ToolCallEvent

        ev = ToolCallEvent(id="c1", name="search", arguments={"q": "python"})
        assert ev.type == "tool_call"
        assert ev.name == "search"
        assert ev.arguments == {"q": "python"}

    def test_tool_result_event(self):
        from loom.types.stream import ToolResultEvent

        ev = ToolResultEvent(tool_call_id="c1", name="search", content="results", is_error=False)
        assert ev.type == "tool_result"
        assert ev.is_error is False

    def test_done_event(self):
        from loom.types.stream import DoneEvent

        ev = DoneEvent(output="final answer", iterations=3, status="success")
        assert ev.type == "done"
        assert ev.iterations == 3

    def test_error_event(self):
        from loom.types.stream import ErrorEvent

        ev = ErrorEvent(message="something went wrong")
        assert ev.type == "error"

    def test_exported_from_types(self):
        """Verify re-exports from loom.types."""
        from loom.types import (
            StreamEvent,
            TextDelta,
        )

        assert TextDelta is not None
        assert StreamEvent is not None


# ── Provider base stream_events fallback ─────────────────────────────────────


class TestProviderBaseStreamEvents:
    @pytest.mark.asyncio
    async def test_completion_request_delegates_to_legacy_provider_methods(self):
        from loom.providers.base import (
            CompletionParams,
            CompletionRequest,
            CompletionResponse,
            LLMProvider,
        )

        class MockProvider(LLMProvider):
            async def _complete(self, messages, params=None):
                return "unused"

            async def _complete_response(self, messages, params=None):
                assert messages == [{"role": "user", "content": "hi"}]
                assert params is not None
                assert params.model == "gpt-test"
                return CompletionResponse(content="ok")

            async def stream(self, messages, params=None):
                yield "ok"

        provider = MockProvider()
        request = CompletionRequest.create(
            [{"role": "user", "content": "hi"}],
            CompletionParams(model="gpt-test"),
            metadata={"run_id": "r1"},
        )

        response = await provider.complete_request(request)

        assert response.content == "ok"
        assert request.metadata["run_id"] == "r1"

    @pytest.mark.asyncio
    async def test_default_stream_events_yields_text_and_tool_calls(self):
        from loom.providers.base import (
            CompletionParams,
            CompletionResponse,
            LLMProvider,
        )
        from loom.types import ToolCall
        from loom.types.stream import TextDelta, ToolCallEvent

        class MockProvider(LLMProvider):
            async def _complete(self, messages, params=None):
                return "hello"

            async def _complete_response(self, messages, params=None):
                return CompletionResponse(
                    content="hello world",
                    tool_calls=[ToolCall(id="c1", name="search", arguments={"q": "test"})],
                )

            async def stream(self, messages, params=None):
                yield "hello world"

        provider = MockProvider()
        events = []
        async for ev in provider.stream_events([], CompletionParams()):
            events.append(ev)

        assert any(isinstance(ev, TextDelta) for ev in events)
        assert any(isinstance(ev, ToolCallEvent) for ev in events)
        text_ev = next(e for e in events if isinstance(e, TextDelta))
        assert text_ev.delta == "hello world"
        tool_ev = next(e for e in events if isinstance(e, ToolCallEvent))
        assert tool_ev.name == "search"

    @pytest.mark.asyncio
    async def test_default_stream_events_empty_content(self):
        from loom.providers.base import CompletionParams, CompletionResponse, LLMProvider

        class EmptyProvider(LLMProvider):
            async def _complete(self, messages, params=None):
                return ""

            async def _complete_response(self, messages, params=None):
                return CompletionResponse(content="", tool_calls=[])

            async def stream(self, messages, params=None):
                return
                yield

        provider = EmptyProvider()
        events = []
        async for ev in provider.stream_events([], CompletionParams()):
            events.append(ev)
        assert events == []


# ── AnthropicProvider stream_events ──────────────────────────────────────────


class TestAnthropicProviderStreamEvents:
    def _make_event(self, type_str: str, **kwargs):
        obj = MagicMock()
        obj.type = type_str
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj

    @pytest.mark.asyncio
    async def test_text_delta_events(self):
        from loom.providers.anthropic import AnthropicProvider
        from loom.types.stream import TextDelta

        async def _mock_stream():
            delta = MagicMock()
            delta.type = "text_delta"
            delta.text = "hello"
            ev = self._make_event("content_block_delta", delta=delta)
            yield ev

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_stream())
        provider = AnthropicProvider(api_key="test", client=mock_client)

        events = []
        async for ev in provider.stream_events([{"role": "user", "content": "hi"}]):
            events.append(ev)

        assert any(isinstance(ev, TextDelta) and ev.delta == "hello" for ev in events)

    @pytest.mark.asyncio
    async def test_tool_call_event_assembled_on_block_stop(self):
        from loom.providers.anthropic import AnthropicProvider
        from loom.types.stream import ToolCallEvent

        async def _mock_stream():
            # content_block_start: tool_use block
            block = MagicMock()
            block.type = "tool_use"
            block.id = "call_1"
            block.name = "search"
            yield self._make_event("content_block_start", content_block=block, index=0)

            # input_json_delta with partial JSON
            delta = MagicMock()
            delta.type = "input_json_delta"
            delta.partial_json = '{"q": "python"}'
            yield self._make_event("content_block_delta", delta=delta, index=0)

            # content_block_stop triggers ToolCallEvent
            yield self._make_event("content_block_stop", index=0)

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_stream())
        provider = AnthropicProvider(api_key="test", client=mock_client)

        events = []
        async for ev in provider.stream_events([{"role": "user", "content": "search"}]):
            events.append(ev)

        tc_events = [e for e in events if isinstance(e, ToolCallEvent)]
        assert len(tc_events) == 1
        assert tc_events[0].id == "call_1"
        assert tc_events[0].name == "search"
        assert tc_events[0].arguments == {"q": "python"}

    @pytest.mark.asyncio
    async def test_thinking_delta_events(self):
        from loom.providers.anthropic import AnthropicProvider
        from loom.types.stream import ThinkingDelta

        async def _mock_stream():
            delta = MagicMock()
            delta.type = "thinking_delta"
            delta.thinking = "let me think..."
            yield self._make_event("content_block_delta", delta=delta)

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_stream())
        provider = AnthropicProvider(api_key="test", client=mock_client)

        events = []
        async for ev in provider.stream_events([{"role": "user", "content": "think"}]):
            events.append(ev)

        thinking = [e for e in events if isinstance(e, ThinkingDelta)]
        assert len(thinking) == 1
        assert thinking[0].delta == "let me think..."

    @pytest.mark.asyncio
    async def test_malformed_tool_call_stream_is_recovered_and_nameless_call_ignored(self):
        from loom.providers.anthropic import AnthropicProvider
        from loom.types.stream import ToolCallEvent

        async def _mock_stream():
            block = MagicMock()
            block.type = "tool_use"
            block.id = "call_1"
            block.name = "search"
            yield self._make_event("content_block_start", content_block=block, index=0)

            delta = MagicMock()
            delta.type = "input_json_delta"
            delta.partial_json = "{bad json"
            yield self._make_event("content_block_delta", delta=delta, index=0)
            yield self._make_event("content_block_stop", index=0)

            nameless_block = MagicMock()
            nameless_block.type = "tool_use"
            nameless_block.id = "call_2"
            nameless_block.name = ""
            yield self._make_event("content_block_start", content_block=nameless_block, index=1)

            valid_delta = MagicMock()
            valid_delta.type = "input_json_delta"
            valid_delta.partial_json = '{"q": "python"}'
            yield self._make_event("content_block_delta", delta=valid_delta, index=1)
            yield self._make_event("content_block_stop", index=1)

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_stream())
        provider = AnthropicProvider(api_key="test", client=mock_client)

        events = []
        async for ev in provider.stream_events([{"role": "user", "content": "search"}]):
            events.append(ev)

        tc_events = [e for e in events if isinstance(e, ToolCallEvent)]
        assert tc_events == [ToolCallEvent(id="call_1", name="search", arguments={})]


# ── OpenAIProvider stream_events ─────────────────────────────────────────────


class TestOpenAIProviderStreamEvents:
    def _make_chunk(self, content=None, tool_calls=None, reasoning=None):
        chunk = MagicMock()
        delta = MagicMock()
        delta.content = content
        delta.tool_calls = tool_calls or []
        delta.reasoning_content = reasoning
        choice = MagicMock()
        choice.delta = delta
        chunk.choices = [choice]
        return chunk

    @pytest.mark.asyncio
    async def test_text_delta_events(self):
        from loom.providers.openai import OpenAIProvider
        from loom.types.stream import TextDelta

        async def _mock_stream():
            yield self._make_chunk(content="hello ")
            yield self._make_chunk(content="world")

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_stream())
        provider = OpenAIProvider(api_key="test", client=mock_client)

        events = []
        async for ev in provider.stream_events([{"role": "user", "content": "hi"}]):
            events.append(ev)

        text_events = [e for e in events if isinstance(e, TextDelta)]
        assert len(text_events) == 2
        assert "".join(e.delta for e in text_events) == "hello world"

    @pytest.mark.asyncio
    async def test_tool_call_assembled_after_stream(self):
        from loom.providers.openai import OpenAIProvider
        from loom.types.stream import ToolCallEvent

        def _tc_delta(idx, id=None, name=None, args=None):
            chunk = MagicMock()
            delta = MagicMock()
            delta.content = None
            delta.reasoning_content = None
            tc = MagicMock()
            tc.index = idx
            tc.id = id or ""
            fn = MagicMock()
            fn.name = name or ""
            fn.arguments = args or ""
            tc.function = fn
            delta.tool_calls = [tc]
            choice = MagicMock()
            choice.delta = delta
            chunk.choices = [choice]
            return chunk

        async def _mock_stream():
            # Chunk 1: tool call id + name start
            yield _tc_delta(0, id="call_1", name="search")
            # Chunk 2: args
            yield _tc_delta(0, args='{"q": "')
            # Chunk 3: rest of args
            yield _tc_delta(0, args='python"}')

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_stream())
        provider = OpenAIProvider(api_key="test", client=mock_client)

        events = []
        async for ev in provider.stream_events([{"role": "user", "content": "search"}]):
            events.append(ev)

        tc_events = [e for e in events if isinstance(e, ToolCallEvent)]
        assert len(tc_events) == 1
        assert tc_events[0].id == "call_1"
        assert tc_events[0].name == "search"
        assert tc_events[0].arguments == {"q": "python"}

    @pytest.mark.asyncio
    async def test_malformed_tool_call_stream_is_recovered_and_nameless_call_ignored(self):
        from loom.providers.openai import OpenAIProvider
        from loom.types.stream import ToolCallEvent

        def _tc_delta(idx, id=None, name=None, args=None):
            chunk = MagicMock()
            delta = MagicMock()
            delta.content = None
            delta.reasoning_content = None
            tc = MagicMock()
            tc.index = idx
            tc.id = id or ""
            fn = MagicMock()
            fn.name = name or ""
            fn.arguments = args or ""
            tc.function = fn
            delta.tool_calls = [tc]
            choice = MagicMock()
            choice.delta = delta
            chunk.choices = [choice]
            return chunk

        async def _mock_stream():
            yield _tc_delta(0, id="call_1", name="search", args="{bad json")
            yield _tc_delta(1, id="call_2", name="", args='{"q": "python"}')

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_stream())
        provider = OpenAIProvider(api_key="test", client=mock_client)

        events = []
        async for ev in provider.stream_events([{"role": "user", "content": "search"}]):
            events.append(ev)

        tc_events = [e for e in events if isinstance(e, ToolCallEvent)]
        assert tc_events == [ToolCallEvent(id="call_1", name="search", arguments={})]

    @pytest.mark.asyncio
    async def test_thinking_delta_when_expose_reasoning(self):
        from loom.providers.base import CompletionParams
        from loom.providers.deepseek import DeepSeekProvider
        from loom.providers.openai import OpenAIProvider
        from loom.types.stream import TextDelta, ThinkingDelta

        async def _mock_stream():
            yield self._make_chunk(reasoning="let me think")
            yield self._make_chunk(content="final answer")

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_stream())
        provider = DeepSeekProvider.__new__(DeepSeekProvider)
        OpenAIProvider.__init__(provider, api_key="test", client=mock_client)

        params = CompletionParams(extensions={"expose_reasoning": True})
        events = []
        async for ev in provider.stream_events([{"role": "user", "content": "think"}], params):
            events.append(ev)

        thinking = [e for e in events if isinstance(e, ThinkingDelta)]
        text = [e for e in events if isinstance(e, TextDelta)]
        assert len(thinking) == 1
        assert thinking[0].delta == "let me think"
        assert len(text) == 1
        assert text[0].delta == "final answer"

    @pytest.mark.asyncio
    async def test_reasoning_not_emitted_without_flag(self):
        from loom.providers.openai import OpenAIProvider
        from loom.types.stream import ThinkingDelta

        async def _mock_stream():
            yield self._make_chunk(reasoning="hidden thinking", content="visible text")

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_stream())
        provider = OpenAIProvider(api_key="test", client=mock_client)

        events = []
        async for ev in provider.stream_events([{"role": "user", "content": "hi"}]):
            events.append(ev)

        # No ThinkingDelta — reasoning_ext_key is None on base OpenAIProvider
        assert not any(isinstance(e, ThinkingDelta) for e in events)


class TestProviderReasoningExtKeys:
    def test_qwen_reasoning_key(self):
        from loom.providers.qwen import QwenProvider

        assert QwenProvider._reasoning_ext_key == "enable_thinking"

    def test_deepseek_reasoning_key(self):
        from loom.providers.deepseek import DeepSeekProvider

        assert DeepSeekProvider._reasoning_ext_key == "expose_reasoning"

    def test_minimax_reasoning_key(self):
        from loom.providers.minimax import MiniMaxProvider

        assert MiniMaxProvider._reasoning_ext_key == "expose_reasoning"

    def test_openai_no_reasoning_key(self):
        from loom.providers.openai import OpenAIProvider

        assert OpenAIProvider._reasoning_ext_key is None

    def test_ollama_inherits_no_reasoning_key(self):
        from loom.providers.ollama import OllamaProvider

        assert OllamaProvider._reasoning_ext_key is None


# ── GeminiProvider stream_events ─────────────────────────────────────────────


class TestGeminiProviderStreamEvents:
    @pytest.mark.asyncio
    async def test_text_delta_events(self):
        from loom.providers.gemini import GeminiProvider
        from loom.types.stream import TextDelta

        chunk1 = MagicMock()
        chunk1.text = "hello "
        chunk1.candidates = []
        chunk2 = MagicMock()
        chunk2.text = "world"
        chunk2.candidates = []

        async def _mock_stream():
            yield chunk1
            yield chunk2

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=_mock_stream())
        mock_genai = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        provider = GeminiProvider(api_key="test", client=mock_genai)

        events = []
        async for ev in provider.stream_events([{"role": "user", "content": "hi"}]):
            events.append(ev)

        text_events = [e for e in events if isinstance(e, TextDelta)]
        assert len(text_events) == 2
        assert "".join(e.delta for e in text_events) == "hello world"


# ── AgentEngine.execute_streaming ────────────────────────────────────────────


class TestEngineExecuteStreaming:
    def _make_engine(self, stream_events_side_effect=None):
        from loom.runtime.engine import AgentEngine, EngineConfig
        from loom.types.stream import TextDelta

        provider = MagicMock()

        async def _default_stream_events(messages, params=None):
            yield TextDelta(delta="final answer")

        provider.stream_events = (
            _default_stream_events
            if stream_events_side_effect is None
            else stream_events_side_effect
        )
        provider.complete_response = AsyncMock()
        provider.complete_streaming = AsyncMock()

        return AgentEngine(provider=provider, config=EngineConfig(enable_memory=False))

    @pytest.mark.asyncio
    async def test_yields_text_delta_and_done(self):
        from loom.types.stream import DoneEvent, TextDelta

        engine = self._make_engine()
        events = []
        async for ev in engine.execute_streaming("hello"):
            events.append(ev)

        assert any(isinstance(ev, TextDelta) for ev in events)
        done_events = [e for e in events if isinstance(e, DoneEvent)]
        assert len(done_events) == 1
        assert done_events[0].output == "final answer"

    @pytest.mark.asyncio
    async def test_tool_call_triggers_tool_result(self):
        from loom.runtime.engine import AgentEngine, EngineConfig
        from loom.tools.schema import Tool, ToolDefinition
        from loom.types.stream import TextDelta, ToolCallEvent, ToolResultEvent

        call_count = [0]

        async def _stream(messages, params=None):
            if call_count[0] == 0:
                # First call: emit a tool call
                yield ToolCallEvent(id="c1", name="greet", arguments={"name": "world"})
            else:
                # Second call: emit final text
                yield TextDelta(delta="done")
            call_count[0] += 1

        provider = MagicMock()
        provider.stream_events = _stream
        provider.complete_response = AsyncMock()
        provider.complete_streaming = AsyncMock()

        async def greet_handler(name: str = "") -> str:
            return f"Hello, {name}!"

        greet_tool = Tool(
            definition=ToolDefinition(name="greet", description="greet", parameters=[]),
            handler=greet_handler,
        )

        engine = AgentEngine(
            provider=provider,
            config=EngineConfig(enable_memory=False),
            tools=[greet_tool],
        )

        events = []
        async for ev in engine.execute_streaming("greet world"):
            events.append(ev)

        tool_result_events = [e for e in events if isinstance(e, ToolResultEvent)]
        assert len(tool_result_events) >= 1
        assert tool_result_events[0].name == "greet"

    @pytest.mark.asyncio
    async def test_error_event_on_provider_exception(self):
        from loom.runtime.engine import AgentEngine, EngineConfig
        from loom.types.stream import ErrorEvent

        async def _failing_stream(messages, params=None):
            raise RuntimeError("provider exploded")
            yield  # make it a generator

        provider = MagicMock()
        provider.stream_events = _failing_stream
        provider.complete_response = AsyncMock()

        engine = AgentEngine(provider=provider, config=EngineConfig(enable_memory=False))
        events = []
        async for ev in engine.execute_streaming("test"):
            events.append(ev)

        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        assert len(error_events) >= 1
        assert "provider exploded" in error_events[0].message


# ── Agent.run_streaming ───────────────────────────────────────────────────────


class TestAgentRunStreaming:
    @pytest.mark.asyncio
    async def test_run_streaming_yields_events(self):
        from loom.agent import Agent
        from loom.config import AgentConfig, ModelRef
        from loom.types.stream import DoneEvent, TextDelta

        async def _stream_events(messages, params=None):
            from loom.types.stream import TextDelta

            yield TextDelta(delta="streamed answer")

        mock_provider = MagicMock()
        mock_provider.stream_events = _stream_events
        mock_provider.complete_response = AsyncMock()
        mock_provider.complete_streaming = AsyncMock()
        mock_provider._retry = MagicMock()
        mock_provider._circuit = MagicMock()
        mock_provider._circuit.is_open.return_value = False

        agent = Agent(
            config=AgentConfig(
                model=ModelRef(provider="anthropic", name="claude-3-5-sonnet-20241022"),
            )
        )
        agent._provider = mock_provider
        agent._provider_resolved = True
        agent._provider_validated = True

        events = []
        async for ev in agent.run_streaming("hello"):
            events.append(ev)

        assert any(isinstance(ev, TextDelta) for ev in events)
        done_events = [e for e in events if isinstance(e, DoneEvent)]
        assert len(done_events) == 1
        assert done_events[0].output == "streamed answer"

    @pytest.mark.asyncio
    async def test_run_streaming_provider_unavailable(self):
        from loom.agent import Agent
        from loom.config import AgentConfig, ModelRef
        from loom.types.stream import ErrorEvent

        agent = Agent(
            config=AgentConfig(
                model=ModelRef(provider="anthropic", name="claude-3-5-sonnet-20241022"),
            )
        )
        # No provider set, no API key → provider will be None
        agent._provider = None
        agent._provider_resolved = True

        events = []
        async for ev in agent.run_streaming("test"):
            events.append(ev)

        assert any(isinstance(ev, ErrorEvent) for ev in events)
