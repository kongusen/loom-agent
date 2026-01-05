"""
测试配置模型
"""

from loom.config.models import AgentConfig, CrewConfig


class TestConfigModels:
    """测试配置模型"""

    def test_agent_config_creation(self):
        """测试创建 Agent 配置"""
        config = AgentConfig(name="test-agent", type="CoderAgent")
        assert config.name == "test-agent"
        assert config.type == "CoderAgent"

    def test_crew_config_creation(self):
        """测试创建 Crew 配置"""
        config = CrewConfig(name="test-crew", agents=["agent1", "agent2"])
        assert config.name == "test-crew"
        assert len(config.agents) == 2
