# LLM 配置指南

Loom v0.2.1 采用了显式的 **Class-First (类优先)** 配置哲学。这意味着你需要为每个提供商实例化特定的 Python 类，以确保类型安全和更好的 IDE 支持。

## 1. 支持的提供商

所有提供商均位于 `loom.builtin` 下。

| 提供商 | 类名 | 说明 |
| :--- | :--- | :--- |
| **OpenAI** | `OpenAILLM` | 标准 OpenAI API。 |
| **DeepSeek (深度求索)** | `DeepSeekLLM` | 国产最强模型之一 (OpenAI 兼容)。 |
| **Claude (Anthropic)** | `ClaudeLLM` | Anthropic Claude 3.5 Sonnet 等。 |
| **Qwen (通义千问)** | `QwenLLM` | 阿里云通义千问。 |
| **Kimi (月之暗面)** | `KimiLLM` | Moonshot AI。 |
| **Zhipu (智谱)** | `ZhipuLLM` | GLM-4 等。 |
| **Custom (自定义)** | `CustomLLM` | 任何 OpenAI 兼容的端点 (Ollama/vLLM)。 |

## 2. 基础用法

实例化类并将其传递给 Agent。

```python
from loom.builtin import Agent, OpenAILLM

# 1. 初始化 LLM
llm = OpenAILLM(
    api_key="sk-...", 
    model="gpt-4",
    temperature=0.7
)

# 2. 创建 Agent
agent = Agent(name="Assistant", llm=llm)
```

## 3. 提供商示例

### DeepSeek (DeepSeek-V3)
```python
from loom.builtin import DeepSeekLLM

llm = DeepSeekLLM(
    api_key="sk-...",
    # 默认模型为 'deepseek-chat'
)
```

### Anthropic (Claude 3.5 Sonnet)
需要安装依赖: `pip install anthropic`。
```python
from loom.builtin import ClaudeLLM

llm = ClaudeLLM(
    api_key="sk-ant-...",
    model="claude-3-5-sonnet-20241022"
)
```

### 自定义端点 (如 Ollama/vLLM)
```python
from loom.builtin import CustomLLM

llm = CustomLLM(
    base_url="http://localhost:11434/v1",
    api_key="ollama", # 严格 API 的占位符
    model="llama3"
)
```

## 4. 高级配置

### 运行时配置 (`RunnableConfig`)
你可以在调用时通过 config 传递运行时能力（如 `max_concurrency`），或在 Agent 上设置默认值。但在 Loom 中，模型特定的参数（如 temperature, top_p）通常保留在 LLM 实例上。

### System Prompts (系统提示词)
系统提示词应传递给 `Agent`，而不是直接传递给 LLM，因为 Agent 负责管理上下文窗口。

```python
agent = Agent(
    ...,
    system_prompt="你是一个严格的代码审查者。"
)
```
