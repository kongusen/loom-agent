# 使用自定义 base_url - OpenAI 兼容服务

Loom Agent 支持任何 OpenAI 兼容的第三方服务，只需指定自定义的 `base_url`。

## 使用场景

1. **API 代理/转发服务**：使用国内代理访问 OpenAI
2. **第三方兼容服务**：使用其他提供 OpenAI 兼容 API 的服务
3. **自建 LLM 服务**：使用 vLLM, FastChat, Ollama 等自建服务
4. **企业内网服务**：使用企业内部部署的 LLM 服务

---

## 方式 1：使用已知提供商 + 自定义 URL

如果使用的是已知提供商（如 OpenAI, DeepSeek），但需要通过代理访问：

```python
import loom

# OpenAI 通过代理访问
agent = loom.agent(
    name="assistant",
    llm="openai",
    api_key="sk-...",
    base_url="https://your-proxy.com/v1"  # 自定义代理 URL
)

# DeepSeek 通过代理
agent = loom.agent(
    name="assistant",
    llm="deepseek",
    api_key="sk-...",
    base_url="https://your-deepseek-proxy.com/v1"
)
```

---

## 方式 2：使用 "custom" 提供商（推荐）

对于完全自定义的 OpenAI 兼容服务，使用 `llm="custom"`：

```python
import loom

agent = loom.agent(
    name="assistant",
    llm="custom",                              # 使用自定义提供商
    api_key="your-api-key",                    # API 密钥
    base_url="https://your-service.com/v1",    # 必须指定 base_url
    model="your-model-name"                    # 模型名称
)
```

---

## 完整示例

### 示例 1：使用 vLLM 自建服务

[vLLM](https://github.com/vllm-project/vllm) 提供 OpenAI 兼容的 API 服务器。

```python
# 启动 vLLM 服务器
# vllm serve Qwen/Qwen2-7B-Instruct --port 8000

import loom, Message
import asyncio

async def main():
    agent = loom.agent(
        name="assistant",
        llm="custom",
        api_key="EMPTY",  # vLLM 默认不需要验证
        base_url="http://localhost:8000/v1",
        model="Qwen/Qwen2-7B-Instruct"
    )

    msg = Message(role="user", content="介绍一下 vLLM")
    response = await agent.run(msg)
    print(response.content)

asyncio.run(main())
```

### 示例 2：使用 Ollama

[Ollama](https://ollama.ai/) 本地运行大模型，也提供 OpenAI 兼容接口。

```python
# 启动 Ollama 并拉取模型
# ollama pull qwen:7b
# ollama serve

import loom, Message
import asyncio

async def main():
    agent = loom.agent(
        name="assistant",
        llm="custom",
        api_key="EMPTY",  # Ollama 不需要 API key
        base_url="http://localhost:11434/v1",
        model="qwen:7b"
    )

    msg = Message(role="user", content="你好")
    response = await agent.run(msg)
    print(response.content)

asyncio.run(main())
```

### 示例 3：使用 FastChat

[FastChat](https://github.com/lm-sys/FastChat) 提供 OpenAI 兼容的 API 服务。

```python
# 启动 FastChat
# python -m fastchat.serve.controller
# python -m fastchat.serve.openai_api_server --port 8000

import loom

agent = loom.agent(
    name="assistant",
    llm="custom",
    api_key="EMPTY",
    base_url="http://localhost:8000/v1",
    model="vicuna-7b"
)
```

### 示例 4：使用 LM Studio

[LM Studio](https://lmstudio.ai/) 本地运行模型，提供 OpenAI 兼容接口。

```python
# 在 LM Studio 中加载模型并启动服务器（默认端口 1234）

import loom

agent = loom.agent(
    name="assistant",
    llm="custom",
    api_key="lm-studio",  # LM Studio 需要任意非空字符串
    base_url="http://localhost:1234/v1",
    model="local-model"  # LM Studio 中加载的模型
)
```

### 示例 5：使用 Text Generation WebUI

[Text Generation WebUI](https://github.com/oobabooga/text-generation-webui) 提供 OpenAI 兼容扩展。

```python
# 启用 openai 扩展并启动服务器

import loom

agent = loom.agent(
    name="assistant",
    llm="custom",
    api_key="EMPTY",
    base_url="http://localhost:5000/v1",
    model="your-model"
)
```

### 示例 6：使用 OpenAI 国内代理

```python
import loom

# 使用国内代理访问 OpenAI
agent = loom.agent(
    name="assistant",
    llm="openai",  # 或者使用 "custom"
    api_key="sk-...",
    base_url="https://api.openai-proxy.com/v1"  # 替换为你的代理地址
)
```

### 示例 7：企业内网 LLM 服务

```python
import loom

agent = loom.agent(
    name="assistant",
    llm="custom",
    api_key="your-internal-key",
    base_url="https://llm.yourcompany.internal/v1",
    model="company-gpt-model"
)
```

---

## 使用 UnifiedLLM（高级）

如果需要更多控制，可以直接使用 `UnifiedLLM`：

```python
import loom
from loom.builtin import UnifiedLLM

# 创建自定义 LLM
llm = UnifiedLLM(
    provider="custom",
    api_key="your-key",
    base_url="https://your-service.com/v1",
    model="your-model",
    temperature=0.7,
    max_tokens=2000,
    timeout=120.0
)

# 使用
agent = loom.agent(name="assistant", llm=llm)
```

---

## 配置参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `llm` | 提供商名称 | `"custom"` 或 `"openai"` |
| `api_key` | API 密钥 | `"sk-..."` 或 `"EMPTY"` |
| `base_url` | API 基础 URL | `"http://localhost:8000/v1"` |
| `model` | 模型名称 | `"gpt-4"` 或自定义模型名 |
| `temperature` | 温度参数 | `0.7` |
| `max_tokens` | 最大 tokens | `2000` |
| `timeout` | 超时时间（秒） | `120.0` |

---

## 字典配置方式

也可以使用字典传递所有参数：

```python
import loom

agent = loom.agent(
    name="assistant",
    llm={
        "provider": "custom",
        "api_key": "your-key",
        "base_url": "https://your-service.com/v1",
        "model": "your-model",
        "temperature": 0.7,
        "max_tokens": 2000
    }
)
```

---

## 验证配置

测试你的配置是否正常工作：

```python
import asyncio
import loom, Message

async def test_custom_llm():
    agent = loom.agent(
        name="test-agent",
        llm="custom",
        api_key="your-key",
        base_url="https://your-service.com/v1",
        model="your-model"
    )

    try:
        msg = Message(role="user", content="Hello!")
        response = await agent.run(msg)
        print(f"✅ 成功: {response.content}")
    except Exception as e:
        print(f"❌ 错误: {e}")

asyncio.run(test_custom_llm())
```

---

## 常见问题

### Q: 我的服务需要特殊的请求头，如何配置？

A: `UnifiedLLM` 使用 OpenAI SDK，可以通过 `kwargs` 传递额外参数：

```python
from loom.builtin import UnifiedLLM

llm = UnifiedLLM(
    provider="custom",
    api_key="your-key",
    base_url="https://your-service.com/v1",
    model="your-model",
    default_headers={"X-Custom-Header": "value"}  # 自定义请求头
)
```

### Q: 我的服务使用不同的认证方式怎么办？

A: 如果你的服务使用特殊认证方式（非 Bearer Token），你需要：

1. 使用 `openai` SDK 的 `http_client` 参数自定义请求
2. 或者实现自己的 `BaseLLM` 适配器

### Q: 为什么使用 "custom" 而不是直接用 "openai"？

A: 使用 `"custom"` 更明确，表示这是自定义服务。同时，`"custom"` 提供商**要求**你必须指定 `base_url`，避免遗漏配置。

### Q: 支持哪些 OpenAI API 特性？

A: 只要你的服务兼容 OpenAI API 格式，就支持：
- 文本生成
- 流式输出
- 工具调用（function calling）
- JSON 模式

---

## 相关文档

- [LLM 支持](./LLM_SUPPORT.md) - 主流 LLM 提供商
- [快速开始](./docs/getting-started/quickstart.md)
- [API 参考](./docs/api/README.md)

---

## 推荐的自建服务

1. **vLLM** - 高性能推理引擎，推荐用于生产环境
2. **Ollama** - 最简单的本地运行方案
3. **LM Studio** - 图形化界面，适合初学者
4. **FastChat** - 功能完整，支持多种模型
5. **Text Generation WebUI** - 功能丰富，社区活跃

---

**提示**：使用自定义服务时，请确保你的服务完全兼容 OpenAI API 格式。如果不兼容，你需要实现自己的 `BaseLLM` 适配器。
