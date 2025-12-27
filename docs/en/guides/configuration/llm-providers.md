# Configuring LLM Providers

> **Problem-Oriented** - Learn to configure different LLM providers (OpenAI, Anthropic, Chinese LLMs, etc.)

## Overview

loom-agent supports multiple LLM providers:
- **OpenAI**: GPT-4, GPT-3.5, etc.
- **Anthropic**: Claude series
- **Chinese LLMs**: DeepSeek, Qwen, Kimi, etc. (via OpenAI-compatible interface)

## Quick Start (Simplest Way)

Simple configuration similar to LlamaIndex:

```python
from loom.llm import OpenAIProvider
from loom.weave import create_agent, run

# Method 1: Auto-read environment variables (recommended)
provider = OpenAIProvider()  # Auto-reads OPENAI_API_KEY and OPENAI_BASE_URL

# Method 2: Specify parameters directly
provider = OpenAIProvider(
    model="gpt-4",
    api_key="sk-...",
    base_url="https://api.openai.com/v1"
)

# Create Agent
agent = create_agent("assistant", role="Assistant", provider=provider)

# Use
result = run(agent, "Hello")
```

**Chinese LLM Examples**:

```python
# DeepSeek
provider = OpenAIProvider(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1"
)

# Kimi
provider = OpenAIProvider(
    model="moonshot-v1-8k",
    base_url="https://api.moonshot.cn/v1"
)
```

## Configuration System Overview

loom-agent provides a systematic LLM configuration system that supports:

### Configuration Model Architecture

```
LLMConfig (Complete Configuration)
├── ConnectionConfig    # Connection configuration (API Key, Base URL, Timeout)
├── GenerationConfig    # Generation parameters (Temperature, Max Tokens, etc.)
├── StreamConfig        # Streaming output configuration
├── StructuredOutputConfig  # Structured output configuration (JSON Mode)
├── ToolConfig          # Tool calling configuration
└── AdvancedConfig      # Advanced configuration (Logprobs, Seed, etc.)
```

### Three Usage Modes

1. **Simplest**: Auto-read environment variables
2. **Quick Configuration**: Pass parameters
3. **Systematic Configuration**: Use LLMConfig (complete control)

## Installation Dependencies

### OpenAI and Compatible Interfaces

```bash
# Install OpenAI SDK
pip install loom-agent[llm]

# Or using poetry
poetry install -E llm
```

### Anthropic Claude

```bash
# Install Anthropic SDK
pip install loom-agent[anthropic]

# Or using poetry
poetry install -E anthropic
```

### Install All Support

```bash
pip install loom-agent[all]
```

## Configuration Methods

### Method 1: Environment Variables (Recommended)

The simplest and most secure configuration method is using environment variables:

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"  # Optional, defaults to official address

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Chinese LLMs (e.g., DeepSeek)
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
```

**Advantages**:
- No hardcoded secrets in code
- Easy to switch between environments
- Follows security best practices

### Method 2: Quick Configuration (Pass Parameters)

Use OpenAIProvider for quick configuration:

```python
from loom.llm import OpenAIProvider

# Quick configuration
provider = OpenAIProvider(
    model="gpt-4",
    api_key="sk-...",
    base_url="https://api.openai.com/v1",
    temperature=0.7,
    max_tokens=1000
)
```

**Advantages**:
- Simple and intuitive
- Suitable for rapid prototyping
- Backward compatible

### Method 3: Systematic Configuration (LLMConfig)

Use the complete configuration system for all advanced features:

```python
from loom.llm import (
    OpenAIProvider,
    LLMConfig,
    GenerationConfig,
    StreamConfig,
    StructuredOutputConfig
)

# Create complete configuration
config = LLMConfig(
    generation=GenerationConfig(
        model="gpt-4",
        temperature=0.7,
        max_tokens=1000,
        seed=42  # Reproducible
    ),
    stream=StreamConfig(
        enabled=True,
        include_usage=True
    ),
    structured_output=StructuredOutputConfig(
        enabled=True,
        format="json_object"
    )
)

provider = OpenAIProvider(config=config)
```

**Advantages**:
- Complete configuration control
- Type-safe (Pydantic validation)
- Supports all advanced features
- Suitable for production environments

### Method 4: Using .env File

Create a `.env` file:

```bash
# .env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_API_KEY=sk-ant-...
```

Load in code:

```python
from dotenv import load_dotenv
load_dotenv()  # Auto-loads environment variables from .env file
```

## Configuration Model Details

### ConnectionConfig (Connection Configuration)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | str | None | API Key |
| `base_url` | str | None | API Base URL |
| `timeout` | float | 60.0 | Request timeout (seconds) |
| `max_retries` | int | 3 | Maximum retry attempts |
| `organization` | str | None | Organization ID |

### GenerationConfig (Generation Parameters)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | str | "gpt-4" | Model name |
| `temperature` | float | 0.7 | Temperature parameter (0.0-2.0) |
| `top_p` | float | 1.0 | Top P sampling |
| `max_tokens` | int | None | Maximum generation tokens |
| `seed` | int | None | Random seed (reproducible) |

### StreamConfig (Streaming Output)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | True | Enable streaming |
| `include_usage` | bool | False | Include token statistics |

### StructuredOutputConfig (Structured Output)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | False | Enable structured output |
| `format` | str | "text" | Output format (json/json_object/text) |
| `schema` | dict | None | JSON Schema |

### ToolConfig (Tool Calling)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tool_choice` | str | "auto" | Tool selection strategy (auto/none/required) |
| `parallel_tool_calls` | bool | True | Allow parallel tool calls |
| `tool_timeout` | float | 30.0 | Tool call timeout (seconds) |

### AdvancedConfig (Advanced Configuration)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `logprobs` | bool | False | Return log probabilities |
| `top_logprobs` | int | None | Return top N logprobs |
| `logit_bias` | dict | None | Token bias |

## Configuration Scenario Examples

### Scenario 1: Streaming Output Configuration

```python
from loom.llm import OpenAIProvider, LLMConfig, StreamConfig

config = LLMConfig(
    stream=StreamConfig(
        enabled=True,
        include_usage=True
    )
)
provider = OpenAIProvider(config=config)
```

### Scenario 2: Structured Output Configuration

```python
config = LLMConfig(
    structured_output=StructuredOutputConfig(
        enabled=True,
        format="json_object"
    )
)
provider = OpenAIProvider(config=config)
```

### Scenario 3: Reproducible Configuration

```python
config = LLMConfig(
    generation=GenerationConfig(
        model="gpt-4",
        temperature=0.7,
        seed=42  # Fixed seed for reproducible results
    )
)
provider = OpenAIProvider(config=config)
```

## Specific Provider Configurations

### OpenAI

**Configure environment variables**:

```bash
export OPENAI_API_KEY="sk-..."
# Optional: Custom Base URL (defaults to https://api.openai.com/v1)
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

**Usage example**:

```python
from loom.llm import OpenAIProvider
from loom.weave import create_agent, run

# Auto-read environment variables
provider = OpenAIProvider()

# Create Agent
agent = create_agent("assistant", role="Assistant", provider=provider)

# Use
result = run(agent, "Hello")
```

### Chinese LLMs (OpenAI-Compatible Interface)

Most Chinese LLMs provide OpenAI-compatible interfaces, requiring only a Base URL change.

#### DeepSeek

**Configure environment variables**:
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
```

**Usage example**:
```python
from loom.llm import OpenAIProvider

provider = OpenAIProvider(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1"
)
```

#### Alibaba Cloud Qwen (Tongyi Qianwen)

**Configure environment variables**:
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

**Usage example**:
```python
provider = OpenAIProvider(
    model="qwen-turbo",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)
```

#### Moonshot AI (Kimi)

**Configure environment variables**:
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"
```

**Usage example**:
```python
provider = OpenAIProvider(
    model="moonshot-v1-8k",
    base_url="https://api.moonshot.cn/v1"
)
```

#### Zhipu AI (GLM)

**Configure environment variables**:
```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://open.bigmodel.cn/api/paas/v4"
```

**Usage example**:
```python
provider = OpenAIProvider(
    model="glm-4",
    base_url="https://open.bigmodel.cn/api/paas/v4"
)
```

### Anthropic Claude

**Configure environment variables**:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Optional: Custom Base URL (defaults to https://api.anthropic.com)
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
```

**Usage example**:

```python
from anthropic import AsyncAnthropic

# Create Anthropic client (auto-reads environment variables)
client = AsyncAnthropic()

# Create custom Provider (requires wrapping Anthropic client)
# Note: Requires implementing LLMProvider interface
```

## Best Practices

### 1. Use Environment Variables

**Recommended**:
```bash
# .env file
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
```

**Not recommended**:
```python
# Hardcoded in code
api_key = "sk-..."  # ❌ Insecure
```

### 2. Use Different Configurations for Different Environments

```bash
# Development environment (.env.dev)
OPENAI_API_KEY=sk-dev-...
OPENAI_BASE_URL=https://api.openai.com/v1

# Production environment (.env.prod)
OPENAI_API_KEY=sk-prod-...
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 3. Validate Configuration

Validate API configuration at startup:

```python
import os

def validate_llm_config():
    """Validate LLM configuration is correct"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    base_url = os.getenv("OPENAI_BASE_URL")
    print(f"✓ API Key: {api_key[:10]}...")
    print(f"✓ Base URL: {base_url or 'default'}")

validate_llm_config()
```

### 4. Use Complete Configuration in Production

In production environments, use complete LLMConfig for better control:

```python
from loom.llm import OpenAIProvider, LLMConfig, GenerationConfig, StreamConfig

# Production configuration
config = LLMConfig(
    generation=GenerationConfig(
        model="gpt-4",
        temperature=0.7,
        max_tokens=2000,
        seed=42  # Reproducible
    ),
    stream=StreamConfig(
        enabled=True,
        include_usage=True  # Monitor token usage
    )
)

provider = OpenAIProvider(config=config)
```

**Advantages**:
- Type-safe, reduces configuration errors
- Complete parameter control
- Easy configuration management and version control
- Supports all advanced features

## Frequently Asked Questions

### Q1: How to switch between different LLM providers?

**A**: Simply modify environment variables:
```bash
# Switch from OpenAI to DeepSeek
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
export OPENAI_API_KEY="sk-deepseek-..."
```

### Q2: Is Base URL required?

**A**: Not always:
- OpenAI official API: Optional, uses default value
- Chinese LLMs: Required, must point to the corresponding API address

### Q3: How to get environment variables in code?

**A**: Use `os.getenv()`:
```python
import os
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
```

### Q4: How to implement a custom LLMProvider?

**A**: Inherit the `LLMProvider` interface and implement `chat()` and `stream_chat()` methods. See [Creating Custom Providers](#) guide for details.

### Q5: When to use quick configuration vs complete configuration?

**A**: Choose based on scenario:

- **Quick configuration**: Suitable for rapid prototyping, simple applications
  ```python
  provider = OpenAIProvider(model="gpt-4", temperature=0.7)
  ```

- **Complete configuration**: Suitable for production environments, scenarios requiring fine control
  ```python
  config = LLMConfig(
      generation=GenerationConfig(model="gpt-4", temperature=0.7, seed=42),
      stream=StreamConfig(enabled=True, include_usage=True)
  )
  provider = OpenAIProvider(config=config)
  ```

### Q6: How to enable structured output (JSON Mode)?

**A**: Use StructuredOutputConfig:

```python
from loom.llm import LLMConfig, StructuredOutputConfig

config = LLMConfig(
    structured_output=StructuredOutputConfig(
        enabled=True,
        format="json_object"
    )
)
provider = OpenAIProvider(config=config)
```

### Q7: How to ensure reproducible results?

**A**: Set the `seed` parameter:

```python
config = LLMConfig(
    generation=GenerationConfig(
        model="gpt-4",
        temperature=0.7,
        seed=42  # Fixed seed
    )
)
```

## Summary

loom-agent provides a systematic LLM configuration system with three usage modes:

### Configuration Mode Selection

1. **Simple Mode** (Auto-read environment variables)
   ```python
   provider = OpenAIProvider()
   ```
   Suitable for: Quick start, simple applications

2. **Quick Configuration** (Pass parameters)
   ```python
   provider = OpenAIProvider(model="gpt-4", temperature=0.7)
   ```
   Suitable for: Rapid prototyping, medium complexity applications

3. **Complete Configuration** (Use LLMConfig)
   ```python
   config = LLMConfig(
       generation=GenerationConfig(...),
       stream=StreamConfig(...),
       structured_output=StructuredOutputConfig(...)
   )
   provider = OpenAIProvider(config=config)
   ```
   Suitable for: Production environments, scenarios requiring fine control

### Key Steps

1. **Install dependencies**: `pip install loom-agent[llm]`
2. **Configure environment variables**: Set `OPENAI_API_KEY` and `OPENAI_BASE_URL`
3. **Choose configuration mode**: Select simple, quick, or complete configuration based on scenario
4. **Validate configuration**: Check environment variables at startup
5. **Use Provider**: Pass to Agent for use

### Configuration System Features

- **Type-safe**: Uses Pydantic models, automatic parameter validation
- **Layered design**: Independent configuration for connection, generation, streaming, structured output, etc.
- **Backward compatible**: Supports simple parameter passing and complete configuration
- **Feature complete**: Covers all OpenAI API parameters and advanced features

## Related Documentation

- [Environment Setup](environment-setup.md) - Complete environment configuration guide
- [Creating Agents](../agents/creating-agents.md) - How to create and use Agents
- [Production Deployment](../deployment/production-deployment.md) - Production environment deployment guide

