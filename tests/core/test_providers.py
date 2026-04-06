"""Test providers system"""

from types import SimpleNamespace

import pytest
from loom.providers import (
    AnthropicProvider,
    CompletionParams,
    LLMProvider,
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
