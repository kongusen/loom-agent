"""Test agent core"""

import pytest
from loom.agent.core import Agent
from loom.agent.runtime import Runtime, RuntimeConfig
from loom.providers.base import LLMProvider, CompletionParams


class MockProvider(LLMProvider):
    """Mock LLM provider"""

    async def complete(self, messages, params: CompletionParams = None):
        return "mock response"

    async def stream(self, messages, params: CompletionParams = None):
        yield "mock"
        yield " response"


class TestAgent:
    """Test Agent"""

    def test_agent_creation(self):
        """Test Agent creation"""
        provider = MockProvider()
        agent = Agent(provider)
        assert agent.provider == provider
        assert agent.runtime is not None
        assert agent.context is not None
        assert agent.depth == 0

    def test_agent_with_config(self):
        """Test Agent with custom config"""
        provider = MockProvider()
        config = RuntimeConfig(max_depth=5, max_tokens=2000)
        agent = Agent(provider, config)
        assert agent.runtime.config.max_depth == 5
        assert agent.runtime.config.max_tokens == 2000


class TestRuntime:
    """Test Runtime"""

    def test_runtime_defaults(self):
        """Test Runtime defaults"""
        runtime = Runtime()
        assert runtime.config.max_depth == 5
        assert runtime.config.max_tokens == 200000

    def test_runtime_custom(self):
        """Test Runtime custom config"""
        config = RuntimeConfig(max_depth=20, max_tokens=8000)
        runtime = Runtime(config)
        assert runtime.config.max_depth == 20
        assert runtime.config.max_tokens == 8000

    def test_check_constraints(self):
        """Test constraint checking"""
        runtime = Runtime()
        ok, reason = runtime.check_constraints(0.5, 3)
        assert ok is True
        assert reason == ""

        ok, reason = runtime.check_constraints(1.0, 3)
        assert ok is False
        assert "overflow" in reason
