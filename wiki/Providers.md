# Providers

BaseLLMProvider 为 LLM 调用提供弹性保障：指数退避重试 + 熔断器保护。

## 重试机制

连续失败时自动重试，指数退避延迟：

```python
from loom.providers.base import BaseLLMProvider, RetryConfig
from loom.providers.openai import OpenAIProvider
from loom import AgentConfig

provider = OpenAIProvider(
    AgentConfig(api_key="sk-xxx", model="gpt-4o-mini"),
    retry=RetryConfig(max_retries=3, base_delay=0.1),
)
```

## 熔断器

连续失败达到阈值后，快速拒绝后续请求，避免雪崩：

```python
from loom.providers.base import CircuitBreakerConfig

provider = OpenAIProvider(
    AgentConfig(api_key="sk-xxx", model="gpt-4o-mini"),
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,
        reset_time=60,
    ),
)
```

## 自定义 Provider

继承 `BaseLLMProvider`，实现 `_do_complete` 和 `_do_stream`：

```python
class FlakyProvider(BaseLLMProvider):
    """模拟不稳定 LLM — 前 N 次失败后恢复。"""

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
```

## 与 Agent 集成

```python
from loom import Agent, AgentConfig

safe_provider = OpenAIProvider(
    AgentConfig(api_key="sk-xxx", model="gpt-4o-mini"),
    retry=RetryConfig(max_retries=2),
)
agent = Agent(provider=safe_provider, config=AgentConfig(max_steps=2))
```

## API 参考

```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    reset_time: float = 60.0

class BaseLLMProvider:
    def __init__(self, retry=None, circuit_breaker=None)
    async def complete(params) -> CompletionResult
    async def stream(params) -> AsyncGenerator[StreamChunk]
    # 子类实现:
    async def _do_complete(params) -> CompletionResult
    async def _do_stream(params) -> AsyncGenerator[StreamChunk]
```

> 完整示例：[`examples/demo/11_provider.py`](../examples/demo/11_provider.py)
