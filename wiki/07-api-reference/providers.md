# LLM Providers

## Built-in Providers

```python
from loom.providers import AnthropicProvider, OpenAIProvider, GeminiProvider

provider = AnthropicProvider(api_key="sk-ant-...")
provider = OpenAIProvider(api_key="sk-...", base_url="https://api.openai.com/v1")
provider = GeminiProvider(api_key="...")
```

## Custom Provider

Subclass `LLMProvider` and implement `_complete`:

```python
from loom.providers.base import LLMProvider, CompletionParams

class MyProvider(LLMProvider):
    def __init__(self):
        super().__init__()   # required — wires retry + circuit breaker

    async def _complete(self, messages, params: CompletionParams | None = None) -> str:
        # call your LLM API here
        return response_text

    async def stream(self, messages, params=None):
        yield chunk
```

## CompletionParams

```python
CompletionParams(
    model="claude-opus-4-6",
    max_tokens=4096,
    temperature=1.0,
)
```

## Retry & Circuit Breaker

All providers inherit retry and circuit breaker from `LLMProvider`:

```python
RetryConfig(
    max_retries=3,
    base_delay=1.0,
    circuit_open_after=5,    # failures before opening circuit
    circuit_reset_after=60.0,
)
```

**Code:** `loom/providers/`
