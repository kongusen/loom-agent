"""
测试 AgentExecutor 工具结果序列化（v0.1.9）

验证：
- serialize_tool_result() 序列化各种类型
- 结构化元数据保留
- 类型信息保留
"""

import pytest
import json
from loom.core.executor import serialize_tool_result


class TestSerializeToolResultDict:
    """测试字典和列表序列化"""

    def test_serialize_dict(self):
        """字典应该序列化为 JSON"""
        result = {"name": "Alice", "age": 30, "active": True}

        content, metadata = serialize_tool_result(result)

        # 内容是 JSON 字符串
        assert isinstance(content, str)
        parsed = json.loads(content)
        assert parsed == result

        # 元数据包含类型信息
        assert metadata["content_type"] == "application/json"
        assert metadata["result_type"] == "dict"

    def test_serialize_list(self):
        """列表应该序列化为 JSON"""
        result = [1, 2, 3, "four", {"five": 5}]

        content, metadata = serialize_tool_result(result)

        # 内容是 JSON 字符串
        parsed = json.loads(content)
        assert parsed == result

        # 元数据包含类型信息
        assert metadata["content_type"] == "application/json"
        assert metadata["result_type"] == "list"

    def test_serialize_nested_dict(self):
        """嵌套字典应该保留结构"""
        result = {
            "user": {"name": "Alice", "email": "alice@example.com"},
            "scores": [85, 90, 95],
        }

        content, metadata = serialize_tool_result(result)

        parsed = json.loads(content)
        assert parsed == result
        assert parsed["user"]["name"] == "Alice"
        assert len(parsed["scores"]) == 3

    def test_serialize_non_json_serializable(self):
        """无法 JSON 序列化的对象应该降级到 repr()"""
        # 包含不可序列化对象
        class CustomObj:
            pass

        result = {"obj": CustomObj()}

        content, metadata = serialize_tool_result(result)

        # 降级到 repr()
        assert metadata["content_type"] == "text/plain"
        assert "serialization_error" in metadata


class TestSerializeToolResultString:
    """测试字符串序列化"""

    def test_serialize_string(self):
        """纯字符串应该原样保留"""
        result = "This is a plain text result"

        content, metadata = serialize_tool_result(result)

        assert content == result
        assert metadata["content_type"] == "text/plain"
        assert metadata["result_type"] == "str"

    def test_serialize_empty_string(self):
        """空字符串应该正常处理"""
        result = ""

        content, metadata = serialize_tool_result(result)

        assert content == ""
        assert metadata["content_type"] == "text/plain"

    def test_serialize_multiline_string(self):
        """多行字符串应该保留换行符"""
        result = "Line 1\nLine 2\nLine 3"

        content, metadata = serialize_tool_result(result)

        assert content == result
        assert "\n" in content


class TestSerializeToolResultNone:
    """测试 None 值序列化"""

    def test_serialize_none(self):
        """None 应该序列化为空字符串"""
        result = None

        content, metadata = serialize_tool_result(result)

        assert content == ""
        assert metadata["content_type"] == "text/plain"
        assert metadata["result_type"] == "NoneType"


class TestSerializeToolResultException:
    """测试异常对象序列化"""

    def test_serialize_exception(self):
        """异常应该序列化为结构化 JSON"""
        result = ValueError("Invalid input")

        content, metadata = serialize_tool_result(result)

        # 内容是 JSON
        parsed = json.loads(content)
        assert parsed["error"] == "ValueError"
        assert parsed["message"] == "Invalid input"
        assert "args" in parsed

        # 元数据标记为错误
        assert metadata["content_type"] == "application/json"
        assert metadata["result_type"] == "Exception"
        assert metadata["error"] is True

    def test_serialize_custom_exception(self):
        """自定义异常应该保留类型信息"""
        class CustomError(Exception):
            pass

        result = CustomError("Custom error occurred")

        content, metadata = serialize_tool_result(result)

        parsed = json.loads(content)
        assert parsed["error"] == "CustomError"
        assert parsed["message"] == "Custom error occurred"

    def test_serialize_exception_with_args(self):
        """异常的 args 应该被保留"""
        result = RuntimeError("arg1", "arg2", "arg3")

        content, metadata = serialize_tool_result(result)

        parsed = json.loads(content)
        assert parsed["error"] == "RuntimeError"
        assert len(parsed["args"]) == 3


class TestSerializeToolResultOtherTypes:
    """测试其他类型序列化"""

    def test_serialize_int(self):
        """整数应该降级到 repr()"""
        result = 42

        content, metadata = serialize_tool_result(result)

        assert content == "42"
        assert metadata["content_type"] == "text/plain"
        assert metadata["result_type"] == "int"

    def test_serialize_float(self):
        """浮点数应该降级到 repr()"""
        result = 3.14159

        content, metadata = serialize_tool_result(result)

        assert "3.14159" in content
        assert metadata["result_type"] == "float"

    def test_serialize_bool(self):
        """布尔值应该降级到 repr()"""
        result = True

        content, metadata = serialize_tool_result(result)

        assert content == "True"
        assert metadata["result_type"] == "bool"

    def test_serialize_custom_object(self):
        """自定义对象应该使用 repr()"""
        class MyClass:
            def __repr__(self):
                return "<MyClass instance>"

        result = MyClass()

        content, metadata = serialize_tool_result(result)

        assert "<MyClass instance>" in content
        assert metadata["result_type"] == "MyClass"


class TestSerializeToolResultComplexScenarios:
    """测试复杂场景"""

    def test_serialize_preserves_unicode(self):
        """应该保留 Unicode 字符"""
        result = {"message": "你好，世界！", "emoji": "🚀"}

        content, metadata = serialize_tool_result(result)

        parsed = json.loads(content)
        assert parsed["message"] == "你好，世界！"
        assert parsed["emoji"] == "🚀"

    def test_serialize_large_dict(self):
        """大型字典应该正常序列化"""
        result = {f"key_{i}": f"value_{i}" for i in range(1000)}

        content, metadata = serialize_tool_result(result)

        parsed = json.loads(content)
        assert len(parsed) == 1000

    def test_serialize_nested_structures(self):
        """深度嵌套结构应该保留"""
        result = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {"data": "deep"}
                    }
                }
            }
        }

        content, metadata = serialize_tool_result(result)

        parsed = json.loads(content)
        assert parsed["level1"]["level2"]["level3"]["level4"]["data"] == "deep"
