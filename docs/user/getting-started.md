# Getting Started with Loom Agent

快速上手指南 - 5分钟开始使用Loom Agent

---

## 安装

### 基础安装

```bash
pip install loom-agent
```

### 安装特定功能

```bash
# OpenAI支持
pip install loom-agent[openai]

# Anthropic支持
pip install loom-agent[anthropic]

# 所有功能
pip install loom-agent[all]
```

### 要求

- Python 3.11+
- pip或poetry

---

## 第一个Agent

### 使用MockLLM（无需API密钥）

```python
from loom import agent
from loom.builtin.llms import MockLLM
import asyncio

async def main():
    # 创建一个简单的agent
    my_agent = agent(llm=MockLLM())

    # 运行agent
    result = await my_agent.run("Hello, Loom Agent!")
    print(result)

asyncio.run(main())
```

### 使用OpenAI

```python
from loom import agent
import asyncio

async def main():
    # 使用OpenAI GPT-4
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        api_key="sk-..."  # 或设置环境变量OPENAI_API_KEY
    )

    result = await my_agent.run("What is 2+2?")
    print(result)

asyncio.run(main())
```

### 使用环境变量

```bash
# 设置环境变量
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4"
```

```python
from loom import agent_from_env
import asyncio

async def main():
    # 自动从环境变量读取配置
    my_agent = agent_from_env()
    result = await my_agent.run("Hello!")
    print(result)

asyncio.run(main())
```

---

## 添加自定义工具

### 使用装饰器创建工具

```python
from loom import agent, tool
import asyncio

# 定义工具
@tool()
def add(a: int, b: int) -> int:
    """将两个数相加"""
    return a + b

@tool()
def multiply(a: int, b: int) -> int:
    """将两个数相乘"""
    return a * b

async def main():
    # 创建带工具的agent
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        api_key="sk-...",
        tools=[add(), multiply()]
    )

    result = await my_agent.run("计算(3 + 5) * 2")
    print(result)

asyncio.run(main())
```

---

## 使用Memory

### 会话记忆

```python
from loom import agent
from loom.builtin.memory import InMemoryMemory
import asyncio

async def main():
    # 创建带记忆的agent
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        api_key="sk-...",
        memory=InMemoryMemory()
    )

    # 第一次对话
    result1 = await my_agent.run("我叫张三")
    print(result1)

    # 第二次对话 - agent会记住之前的内容
    result2 = await my_agent.run("我叫什么名字？")
    print(result2)  # 应该回答"张三"

asyncio.run(main())
```

### 持久化记忆

```python
from loom import agent
from loom.builtin.memory import PersistentMemory
import asyncio

async def main():
    # 使用持久化内存（保存到文件）
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        api_key="sk-...",
        memory=PersistentMemory(storage_path="./agent_memory")
    )

    result = await my_agent.run("记住这个数字：42")
    print(result)

    # 重启程序后，记忆仍然存在

asyncio.run(main())
```

---

## RAG（检索增强生成）

### 基础RAG

```python
from loom import agent
from loom.builtin.retriever import InMemoryRetriever
from loom.core.retrieval import RAGPattern
import asyncio

async def main():
    # 创建检索器
    retriever = InMemoryRetriever()

    # 添加文档
    await retriever.add_documents([
        "Loom Agent是一个生产就绪的Python Agent框架。",
        "它提供企业级的可靠性和可观测性。",
        "支持多种LLM提供商，包括OpenAI和Anthropic。"
    ])

    # 创建RAG模式
    rag = RAGPattern(retriever=retriever)

    # 创建带RAG的agent
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        api_key="sk-...",
        rag_pattern=rag
    )

    result = await my_agent.run("Loom Agent支持哪些LLM？")
    print(result)

asyncio.run(main())
```

---

## 错误处理和重试

Loom Agent内置了强大的错误处理：

```python
from loom import agent
import asyncio

async def main():
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        api_key="sk-...",
        max_retries=3,              # 最多重试3次
        timeout=30.0,               # 30秒超时
        enable_circuit_breaker=True # 启用断路器
    )

    try:
        result = await my_agent.run("Hello!")
        print(result)
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
```

---

## 流式输出

```python
from loom import agent
import asyncio

async def main():
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        api_key="sk-..."
    )

    # 流式输出
    async for chunk in my_agent.stream("写一首诗"):
        print(chunk, end="", flush=True)
    print()  # 换行

asyncio.run(main())
```

---

## 配置选项

### 环境配置

```python
from loom import agent, AgentConfig

# 开发环境
dev_config = AgentConfig(
    max_iterations=10,
    timeout=10.0,
    enable_circuit_breaker=False
)

# 生产环境
prod_config = AgentConfig(
    max_iterations=50,
    timeout=30.0,
    enable_circuit_breaker=True,
    max_retries=3
)

my_agent = agent(
    provider="openai",
    model="gpt-4",
    config=prod_config
)
```

---

## 下一步

### 深入学习

- **完整教程**: [用户指南](user-guide.md)
- **API文档**: [API参考](api-reference.md)
- **示例代码**: [examples/](examples/)

### 常见用例

- [创建自定义工具](examples/custom-tools.md)
- [RAG模式详解](examples/rag-patterns.md)
- [生产环境配置](user-guide.md#生产环境配置)
- [错误处理最佳实践](user-guide.md#错误处理)

### 获取帮助

- **GitHub Issues**: https://github.com/kongusen/loom-agent/issues
- **用户指南**: [docs/user/user-guide.md](user-guide.md)
- **Email**: wanghaishan0210@gmail.com

---

## 快速参考

### 创建Agent的三种方式

```python
# 方式1: 直接指定provider和model
agent(provider="openai", model="gpt-4", api_key="sk-...")

# 方式2: 从环境变量
agent_from_env()

# 方式3: 使用LLM实例
from loom.builtin.llms import OpenAILLM
llm = OpenAILLM(model="gpt-4", api_key="sk-...")
agent(llm=llm)
```

### 常用配置

```python
agent(
    provider="openai",
    model="gpt-4",
    api_key="sk-...",
    temperature=0.7,          # 创造性
    max_iterations=50,        # 最大迭代次数
    max_retries=3,           # 重试次数
    timeout=30.0,            # 超时（秒）
    tools=[...],             # 工具列表
    memory=InMemoryMemory(), # 记忆
    rag_pattern=rag          # RAG模式
)
```

### 运行Agent

```python
# 异步运行
result = await my_agent.run("prompt")

# 流式输出
async for chunk in my_agent.stream("prompt"):
    print(chunk)

# 带回调
async def on_tool_call(tool_name, args):
    print(f"Calling {tool_name} with {args}")

result = await my_agent.run("prompt", callbacks={"on_tool_call": on_tool_call})
```

---

**准备好开始了？查看[完整用户指南](user-guide.md)了解更多高级功能！**
