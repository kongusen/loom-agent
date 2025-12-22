# 工具系统指南

工具是 Agent 与外部世界交互的主要方式。Loom 将 Python 函数转换为 LLM 能够理解并调用的工具 Schema。

## 1. 定义工具

`@tool` 装饰器是定义工具的标准方式。

### 基础工具
```python
from loom.builtin import tool

@tool
async def add(a: int, b: int) -> int:
    """计算两个数字的和。"""
    return a + b
```

### 复杂参数 (Pydantic)
Loom 原生支持复杂类型。

```python
from typing import List

@tool
async def send_email(recipients: List[str], subject: str, body: str):
    """
    发送电子邮件给多个收件人。
    
    Args:
        recipients: 邮箱地址列表
        subject: 邮件主题
        body: 纯文本正文
    """
    # 实现代码...
```

## 2. 最佳实践

### 类型提示是必须的
工具生成器使用类型提示 (Type Hints) 来构建 JSON schema。
- ✅ `def func(x: int)`
- ❌ `def func(x)` -> 逻辑会失败或生成 "any" 类型，这会混淆 LLM。

### Docstrings 至关重要
LLM 读取 docstring 来理解：
1. **What**: 工具实际上做了什么（摘要）。
2. **When**: 何时使用它。
3. **What**: 每个参数的含义（Args 部分）。

**格式**: 推荐使用 Google 风格或 NumPy 风格的 docstrings。

## 3. 并发控制
工具由 `RecursiveEngine` 异步执行。
如果您传递 `RunnableConfig(max_concurrency=N)`，引擎将限制并行执行的数量。

```python
agent.invoke("...", config={"max_concurrency": 5})
```
