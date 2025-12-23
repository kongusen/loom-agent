# 构建 Agent (Building Agents)

Agent 是 Loom 中的决策者。

## 基础 Agent

最简单的 Agent 需要 `dispatcher`（分发器）、`node_id` 和 `role`（角色）。

```python
from loom.node.agent import AgentNode

agent = AgentNode(
    node_id="agent/basic",
    dispatcher=app.dispatcher,
    role="Generic Assistant"
)
```

## 自定义行为 (Customizing Behavior)

### 系统提示词 (System Prompt)
定义个性和约束。

```python
agent = AgentNode(
    ...,
    system_prompt="你是一个刻薄的编程助手。只用 Python 代码回答。"
)
```

### 添加工具 (Adding Tools)
赋予 Agent 能力。

```python
agent = AgentNode(
    ...,
    tools=[calculator_tool, search_tool]
)
```

### 自定义 LLM 提供商 (Custom LLM Provider)
By default, Loom uses a `MockLLMProvider` for testing. To use a real LLM (e.g., OpenAI), implement the `LLMProvider` protocol.
默认情况下，Loom 使用 `MockLLMProvider` 进行测试。要使用从真实的 LLM（如 OpenAI），请实现 `LLMProvider` 协议或使用现有的适配器。

```python
from loom.interfaces.llm import LLMProvider, LLMResponse
import openai

class OpenAIProvider(LLMProvider):
    # ... 实现细节 ...
    pass

agent = AgentNode(
    ...,
    provider=OpenAIProvider(api_key="sk-...")
)
```
