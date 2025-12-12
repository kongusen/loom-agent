"""
测试 StreamAccumulator 的功能

验证流式累积器能正确处理：
- 纯文本流式响应
- JSON 模式响应
- 工具调用响应
- 混合类型内容
"""

import json
import pytest
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from loom.utils.stream_accumulator import (
    StreamAccumulator,
    SimpleStreamAccumulator,
    safe_string_concat,
    is_json_content,
)


# Mock OpenAI 流式响应结构
@dataclass
class MockDelta:
    content: Optional[Any] = None
    role: Optional[str] = None
    tool_calls: Optional[List] = None


@dataclass
class MockChoice:
    delta: MockDelta
    finish_reason: Optional[str] = None


@dataclass
class MockChunk:
    choices: List[MockChoice]


@dataclass
class MockToolCallDelta:
    index: int
    id: Optional[str] = None
    type: Optional[str] = None
    function: Optional[Any] = None


@dataclass
class MockFunction:
    name: Optional[str] = None
    arguments: Optional[str] = None


class TestStreamAccumulator:
    """测试 StreamAccumulator 类"""

    def test_simple_text_stream(self):
        """测试简单文本流式累积"""
        accumulator = StreamAccumulator(mode='text')

        # 模拟流式文本块
        chunks = [
            MockChunk([MockChoice(MockDelta(content="Hello", role="assistant"))]),
            MockChunk([MockChoice(MockDelta(content=" "))]),
            MockChunk([MockChoice(MockDelta(content="world"))]),
            MockChunk([MockChoice(MockDelta(content="!"), finish_reason="stop")]),
        ]

        for chunk in chunks:
            accumulator.add(chunk)

        result = accumulator.get_result()
        assert result['content'] == "Hello world!"
        assert result['role'] == "assistant"
        assert result['finish_reason'] == "stop"
        assert 'tool_calls' not in result or not result['tool_calls']

    def test_json_mode_stream(self):
        """测试 JSON 模式流式累积"""
        accumulator = StreamAccumulator(mode='json')

        # 模拟 JSON 流式块
        json_str = '{"name": "Alice", "age": 30}'
        chunks = [
            MockChunk([MockChoice(MockDelta(content=char))]) for char in json_str
        ]
        chunks.append(MockChunk([MockChoice(MockDelta(), finish_reason="stop")]))

        for chunk in chunks:
            accumulator.add(chunk)

        result = accumulator.get_result()
        assert isinstance(result['content'], dict)
        assert result['content']['name'] == "Alice"
        assert result['content']['age'] == 30

    def test_auto_detect_json(self):
        """测试自动检测 JSON 模式"""
        accumulator = StreamAccumulator(mode='auto')

        # JSON 格式的内容
        json_str = '{"message": "test", "value": 42}'
        chunks = [
            MockChunk([MockChoice(MockDelta(content=char))]) for char in json_str
        ]

        for chunk in chunks:
            accumulator.add(chunk)

        result = accumulator.get_result()
        # 自动模式应该检测到 JSON 并解析
        assert isinstance(result['content'], dict)
        assert result['content']['message'] == "test"
        assert result['content']['value'] == 42

    def test_dict_content(self):
        """测试直接返回字典内容的情况"""
        accumulator = StreamAccumulator(mode='auto')

        # 模拟某些情况下 LLM 直接返回字典
        dict_content = {"key": "value", "number": 123}
        chunk = MockChunk([MockChoice(MockDelta(content=dict_content))])

        accumulator.add(chunk)

        result = accumulator.get_result()
        # 应该能够处理字典内容
        content = result['content']
        assert isinstance(content, (dict, str))
        if isinstance(content, str):
            # 如果被序列化了，应该能解析回字典
            parsed = json.loads(content)
            assert parsed['key'] == "value"
            assert parsed['number'] == 123

    def test_tool_calls_accumulation(self):
        """测试工具调用的累积"""
        accumulator = StreamAccumulator(mode='auto')

        # 模拟工具调用流式响应
        chunks = [
            MockChunk([
                MockChoice(MockDelta(
                    tool_calls=[
                        MockToolCallDelta(
                            index=0,
                            id="call_123",
                            type="function",
                            function=MockFunction(name="get_weather")
                        )
                    ]
                ))
            ]),
            MockChunk([
                MockChoice(MockDelta(
                    tool_calls=[
                        MockToolCallDelta(
                            index=0,
                            function=MockFunction(arguments='{"loc')
                        )
                    ]
                ))
            ]),
            MockChunk([
                MockChoice(MockDelta(
                    tool_calls=[
                        MockToolCallDelta(
                            index=0,
                            function=MockFunction(arguments='ation": "SF"}')
                        )
                    ]
                ))
            ]),
            MockChunk([MockChoice(MockDelta(), finish_reason="tool_calls")]),
        ]

        for chunk in chunks:
            accumulator.add(chunk)

        result = accumulator.get_result()
        tool_calls = result.get('tool_calls', [])

        assert len(tool_calls) == 1
        assert tool_calls[0]['id'] == "call_123"
        assert tool_calls[0]['function']['name'] == "get_weather"
        assert tool_calls[0]['function']['arguments']['location'] == "SF"

    def test_multiple_tool_calls(self):
        """测试多个并行工具调用"""
        accumulator = StreamAccumulator(mode='auto')

        chunks = [
            # 第一个工具调用
            MockChunk([
                MockChoice(MockDelta(
                    tool_calls=[
                        MockToolCallDelta(
                            index=0,
                            id="call_1",
                            type="function",
                            function=MockFunction(name="tool1", arguments='{"a": 1}')
                        )
                    ]
                ))
            ]),
            # 第二个工具调用
            MockChunk([
                MockChoice(MockDelta(
                    tool_calls=[
                        MockToolCallDelta(
                            index=1,
                            id="call_2",
                            type="function",
                            function=MockFunction(name="tool2", arguments='{"b": 2}')
                        )
                    ]
                ))
            ]),
        ]

        for chunk in chunks:
            accumulator.add(chunk)

        tool_calls = accumulator.get_tool_calls()
        assert len(tool_calls) == 2
        assert tool_calls[0]['function']['name'] == "tool1"
        assert tool_calls[1]['function']['name'] == "tool2"

    def test_empty_stream(self):
        """测试空流式响应"""
        accumulator = StreamAccumulator(mode='auto')

        result = accumulator.get_result()
        assert result['content'] is None
        assert result['role'] is None
        assert result['finish_reason'] is None

    def test_mixed_content_types(self):
        """测试混合类型内容"""
        accumulator = StreamAccumulator(mode='auto')

        chunks = [
            MockChunk([MockChoice(MockDelta(content="String "))]),
            MockChunk([MockChoice(MockDelta(content={"key": "value"}))]),
            MockChunk([MockChoice(MockDelta(content=" more"))]),
        ]

        for chunk in chunks:
            accumulator.add(chunk)

        content = accumulator.get_content()
        # 应该能够处理混合类型并转换为字符串
        assert isinstance(content, str)
        assert "String" in content


class TestSimpleStreamAccumulator:
    """测试 SimpleStreamAccumulator 类"""

    def test_simple_text(self):
        """测试简单文本累积"""
        accumulator = SimpleStreamAccumulator(parse_json=False)

        chunks = [
            MockChunk([MockChoice(MockDelta(content="Hello"))]),
            MockChunk([MockChoice(MockDelta(content=" world"))]),
        ]

        for chunk in chunks:
            accumulator.add(chunk)

        result = accumulator.get_result()
        assert result == "Hello world"

    def test_json_parsing(self):
        """测试 JSON 解析"""
        accumulator = SimpleStreamAccumulator(parse_json=True)

        json_str = '{"test": true}'
        chunks = [
            MockChunk([MockChoice(MockDelta(content=char))]) for char in json_str
        ]

        for chunk in chunks:
            accumulator.add(chunk)

        result = accumulator.get_result()
        assert isinstance(result, dict)
        assert result['test'] is True


class TestUtilityFunctions:
    """测试工具函数"""

    def test_safe_string_concat_strings(self):
        """测试安全字符串连接 - 纯字符串"""
        parts = ["Hello", " ", "world", "!"]
        result = safe_string_concat(parts)
        assert result == "Hello world!"

    def test_safe_string_concat_mixed_types(self):
        """测试安全字符串连接 - 混合类型"""
        parts = ["String", {"key": "value"}, 123, None, "end"]
        result = safe_string_concat(parts)
        assert isinstance(result, str)
        assert "String" in result
        assert "end" in result

    def test_safe_string_concat_dict(self):
        """测试安全字符串连接 - 包含字典"""
        parts = ["Data: ", {"name": "test", "value": 42}]
        result = safe_string_concat(parts)
        assert isinstance(result, str)
        assert "Data: " in result
        # 字典应该被序列化为 JSON
        assert "name" in result or "test" in result

    def test_safe_string_concat_bytes(self):
        """测试安全字符串连接 - 包含字节"""
        parts = ["Text: ", b"bytes content", " end"]
        result = safe_string_concat(parts)
        assert isinstance(result, str)
        assert "Text: " in result
        assert "bytes content" in result
        assert " end" in result

    def test_is_json_content_dict(self):
        """测试 JSON 内容检测 - 字典"""
        assert is_json_content({"key": "value"}) is True
        assert is_json_content([1, 2, 3]) is True

    def test_is_json_content_string(self):
        """测试 JSON 内容检测 - 字符串"""
        assert is_json_content('{"key": "value"}') is True
        assert is_json_content('[1, 2, 3]') is True
        assert is_json_content('plain text') is False
        assert is_json_content('') is False

    def test_is_json_content_invalid_json(self):
        """测试 JSON 内容检测 - 无效 JSON"""
        # 看起来像 JSON 但实际上无效
        assert is_json_content('{invalid}') is False
        assert is_json_content('[not, json]') is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
