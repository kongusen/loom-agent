# 配置 LLM 提供商

> **问题导向** - 学会配置不同的 LLM 提供商（OpenAI、Anthropic、国内大模型等）

## 概述

loom-agent 支持多种 LLM 提供商：
- **OpenAI**：GPT-4, GPT-3.5 等
- **Anthropic**：Claude 系列
- **国内大模型**：DeepSeek, Qwen, Kimi 等（通过 OpenAI 兼容接口）

## 快速开始（最简单方式）

类似 LlamaIndex 的简单配置方式：

```python
from loom.llm import OpenAIProvider
from loom.weave import create_agent, run

# 方式 1：自动读取环境变量（推荐）
provider = OpenAIProvider()  # 自动读取 OPENAI_API_KEY 和 OPENAI_BASE_URL

# 方式 2：直接指定参数
provider = OpenAIProvider(
    model="gpt-4",
    api_key="sk-...",
    base_url="https://api.openai.com/v1"
)

# 创建 Agent
agent = create_agent("assistant", role="助手", provider=provider)

# 使用
result = run(agent, "你好")
```

**国内大模型示例**：

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

## 配置体系概述

loom-agent 提供了系统化的 LLM 配置体系，支持：

### 配置模型架构

```
LLMConfig (完整配置)
├── ConnectionConfig    # 连接配置（API Key、Base URL、超时）
├── GenerationConfig    # 生成参数（Temperature、Max Tokens 等）
├── StreamConfig        # 流式输出配置
├── StructuredOutputConfig  # 结构化输出配置（JSON Mode）
├── ToolConfig          # 工具调用配置
└── AdvancedConfig      # 高级配置（Logprobs、Seed 等）
```

### 三种使用方式

1. **最简单**：自动读取环境变量
2. **快速配置**：传递参数
3. **系统化配置**：使用 LLMConfig（完整控制）

## 安装依赖

### OpenAI 及兼容接口

```bash
# 安装 OpenAI SDK
pip install loom-agent[llm]

# 或使用 poetry
poetry install -E llm
```

### Anthropic Claude

```bash
# 安装 Anthropic SDK
pip install loom-agent[anthropic]

# 或使用 poetry
poetry install -E anthropic
```

### 安装所有支持

```bash
pip install loom-agent[all]
```

## 配置方式

### 方式 1：环境变量（推荐）

最简单和安全的配置方式是使用环境变量：

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选，默认为官方地址

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# 国内大模型（以 DeepSeek 为例）
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
```

**优势**：
- 不会将密钥硬编码到代码中
- 易于在不同环境切换
- 符合安全最佳实践

### 方式 2：快速配置（传递参数）

使用 OpenAIProvider 快速配置：

```python
from loom.llm import OpenAIProvider

# 快速配置
provider = OpenAIProvider(
    model="gpt-4",
    api_key="sk-...",
    base_url="https://api.openai.com/v1",
    temperature=0.7,
    max_tokens=1000
)
```

**优势**：
- 简单直观
- 适合快速原型开发
- 向后兼容

### 方式 3：系统化配置（LLMConfig）

使用完整的配置体系，支持所有高级功能：

```python
from loom.llm import (
    OpenAIProvider,
    LLMConfig,
    GenerationConfig,
    StreamConfig,
    StructuredOutputConfig
)

# 创建完整配置
config = LLMConfig(
    generation=GenerationConfig(
        model="gpt-4",
        temperature=0.7,
        max_tokens=1000,
        seed=42  # 可复现
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

**优势**：
- 完整的配置控制
- 类型安全（Pydantic 验证）
- 支持所有高级功能
- 适合生产环境

### 方式 4：使用 .env 文件

创建 `.env` 文件：

```bash
# .env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_API_KEY=sk-ant-...
```

在代码中加载：

```python
from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env 文件中的环境变量
```

## 配置模型详解

### ConnectionConfig（连接配置）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key` | str | None | API Key |
| `base_url` | str | None | API Base URL |
| `timeout` | float | 60.0 | 请求超时（秒）|
| `max_retries` | int | 3 | 最大重试次数 |
| `organization` | str | None | 组织 ID |

### GenerationConfig（生成参数）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | str | "gpt-4" | 模型名称 |
| `temperature` | float | 0.7 | 温度参数（0.0-2.0）|
| `top_p` | float | 1.0 | Top P 采样 |
| `max_tokens` | int | None | 最大生成 Token 数 |
| `seed` | int | None | 随机种子（可复现）|

### StreamConfig（流式输出）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | True | 是否启用流式 |
| `include_usage` | bool | False | 是否包含 Token 统计 |

### StructuredOutputConfig（结构化输出）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | False | 是否启用 |
| `format` | str | "text" | 输出格式（json/json_object/text）|
| `schema` | dict | None | JSON Schema |

## 配置场景示例

### 场景 1：流式输出配置

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

### 场景 2：结构化输出配置

```python
config = LLMConfig(
    structured_output=StructuredOutputConfig(
        enabled=True,
        format="json_object"
    )
)
provider = OpenAIProvider(config=config)
```

### 场景 3：可复现配置

```python
config = LLMConfig(
    generation=GenerationConfig(
        model="gpt-4",
        temperature=0.7,
        seed=42  # 固定种子，结果可复现
    )
)
provider = OpenAIProvider(config=config)
```

## 具体提供商配置

### OpenAI

**配置环境变量**：

```bash
export OPENAI_API_KEY="sk-..."
# 可选：自定义 Base URL（默认为 https://api.openai.com/v1）
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

**使用示例**：

```python
from loom.llm import OpenAIProvider
from loom.weave import create_agent, run

# 自动读取环境变量
provider = OpenAIProvider()

# 创建 Agent
agent = create_agent("assistant", role="助手", provider=provider)

# 使用
result = run(agent, "你好")
```

### 国内大模型（OpenAI 兼容接口）

大多数国内大模型都提供 OpenAI 兼容接口，只需修改 Base URL 即可。

#### DeepSeek

**配置环境变量**：
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
```

**使用示例**：
```python
from loom.llm import OpenAIProvider

provider = OpenAIProvider(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1"
)
```

#### 阿里云 Qwen（通义千问）

**配置环境变量**：
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

**使用示例**：
```python
provider = OpenAIProvider(
    model="qwen-turbo",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)
```

#### Moonshot AI (Kimi)

**配置环境变量**：
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"
```

**使用示例**：
```python
provider = OpenAIProvider(
    model="moonshot-v1-8k",
    base_url="https://api.moonshot.cn/v1"
)
```

#### 智谱 AI (GLM)

**配置环境变量**：
```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://open.bigmodel.cn/api/paas/v4"
```

**使用示例**：
```python
provider = OpenAIProvider(
    model="glm-4",
    base_url="https://open.bigmodel.cn/api/paas/v4"
)
```

### Anthropic Claude

**配置环境变量**：

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# 可选：自定义 Base URL（默认为 https://api.anthropic.com）
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
```

**使用示例**：

```python
from anthropic import AsyncAnthropic

# 创建 Anthropic 客户端（自动读取环境变量）
client = AsyncAnthropic()

# 创建自定义 Provider（需要封装 Anthropic 客户端）
# 注：需要实现 LLMProvider 接口
```

## 最佳实践

### 1. 使用环境变量

**推荐**：
```bash
# .env 文件
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
```

**不推荐**：
```python
# 硬编码在代码中
api_key = "sk-..."  # ❌ 不安全
```

### 2. 不同环境使用不同配置

```bash
# 开发环境 (.env.dev)
OPENAI_API_KEY=sk-dev-...
OPENAI_BASE_URL=https://api.openai.com/v1

# 生产环境 (.env.prod)
OPENAI_API_KEY=sk-prod-...
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 3. 验证配置

在启动时验证 API 配置：

```python
import os

def validate_llm_config():
    """验证 LLM 配置是否正确"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 未设置")

    base_url = os.getenv("OPENAI_BASE_URL")
    print(f"✓ API Key: {api_key[:10]}...")
    print(f"✓ Base URL: {base_url or '默认'}")

validate_llm_config()
```

### 4. 生产环境使用完整配置

在生产环境中，推荐使用完整的 LLMConfig 以获得更好的控制：

```python
from loom.llm import OpenAIProvider, LLMConfig, GenerationConfig, StreamConfig

# 生产环境配置
config = LLMConfig(
    generation=GenerationConfig(
        model="gpt-4",
        temperature=0.7,
        max_tokens=2000,
        seed=42  # 可复现
    ),
    stream=StreamConfig(
        enabled=True,
        include_usage=True  # 监控 Token 使用
    )
)

provider = OpenAIProvider(config=config)
```

**优势**：
- 类型安全，减少配置错误
- 完整的参数控制
- 便于配置管理和版本控制
- 支持所有高级功能

## 常见问题

### Q1: 如何切换不同的 LLM 提供商？

**A**: 只需修改环境变量即可：
```bash
# 从 OpenAI 切换到 DeepSeek
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
export OPENAI_API_KEY="sk-deepseek-..."
```

### Q2: Base URL 必须配置吗？

**A**: 不是必须的：
- OpenAI 官方 API：可以不配置，使用默认值
- 国内大模型：必须配置，指向对应的 API 地址

### Q3: 如何在代码中获取环境变量？

**A**: 使用 `os.getenv()`：
```python
import os
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
```

### Q4: 如何实现自定义 LLMProvider？

**A**: 继承 `LLMProvider` 接口并实现 `chat()` 和 `stream_chat()` 方法。详见 [创建自定义 Provider](#) 指南。

### Q5: 什么时候使用快速配置，什么时候使用完整配置？

**A**: 根据场景选择：

- **快速配置**：适合快速原型开发、简单应用
  ```python
  provider = OpenAIProvider(model="gpt-4", temperature=0.7)
  ```

- **完整配置**：适合生产环境、需要精细控制的场景
  ```python
  config = LLMConfig(
      generation=GenerationConfig(model="gpt-4", temperature=0.7, seed=42),
      stream=StreamConfig(enabled=True, include_usage=True)
  )
  provider = OpenAIProvider(config=config)
  ```

### Q6: 如何启用结构化输出（JSON Mode）？

**A**: 使用 StructuredOutputConfig：

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

### Q7: 如何确保结果可复现？

**A**: 设置 `seed` 参数：

```python
config = LLMConfig(
    generation=GenerationConfig(
        model="gpt-4",
        temperature=0.7,
        seed=42  # 固定种子
    )
)
```

## 总结

loom-agent 提供了系统化的 LLM 配置体系，支持三种使用方式：

### 配置方式选择

1. **简单模式**（自动读取环境变量）
   ```python
   provider = OpenAIProvider()
   ```
   适合：快速开始、简单应用

2. **快速配置**（传递参数）
   ```python
   provider = OpenAIProvider(model="gpt-4", temperature=0.7)
   ```
   适合：快速原型开发、中等复杂度应用

3. **完整配置**（使用 LLMConfig）
   ```python
   config = LLMConfig(
       generation=GenerationConfig(...),
       stream=StreamConfig(...),
       structured_output=StructuredOutputConfig(...)
   )
   provider = OpenAIProvider(config=config)
   ```
   适合：生产环境、需要精细控制的场景

### 关键步骤

1. **安装依赖**：`pip install loom-agent[llm]`
2. **配置环境变量**：设置 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`
3. **选择配置方式**：根据场景选择简单、快速或完整配置
4. **验证配置**：启动时检查环境变量是否正确
5. **使用 Provider**：传递给 Agent 使用

### 配置体系特点

- **类型安全**：使用 Pydantic 模型，自动验证参数
- **分层设计**：连接、生成、流式、结构化输出等独立配置
- **向后兼容**：支持简单参数传递，也支持完整配置
- **功能完整**：覆盖所有 OpenAI API 参数和高级特性

## 相关文档

- [环境配置](environment-setup.md) - 完整的环境配置指南
- [创建 Agent](../agents/creating-agents.md) - 如何创建和使用 Agent
- [生产部署](../deployment/production-deployment.md) - 生产环境部署指南
