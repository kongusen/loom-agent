"""
API Models Unit Tests

测试API配置模型
"""

import pytest
from pydantic import ValidationError

from loom.api.models import AgentConfig, MemoryConfig


class TestMemoryConfig:
    """测试MemoryConfig模型"""

    def test_memory_config_default(self):
        """测试默认配置"""
        config = MemoryConfig()

        assert config.max_l1_size == 50
        assert config.max_l2_size == 100
        assert config.max_l3_size == 500
        assert config.enable_l4_vectorization is True
        assert config.max_task_index_size == 1000
        assert config.max_fact_index_size == 5000

    def test_memory_config_custom(self):
        """测试自定义配置"""
        config = MemoryConfig(
            max_l1_size=100,
            max_l2_size=200,
            max_l3_size=1000,
            enable_l4_vectorization=False,
            max_task_index_size=2000,
            max_fact_index_size=10000,
        )

        assert config.max_l1_size == 100
        assert config.max_l2_size == 200
        assert config.max_l3_size == 1000
        assert config.enable_l4_vectorization is False
        assert config.max_task_index_size == 2000
        assert config.max_fact_index_size == 10000

    def test_memory_config_validation_min(self):
        """测试最小值验证"""
        with pytest.raises(ValidationError):
            MemoryConfig(max_l1_size=0)  # 小于最小值1

    def test_memory_config_validation_max(self):
        """测试最大值验证"""
        with pytest.raises(ValidationError):
            MemoryConfig(max_l1_size=1001)  # 大于最大值1000


class TestAgentConfig:
    """测试AgentConfig模型"""

    def test_agent_config_minimal(self):
        """测试最小化配置"""
        config = AgentConfig(
            agent_id="test-agent",
            name="Test Agent",
        )

        assert config.agent_id == "test-agent"
        assert config.name == "Test Agent"
        assert config.description == ""
        assert config.capabilities == ["tool_use"]
        assert config.system_prompt == ""
        assert config.max_iterations == 10
        assert config.require_done_tool is True
        assert config.enable_observation is True
        assert config.max_context_tokens == 4000
        assert isinstance(config.memory_config, MemoryConfig)

    def test_agent_config_full(self):
        """测试完整配置"""
        memory_config = MemoryConfig(max_l1_size=100)
        config = AgentConfig(
            agent_id="test-agent",
            name="Test Agent",
            description="A test agent",
            capabilities=["tool_use", "reflection"],
            system_prompt="You are a test agent",
            max_iterations=20,
            require_done_tool=False,
            enable_observation=False,
            max_context_tokens=8000,
            memory_config=memory_config,
        )

        assert config.description == "A test agent"
        assert config.capabilities == ["tool_use", "reflection"]
        assert config.system_prompt == "You are a test agent"
        assert config.max_iterations == 20
        assert config.require_done_tool is False
        assert config.enable_observation is False
        assert config.max_context_tokens == 8000
        assert config.memory_config.max_l1_size == 100

    def test_agent_config_capabilities_valid(self):
        """测试有效的capabilities"""
        config = AgentConfig(
            agent_id="test-agent",
            name="Test Agent",
            capabilities=["tool_use", "reflection", "planning", "multi_agent"],
        )

        assert len(config.capabilities) == 4

    def test_agent_config_capabilities_invalid(self):
        """测试无效的capabilities"""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                agent_id="test-agent",
                name="Test Agent",
                capabilities=["invalid_capability"],
            )

        assert "Invalid capability" in str(exc_info.value)

    def test_agent_config_phase3_fields(self):
        """测试Phase 3新增字段（enabled_skills, disabled_tools, extra_tools）"""
        config = AgentConfig(
            agent_id="test-agent",
            name="Test Agent",
            enabled_skills={"skill1", "skill2"},
            disabled_tools={"tool1"},
            extra_tools={"tool2", "tool3"},
        )

        assert config.enabled_skills == {"skill1", "skill2"}
        assert config.disabled_tools == {"tool1"}
        assert config.extra_tools == {"tool2", "tool3"}

    def test_agent_config_phase3_fields_default(self):
        """测试Phase 3字段的默认值"""
        config = AgentConfig(
            agent_id="test-agent",
            name="Test Agent",
        )

        assert config.enabled_skills == set()
        assert config.disabled_tools == set()
        assert config.extra_tools == set()
