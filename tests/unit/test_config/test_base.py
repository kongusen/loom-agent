"""
Base Configuration Unit Tests

测试基础配置类的序列化功能
"""

import json

from loom.config.base import LoomBaseConfig


class TestConfig(LoomBaseConfig):
    """测试用配置类"""

    name: str = "test"
    value: int = 42
    optional: str | None = None


class TestLoomBaseConfig:
    """测试LoomBaseConfig基类"""

    def test_to_dict(self):
        """测试转换为字典"""
        config = TestConfig(name="test", value=100)
        result = config.to_dict()

        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 100
        assert "optional" not in result  # None值应该被排除

    def test_to_dict_with_optional(self):
        """测试带可选字段的字典转换"""
        config = TestConfig(name="test", value=100, optional="data")
        result = config.to_dict()

        assert result["optional"] == "data"

    def test_from_dict(self):
        """测试从字典创建配置"""
        data = {"name": "test", "value": 200}
        config = TestConfig.from_dict(data)

        assert config.name == "test"
        assert config.value == 200

    def test_to_json(self):
        """测试转换为JSON"""
        config = TestConfig(name="test", value=100)
        result = config.to_json()

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["name"] == "test"
        assert parsed["value"] == 100

    def test_from_json(self):
        """测试从JSON创建配置"""
        json_str = '{"name": "test", "value": 300}'
        config = TestConfig.from_json(json_str)

        assert config.name == "test"
        assert config.value == 300
