"""Test providers system"""

from types import SimpleNamespace

import pytest

from loom.providers import (
    AnthropicProvider,
    CompletionParams,
    CompletionResponse,
    GeminiProvider,
    OpenAIProvider,
)


class TestProviders:
    """Test providers"""

    def test_completion_params(self):
        """Test CompletionParams"""
        params = CompletionParams(temperature=0.7, max_tokens=100)
        assert params.temperature == 0.7
        assert params.max_tokens == 100

    @pytest.mark.asyncio
    async def test_openai_provider_complete(self):
        """Test OpenAI provider complete with injected client."""

        class FakeCompletions:
            async def create(self, **kwargs):
                assert kwargs["model"] == "gpt-test"
                assert kwargs["messages"][-1]["content"] == "hello"
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content="hi there")
                        )
                    ]
                )

        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=FakeCompletions())
        )
        provider = OpenAIProvider(api_key="test", client=fake_client)
        result = await provider.complete(
            [{"role": "user", "content": "hello"}],
            CompletionParams(model="gpt-test", max_tokens=16, temperature=0.2),
        )
        assert result == "hi there"

    @pytest.mark.asyncio
    async def test_openai_provider_stream(self):
        """Test OpenAI provider stream with injected client."""

        class FakeStream:
            def __init__(self, chunks):
                self._chunks = iter(chunks)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self._chunks)
                except StopIteration as exc:
                    raise StopAsyncIteration from exc

        class FakeCompletions:
            async def create(self, **kwargs):
                assert kwargs["stream"] is True
                return FakeStream(
                    [
                        SimpleNamespace(
                            choices=[
                                SimpleNamespace(delta=SimpleNamespace(content="hi"))
                            ]
                        ),
                        SimpleNamespace(
                            choices=[
                                SimpleNamespace(delta=SimpleNamespace(content=" there"))
                            ]
                        ),
                    ]
                )

        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=FakeCompletions())
        )
        provider = OpenAIProvider(api_key="test", client=fake_client)
        chunks = []
        async for chunk in provider.stream(
            [{"role": "user", "content": "hello"}],
            CompletionParams(model="gpt-test"),
        ):
            chunks.append(chunk)

        assert chunks == ["hi", " there"]

    @pytest.mark.asyncio
    async def test_openai_provider_complete_response_supports_tool_calls(self):
        """Test OpenAI provider structured tool-call response."""

        class FakeCompletions:
            async def create(self, **kwargs):
                assert kwargs["tools"] == [
                    {
                        "type": "function",
                        "function": {
                            "name": "search_docs",
                            "description": "Search docs",
                            "parameters": {
                                "type": "object",
                                "properties": {"query": {"type": "string"}},
                                "required": ["query"],
                            },
                        },
                    }
                ]
                assert kwargs["tool_choice"] == "auto"
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content="",
                                tool_calls=[
                                    SimpleNamespace(
                                        id="call_1",
                                        function=SimpleNamespace(
                                            name="search_docs",
                                            arguments='{"query":"loom"}',
                                        ),
                                    )
                                ],
                            )
                        )
                    ]
                )

        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
        provider = OpenAIProvider(api_key="test", client=fake_client)
        result = await provider.complete_response(
            [{"role": "user", "content": "find loom docs"}],
            CompletionParams(
                model="gpt-test",
                tools=[
                    {
                        "name": "search_docs",
                        "description": "Search docs",
                        "parameters": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }
                ],
            ),
        )

        assert isinstance(result, CompletionResponse)
        assert result.tool_calls[0].name == "search_docs"
        assert result.tool_calls[0].arguments == {"query": "loom"}

    def test_openai_provider_missing_dependency(self, monkeypatch):
        """Test OpenAI provider raises a helpful error without SDK."""
        provider = OpenAIProvider(api_key="test")

        import builtins

        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("forced missing dependency")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(ImportError) as exc:
            _ = provider.client

        assert "openai package is required" in str(exc.value)

    @pytest.mark.asyncio
    async def test_anthropic_provider_complete(self):
        """Test Anthropic provider complete with injected client."""

        class FakeMessages:
            async def create(self, **kwargs):
                assert kwargs["model"] == "claude-test"
                assert kwargs["system"] == "system prompt"
                assert kwargs["messages"] == [{"role": "user", "content": "hello"}]
                return SimpleNamespace(
                    content=[
                        SimpleNamespace(type="text", text="anthropic response")
                    ]
                )

        fake_client = SimpleNamespace(messages=FakeMessages())
        provider = AnthropicProvider(api_key="test", client=fake_client)
        result = await provider.complete(
            [
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "hello"},
            ],
            CompletionParams(model="claude-test", max_tokens=64, temperature=0.1),
        )
        assert result == "anthropic response"

    @pytest.mark.asyncio
    async def test_anthropic_provider_stream(self):
        """Test Anthropic provider stream with injected client."""

        class FakeStream:
            def __init__(self, chunks):
                self._chunks = iter(chunks)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self._chunks)
                except StopIteration as exc:
                    raise StopAsyncIteration from exc

        class FakeMessages:
            async def create(self, **kwargs):
                assert kwargs["stream"] is True
                return FakeStream(
                    [
                        SimpleNamespace(
                            type="content_block_delta",
                            delta=SimpleNamespace(text="hello"),
                        ),
                        SimpleNamespace(
                            type="content_block_delta",
                            delta=SimpleNamespace(text=" world"),
                        ),
                    ]
                )

        fake_client = SimpleNamespace(messages=FakeMessages())
        provider = AnthropicProvider(api_key="test", client=fake_client)
        chunks = []
        async for chunk in provider.stream(
            [{"role": "user", "content": "hello"}],
            CompletionParams(model="claude-test"),
        ):
            chunks.append(chunk)

        assert chunks == ["hello", " world"]

    @pytest.mark.asyncio
    async def test_anthropic_provider_complete_response_supports_tool_calls(self):
        """Test Anthropic provider structured tool-call response."""

        class FakeMessages:
            async def create(self, **kwargs):
                assert kwargs["tools"] == [
                    {
                        "name": "search_docs",
                        "description": "Search docs",
                        "input_schema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }
                ]
                assert kwargs["tool_choice"] == {"type": "auto"}
                return SimpleNamespace(
                    content=[
                        SimpleNamespace(
                            type="tool_use",
                            id="toolu_1",
                            name="search_docs",
                            input={"query": "loom"},
                        )
                    ]
                )

        fake_client = SimpleNamespace(messages=FakeMessages())
        provider = AnthropicProvider(api_key="test", client=fake_client)
        result = await provider.complete_response(
            [{"role": "user", "content": "find loom docs"}],
            CompletionParams(
                model="claude-test",
                tools=[
                    {
                        "name": "search_docs",
                        "description": "Search docs",
                        "parameters": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }
                ],
            ),
        )

        assert isinstance(result, CompletionResponse)
        assert result.tool_calls[0].id == "toolu_1"
        assert result.tool_calls[0].arguments == {"query": "loom"}

    def test_anthropic_provider_missing_dependency(self, monkeypatch):
        """Test Anthropic provider raises a helpful error without SDK."""
        provider = AnthropicProvider(api_key="test")

        import builtins

        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("forced missing dependency")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(ImportError) as exc:
            _ = provider.client

        assert "anthropic package is required" in str(exc.value)

    @pytest.mark.asyncio
    async def test_gemini_provider_complete_response_supports_tool_calls(self):
        """Test Gemini provider structured tool-call response."""

        class FakePart:
            def __init__(self, *, text=None, function_call=None):
                self.text = text
                self.function_call = function_call

        class FakeFunctionCall:
            def __init__(self, name, args):
                self.name = name
                self.args = args

        class FakeModel:
            async def generate_content_async(self, **kwargs):
                assert kwargs["tools"] == [
                    {
                        "function_declarations": [
                            {
                                "name": "search_docs",
                                "description": "Search docs",
                                "parameters": {
                                    "type": "object",
                                    "properties": {"query": {"type": "string"}},
                                    "required": ["query"],
                                },
                            }
                        ]
                    }
                ]
                assert kwargs["tool_config"] == {"function_calling_config": {"mode": "AUTO"}}
                assert kwargs["contents"][1]["role"] == "model"
                assert kwargs["contents"][1]["parts"][0]["function_call"]["name"] == "search_docs"
                assert kwargs["contents"][2]["role"] == "user"
                assert kwargs["contents"][2]["parts"][0]["function_response"]["name"] == "search_docs"
                return SimpleNamespace(
                    candidates=[
                        SimpleNamespace(
                            content=SimpleNamespace(
                                parts=[
                                    FakePart(
                                        function_call=FakeFunctionCall(
                                            name="search_docs",
                                            args={"query": "loom"},
                                        )
                                    )
                                ]
                            )
                        )
                    ]
                )

        fake_client = SimpleNamespace(GenerativeModel=lambda model: FakeModel())
        provider = GeminiProvider(api_key="test", client=fake_client)
        result = await provider.complete_response(
            [
                {"role": "user", "content": "find loom docs"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "call_1", "name": "search_docs", "arguments": {"query": "loom"}}
                    ],
                },
                {
                    "role": "tool",
                    "name": "search_docs",
                    "tool_call_id": "call_1",
                    "content": "found docs",
                },
            ],
            CompletionParams(
                model="gemini-test",
                tools=[
                    {
                        "name": "search_docs",
                        "description": "Search docs",
                        "parameters": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }
                ],
            ),
        )

        assert isinstance(result, CompletionResponse)
        assert result.tool_calls[0].name == "search_docs"
        assert result.tool_calls[0].arguments == {"query": "loom"}
