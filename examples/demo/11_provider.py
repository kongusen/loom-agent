"""11 — 弹性 Provider：重试 + 熔断器保障 LLM 调用可靠性。"""

import asyncio
from loom import Agent, AgentConfig
from loom.providers.base import BaseLLMProvider, RetryConfig, CircuitBreakerConfig
from loom.providers.openai import OpenAIProvider
from loom.types import CompletionParams, CompletionResult, TokenUsage, UserMessage
from _provider import create_provider, _KEY, _BASE, _MODEL


class FlakyProvider(BaseLLMProvider):
    """模拟不稳定 LLM — 前 N 次失败后恢复真实调用。"""

    def __init__(self, real_provider, fail_count=2, **kwargs):
        super().__init__(**kwargs)
        self._real = real_provider
        self._fail_count = fail_count
        self._calls = 0

    async def _do_complete(self, params):
        self._calls += 1
        if self._calls <= self._fail_count:
            raise ConnectionError(f"调用 #{self._calls} 网络超时")
        return await self._real._do_complete(params)

    async def _do_stream(self, params):
        async for chunk in self._real._do_stream(params):
            yield chunk


async def main():
    real = OpenAIProvider(AgentConfig(api_key=_KEY, base_url=_BASE, model=_MODEL))

    # ── 1. 重试成功 — 2次失败后恢复真实 LLM ──
    print("[1] 重试机制 (2次网络超时后恢复)")
    provider = FlakyProvider(
        real, fail_count=2,
        retry=RetryConfig(max_retries=3, base_delay=0.1),
    )
    result = await provider.complete(CompletionParams(
        messages=[UserMessage(content="用一句话介绍Python")],
    ))
    print(f"  第{provider._calls}次成功: {result.content[:80]}")

    # ── 2. 熔断器保护 ──
    print("\n[2] 熔断器 (连续失败后快速拒绝)")
    provider2 = FlakyProvider(
        real, fail_count=100,
        retry=RetryConfig(max_retries=0),
        circuit_breaker=CircuitBreakerConfig(failure_threshold=3, reset_time=60),
    )
    for i in range(4):
        try:
            await provider2.complete(CompletionParams(messages=[UserMessage(content="test")]))
        except Exception as e:
            print(f"  调用 #{i+1}: {type(e).__name__} — {e}")

    # ── 3. 带重试的真实 Agent ──
    print("\n[3] Agent + 重试 Provider")
    safe_provider = create_provider(retry=RetryConfig(max_retries=2))
    agent = Agent(provider=safe_provider, config=AgentConfig(max_steps=2))
    r = await agent.run("1+1=?")
    print(f"  回复: {r.content[:80]}")


if __name__ == "__main__":
    asyncio.run(main())
