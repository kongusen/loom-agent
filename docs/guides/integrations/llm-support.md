# Loom Agent - 主流 LLM 支持

Loom Agent 支持主流 LLM 提供商，让你通过简单配置即可使用。

## 安装

```bash
# 基础安装（只有核心框架）
pip install loom-agent

# 带 LLM 支持（推荐）
pip install "loom-agent[llm]"

# 完整安装
pip install "loom-agent[all]"
```

## 支持的 LLM 提供商

### 1. OpenAI 兼容提供商（使用 UnifiedLLM）

这些提供商都支持 OpenAI 兼容的 API 格式，只需安装 `openai` SDK：

```bash
pip install openai
```

**支持的提供商**：
- **OpenAI** - GPT-4, GPT-3.5-turbo
- **DeepSeek** - deepseek-chat, deepseek-coder（国产）
- **Qwen/通义千问** - qwen-turbo, qwen-plus, qwen-max（阿里）
- **Kimi/月之暗面** - moonshot-v1-8k, moonshot-v1-32k
- **智谱/GLM** - glm-4, glm-4-air（国产）
- **豆包** - doubao-pro-4k（字节跳动）
- **零一万物** - yi-large, yi-medium（国产）

### 2. 非兼容提供商（使用专门适配器）

这些提供商使用自己的 API 格式，需要安装对应的 SDK：

- **Anthropic Claude** - `pip install anthropic`
- **Google Gemini** - `pip install google-generativeai`（待实现）

---

## 使用方式

### 方式 1：极简配置（推荐）

这是最简单的使用方式，直接指定提供商名称：

```python
import loom, Message

# OpenAI
agent = loom.agent(
    name="assistant",
    llm="openai",
    api_key="sk-..."
)

# DeepSeek（国产）
agent = loom.agent(
    name="assistant",
    llm="deepseek",
    api_key="sk-..."
)

# 通义千问（阿里）
agent = loom.agent(
    name="assistant",
    llm="qwen",
    api_key="sk-..."
)

# Kimi（月之暗面）
agent = loom.agent(
    name="assistant",
    llm="kimi",
    api_key="sk-..."
)

# 智谱 GLM
agent = loom.agent(
    name="assistant",
    llm="zhipu",
    api_key="sk-..."
)
```

### 方式 2：详细配置

指定更多参数（模型、温度、最大 tokens 等）：

```python
import loom

agent = loom.agent(
    name="assistant",
    llm="deepseek",              # 提供商
    api_key="sk-...",            # API 密钥
    model="deepseek-chat",       # 模型名称
    temperature=0.7,             # 温度
    max_tokens=2000,             # 最大 tokens
    top_p=0.9                    # Top-p 采样
)
```

### 方式 3：字典配置

使用字典传递所有参数：

```python
import loom

agent = loom.agent(
    name="assistant",
    llm={
        "provider": "qwen",
        "api_key": "sk-...",
        "model": "qwen-turbo",
        "temperature": 0.7,
        "max_tokens": 2000
    }
)
```

### 方式 4：直接使用 LLM 实例

高级用户可以直接创建 LLM 实例：

```python
import loom
from loom.builtin import UnifiedLLM

# 创建 LLM 实例
llm = UnifiedLLM(
    provider="openai",
    api_key="sk-...",
    model="gpt-4",
    temperature=0.7
)

# 创建 Agent
agent = loom.agent(name="assistant", llm=llm)
```

---

## 完整示例

### 示例 1：使用 OpenAI

```python
import asyncio
import loom, Message, tool

# 定义工具
@tool()
async def calculator(expression: str) -> float:
    """计算数学表达式"""
    return eval(expression)

async def main():
    # 创建 Agent
    agent = loom.agent(
        name="assistant",
        llm="openai",
        api_key="sk-...",
        model="gpt-4",
        tools=[calculator]
    )

    # 使用
    msg = Message(role="user", content="计算 123 * 456")
    response = await agent.run(msg)
    print(response.content)

asyncio.run(main())
```

### 示例 2：使用 DeepSeek（国产）

```python
import asyncio
import loom, Message

async def main():
    # DeepSeek 是性价比很高的国产模型
    agent = loom.agent(
        name="coder",
        llm="deepseek",
        api_key="sk-...",
        model="deepseek-coder",  # 代码专用模型
        system_prompt="你是一个代码助手"
    )

    msg = Message(role="user", content="用 Python 写一个快速排序")
    response = await agent.run(msg)
    print(response.content)

asyncio.run(main())
```

### 示例 3：使用通义千问（阿里）

```python
import asyncio
import loom, Message

async def main():
    # 通义千问是阿里云的大模型
    agent = loom.agent(
        name="assistant",
        llm="qwen",
        api_key="sk-...",  # 阿里云 API Key
        model="qwen-max",
        temperature=0.7
    )

    msg = Message(role="user", content="介绍一下杭州")
    response = await agent.run(msg)
    print(response.content)

asyncio.run(main())
```

### 示例 4：使用 Kimi（月之暗面）

```python
import asyncio
import loom, Message

async def main():
    # Kimi 支持长文本
    agent = loom.agent(
        name="assistant",
        llm="kimi",
        api_key="sk-...",
        model="moonshot-v1-128k",  # 128k 上下文
    )

    msg = Message(role="user", content="总结这篇长文...")
    response = await agent.run(msg)
    print(response.content)

asyncio.run(main())
```

### 示例 5：使用智谱 GLM

```python
import asyncio
import loom, Message

async def main():
    # 智谱 AI 的 GLM 模型
    agent = loom.agent(
        name="assistant",
        llm="zhipu",
        api_key="...",  # 智谱 API Key
        model="glm-4"
    )

    msg = Message(role="user", content="什么是人工智能？")
    response = await agent.run(msg)
    print(response.content)

asyncio.run(main())
```

---

## 多 Agent 协作（Crew）

不同的 Agent 可以使用不同的 LLM：

```python
import loom
from loom.patterns import Crew

# 研究员使用 DeepSeek（性价比高）
researcher = loom.agent(
    name="researcher",
    llm="deepseek",
    api_key="sk-...",
    system_prompt="你是研究员，负责收集信息"
)

# 撰写员使用 GPT-4（质量高）
writer = loom.agent(
    name="writer",
    llm="openai",
    api_key="sk-...",
    model="gpt-4",
    system_prompt="你是撰写员，负责整理成文章"
)

# 创建 Crew
crew = Crew(agents=[researcher, writer], mode="sequential")
result = await crew.run("写一篇关于 AI Agent 的文章")
print(result)
```

---

## 使用便捷别名

除了 `UnifiedLLM`，我们还提供了便捷别名：

```python
from loom.builtin import (
    OpenAILLM,
    DeepSeekLLM,
    QwenLLM,
    KimiLLM,
    ZhipuLLM
)

# 使用别名（更简洁）
llm = DeepSeekLLM(api_key="sk-...", model="deepseek-chat")
agent = loom.agent(name="assistant", llm=llm)
```

---

## API 密钥管理

**建议使用环境变量**管理 API 密钥：

```bash
# .env 文件
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
QWEN_API_KEY=sk-...
```

```python
import os
import loom

agent = loom.agent(
    name="assistant",
    llm="deepseek",
    api_key=os.getenv("DEEPSEEK_API_KEY")
)
```

---

## 自定义 base_url（代理/兼容服务）

如果你使用代理或兼容服务，可以自定义 `base_url`：

```python
from loom.builtin import UnifiedLLM

llm = UnifiedLLM(
    provider="openai",
    api_key="sk-...",
    base_url="https://your-proxy.com/v1"  # 自定义 URL
)
```

---

## 支持的模型列表

### OpenAI
- gpt-4
- gpt-4-turbo
- gpt-4o
- gpt-3.5-turbo
- o1-preview
- o1-mini

### DeepSeek（国产）
- deepseek-chat
- deepseek-coder

### Qwen/通义千问（阿里）
- qwen-turbo
- qwen-plus
- qwen-max
- qwen-long

### Kimi/月之暗面
- moonshot-v1-8k
- moonshot-v1-32k
- moonshot-v1-128k

### 智谱/GLM（国产）
- glm-4
- glm-4-air
- glm-4-flash
- glm-3-turbo

### 豆包（字节跳动）
- doubao-pro-4k
- doubao-pro-32k
- doubao-lite-4k

### 零一万物（国产）
- yi-large
- yi-medium
- yi-vision
- yi-medium-200k

---

## 常见问题

### Q: 如何选择 LLM 提供商？

A: 根据你的需求：
- **质量优先**：OpenAI GPT-4
- **性价比**：DeepSeek, Qwen
- **长文本**：Kimi (128k 上下文)
- **国产替代**：DeepSeek, Qwen, 智谱, 豆包, 零一万物

### Q: 需要安装什么依赖？

A:
- OpenAI 兼容提供商：`pip install openai`
- Anthropic: `pip install anthropic`

### Q: 如何添加新的提供商？

A: 如果提供商兼容 OpenAI 格式，只需在 `loom/builtin/llms/providers.py` 中添加配置：

```python
"your_provider": {
    "name": "Your Provider",
    "base_url": "https://api.your-provider.com/v1",
    "default_model": "model-name",
    "models": ["model-1", "model-2"],
    "description": "描述"
}
```

### Q: 支持流式输出吗？

A: 是的，所有 LLM 都支持流式输出。框架内部已经处理好了。

---

## 相关文档

- [核心文档](../README.md)
- [API 参考](../docs/api/README.md)
- [快速开始](../docs/getting-started/quickstart.md)

## 许可证

MIT License
