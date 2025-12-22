# LLM Configuration Guide

Loom v0.2.1 adopts an explicit **Class-First** philosophy for LLM configuration. This means you instantiate specific Python classes for each provider, ensuring type safety and better IDE support.

## 1. Supported Providers

All providers are available under `loom.builtin`.

| Provider | Class | Description |
| :--- | :--- | :--- |
| **OpenAI** | `OpenAILLM` | Standard OpenAI API. |
| **DeepSeek** | `DeepSeekLLM` | DeepSeek (OpenAI Compatible). |
| **Claude** | `ClaudeLLM` | Anthropic's Claude 3.5 Sonnet etc. |
| **Qwen** | `QwenLLM` | Alibaba Tongyi Qianwen. |
| **Kimi** | `KimiLLM` | Moonshot AI. |
| **Zhipu** | `ZhipuLLM` | GLM-4 etc. |
| **Custom** | `CustomLLM` | Any OpenAI-compatible endpoint. |

## 2. Basic Usage

Instantiate the class and pass it to the Agent.

```python
from loom.builtin import Agent, OpenAILLM

# 1. Initialize LLM
llm = OpenAILLM(
    api_key="sk-...", 
    model="gpt-4",
    temperature=0.7
)

# 2. Create Agent
agent = Agent(name="Assistant", llm=llm)
```

## 3. Provider Examples

### DeepSeek (DeepSeek-V3)
```python
from loom.builtin import DeepSeekLLM

llm = DeepSeekLLM(
    api_key="sk-...",
    # Default model is 'deepseek-chat'
)
```

### Anthropic (Claude 3.5 Sonnet)
Requires `pip install anthropic`.
```python
from loom.builtin import ClaudeLLM

llm = ClaudeLLM(
    api_key="sk-ant-...",
    model="claude-3-5-sonnet-20241022"
)
```

### Custom Endpoint (e.g. vLLM/Ollama)
```python
from loom.builtin import CustomLLM

llm = CustomLLM(
    base_url="http://localhost:11434/v1",
    api_key="ollama", # Placeholder for strict APIs
    model="llama3"
)
```

## 4. Advanced Configuration

### Runtime Config (`RunnableConfig`)
You can pass runtime capabilities like `max_concurrency` via the config when invoking, OR set defaults on the Agent. But LLM-specific parameters (temp, top_p) stay on the LLM instance.

### System Prompts
System prompts should be passed to the `Agent`, not the LLM directly, as the Agent manages the context window.

```python
agent = Agent(
    ...,
    system_prompt="You are a strict code reviewer."
)
```
