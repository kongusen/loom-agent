"""Test providers system"""

from types import SimpleNamespace

import pytest

from loom.providers import (
    AnthropicProvider,
    CompletionParams,
    CompletionRequest,
    CompletionResponse,
    GeminiProvider,
    LLMProvider,
    OpenAIProvider,
    ProviderToolParameter,
    ProviderToolSpec,
)
from loom.types import ToolCall
from loom.utils import ProviderUnavailableError, RateLimitError


class TestProviders:
    """Test providers"""

    def test_completion_params(self):
        """Test CompletionParams"""
        params = CompletionParams(temperature=0.7, max_tokens=100)
        assert params.temperature == 0.7
        assert params.max_tokens == 100

    def test_completion_params_exposes_typed_tool_specs(self):
        tool = ProviderToolSpec(
            name="search_docs",
            description="Search docs",
            parameters=(
                ProviderToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True,
                ),
            ),
        )
        params = CompletionParams(tools=[tool])

        assert params.tool_specs() == [tool]
        assert params.tool_dicts() == [
            {
                "name": "search_docs",
                "description": "Search docs",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        }
                    },
                    "required": ["query"],
                },
            }
        ]

        round_trip = CompletionParams(tools=params.tool_dicts())
        assert round_trip.tool_specs() == [tool]

    @pytest.mark.asyncio
    async def test_request_native_provider_can_skip_legacy_methods(self):
        from loom.types.stream import TextDelta

        class NativeProvider(LLMProvider):
            async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
                assert request.messages[-1]["content"] == "hello"
                assert request.params.model == "native-test"
                return CompletionResponse(content="native response")

        provider = NativeProvider()
        request = CompletionRequest.create(
            [{"role": "user", "content": "hello"}],
            CompletionParams(model="native-test"),
        )

        response = await provider.complete_request(request)
        compat_response = await provider.complete_response(
            [{"role": "user", "content": "hello"}],
            CompletionParams(model="native-test"),
        )
        text = await provider.complete(
            [{"role": "user", "content": "hello"}],
            CompletionParams(model="native-test"),
        )
        events = [event async for event in provider.stream_request_events(request)]

        assert response.content == "native response"
        assert compat_response.content == "native response"
        assert text == "native response"
        assert any(isinstance(event, TextDelta) and event.delta == "native response" for event in events)

    @pytest.mark.asyncio
    async def test_complete_request_uses_retry_and_circuit_breaker(self):
        class NativeProvider(LLMProvider):
            def __init__(self) -> None:
                super().__init__()
                self.calls = 0

            async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("transient failure")
                return CompletionResponse(content="recovered")

        provider = NativeProvider()
        provider._retry.max_retries = 2
        provider._retry.base_delay = 0

        response = await provider.complete_request(
            CompletionRequest.create([{"role": "user", "content": "hello"}])
        )

        assert response.content == "recovered"
        assert provider.calls == 2

    @pytest.mark.asyncio
    async def test_complete_request_streaming_falls_back_to_request_native_tool_calls(self):
        class NativeProvider(LLMProvider):
            async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
                return CompletionResponse(
                    content="fallback text",
                    tool_calls=[
                        ToolCall(
                            id="call_1",
                            name="search_docs",
                            arguments={"query": "loom"},
                        )
                    ],
                )

        tokens: list[str] = []
        provider = NativeProvider()
        response = await provider.complete_request_streaming(
            CompletionRequest.create([{"role": "user", "content": "hello"}]),
            tokens.append,
        )

        assert tokens == ["fallback text"]
        assert response.tool_calls == [
            ToolCall(id="call_1", name="search_docs", arguments={"query": "loom"})
        ]

    @pytest.mark.asyncio
    async def test_complete_request_maps_429_to_rate_limit_error(self):
        class NativeProvider(LLMProvider):
            async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
                raise RuntimeError("429 rate limit exceeded")

        provider = NativeProvider()
        provider._retry.max_retries = 1

        with pytest.raises(RateLimitError):
            await provider.complete_request(
                CompletionRequest.create([{"role": "user", "content": "hello"}])
            )

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

    def test_concrete_providers_use_request_native_contract(self):
        fake_client = SimpleNamespace()

        assert OpenAIProvider(api_key="test", client=fake_client)._uses_request_native_completion()
        assert AnthropicProvider(api_key="test", client=fake_client)._uses_request_native_completion()
        assert GeminiProvider(api_key="test", client=fake_client)._uses_request_native_completion()

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

    def test_openai_provider_accepts_typed_tool_specs(self):
        provider = OpenAIProvider(api_key="test", client=SimpleNamespace())
        payload = provider._build_request(
            [{"role": "user", "content": "find loom docs"}],
            CompletionParams(
                model="gpt-test",
                tools=[
                    ProviderToolSpec(
                        name="search_docs",
                        description="Search docs",
                        parameters=(
                            ProviderToolParameter(name="query", type="string", required=True),
                        ),
                    )
                ],
            ),
        )

        assert payload["tools"] == [
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

    def test_openai_provider_ignores_nameless_tool_calls_and_recovers_bad_arguments(self):
        provider = OpenAIProvider(api_key="test", client=SimpleNamespace())

        tool_calls = provider._extract_tool_calls(
            [
                SimpleNamespace(
                    id="call_1",
                    function=SimpleNamespace(name="search_docs", arguments="{bad json"),
                ),
                SimpleNamespace(
                    id="call_2",
                    function=SimpleNamespace(name="", arguments='{"query":"loom"}'),
                ),
            ]
        )

        assert tool_calls == [ToolCall(id="call_1", name="search_docs", arguments={})]

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

    def test_anthropic_provider_accepts_typed_tool_specs(self):
        provider = AnthropicProvider(api_key="test", client=SimpleNamespace())
        payload = provider._build_request(
            [{"role": "user", "content": "find loom docs"}],
            CompletionParams(
                model="claude-test",
                tools=[
                    ProviderToolSpec(
                        name="search_docs",
                        description="Search docs",
                        parameters=(
                            ProviderToolParameter(name="query", type="string", required=True),
                        ),
                    )
                ],
            ),
        )

        assert payload["tools"] == [
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

    def test_anthropic_provider_ignores_nameless_tool_calls_and_recovers_bad_input(self):
        provider = AnthropicProvider(api_key="test", client=SimpleNamespace())

        tool_calls = provider._extract_tool_calls(
            [
                SimpleNamespace(
                    type="tool_use",
                    id="toolu_1",
                    name="search_docs",
                    input="not a dict",
                ),
                SimpleNamespace(
                    type="tool_use",
                    id="toolu_2",
                    name="",
                    input={"query": "loom"},
                ),
            ]
        )

        assert tool_calls == [ToolCall(id="toolu_1", name="search_docs", arguments={})]

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

    def test_gemini_provider_accepts_typed_tool_specs(self):
        provider = GeminiProvider(api_key="test", client=SimpleNamespace())
        params = CompletionParams(
            model="gemini-test",
            tools=[
                ProviderToolSpec(
                    name="search_docs",
                    description="Search docs",
                    parameters=(
                        ProviderToolParameter(name="query", type="string", required=True),
                    ),
                )
            ],
        )

        assert provider._build_tools(params.tool_dicts()) == [
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

    def test_gemini_provider_ignores_nameless_tool_calls_and_recovers_bad_args(self):
        class FakeFunctionCall:
            def __init__(self, name, args):
                self.name = name
                self.args = args

        class FakePart:
            def __init__(self, function_call):
                self.function_call = function_call

        response = SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(
                        parts=[
                            FakePart(FakeFunctionCall("search_docs", "not a dict")),
                            FakePart(FakeFunctionCall("", {"query": "loom"})),
                        ]
                    )
                )
            ]
        )
        provider = GeminiProvider(api_key="test", client=SimpleNamespace())

        assert provider._extract_tool_calls(response) == [
            ToolCall(id="search_docs_1", name="search_docs", arguments={})
        ]

    @pytest.mark.asyncio
    async def test_provider_base_maps_429_to_rate_limit_error(self):
        class FlakyProvider(LLMProvider):
            async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
                raise RuntimeError("429 rate limit exceeded")

            def stream(self, messages: list, params: CompletionParams | None = None):
                async def _gen():
                    yield ""
                return _gen()

        provider = FlakyProvider()
        with pytest.raises(RateLimitError):
            await provider.complete([{"role": "user", "content": "hello"}])

    @pytest.mark.asyncio
    async def test_provider_base_uses_provider_unavailable_error_when_circuit_open(self):
        class DownProvider(LLMProvider):
            async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
                raise RuntimeError("network down")

            def stream(self, messages: list, params: CompletionParams | None = None):
                async def _gen():
                    yield ""
                return _gen()

        provider = DownProvider()
        provider._retry.max_retries = 1
        provider._retry.circuit_open_after = 1

        with pytest.raises(ProviderUnavailableError):
            await provider.complete([{"role": "user", "content": "hello"}])
        with pytest.raises(ProviderUnavailableError):
            await provider.complete([{"role": "user", "content": "hello again"}])

    def test_openai_provider_client_pool_reused_across_instances(self):
        pooled_client = object()
        OpenAIProvider.clear_client_pool()
        OpenAIProvider._shared_clients[("shared-key", None, None)] = pooled_client
        try:
            provider = OpenAIProvider(api_key="shared-key")
            assert provider.client is pooled_client
        finally:
            OpenAIProvider.clear_client_pool()

    def test_anthropic_provider_client_pool_reused_across_instances(self):
        pooled_client = object()
        AnthropicProvider.clear_client_pool()
        AnthropicProvider._shared_clients[("shared-key", None)] = pooled_client
        try:
            provider = AnthropicProvider(api_key="shared-key")
            assert provider.client is pooled_client
        finally:
            AnthropicProvider.clear_client_pool()
