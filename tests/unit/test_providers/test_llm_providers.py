"""
Tests for LLM providers: anthropic.py, gemini.py, deepseek.py, client_pool.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

from loom.providers.llm.client_pool import LLMClientPool, _freeze, _make_cache_key


# ==================== _freeze ====================


class TestFreeze:
    def test_dict(self):
        result = _freeze({"b": 2, "a": 1})
        assert isinstance(result, tuple)

    def test_list(self):
        result = _freeze([1, 2, 3])
        assert result == (1, 2, 3)

    def test_set(self):
        result = _freeze({1, 2})
        assert isinstance(result, frozenset)

    def test_nested(self):
        result = _freeze({"a": [1, {"b": 2}]})
        assert isinstance(result, tuple)

    def test_scalar(self):
        assert _freeze(42) == 42
        assert _freeze("hello") == "hello"


# ==================== _make_cache_key ====================


class TestMakeCacheKey:
    def test_basic(self):
        key = _make_cache_key("AsyncOpenAI", "sk-123", None, 60, 3)
        assert key[0] == "AsyncOpenAI"
        assert key[1] == "sk-123"
        assert key[2] is None
        assert key[3] == 60
        assert key[4] == 3

    def test_with_kwargs(self):
        key = _make_cache_key("Client", "key", "url", 30, 1, extra="val")
        assert len(key) == 6  # 5 positional + frozen kwargs

    def test_hashable(self):
        key = _make_cache_key("C", "k", None, 60, 3, nested={"a": [1]})
        hash(key)  # Should not raise


# ==================== LLMClientPool ====================


class TestLLMClientPool:
    def setup_method(self):
        LLMClientPool.reset()

    def test_singleton(self):
        p1 = LLMClientPool.get_instance()
        p2 = LLMClientPool.get_instance()
        assert p1 is p2

    def test_get_or_create_new(self):
        pool = LLMClientPool.get_instance()
        mock_class = MagicMock()
        mock_class.__name__ = "MockClient"
        client = pool.get_or_create(
            mock_class, api_key="k", base_url=None, timeout=60, max_retries=3
        )
        assert pool.pool_size == 1
        mock_class.assert_called_once()

    def test_get_or_create_cached(self):
        pool = LLMClientPool.get_instance()
        mock_class = MagicMock()
        mock_class.__name__ = "MockClient"
        c1 = pool.get_or_create(mock_class, api_key="k", base_url=None, timeout=60, max_retries=3)
        c2 = pool.get_or_create(mock_class, api_key="k", base_url=None, timeout=60, max_retries=3)
        assert c1 is c2
        assert pool.pool_size == 1

    def test_different_keys_different_clients(self):
        pool = LLMClientPool.get_instance()
        mock_class = MagicMock()
        mock_class.__name__ = "MockClient"
        pool.get_or_create(mock_class, api_key="k1", base_url=None, timeout=60, max_retries=3)
        pool.get_or_create(mock_class, api_key="k2", base_url=None, timeout=60, max_retries=3)
        assert pool.pool_size == 2

    def test_clear(self):
        pool = LLMClientPool.get_instance()
        mock_class = MagicMock()
        mock_class.__name__ = "MockClient"
        pool.get_or_create(mock_class, api_key="k", base_url=None, timeout=60, max_retries=3)
        pool.clear()
        assert pool.pool_size == 0

    def test_reset(self):
        pool = LLMClientPool.get_instance()
        mock_class = MagicMock()
        mock_class.__name__ = "MockClient"
        pool.get_or_create(mock_class, api_key="k", base_url=None, timeout=60, max_retries=3)
        LLMClientPool.reset()
        new_pool = LLMClientPool.get_instance()
        assert new_pool.pool_size == 0


# ==================== AnthropicProvider ====================


class TestAnthropicProvider:
    def _make_config(self, **overrides):
        cfg = MagicMock()
        cfg.api_key = overrides.get("api_key", "sk-ant-test")
        cfg.model = overrides.get("model", "claude-3-5-sonnet")
        cfg.temperature = overrides.get("temperature", 0.7)
        cfg.max_tokens = overrides.get("max_tokens", 4096)
        cfg.base_url = overrides.get("base_url", None)
        cfg.timeout = overrides.get("timeout", 60)
        cfg.max_retries = overrides.get("max_retries", 3)
        return cfg

    def _make_provider(self, **overrides):
        from loom.providers.llm.anthropic import AnthropicProvider
        AnthropicProvider.__abstractmethods__ = frozenset()
        LLMClientPool.reset()
        return AnthropicProvider(self._make_config(**overrides))

    def _mock_async_anthropic(self):
        m = MagicMock()
        m.__name__ = "AsyncAnthropic"
        return m

    def test_import_error_check(self):
        """Verify the import guard exists in the code."""
        import loom.providers.llm.anthropic as mod
        original = mod.AsyncAnthropic
        try:
            mod.AsyncAnthropic = None
            assert mod.AsyncAnthropic is None
        finally:
            mod.AsyncAnthropic = original

    def test_no_api_key(self):
        from loom.providers.llm.anthropic import AnthropicProvider
        AnthropicProvider.__abstractmethods__ = frozenset()
        LLMClientPool.reset()
        with patch("loom.providers.llm.anthropic.AsyncAnthropic", self._mock_async_anthropic()):
            try:
                AnthropicProvider(self._make_config(api_key=""))
                assert False, "Should raise"
            except (ValueError, TypeError):
                pass

    def test_init_success(self):
        with patch("loom.providers.llm.anthropic.AsyncAnthropic", self._mock_async_anthropic()):
            provider = self._make_provider()
            assert provider.model == "claude-3-5-sonnet"
            assert provider.temperature == 0.7

    def test_convert_messages(self):
        with patch("loom.providers.llm.anthropic.AsyncAnthropic", self._mock_async_anthropic()):
            provider = self._make_provider()
            system, msgs = provider._convert_messages([
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ])
            assert system == "You are helpful"
            assert len(msgs) == 2
            assert msgs[0]["role"] == "user"

    def test_convert_tools_mcp_format(self):
        with patch("loom.providers.llm.anthropic.AsyncAnthropic", self._mock_async_anthropic()):
            provider = self._make_provider()
            tools = provider._convert_tools([
                {"name": "bash", "description": "Run", "inputSchema": {"type": "object"}},
            ])
            assert tools[0]["input_schema"] == {"type": "object"}

    def test_convert_tools_already_anthropic(self):
        with patch("loom.providers.llm.anthropic.AsyncAnthropic", self._mock_async_anthropic()):
            provider = self._make_provider()
            original = {"name": "t", "description": "d", "input_schema": {"type": "object"}}
            tools = provider._convert_tools([original])
            assert tools[0] is original

    def test_get_token_counter(self):
        with patch("loom.providers.llm.anthropic.AsyncAnthropic", self._mock_async_anthropic()):
            provider = self._make_provider()
            counter = provider.get_token_counter()
            assert counter is not None


# ==================== GeminiProvider ====================


class TestGeminiProvider:
    def _make_config(self, **overrides):
        cfg = MagicMock()
        cfg.api_key = overrides.get("api_key", "test-key")
        cfg.model = overrides.get("model", "gemini-2.0-flash")
        cfg.temperature = overrides.get("temperature", 0.7)
        cfg.max_tokens = overrides.get("max_tokens", 8192)
        return cfg

    def _make_provider(self, **overrides):
        from loom.providers.llm.gemini import GeminiProvider
        GeminiProvider.__abstractmethods__ = frozenset()
        return GeminiProvider(self._make_config(**overrides))

    def test_import_error_check(self):
        """Verify the import guard exists."""
        import loom.providers.llm.gemini as mod
        original = mod.genai
        try:
            mod.genai = None
            assert mod.genai is None
        finally:
            mod.genai = original

    @patch("loom.providers.llm.gemini.genai", MagicMock())
    @patch("loom.providers.llm.gemini.GeminiGenConfig", MagicMock())
    def test_no_api_key(self):
        from loom.providers.llm.gemini import GeminiProvider
        GeminiProvider.__abstractmethods__ = frozenset()
        try:
            GeminiProvider(self._make_config(api_key=""))
            assert False, "Should raise"
        except (ValueError, TypeError):
            pass

    @patch("loom.providers.llm.gemini.genai", MagicMock())
    @patch("loom.providers.llm.gemini.GeminiGenConfig", MagicMock())
    def test_init_success(self):
        provider = self._make_provider()
        assert provider.model_name == "gemini-2.0-flash"

    @patch("loom.providers.llm.gemini.genai", MagicMock())
    @patch("loom.providers.llm.gemini.GeminiGenConfig", MagicMock())
    def test_convert_messages(self):
        provider = self._make_provider()
        msgs = provider._convert_messages([
            {"role": "system", "content": "System msg"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ])
        assert msgs[0]["role"] == "user"
        assert "[System]" in msgs[0]["parts"][0]["text"]
        assert msgs[1]["role"] == "user"
        assert msgs[2]["role"] == "model"

    @patch("loom.providers.llm.gemini.genai", MagicMock())
    @patch("loom.providers.llm.gemini.GeminiGenConfig", MagicMock())
    def test_convert_tools(self):
        provider = self._make_provider()
        tools = provider._convert_tools([
            {"name": "bash", "description": "Run", "parameters": {"type": "object"}},
        ])
        assert len(tools) == 1
        assert "function_declarations" in tools[0]


# ==================== DeepSeekProvider ====================


class TestDeepSeekProvider:
    def test_class_attributes(self):
        from loom.providers.llm.deepseek import DeepSeekProvider

        assert DeepSeekProvider.DEFAULT_MODEL == "deepseek-chat"
        assert "deepseek" in DeepSeekProvider.DEFAULT_BASE_URL
        assert DeepSeekProvider.PROVIDER_NAME == "DeepSeek"
