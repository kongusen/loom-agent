"""
Token 计数器测试脚本

验证 Token 计数功能是否正常工作。
"""

import pytest

from loom.memory.tokenizer import (
    AnthropicCounter,
    EstimateCounter,
    TiktokenCounter,
)


def test_estimate_counter():
    """测试估算计数器"""
    counter = EstimateCounter()

    # 测试英文文本
    text_en = "Hello, this is a test message."
    tokens_en = counter.count(text_en)
    assert tokens_en > 0, "英文文本的token数应该大于0"
    assert isinstance(tokens_en, int), "token数应该是整数"

    # 测试中文文本
    text_cn = "你好，这是一条测试消息。"
    tokens_cn = counter.count(text_cn)
    assert tokens_cn > 0, "中文文本的token数应该大于0"
    assert isinstance(tokens_cn, int), "token数应该是整数"

    # 测试消息列表
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    tokens_msgs = counter.count_messages(messages)
    assert tokens_msgs > 0, "消息列表的token数应该大于0"
    assert isinstance(tokens_msgs, int), "token数应该是整数"


def test_tiktoken_counter():
    """测试 Tiktoken 计数器"""
    try:
        counter = TiktokenCounter(model="gpt-4")

        # 测试英文文本
        text_en = "Hello, this is a test message."
        tokens_en = counter.count(text_en)
        assert tokens_en > 0, "英文文本的token数应该大于0"
        assert isinstance(tokens_en, int), "token数应该是整数"

        # 测试中文文本
        text_cn = "你好，这是一条测试消息。"
        tokens_cn = counter.count(text_cn)
        assert tokens_cn > 0, "中文文本的token数应该大于0"
        assert isinstance(tokens_cn, int), "token数应该是整数"

        # 测试消息列表
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        tokens_msgs = counter.count_messages(messages)
        assert tokens_msgs > 0, "消息列表的token数应该大于0"
        assert isinstance(tokens_msgs, int), "token数应该是整数"

    except Exception as e:
        # 如果tiktoken未安装，跳过测试
        pytest.skip(f"TiktokenCounter 测试跳过（可能未安装 tiktoken）: {e}")


def test_anthropic_counter():
    """测试 Anthropic 计数器"""
    counter = AnthropicCounter()

    # 测试英文文本
    text_en = "Hello, this is a test message."
    tokens_en = counter.count(text_en)
    assert tokens_en > 0, "英文文本的token数应该大于0"
    assert isinstance(tokens_en, int), "token数应该是整数"

    # 测试中文文本
    text_cn = "你好，这是一条测试消息。"
    tokens_cn = counter.count(text_cn)
    assert tokens_cn > 0, "中文文本的token数应该大于0"
    assert isinstance(tokens_cn, int), "token数应该是整数"
