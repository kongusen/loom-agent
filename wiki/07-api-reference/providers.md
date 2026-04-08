# Providers

This page explains how Loom connects to model providers and how application developers should configure environment variables.

For application code, the recommended path is:

- select a provider with `ModelRef`
- provide keys and base URLs through environment variables

Avoid constructing `AnthropicProvider` or `OpenAIProvider` directly unless you are extending Loom internals.

## 1. Standard Usage

```python
from loom import AgentConfig, ModelRef, create_agent

agent = create_agent(
    AgentConfig(
        model=ModelRef.openai("gpt-4.1-mini"),
        instructions="You are a technical assistant.",
    )
)
```

Loom resolves the provider lazily on first execution based on `ModelRef`.

## 2. Supported Providers

| Provider | Constructor | Default API Key Env Var | Base URL |
|---|---|---|---|
| Anthropic | `ModelRef.anthropic(name)` | `ANTHROPIC_API_KEY` | `api_base` |
| OpenAI | `ModelRef.openai(name)` | `OPENAI_API_KEY` | `api_base` or `OPENAI_BASE_URL` |
| Gemini | `ModelRef.gemini(name)` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | no public base URL field today |
| Qwen | `ModelRef.qwen(name)` | `DASHSCOPE_API_KEY` | provider default endpoint |
| Ollama | `ModelRef.ollama(name)` | not required | `api_base` or `OLLAMA_BASE_URL`, default `http://localhost:11434` |

## 3. OpenAI-Compatible Endpoints

If you are using an OpenAI-compatible gateway:

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://your-openai-compatible-endpoint/v1"
```

```python
from loom import AgentConfig, ModelRef, create_agent

agent = create_agent(
    AgentConfig(
        model=ModelRef.openai("gpt-4.1-mini"),
        instructions="You are a platform assistant.",
    )
)
```

If you do not want to use the default environment variable names:

```python
import os

from loom import ModelRef

model = ModelRef.openai(
    "my-model",
    api_base=os.getenv("MY_MODEL_BASE_URL"),
    api_key_env="MY_MODEL_API_KEY",
)
```

## 4. Anthropic

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

```python
model = ModelRef.anthropic("claude-sonnet-4")
```

If you are routing through a private proxy:

```python
model = ModelRef.anthropic(
    "claude-sonnet-4",
    api_base="https://your-proxy.example.com",
)
```

## 5. Gemini

```bash
export GEMINI_API_KEY="..."
```

or:

```bash
export GOOGLE_API_KEY="..."
```

```python
model = ModelRef.gemini("gemini-2.5-flash")
```

## 6. Qwen

```bash
export DASHSCOPE_API_KEY="..."
```

```python
model = ModelRef.qwen("qwen-max")
```

## 7. Ollama

```bash
export OLLAMA_BASE_URL="http://localhost:11434"
```

```python
model = ModelRef.ollama("llama3")
```

Or set it explicitly:

```python
model = ModelRef.ollama(
    "llama3",
    api_base="http://localhost:11434",
)
```

## 8. What Happens When Provider Initialization Fails

If provider initialization fails, Loom does not necessarily raise immediately. It falls back according to runtime configuration.

Default fallback:

```python
RuntimeFallbackMode.LOCAL_SUMMARY
```

That means:

- the environment variable may be missing
- provider construction may fail
- the agent may still return a local fallback summary result

If you want strict failure:

```python
from loom.config import RuntimeConfig, RuntimeFallback, RuntimeFallbackMode, RuntimeFeatures

runtime = RuntimeConfig(
    features=RuntimeFeatures(
        fallback=RuntimeFallback(mode=RuntimeFallbackMode.ERROR),
    )
)
```

Then pass it into `AgentConfig(runtime=runtime)`.

## 9. Recommended Environment Variable Patterns

### OpenAI-compatible gateway

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://gateway.example.com/v1"
```

```python
model = ModelRef.openai("gpt-4.1-mini")
```

### Multi-provider switching

```python
import os

from loom import AgentConfig, ModelRef, create_agent


def build_model() -> ModelRef:
    provider = os.getenv("LOOM_PROVIDER", "openai").lower()
    model_name = os.getenv("LOOM_MODEL_NAME", "gpt-4.1-mini")

    if provider == "anthropic":
        return ModelRef.anthropic(model_name)
    if provider == "gemini":
        return ModelRef.gemini(model_name)
    if provider == "qwen":
        return ModelRef.qwen(model_name)
    if provider == "ollama":
        return ModelRef.ollama(model_name)
    return ModelRef.openai(model_name)


agent = create_agent(
    AgentConfig(
        model=build_model(),
        instructions="You are a multi-provider assistant.",
    )
)
```

Notes:

- `LOOM_PROVIDER` and `LOOM_MODEL_NAME` are application-level conventions
- Loom still reads provider credentials from the provider-specific standard environment variables

## 10. Advanced Extension Path

If you are extending Loom internals, look at:

- `loom.providers.base.LLMProvider`
- `loom.providers.openai.OpenAIProvider`
- `loom.providers.anthropic.AnthropicProvider`
- `loom.providers.gemini.GeminiProvider`

Most application developers do not need to depend on these classes directly.

The public best practice remains:

```text
ModelRef + AgentConfig + create_agent()
```

Related example:

- [02_provider_config.py](https://github.com/kongusen/loom-agent/blob/main/examples/02_provider_config.py)
