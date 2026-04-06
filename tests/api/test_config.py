"""Test API config"""

import pytest
from loom.api import (
    AgentConfig,
    LLMConfig,
    ToolConfig,
    PolicyConfig,
)


class TestConfig:
    """Test configuration classes"""

    def test_llm_config_defaults(self):
        """Test LLMConfig defaults"""
        config = LLMConfig()
        assert config.model == "gpt-4-turbo"
        assert config.temperature == 0.7
        assert config.timeout == 120

    def test_llm_config_custom(self):
        """Test LLMConfig custom values"""
        config = LLMConfig(model="gpt-4", temperature=0.5)
        assert config.model == "gpt-4"
        assert config.temperature == 0.5

    def test_tool_config_defaults(self):
        """Test ToolConfig defaults"""
        config = ToolConfig()
        assert isinstance(config.allow, list)
        assert isinstance(config.deny, list)

    def test_tool_config_custom(self):
        """Test ToolConfig custom values"""
        config = ToolConfig(
            allow=["bash", "file_read"],
            deny=["rm_rf"]
        )
        assert "bash" in config.allow
        assert "rm_rf" in config.deny

    def test_policy_config_defaults(self):
        """Test PolicyConfig defaults"""
        config = PolicyConfig()
        assert config.policy_id == "default"
        assert config.max_depth == 3

    def test_agent_config_defaults(self):
        """Test AgentConfig defaults"""
        config = AgentConfig(name="test")
        assert config.name == "test"
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.tools, ToolConfig)

    def test_agent_config_custom(self):
        """Test AgentConfig custom values"""
        llm = LLMConfig(model="gpt-4")
        config = AgentConfig(name="test", llm=llm)
        assert config.llm.model == "gpt-4"
