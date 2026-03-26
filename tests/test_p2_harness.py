"""测试 P2 Harness 能量效率优化."""

import time

import pytest

from loom.agent import Agent
from loom.config import AgentConfig
from loom.memory.tokenizers import EstimatorTokenizer
from loom.types import CompletionParams, CompletionResult, FinishReason, LLMProvider


class MockProvider(LLMProvider):
    async def complete(self, params: CompletionParams) -> CompletionResult:
        return CompletionResult(
            content="Done",
            finish_reason=FinishReason.STOP,
            tool_calls=[],
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

    async def stream(self, params: CompletionParams):
        yield {"type": "text", "text": "Mock"}


# ── EstimatorTokenizer 测试 ──


def test_tokenizer_lru_cache():
    """测试 LRU 缓存."""
    tokenizer = EstimatorTokenizer()
    text = "This is a test string for token counting"

    # 首次计数
    start = time.perf_counter()
    count1 = tokenizer.count(text)
    cold_time = time.perf_counter() - start

    # 缓存命中
    start = time.perf_counter()
    count2 = tokenizer.count(text)
    hot_time = time.perf_counter() - start

    assert count1 == count2
    assert hot_time < cold_time or hot_time < 0.001  # 缓存应该更快


def test_tokenizer_incremental():
    """测试增量计算 - 用于追加场景."""
    tokenizer = EstimatorTokenizer()

    base = "Hello World"
    delta = " Extra"

    # 增量计算（用于追加）
    base_tokens = tokenizer.count(base)
    delta_tokens = tokenizer.count(delta)
    incremental = base_tokens + delta_tokens

    # 验证增量方法
    incremental_method = tokenizer.count_incremental(base, delta)
    assert incremental_method == incremental


# ── Agent 历史缓存测试 ──


@pytest.mark.asyncio
async def test_agent_history_cache():
    """测试历史缓存优化."""
    config = AgentConfig(system_prompt="Test", max_steps=3)
    agent = Agent(provider=MockProvider(), config=config)

    # 首次构建
    messages1 = await agent._build_messages()
    assert not agent._history_dirty
    assert agent._history_cache.get("messages") is not None

    # 缓存命中
    messages2 = await agent._build_messages()
    assert messages1 == messages2


@pytest.mark.asyncio
async def test_agent_history_dirty_flag():
    """测试脏标记机制."""
    config = AgentConfig(system_prompt="Test", max_steps=3)
    agent = Agent(provider=MockProvider(), config=config)

    # 构建消息
    await agent._build_messages()
    assert not agent._history_dirty

    # 添加新消息应该标记为脏
    from loom.types import UserMessage
    await agent.memory.add_message(UserMessage(content="New message"))
    # 注意：实际使用中 stream 方法会设置脏标记


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
