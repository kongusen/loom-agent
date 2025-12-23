# 快速上手 (Quickstart)

本指南将带你构建第一个 Loom Agent。为了简化，我们首先使用内置的 `MockLLMProvider`，这样你无需 API Key 即可运行。

## 1. 创建你的应用

创建一个名为 `hello_loom.py` 的文件：

```python
import asyncio
from loom.api.main import LoomApp
from loom.node.agent import AgentNode
from loom.infra.llm.mock import MockLLMProvider

async def main():
    # 1. 初始化 Loom 应用
    app = LoomApp()
    
    # 2. 准备模拟 LLM (仅用于演示)
    # 在生产环境中，你会使用 OpenAIProvider 等
    mock_llm = MockLLMProvider(responses=[
        "Thought: 用户在跟我打招呼，我应该礼貌回复。\nFinal Answer: 你好！我是 Loom Agent。"
    ])
    
    # 3. 创建一个 Agent 节点
    agent = AgentNode(
        node_id="greeter",
        dispatcher=app.dispatcher,  # 连接到应用的分发器
        role="Greeter",
        provider=mock_llm,
        system_prompt="你是一个友好的助手。"
    )
    
    # 4. 将节点注册到应用中
    app.add_node(agent)
    
    # 5. 运行任务
    print("User: Hello!")
    result = await app.run(
        task="Hello!", 
        target="greeter"
    )
    
    print(f"Agent: {result['response']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 2. 运行

```bash
python hello_loom.py
```

## 输出

你应该会看到：
```text
User: Hello!
Agent: 你好！我是 Loom Agent。
```

## 刚刚发生了什么？

1.  **`LoomApp`**: 启动了事件总线 (Event Bus) 和分发器 (Dispatcher)。
2.  **`AgentNode`**: 你创建了一个智能体节点。它不仅是一个对象，还是一个连接到总线的**分形节点**。
3.  **`app.run`**:
    *   将你的任务封装为一个 `CloudEvent` (类型: `node.request`)。
    *   将其发送给 `greeter` (Agent 的 ID)。
    *   等待 Agent 处理并返回 `node.response`。

## 下一步

现在你已经跑通了流程，让我们看看如何接入真实的 LLM：
*   **[接入真实 LLM (OpenAI)](../../08_examples/basic_agent_openai.md)**: 使用 API Key 进行真实对话。
*   **[核心概念](../02_core_concepts/index.md)**: 了解为什么我们需要"节点"和"事件"。
