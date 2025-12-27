"""
测试配置加载功能
"""

import pytest
import tempfile
import os
from pathlib import Path

from loom.config.models import LoomConfig, AgentConfig, CrewConfig, ControlConfig
from loom.config.loader import ConfigLoader
from loom.api.main import LoomApp
from loom.weave import reset_app


@pytest.fixture(autouse=True)
def reset_global_app():
    """每个测试前重置全局 App"""
    reset_app()
    yield
    reset_app()


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


class TestConfigLoader:
    """测试配置加载器"""

    def test_load_yaml_basic(self):
        """测试加载基本 YAML 配置"""
        yaml_content = """
version: "1.0"
agents:
  - name: test-agent
    role: "测试角色"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = ConfigLoader.load_yaml(temp_path)
            assert config.version == "1.0"
            assert len(config.agents) == 1
            assert config.agents[0].name == "test-agent"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_from_file_creates_app(self):
        """测试从文件创建 App"""
        yaml_content = """
version: "1.0"
control:
  budget: 5000
agents:
  - name: test-agent
    type: AnalystAgent
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            app, agents, crews = ConfigLoader.from_file(temp_path)
            assert app is not None
            assert "test-agent" in agents
            assert agents["test-agent"].node_id == "test-agent"
        finally:
            os.unlink(temp_path)
